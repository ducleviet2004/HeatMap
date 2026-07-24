"""Unit tests & Precision/Recall Benchmark suite cho Task W4-B03 (Yêu cầu > 90%)."""

from typing import Any

import pytest

from app.core.config import Settings
from app.schemas.map_matching import MapMatchStatus
from app.services.gps_cleaning import GpsCleaningService
from app.services.map_matching import MapMatchingService
from tests.fixtures.labeled_test_set import LABELED_TEST_SET


class MockOsrmClient:
    """Mock OSRM Client giả lập phản hồi cho từng kịch bản kiểm định."""

    async def match_trace(
        self,
        coordinates: list[tuple[float, float]],
        timestamps: list[int] | None = None,
        radiuses: list[float] | None = None,
        overview: str = "full",
        geometries: str = "geojson",
    ) -> dict[str, Any] | None:
        # Báo NoMatch nếu bán kính quá nhỏ ở kịch bản Tunnel/Bridge (radiuses < 100m)
        is_tunnel_scenario = coordinates[0][0] == 106.7009 and len(coordinates) == 3
        if radiuses and radiuses[0] < 100.0 and is_tunnel_scenario:
            return {"code": "NoMatch", "message": "Could not match trace at small radius"}

        return {
            "code": "Ok",
            "matchings": [
                {
                    "confidence": 0.95,
                    "geometry": {
                        "type": "LineString",
                        "coordinates": [list(c) for c in coordinates],
                    },
                    "legs": [
                        {"annotation": {"nodes": [100, 200]}}
                        for _ in range(max(1, len(coordinates) - 1))
                    ],
                }
            ],
            "tracepoints": [{"location": list(c)} for c in coordinates],
        }


@pytest.mark.asyncio
async def test_gps_cleaning_precision_recall_benchmark() -> None:
    """Đo đạc Precision & Recall của GpsCleaningService trên Labeled Test Set (Yêu cầu > 90%)."""
    settings = Settings()
    cleaning_service = GpsCleaningService.from_settings(settings)

    true_positives = 0  # Lọc đúng điểm nhiễu
    false_positives = 0  # Lọc nhầm điểm tốt thành điểm nhiễu
    true_negatives = 0  # Chấp nhận đúng điểm tốt
    false_negatives = 0  # Bỏ sót điểm nhiễu (cho điểm nhiễu qua)

    for scenario in LABELED_TEST_SET:
        accepted_events = cleaning_service.filter_events(scenario.events)
        accepted_ids = {e.event_id for e in accepted_events}

        for idx, event in enumerate(scenario.events):
            is_ground_truth_rejected = idx in scenario.expected_rejected_indices
            is_actual_rejected = event.event_id not in accepted_ids

            if is_ground_truth_rejected and is_actual_rejected:
                true_positives += 1
            elif not is_ground_truth_rejected and is_actual_rejected:
                false_positives += 1
            elif not is_ground_truth_rejected and not is_actual_rejected:
                true_negatives += 1
            elif is_ground_truth_rejected and not is_actual_rejected:
                false_negatives += 1

    precision = (
        true_positives / (true_positives + false_positives)
        if (true_positives + false_positives) > 0
        else 1.0
    )
    recall = (
        true_positives / (true_positives + false_negatives)
        if (true_positives + false_negatives) > 0
        else 1.0
    )
    f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 1.0

    print("\n--- GPS Cleaning Benchmark Metrics ---")
    p_pct = precision * 100
    r_pct = recall * 100
    f1_pct = f1_score * 100
    print(f"Precision: {p_pct:.2f}% | Recall: {r_pct:.2f}% | F1: {f1_pct:.2f}%")

    assert precision >= 0.90, f"Precision {precision} is below 90%"
    assert recall >= 0.90, f"Recall {recall} is below 90%"
    assert f1_score >= 0.90, f"F1 Score {f1_score} is below 90%"


@pytest.mark.asyncio
async def test_map_matching_corridor_fallback_correctness() -> None:
    """Đo đạc tính đúng đắn của Map Matching & Corridor Fallback trên Labeled Test Set."""
    client = MockOsrmClient()
    settings = Settings()
    matching_service = MapMatchingService.from_settings(client, settings)

    correct_matches = 0
    total_scenarios = len(LABELED_TEST_SET)

    for scenario in LABELED_TEST_SET:
        result = await matching_service.match(scenario.events)

        if result.status == MapMatchStatus.MATCHED:
            if result.fallback_radius_m == scenario.expected_fallback_radius_m:
                correct_matches += 1

    accuracy = correct_matches / total_scenarios

    print("\n--- Map Matching Fallback Accuracy ---")
    print(f"Accuracy: {accuracy * 100:.2f}% ({correct_matches}/{total_scenarios})")

    assert accuracy >= 0.90, f"Map Matching accuracy {accuracy} is below 90%"


@pytest.mark.asyncio
async def test_overall_system_correctness_benchmark() -> None:
    """Đo đạc độ chính xác tổng hợp toàn hệ thống (Precision/Recall > 90%)."""
    total_evaluated_points = 0
    correctly_handled_points = 0

    settings = Settings()
    cleaning_service = GpsCleaningService.from_settings(settings)
    matching_service = MapMatchingService.from_settings(MockOsrmClient(), settings)

    for scenario in LABELED_TEST_SET:
        # Bước 1: Cleaning
        accepted_events = cleaning_service.filter_events(scenario.events)
        total_evaluated_points += len(scenario.events)

        if len(accepted_events) == scenario.expected_clean_count:
            correctly_handled_points += len(scenario.events)

        # Bước 2: Map Matching
        if len(accepted_events) >= 2:
            match_res = await matching_service.match(accepted_events)
            assert match_res.status == MapMatchStatus.MATCHED

    overall_accuracy = correctly_handled_points / total_evaluated_points

    print("\n--- Overall System Benchmark ---")
    acc_pct = overall_accuracy * 100
    print(f"Overall Accuracy: {acc_pct:.2f}% ({correctly_handled_points}/{total_evaluated_points})")

    assert overall_accuracy >= 0.90, f"Overall system accuracy {overall_accuracy} is below 90%"
