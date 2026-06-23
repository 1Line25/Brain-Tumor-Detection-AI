from __future__ import annotations

from pathlib import Path
from typing import Any

import cv2
import numpy as np
from PIL import Image

from app.core.config import get_settings


class GradCAMService:
    """
    Service tạo ảnh Grad-CAM cho ảnh MRI.

    File này chỉ tạo ảnh PNG dạng bytes. Việc lưu ảnh xuống storage
    được tách riêng cho StorageService xử lý.
    """

    def __init__(self) -> None:
        settings = get_settings()

        # Notebook train của dự án dùng IMG_SIZE = (240, 240).
        self.image_size = settings.model_input_size

        # Đã kiểm tra trực tiếp best_cnn_model.h5:
        # Conv2D cuối cùng là conv2d_13.
        self.last_conv_layer_name = settings.gradcam_last_conv_layer_name

    def generate(
        self,
        *,
        model: Any,
        image_path: str | Path,
        class_index: int,
    ) -> bytes:
        """
        Tạo Grad-CAM overlay trên ảnh MRI gốc.

        TensorFlow được import trong hàm để backend không khởi động nặng
        khi chỉ chạy migration hoặc API không cần inference.
        """

        import tensorflow as tf

        preprocessed_image = self._preprocess_image(image_path)
        target_layer = self._get_target_conv_layer(model, tf)

        grad_model = tf.keras.models.Model(
            inputs=model.inputs,
            outputs=[
                target_layer.output,
                model.output,
            ],
        )

        with tf.GradientTape() as tape:
            conv_outputs, predictions = grad_model(preprocessed_image)
            class_score = predictions[:, class_index]

        grads = tape.gradient(class_score, conv_outputs)

        if grads is None:
            raise ValueError("Cannot compute gradients for Grad-CAM")

        # Lấy trọng số của từng feature map bằng global average pooling.
        pooled_grads = tf.reduce_mean(grads, axis=(0, 1, 2))
        conv_outputs = conv_outputs[0]

        # Nhân feature map với trọng số để tạo heatmap.
        heatmap = conv_outputs @ pooled_grads[..., tf.newaxis]
        heatmap = tf.squeeze(heatmap)

        # Chỉ giữ vùng đóng góp dương cho class dự đoán.
        heatmap = tf.maximum(heatmap, 0)

        # Normalize về 0..1 để tô màu ổn định.
        max_value = tf.reduce_max(heatmap)

        # max_value là Tensor scalar; chuyển sang float để tránh lỗi dùng Tensor
        # trực tiếp trong điều kiện Python.
        if float(max_value.numpy()) == 0.0:
            heatmap = tf.zeros_like(heatmap)
        else:
            heatmap = heatmap / max_value

        return self._overlay_heatmap(
            image_path=image_path,
            heatmap=heatmap.numpy(),
        )

    def find_last_conv_layer_name(self, model: Any) -> str:
        """
        Tìm Conv2D layer cuối cùng trong model.

        Đây là fallback nếu config bị sai tên layer.
        Với best_cnn_model.h5 hiện tại, kết quả mong đợi là conv2d_13.
        """

        import tensorflow as tf

        for layer in reversed(model.layers):
            if isinstance(layer, tf.keras.layers.Conv2D):
                return layer.name

            # Hỗ trợ nested model nếu sau này đổi sang transfer learning.
            if hasattr(layer, "layers"):
                for sublayer in reversed(layer.layers):
                    if isinstance(sublayer, tf.keras.layers.Conv2D):
                        return sublayer.name

        raise ValueError("No Conv2D layer found in model")

    def _get_target_conv_layer(self, model: Any, tf: Any) -> Any:
        """
        Lấy layer Conv2D dùng cho Grad-CAM.

        Ưu tiên conv2d_13; nếu không tồn tại thì tự tìm Conv2D cuối cùng.
        """

        try:
            return model.get_layer(self.last_conv_layer_name)
        except ValueError:
            fallback_layer_name = self.find_last_conv_layer_name(model)
            self.last_conv_layer_name = fallback_layer_name
            return model.get_layer(fallback_layer_name)

    def _preprocess_image(self, image_path: str | Path) -> np.ndarray:
        """
        Tiền xử lý ảnh giống lúc train:
        resize 240x240, RGB, scale pixel 0..1, thêm batch dimension.
        """

        image = Image.open(image_path).convert("RGB")
        image = image.resize(self.image_size)

        image_array = np.asarray(image, dtype=np.float32) / 255.0

        return np.expand_dims(image_array, axis=0)

    def _overlay_heatmap(
        self,
        *,
        image_path: str | Path,
        heatmap: np.ndarray,
        alpha: float = 0.4,
    ) -> bytes:
        """
        Overlay heatmap lên ảnh MRI gốc và trả về PNG bytes.
        """

        original_image = Image.open(image_path).convert("RGB")
        original_size = original_image.size

        heatmap_resized = cv2.resize(heatmap, original_size)
        heatmap_uint8 = np.uint8(255 * heatmap_resized)

        # COLORMAP_JET là kiểu hiển thị Grad-CAM phổ biến, dễ nhìn khi demo.
        colored_heatmap = cv2.applyColorMap(heatmap_uint8, cv2.COLORMAP_JET)
        colored_heatmap = cv2.cvtColor(colored_heatmap, cv2.COLOR_BGR2RGB)

        original_array = np.asarray(original_image, dtype=np.uint8)

        overlay = cv2.addWeighted(
            original_array,
            1 - alpha,
            colored_heatmap,
            alpha,
            0,
        )

        success, encoded_image = cv2.imencode(
            ".png",
            cv2.cvtColor(overlay, cv2.COLOR_RGB2BGR),
        )

        if not success:
            raise ValueError("Failed to encode Grad-CAM image")

        return encoded_image.tobytes()
