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

        # EfficientNetB0 nằm dưới dạng nested model; mặc định dùng top_conv.
        # Nếu tên layer thay đổi, service sẽ tự tìm Conv2D cuối cùng.
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
        owner_model, target_layer, target_layer_idx = self._find_target_conv_layer(
            model,
            tf,
        )
        feature_model = tf.keras.models.Model(
            owner_model.inputs,
            target_layer.output,
        )
        classifier_model = self._build_classifier_after_target(
            root_model=model,
            owner_model=owner_model,
            target_layer=target_layer,
            target_layer_idx=target_layer_idx,
            tf=tf,
        )

        with tf.GradientTape() as tape:
            conv_outputs = feature_model(preprocessed_image, training=False)
            tape.watch(conv_outputs)
            predictions = classifier_model(conv_outputs, training=False)
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
        Với EfficientNetB0, kết quả mong đợi thường là top_conv.
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

    def _find_target_conv_layer(
        self,
        model: Any,
        tf: Any,
    ) -> tuple[Any, Any, int]:
        """
        Trả về model sở hữu layer, layer Conv2D đích và vị trí của layer.

        EfficientNetB0 là một model lồng bên trong model phân loại, vì vậy gọi
        root_model.get_layer("top_conv") trực tiếp sẽ không tìm thấy layer.
        """

        configured = self._find_named_conv_layer(
            model,
            self.last_conv_layer_name,
            tf,
        )
        if configured is not None:
            return configured

        fallback = self._find_last_conv_layer(model, tf)
        if fallback is None:
            raise ValueError("No Conv2D layer found in model")

        self.last_conv_layer_name = fallback[1].name
        return fallback

    def _find_named_conv_layer(
        self,
        model: Any,
        layer_name: str,
        tf: Any,
    ) -> tuple[Any, Any, int] | None:
        """Tìm một Conv2D theo tên trong cả model gốc và nested models."""

        for index, layer in enumerate(model.layers):
            if (
                layer.name == layer_name
                and isinstance(layer, tf.keras.layers.Conv2D)
            ):
                return model, layer, index

            if isinstance(layer, tf.keras.Model):
                nested_result = self._find_named_conv_layer(
                    layer,
                    layer_name,
                    tf,
                )
                if nested_result is not None:
                    return nested_result

        return None

    def _find_last_conv_layer(
        self,
        model: Any,
        tf: Any,
    ) -> tuple[Any, Any, int] | None:
        """Tìm Conv2D cuối cùng theo thứ tự ngược, hỗ trợ nested models."""

        for index in range(len(model.layers) - 1, -1, -1):
            layer = model.layers[index]

            if isinstance(layer, tf.keras.Model):
                nested_result = self._find_last_conv_layer(layer, tf)
                if nested_result is not None:
                    return nested_result

            if isinstance(layer, tf.keras.layers.Conv2D):
                return model, layer, index

        return None

    def _build_classifier_after_target(
        self,
        *,
        root_model: Any,
        owner_model: Any,
        target_layer: Any,
        target_layer_idx: int,
        tf: Any,
    ) -> Any:
        """
        Dựng phần model từ output Conv2D đích đến output phân loại.

        Với EfficientNetB0, phần này gồm các layer còn lại trong backbone rồi
        đến GlobalAveragePooling/Dense head của root model.
        """

        classifier_input = tf.keras.Input(
            shape=target_layer.output.shape[1:],
        )
        x = classifier_input

        for layer in owner_model.layers[target_layer_idx + 1:]:
            if not isinstance(layer, tf.keras.layers.InputLayer):
                x = layer(x)

        if owner_model is not root_model:
            owner_index = next(
                (
                    index
                    for index, layer in enumerate(root_model.layers)
                    if layer is owner_model
                ),
                None,
            )
            if owner_index is None:
                raise ValueError(
                    "Nested model containing Grad-CAM layer is not attached "
                    "directly to the root model"
                )

            for layer in root_model.layers[owner_index + 1:]:
                if not isinstance(layer, tf.keras.layers.InputLayer):
                    x = layer(x)

        return tf.keras.models.Model(classifier_input, x)

    def _preprocess_image(self, image_path: str | Path) -> np.ndarray:
        """
        Tiền xử lý ảnh giống lúc train:
        resize 240x240, RGB, giữ pixel 0..255, thêm batch dimension.
        """

        with Image.open(image_path) as source_image:
            image = source_image.convert("RGB").resize(self.image_size)
            image_array = np.asarray(image, dtype=np.float32)

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

        with Image.open(image_path) as source_image:
            original_image = source_image.convert("RGB")
            original_size = original_image.size
            original_array = np.asarray(original_image, dtype=np.uint8)

        heatmap_resized = cv2.resize(heatmap, original_size)
        heatmap_uint8 = np.uint8(255 * heatmap_resized)

        # COLORMAP_JET là kiểu hiển thị Grad-CAM phổ biến, dễ nhìn khi demo.
        colored_heatmap = cv2.applyColorMap(heatmap_uint8, cv2.COLORMAP_JET)
        colored_heatmap = cv2.cvtColor(colored_heatmap, cv2.COLOR_BGR2RGB)

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
