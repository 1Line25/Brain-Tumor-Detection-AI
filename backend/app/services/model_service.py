from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from time import monotonic

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


@dataclass(frozen=True)
class ModelHealthStatus:
    """Kết quả kiểm tra model dùng cho readiness/health check."""

    ready: bool
    detail: str
    model_name: str | None = None
    output_classes: int | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "ready": self.ready,
            "detail": self.detail,
            "model_name": self.model_name,
            "output_classes": self.output_classes,
        }


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
    _health_lock = Lock()
    _health_status: ModelHealthStatus | None = None
    _health_checked_at: float = 0.0
    _failed_health_retry_seconds = 30.0

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

        try:
            # Gọi trực tiếp nhẹ hơn model.predict() cho từng ảnh đơn lẻ.
            raw_prediction = model(input_tensor, training=False)
            result = self._parse_prediction(raw_prediction)
        except Exception:
            self._mark_unhealthy("runtime_inference_failed")
            raise

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

    def check_health(self, *, force: bool = False) -> ModelHealthStatus:
        """
        Xác nhận model thực sự dùng được, không chỉ kiểm tra file tồn tại.

        Lần kiểm tra đầu tiên sẽ:
        - load file model,
        - kiểm tra input/output,
        - chạy một inference warm-up bằng tensor rỗng,
        - xác nhận output có đủ nhãn và không chứa NaN/Infinity.

        Kết quả thành công được cache. Kết quả lỗi được thử lại sau một khoảng
        ngắn để hệ thống có thể tự phục hồi nếu model được mount lại.
        """

        cached = self.__class__._health_status
        elapsed = monotonic() - self.__class__._health_checked_at

        if not force and cached is not None:
            if cached.ready:
                return cached
            if elapsed < self.__class__._failed_health_retry_seconds:
                return cached

        with self.__class__._health_lock:
            cached = self.__class__._health_status
            elapsed = monotonic() - self.__class__._health_checked_at

            if not force and cached is not None:
                if cached.ready:
                    return cached
                if elapsed < self.__class__._failed_health_retry_seconds:
                    return cached

            status = self._run_health_check()
            self.__class__._health_status = status
            self.__class__._health_checked_at = monotonic()
            return status

    def _run_health_check(self) -> ModelHealthStatus:
        """Thực hiện load và warm-up model một lần."""

        if not self.model_path.is_file():
            logger.error(
                "Model health check thất bại: không tìm thấy file {}.",
                self.model_path,
            )
            return ModelHealthStatus(
                ready=False,
                detail="model_file_missing",
            )

        try:
            model = self.get_model()
            self._validate_model_input_shape(model)

            warmup_tensor = np.zeros(
                (
                    1,
                    self.image_size[0],
                    self.image_size[1],
                    3,
                ),
                dtype=np.float32,
            )
            raw_prediction = model(warmup_tensor, training=False)
            probabilities = np.asarray(raw_prediction).reshape(-1)

            if len(probabilities) != len(self.labels):
                raise ValueError(
                    "Model output classes do not match configured labels"
                )

            if not np.all(np.isfinite(probabilities)):
                raise ValueError("Model warm-up output contains NaN or Infinity")

            if np.any(probabilities < 0) or np.any(probabilities > 1):
                raise ValueError("Model output is not a probability distribution")

            if not np.isclose(
                float(np.sum(probabilities)),
                1.0,
                atol=1e-3,
            ):
                raise ValueError("Model output probabilities do not sum to 1")

            # Dùng parser thật để kiểm tra label mapping và enum của runtime.
            self._parse_prediction(raw_prediction)

            model_name = getattr(model, "name", type(model).__name__)
            logger.info(
                "Model health check thành công | model={} classes={}.",
                model_name,
                len(probabilities),
            )
            return ModelHealthStatus(
                ready=True,
                detail="ready",
                model_name=str(model_name),
                output_classes=len(probabilities),
            )
        except Exception:
            logger.exception(
                "Model health check thất bại khi load hoặc warm-up model."
            )
            return ModelHealthStatus(
                ready=False,
                detail="model_load_or_warmup_failed",
            )

    def _mark_unhealthy(self, detail: str) -> None:
        """Đánh dấu model lỗi nếu inference thật phát sinh exception."""

        with self.__class__._health_lock:
            self.__class__._health_status = ModelHealthStatus(
                ready=False,
                detail=detail,
            )
            self.__class__._health_checked_at = monotonic()

    def _validate_model_input_shape(self, model) -> None:
        """Kiểm tra kích thước input model tương thích cấu hình backend."""

        input_shape = getattr(model, "input_shape", None)
        if isinstance(input_shape, list):
            if len(input_shape) != 1:
                raise ValueError("Model must have exactly one input")
            input_shape = input_shape[0]

        if input_shape is None or len(input_shape) != 4:
            raise ValueError("Model input must have shape (batch, height, width, 3)")

        expected = (
            self.image_size[0],
            self.image_size[1],
            3,
        )
        actual = tuple(input_shape[1:])

        for actual_value, expected_value in zip(actual, expected):
            if actual_value is not None and int(actual_value) != expected_value:
                raise ValueError(
                    f"Model input shape {actual} does not match {expected}"
                )

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
