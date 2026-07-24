"""Phan loai GPS gap va tach trace ma khong tao GPS point gia."""

from dataclasses import dataclass

from app.core.config import Settings
from app.schemas.gps import GpsEventCreate, GpsGapReason, GpsGapRecord


@dataclass(frozen=True)
class GpsGapAnalysis:
    """Cac trace segment doc lap va GPS gap tim thay giua chung."""

    segments: list[list[GpsEventCreate]]
    gaps: list[GpsGapRecord]


class GpsGapService:
    """Ap dung GPS gap rule <15s, 15-120s va >120s theo BR-08."""

    def __init__(self, *, medium_gap_seconds: float = 15, split_gap_seconds: float = 120) -> None:
        if medium_gap_seconds <= 0:
            raise ValueError("medium_gap_seconds must be positive")
        if split_gap_seconds <= medium_gap_seconds:
            raise ValueError("split_gap_seconds must be greater than medium_gap_seconds")
        self.medium_gap_seconds = medium_gap_seconds
        self.split_gap_seconds = split_gap_seconds

    @classmethod
    def from_settings(cls, settings: Settings) -> "GpsGapService":
        """Tao service tu threshold duoc khai bao trong Settings."""
        return cls(
            medium_gap_seconds=settings.gps_medium_gap_seconds,
            split_gap_seconds=settings.gps_split_gap_seconds,
        )

    def analyze(self, events: list[GpsEventCreate]) -> GpsGapAnalysis:
        """Giu nguyen input order; chi split segment khi gap lon hon 120 giay."""
        if not events:
            return GpsGapAnalysis(segments=[], gaps=[])

        segments: list[list[GpsEventCreate]] = [[events[0]]]
        gaps: list[GpsGapRecord] = []

        for previous, current in zip(events, events[1:], strict=False):
            duration_seconds = (current.recorded_at - previous.recorded_at).total_seconds()
            if duration_seconds <= 0:
                # Khong sort hoac sua raw GPS; OSRM se bo timestamps khong tang.
                segments[-1].append(current)
                continue

            reason, should_split = self._classify(duration_seconds)
            if reason is not None:
                gaps.append(
                    GpsGapRecord(
                        before_sequence_no=previous.sequence_no,
                        after_sequence_no=current.sequence_no,
                        duration_seconds=duration_seconds,
                        reason_code=reason,
                        split_segment=should_split,
                    )
                )

            if should_split:
                segments.append([current])
            else:
                segments[-1].append(current)

        return GpsGapAnalysis(segments=segments, gaps=gaps)

    def _classify(self, duration_seconds: float) -> tuple[GpsGapReason | None, bool]:
        """Tra ve reason_code va quyet dinh co split segment hay khong."""
        # Dung 15 giay thuoc medium gap; dung 120 giay van chua split.
        if duration_seconds < self.medium_gap_seconds:
            return None, False
        if duration_seconds <= self.split_gap_seconds:
            return GpsGapReason.MEDIUM_GAP, False
        return GpsGapReason.LONG_GAP_SPLIT, True
