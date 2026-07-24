"""Loc GPS point bi nhieu nhung luon giu nguyen raw GPS data."""

from collections.abc import Iterable
from typing import Protocol, TypeVar

from app.core.config import Settings
from app.schemas.gps import GpsCleaningResult, GpsRejectionReason


class GpsMeasurement(Protocol):
    """GPS point chi can accuracy va speed de su dung cleaning filter."""

    @property
    def accuracy_m(self) -> float | None: ...

    @property
    def speed_kmh(self) -> float | None: ...


GpsMeasurementT = TypeVar("GpsMeasurementT", bound=GpsMeasurement)


class GpsCleaningService:
    """Kiem tra GPS point co dat threshold accuracy va speed hay khong."""

    def __init__(
        self,
        *,
        max_accuracy_m: float,
        max_speed_kmh: float,
        threshold_config_version: str,
    ) -> None:
        """Khoi tao cleaning filter va validate cac threshold co ban."""
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
        """Lay threshold tu Settings de co the thay doi bang environment variable."""
        return cls(
            max_accuracy_m=settings.gps_max_accuracy_m,
            max_speed_kmh=settings.gps_max_speed_kmh,
            threshold_config_version=settings.threshold_config_version,
        )

    def evaluate(self, event: GpsMeasurement) -> GpsCleaningResult:
        """Kiem tra mot GPS point va tra ve reason neu point bi reject."""
        reasons: list[GpsRejectionReason] = []

        # Dung dau > nen gia tri bang threshold van duoc accept.
        # Neu accuracy hoac speed la None thi chua du du lieu de reject point.
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
        """Tra ve point dat chuan ma khong sua hoac xoa raw GPS data."""
        return [event for event in events if self.evaluate(event).accepted]
