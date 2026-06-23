from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from threading import Lock

import numpy as np
from PIL import Image

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
    Service chạy inference với best_cnn_model.h5.

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
        3. Gọi model.predict().
        4. Chuyển output thành nhãn, confidence và probabilities.
        """

        model = self.get_model()
        input_tensor = self._preprocess_image(image_path)

        # verbose=0 giúp log backend gọn hơn khi có nhiều request.
        raw_prediction = model.predict(input_tensor, verbose=0)

        return self._parse_prediction(raw_prediction)

    def get_model(self):
        """
        Load model từ best_cnn_model.h5 nếu chưa load.

        TensorFlow được import trong hàm để các tác vụ không cần inference
        như migration/database check không bị khởi động nặng.
        """

        if self.__class__._model is not None:
            return self.__class__._model

        with self.__class__._model_lock:
            if self.__class__._model is not None:
                return self.__class__._model

            if not self.model_path.exists():
                raise FileNotFoundError(f"Model file not found: {self.model_path}")

            from tensorflow.keras.models import load_model

            self.__class__._model = load_model(self.model_path)

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
        - scale pixel từ 0..255 về 0..1,
        - thêm batch dimension: (H, W, C) -> (1, H, W, C).
        """

        image = Image.open(image_path).convert("RGB")
        image = image.resize(self.image_size)

        image_array = np.asarray(image, dtype=np.float32) / 255.0

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
