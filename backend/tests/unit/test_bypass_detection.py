import pytest

from app.schemas.bypass import BypassReason, PlannedRoadEdge
from app.services.bypass_detection import BypassDetectionService


@pytest.fixture
def service() -> BypassDetectionService:
    return BypassDetectionService(
        minimum_match_confidence=0.7,
        minimum_missing_run_m=50.0,
        corridor_tolerance_m=30.0,
        algorithm_version="ordered-edge-v1",
        threshold_config_version="v1",
    )


def edge(
    edge_id: str,
    *,
    length_m: float = 30.0,
    corridor_distance_m: float | None = 50.0,
    observed: bool = True,
) -> PlannedRoadEdge:
    return PlannedRoadEdge(
        edge_id=edge_id,
        length_m=length_m,
        corridor_distance_m=corridor_distance_m,
        observed=observed,
    )


def compare(
    service: BypassDetectionService,
    planned: list[PlannedRoadEdge],
    actual: list[str],
    *,
    confidence: float = 0.9,
    planned_version: str = "vietnam-v1",
    actual_version: str = "vietnam-v1",
):
    return service.compare(
        planned,
        actual,
        planned_routing_data_version=planned_version,
        actual_routing_data_version=actual_version,
        map_match_confidence=confidence,
    )


def test_confirms_contiguous_missing_planned_edges(
    service: BypassDetectionService,
) -> None:
    planned = [edge("A"), edge("B"), edge("C"), edge("D")]

    result = compare(service, planned, ["A", "X", "D"])

    assert result.missing_edge_count == 2
    assert result.confirmed_bypass_count == 1
    assert result.bypass_segments[0].planned_edge_ids == ["B", "C"]
    assert result.bypass_segments[0].start_planned_index == 1
    assert result.bypass_segments[0].end_planned_index == 2
    assert result.bypass_segments[0].missing_length_m == 60.0
    assert result.bypass_segments[0].confirmed is True
    assert result.bypass_segments[0].reason_code == BypassReason.CONFIRMED_BYPASS


def test_actual_detour_edges_do_not_create_missing_planned_edges(
    service: BypassDetectionService,
) -> None:
    planned = [edge("A"), edge("B"), edge("C")]

    result = compare(service, planned, ["A", "X", "B", "C"])

    assert result.missing_edge_count == 0
    assert result.bypass_segments == []


def test_separates_non_contiguous_missing_runs(
    service: BypassDetectionService,
) -> None:
    planned = [
        edge("A"),
        edge("B", length_m=60),
        edge("C"),
        edge("D", length_m=60),
        edge("E"),
    ]

    result = compare(service, planned, ["A", "C", "E"])

    assert [segment.planned_edge_ids for segment in result.bypass_segments] == [["B"], ["D"]]
    assert result.confirmed_bypass_count == 2


def test_lcs_handles_repeated_edge_ids(service: BypassDetectionService) -> None:
    planned = [edge("A"), edge("B"), edge("A"), edge("C")]

    result = compare(service, planned, ["A", "A", "C"])

    assert result.bypass_segments[0].planned_edge_ids == ["B"]
    assert result.bypass_segments[0].start_planned_index == 1


@pytest.mark.parametrize(
    ("confidence", "planned_version", "actual_version", "expected_reason"),
    [
        (0.69, "v1", "v1", BypassReason.LOW_MATCH_CONFIDENCE),
        (0.9, "v1", "v2", BypassReason.ROUTING_VERSION_MISMATCH),
    ],
)
def test_quality_gates_prevent_false_confirmation(
    service: BypassDetectionService,
    confidence: float,
    planned_version: str,
    actual_version: str,
    expected_reason: BypassReason,
) -> None:
    result = compare(
        service,
        [edge("A"), edge("B", length_m=60), edge("C")],
        ["A", "C"],
        confidence=confidence,
        planned_version=planned_version,
        actual_version=actual_version,
    )

    assert result.confirmed_bypass_count == 0
    assert result.bypass_segments[0].reason_code == expected_reason


def test_short_missing_run_is_not_confirmed(service: BypassDetectionService) -> None:
    result = compare(service, [edge("A"), edge("B", length_m=20), edge("C")], ["A", "C"])

    assert result.bypass_segments[0].confirmed is False
    assert result.bypass_segments[0].reason_code == BypassReason.BELOW_MINIMUM_LENGTH


def test_same_corridor_is_treated_as_possible_gps_drift(
    service: BypassDetectionService,
) -> None:
    planned = [
        edge("A"),
        edge("B", length_m=30, corridor_distance_m=10),
        edge("C", length_m=30, corridor_distance_m=20),
        edge("D"),
    ]

    result = compare(service, planned, ["A", "D"])

    assert result.bypass_segments[0].confirmed is False
    assert result.bypass_segments[0].average_deviation_distance_m == 15.0
    assert result.bypass_segments[0].reason_code == BypassReason.SAME_CORRIDOR


def test_run_inside_gps_gap_is_not_confirmed(service: BypassDetectionService) -> None:
    planned = [
        edge("A"),
        edge("B", observed=False),
        edge("C", observed=False),
        edge("D"),
    ]

    result = compare(service, planned, ["A", "D"])

    assert result.bypass_segments[0].confirmed is False
    assert result.bypass_segments[0].reason_code == BypassReason.GPS_GAP


def test_missing_corridor_data_is_not_confirmed(service: BypassDetectionService) -> None:
    planned = [
        edge("A"),
        edge("B", corridor_distance_m=None),
        edge("C", corridor_distance_m=None),
        edge("D"),
    ]

    result = compare(service, planned, ["A", "D"])

    assert result.bypass_segments[0].confirmed is False
    assert result.bypass_segments[0].reason_code == BypassReason.CORRIDOR_DATA_MISSING
