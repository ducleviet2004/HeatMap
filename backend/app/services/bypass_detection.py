"""So sánh ordered road-edge sequence và xác định bypass theo BR-01, BR-02."""

from collections.abc import Sequence

from app.core.config import Settings
from app.schemas.bypass import (
    BypassReason,
    BypassSegmentResult,
    EdgeSequenceComparisonResult,
    PlannedRoadEdge,
)


class BypassDetectionService:
    """Tìm planned edge bị thiếu và kiểm tra các điều kiện xác nhận bypass."""

    def __init__(
        self,
        *,
        minimum_match_confidence: float,
        minimum_missing_run_m: float,
        corridor_tolerance_m: float,
        algorithm_version: str,
        threshold_config_version: str,
    ) -> None:
        if not 0 <= minimum_match_confidence <= 1:
            raise ValueError("minimum_match_confidence must be between 0 and 1")
        if minimum_missing_run_m <= 0:
            raise ValueError("minimum_missing_run_m must be positive")
        if corridor_tolerance_m <= 0:
            raise ValueError("corridor_tolerance_m must be positive")

        self.minimum_match_confidence = minimum_match_confidence
        self.minimum_missing_run_m = minimum_missing_run_m
        self.corridor_tolerance_m = corridor_tolerance_m
        self.algorithm_version = algorithm_version
        self.threshold_config_version = threshold_config_version

    @classmethod
    def from_settings(cls, settings: Settings) -> "BypassDetectionService":
        """Lấy threshold và version từ cấu hình ứng dụng."""
        return cls(
            minimum_match_confidence=settings.bypass_min_match_confidence,
            minimum_missing_run_m=settings.bypass_min_missing_run_m,
            corridor_tolerance_m=settings.bypass_corridor_tolerance_m,
            algorithm_version=settings.algorithm_version,
            threshold_config_version=settings.threshold_config_version,
        )

    def compare(
        self,
        planned_edges: Sequence[PlannedRoadEdge],
        actual_edge_ids: Sequence[str],
        *,
        planned_routing_data_version: str,
        actual_routing_data_version: str,
        map_match_confidence: float,
    ) -> EdgeSequenceComparisonResult:
        """So sánh hai edge sequence và đánh giá từng missing run."""
        if not 0 <= map_match_confidence <= 1:
            raise ValueError("map_match_confidence must be between 0 and 1")

        planned_edge_ids = [edge.edge_id for edge in planned_edges]
        matched_indices = self._matched_planned_indices(planned_edge_ids, actual_edge_ids)
        missing_runs = self._contiguous_missing_runs(len(planned_edges), matched_indices)

        bypass_segments = [
            self._evaluate_missing_run(
                planned_edges[start_index : end_index + 1],
                start_index=start_index,
                end_index=end_index,
                versions_match=(planned_routing_data_version == actual_routing_data_version),
                map_match_confidence=map_match_confidence,
            )
            for start_index, end_index in missing_runs
        ]

        return EdgeSequenceComparisonResult(
            missing_edge_count=sum(len(segment.planned_edge_ids) for segment in bypass_segments),
            confirmed_bypass_count=sum(segment.confirmed for segment in bypass_segments),
            bypass_segments=bypass_segments,
            planned_routing_data_version=planned_routing_data_version,
            actual_routing_data_version=actual_routing_data_version,
            map_match_confidence=map_match_confidence,
            algorithm_version=self.algorithm_version,
            threshold_config_version=self.threshold_config_version,
        )

    def _evaluate_missing_run(
        self,
        edges: Sequence[PlannedRoadEdge],
        *,
        start_index: int,
        end_index: int,
        versions_match: bool,
        map_match_confidence: float,
    ) -> BypassSegmentResult:
        """Chạy lần lượt các cổng an toàn BR-02 cho một missing run."""
        missing_length_m = sum(edge.length_m for edge in edges)
        average_deviation_m = self._weighted_corridor_distance(edges)

        # Thứ tự kiểm tra giúp reason_code luôn ổn định và dễ giải thích.
        if not versions_match:
            reason = BypassReason.ROUTING_VERSION_MISMATCH
        elif map_match_confidence < self.minimum_match_confidence:
            reason = BypassReason.LOW_MATCH_CONFIDENCE
        elif missing_length_m < self.minimum_missing_run_m:
            reason = BypassReason.BELOW_MINIMUM_LENGTH
        elif all(not edge.observed for edge in edges):
            reason = BypassReason.GPS_GAP
        elif average_deviation_m is None:
            reason = BypassReason.CORRIDOR_DATA_MISSING
        elif average_deviation_m <= self.corridor_tolerance_m:
            # Edge ID khác nhưng geometry vẫn cùng hành lang thường là GPS drift hoặc graph khác.
            reason = BypassReason.SAME_CORRIDOR
        else:
            reason = BypassReason.CONFIRMED_BYPASS

        return BypassSegmentResult(
            start_planned_index=start_index,
            end_planned_index=end_index,
            planned_edge_ids=[edge.edge_id for edge in edges],
            missing_length_m=missing_length_m,
            average_deviation_distance_m=average_deviation_m,
            confirmed=reason == BypassReason.CONFIRMED_BYPASS,
            reason_code=reason,
        )

    @staticmethod
    def _weighted_corridor_distance(edges: Sequence[PlannedRoadEdge]) -> float | None:
        """Tính distance trung bình theo chiều dài edge; thiếu dữ liệu thì không tự xác nhận."""
        if any(edge.corridor_distance_m is None for edge in edges):
            return None
        total_length = sum(edge.length_m for edge in edges)
        weighted_distance = sum(
            edge.length_m * edge.corridor_distance_m
            for edge in edges
            if edge.corridor_distance_m is not None
        )
        return weighted_distance / total_length

    @staticmethod
    def _matched_planned_indices(
        planned_edge_ids: Sequence[str],
        actual_edge_ids: Sequence[str],
    ) -> set[int]:
        """Dùng LCS để match đúng thứ tự, kể cả khi route có edge lặp."""
        planned_count = len(planned_edge_ids)
        actual_count = len(actual_edge_ids)
        lcs_lengths = [[0 for _ in range(actual_count + 1)] for _ in range(planned_count + 1)]

        for planned_index in range(planned_count - 1, -1, -1):
            for actual_index in range(actual_count - 1, -1, -1):
                if planned_edge_ids[planned_index] == actual_edge_ids[actual_index]:
                    lcs_lengths[planned_index][actual_index] = (
                        1 + lcs_lengths[planned_index + 1][actual_index + 1]
                    )
                else:
                    lcs_lengths[planned_index][actual_index] = max(
                        lcs_lengths[planned_index + 1][actual_index],
                        lcs_lengths[planned_index][actual_index + 1],
                    )

        matched_indices: set[int] = set()
        planned_index = 0
        actual_index = 0
        while planned_index < planned_count and actual_index < actual_count:
            if planned_edge_ids[planned_index] == actual_edge_ids[actual_index]:
                matched_indices.add(planned_index)
                planned_index += 1
                actual_index += 1
            elif (
                lcs_lengths[planned_index + 1][actual_index]
                >= lcs_lengths[planned_index][actual_index + 1]
            ):
                planned_index += 1
            else:
                actual_index += 1

        return matched_indices

    @staticmethod
    def _contiguous_missing_runs(
        planned_edge_count: int,
        matched_indices: set[int],
    ) -> list[tuple[int, int]]:
        """Gom các planned edge bị thiếu liền nhau thành từng bypass candidate."""
        missing_indices = [
            index for index in range(planned_edge_count) if index not in matched_indices
        ]
        if not missing_indices:
            return []

        runs: list[tuple[int, int]] = []
        run_start = missing_indices[0]
        run_end = run_start
        for index in missing_indices[1:]:
            if index == run_end + 1:
                run_end = index
                continue
            runs.append((run_start, run_end))
            run_start = index
            run_end = index
        runs.append((run_start, run_end))
        return runs
