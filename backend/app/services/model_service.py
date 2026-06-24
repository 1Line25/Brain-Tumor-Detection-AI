from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from threading import Lock

import numpy as np
from PIL import Image
from loguru import logger

from app.core.config import get_settings
from app.models.prediction import TumorClass


@dataclass(frozen=True)
class ModelPrediction:
    """
    Kết quả dự đoán trả về từ model.

    Dùng dataclass để tầng inference không phụ thuộc trực tiếp vào Pydantic.
    """

    predicted_class: TumorClass
    confidence: float
    probabilities: dict[str, float]


class ModelService:
    """
    Service chạy inference với EfficientNetB0 trong best_tl_model.h5.

    Tối ưu:
    - Lazy-load model: chỉ load khi request đầu tiên cần dự đoán.
    - Cache model trong memory để không load lại file .h5 mỗi request.
    - Dùng Lock để tránh nhiều request cùng lúc load model trùng nhau.
    """

    _model = None
    _model_lock = Lock()

    def __init__(self) -> None:
        settings = get_settings()

        self.model_path = settings.model_path
        self.image_size = settings.model_input_size
        self.labels = settings.model_labels

    def predict(self, image_path: str | Path) -> ModelPrediction:
        """
        Chạy dự đoán trên một ảnh MRI.

        Quy trình:
        1. Load model nếu chưa có trong memory.
        2. Tiền xử lý ảnh giống lúc train.
        3. Gọi model trực tiếp ở chế độ inference.
        4. Chuyển output thành nhãn, confidence và probabilities.
        """

        model = self.get_model()
        input_tensor = self._preprocess_image(image_path)
        logger.info("Bắt đầu chạy inference cho ảnh MRI.")

        # Gọi trực tiếp nhẹ hơn model.predict() cho từng ảnh đơn lẻ.
        raw_prediction = model(input_tensor, training=False)

        result = self._parse_prediction(raw_prediction)
        logger.info(
            "Inference hoàn tất | nhãn={} độ_tin_cậy={:.4f}",
            result.predicted_class.value,
            result.confidence,
        )
        return result

    def get_model(self):
        """
        Load model EfficientNetB0 từ best_tl_model.h5 nếu chưa load.

        TensorFlow được import trong hàm để các tác vụ không cần inference
        như migration/database check không bị khởi động nặng.
        """

        if self.__class__._model is not None:
            return self.__class__._model

        with self.__class__._model_lock:
            if self.__class__._model is not None:
                return self.__class__._model

            if not self.model_path.exists():
                logger.error("Không tìm thấy file model tại {}.", self.model_path)
                raise FileNotFoundError(f"Không tìm thấy file model: {self.model_path}")

            from tensorflow.keras.models import load_model

            logger.info("Đang nạp model inference từ {}.", self.model_path)
            # Backend chỉ inference nên không cần khôi phục optimizer/loss.
            # compile=False cũng tránh lỗi khi model được lưu bởi phiên bản Keras khác.
            self.__class__._model = load_model(self.model_path, compile=False)
            logger.info("Đã nạp model inference thành công.")

        return self.__class__._model

    def _get_model(self):
        """
        Alias giữ tương thích với code cũ.

        Code mới nên dùng get_model() để tránh gọi private method từ service khác.
        """

        return self.get_model()

    def _preprocess_image(self, image_path: str | Path) -> np.ndarray:
        """
        Tiền xử lý ảnh MRI trước khi đưa vào model.

        Khớp notebook train:
        - resize về 240x240,
        - chuyển RGB,
        - giữ pixel ở thang 0..255 vì EfficientNetB0 có preprocessing nội bộ,
        - thêm batch dimension: (H, W, C) -> (1, H, W, C).
        """

        with Image.open(image_path) as source_image:
            image = source_image.convert("RGB").resize(self.image_size)
            image_array = np.asarray(image, dtype=np.float32)

        # EfficientNetB0 của Keras có preprocessing nội bộ và nhận float 0..255.
        return np.expand_dims(image_array, axis=0)

    def _parse_prediction(self, raw_prediction) -> ModelPrediction:
        """
        Chuyển output model thành kết quả dễ dùng cho backend.
        """

        probabilities_array = np.asarray(raw_prediction).reshape(-1)

        if len(probabilities_array) != len(self.labels):
            raise ValueError(
                "Model output size does not match configured labels. "
                f"Output size={len(probabilities_array)}, labels={len(self.labels)}"
            )

        predicted_index = int(np.argmax(probabilities_array))
        predicted_label = self.labels[predicted_index]

        probabilities = {
            label: float(probabilities_array[index])
            for index, label in enumerate(self.labels)
        }

        return ModelPrediction(
            predicted_class=TumorClass(predicted_label),
            confidence=float(probabilities_array[predicted_index]),
            probabilities=probabilities,
        )
