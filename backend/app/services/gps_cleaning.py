"""Lọc các điểm GPS nhiễu nhưng luôn giữ nguyên dữ liệu GPS gốc."""

from collections.abc import Iterable
from typing import Protocol, TypeVar

from app.core.config import Settings
from app.schemas.gps import GpsCleaningResult, GpsRejectionReason


class GpsMeasurement(Protocol):
    """Một điểm GPS chỉ cần có accuracy và speed để sử dụng bộ lọc này."""

    @property
    def accuracy_m(self) -> float | None: ...

    @property
    def speed_kmh(self) -> float | None: ...


GpsMeasurementT = TypeVar("GpsMeasurementT", bound=GpsMeasurement)


class GpsCleaningService:
    """Kiểm tra một điểm GPS có đạt ngưỡng accuracy và speed hay không."""

    def __init__(
        self,
        *,
        max_accuracy_m: float,
        max_speed_kmh: float,
        threshold_config_version: str,
    ) -> None:
        """Khởi tạo bộ lọc và kiểm tra các giá trị cấu hình cơ bản."""
        if max_accuracy_m <= 0:
            raise ValueError("max_accuracy_m must be positive")
        if max_speed_kmh <= 0:
            raise ValueError("max_speed_kmh must be positive")
        if not threshold_config_version.strip():
            raise ValueError("threshold_config_version must not be blank")

        self.max_accuracy_m = max_accuracy_m
        self.max_speed_kmh = max_speed_kmh
        self.threshold_config_version = threshold_config_version

    @classmethod
    def from_settings(cls, settings: Settings) -> "GpsCleaningService":
        """Lấy threshold từ Settings để có thể thay đổi bằng biến môi trường."""
        return cls(
            max_accuracy_m=settings.gps_max_accuracy_m,
            max_speed_kmh=settings.gps_max_speed_kmh,
            threshold_config_version=settings.threshold_config_version,
        )

    def evaluate(self, event: GpsMeasurement) -> GpsCleaningResult:
        """Kiểm tra một điểm GPS và trả về các lý do nếu điểm đó bị loại."""
        reasons: list[GpsRejectionReason] = []

        # Dùng dấu > nên giá trị đúng bằng threshold vẫn được chấp nhận.
        # Nếu accuracy hoặc speed là None thì chưa đủ thông tin để loại điểm.
        if event.accuracy_m is not None and event.accuracy_m > self.max_accuracy_m:
            reasons.append(GpsRejectionReason.POOR_ACCURACY)
        if event.speed_kmh is not None and event.speed_kmh > self.max_speed_kmh:
            reasons.append(GpsRejectionReason.EXCESSIVE_SPEED)

        return GpsCleaningResult(
            accepted=not reasons,
            reasons=tuple(reasons),
            threshold_config_version=self.threshold_config_version,
        )

    def filter_events(self, events: Iterable[GpsMeasurementT]) -> list[GpsMeasurementT]:
        """Trả về các điểm đạt chuẩn mà không sửa hoặc xóa dữ liệu GPS gốc."""
        return [event for event in events if self.evaluate(event).accepted]
