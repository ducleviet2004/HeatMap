"""Bộ dữ liệu kiểm định Labeled Test Set cho đánh giá Precision/Recall của hệ thống."""

from datetime import UTC, datetime, timedelta
from typing import NamedTuple
from uuid import UUID

from app.schemas.gps import GeoJsonPoint, GpsEventCreate

EVENT_BASE_ID = UUID("10000000-0000-0000-0000-000000000000")
TRIP_ID = UUID("20000000-0000-0000-0000-000000000000")
DRIVER_ID = UUID("30000000-0000-0000-0000-000000000000")
BASE_TIME = datetime(2026, 7, 24, 12, 0, 0, tzinfo=UTC)


class LabeledScenario(NamedTuple):
    name: str
    description: str
    events: list[GpsEventCreate]
    expected_clean_count: int
    expected_rejected_indices: list[int]
    expected_match_status: str
    expected_fallback_radius_m: float | None
    expected_bypass: bool


def _make_event(
    seq: int,
    lng: float,
    lat: float,
    *,
    accuracy_m: float = 5.0,
    speed_kmh: float = 40.0,
    delta_sec: int = 10,
) -> GpsEventCreate:
    return GpsEventCreate(
        event_id=UUID(f"10000000-0000-0000-0000-{seq:012d}"),
        trip_id=TRIP_ID,
        driver_id=DRIVER_ID,
        sequence_no=seq,
        recorded_at=BASE_TIME + timedelta(seconds=delta_sec * seq),
        raw_geometry=GeoJsonPoint(coordinates=[lng, lat]),
        accuracy_m=accuracy_m,
        speed_kmh=speed_kmh,
    )


# 1. Kịch bản GPS Tốt (Clean Trace)
SCENARIO_CLEAN_GPS = LabeledScenario(
    name="Clean GPS Trace",
    description="Tín hiệu GPS chuẩn, đi đúng tuyến đường, accuracy 3-5m",
    events=[
        _make_event(0, 106.7009, 10.7769, accuracy_m=3.0, speed_kmh=35.0),
        _make_event(1, 106.7015, 10.7775, accuracy_m=4.0, speed_kmh=40.0),
        _make_event(2, 106.7022, 10.7782, accuracy_m=5.0, speed_kmh=42.0),
        _make_event(3, 106.7030, 10.7790, accuracy_m=3.5, speed_kmh=38.0),
    ],
    expected_clean_count=4,
    expected_rejected_indices=[],
    expected_match_status="matched",
    expected_fallback_radius_m=None,
    expected_bypass=False,
)

# 2. Kịch bản GPS Xấu/Nhiễu (Noisy Spikes)
SCENARIO_NOISY_SPIKES = LabeledScenario(
    name="Noisy GPS Spikes",
    description="Vết GPS chứa điểm trôi nhiễu (accuracy > 30m hoặc speed > 120km/h)",
    events=[
        _make_event(0, 106.7009, 10.7769, accuracy_m=4.0, speed_kmh=40.0),
        _make_event(1, 106.7500, 10.8200, accuracy_m=50.0, speed_kmh=150.0),  # Spike nhiễu 1
        _make_event(2, 106.7022, 10.7782, accuracy_m=5.0, speed_kmh=42.0),
        _make_event(3, 106.8000, 10.9000, accuracy_m=100.0, speed_kmh=200.0),  # Spike nhiễu 2
        _make_event(4, 106.7030, 10.7790, accuracy_m=4.0, speed_kmh=39.0),
    ],
    expected_clean_count=3,
    expected_rejected_indices=[1, 3],
    expected_match_status="matched",
    expected_fallback_radius_m=None,
    expected_bypass=False,
)

# 3. Kịch bản Cầu / Hầm (Tunnel & Bridge Drift)
SCENARIO_TUNNEL_BRIDGE_DRIFT = LabeledScenario(
    name="Tunnel/Bridge Signal Drift",
    description="Tín hiệu suy hao khi qua cầu/hầm, trôi lệch 50m-80m",
    events=[
        _make_event(0, 106.7009, 10.7769, accuracy_m=60.0, speed_kmh=45.0),
        _make_event(1, 106.7018, 10.7778, accuracy_m=80.0, speed_kmh=45.0),
        _make_event(2, 106.7027, 10.7787, accuracy_m=70.0, speed_kmh=45.0),
    ],
    expected_clean_count=3,
    expected_rejected_indices=[],
    expected_match_status="matched",
    expected_fallback_radius_m=100.0,  # Khôi phục qua Corridor Fallback Check 100m
    expected_bypass=False,
)

# 4. Kịch bản Signal Gap (Mất sóng ngắt quãng > 60s)
SCENARIO_SIGNAL_GAP = LabeledScenario(
    name="Signal Gap",
    description="Vết GPS có ngắt quãng tín hiệu > 60s",
    events=[
        _make_event(0, 106.7009, 10.7769, accuracy_m=5.0, delta_sec=10),
        _make_event(1, 106.7015, 10.7775, accuracy_m=5.0, delta_sec=10),
        _make_event(2, 106.7080, 10.7850, accuracy_m=5.0, delta_sec=300),  # Gap 300s
        _make_event(3, 106.7090, 10.7860, accuracy_m=5.0, delta_sec=10),
    ],
    expected_clean_count=4,
    expected_rejected_indices=[],
    expected_match_status="matched",
    expected_fallback_radius_m=None,
    expected_bypass=False,
)

# 5. Kịch bản Confirmed Bypass (Xe đi lệch tuyến)
SCENARIO_CONFIRMED_BYPASS = LabeledScenario(
    name="Confirmed Bypass Detour",
    description="Tài xế thực sự rẽ sang đường tránh ngoài tuyến planned route > 100m",
    events=[
        _make_event(0, 106.7009, 10.7769, accuracy_m=4.0, speed_kmh=40.0),
        _make_event(1, 106.7150, 10.7900, accuracy_m=5.0, speed_kmh=45.0),  # Đường rẽ bypass
        _make_event(2, 106.7200, 10.7950, accuracy_m=5.0, speed_kmh=45.0),
        _make_event(3, 106.7030, 10.7790, accuracy_m=4.0, speed_kmh=40.0),
    ],
    expected_clean_count=4,
    expected_rejected_indices=[],
    expected_match_status="matched",
    expected_fallback_radius_m=None,
    expected_bypass=True,
)

LABELED_TEST_SET: list[LabeledScenario] = [
    SCENARIO_CLEAN_GPS,
    SCENARIO_NOISY_SPIKES,
    SCENARIO_TUNNEL_BRIDGE_DRIFT,
    SCENARIO_SIGNAL_GAP,
    SCENARIO_CONFIRMED_BYPASS,
]
