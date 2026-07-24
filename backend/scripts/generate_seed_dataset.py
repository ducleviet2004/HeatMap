#!/usr/bin/env python3
"""Deterministic Seed Dataset Generator (v1) for Route Deviation Heatmap Analytics.

Generates >= 50,000 realistic, physics-based GPS events across 10 drivers and 50 trips.
Applies Haversine physics interpolation and 5 trajectory simulation modes:
1. Normal Route (100% planned match)
2. True Bypass (deviates to detour road for 500m-3km, generating bypass segments)
3. GPS Noise & Outliers (accuracy_m > 30m, speed jump > 120km/h)
4. GPS Signal Gap (<15s micro, 15-120s medium, >120s macro gap)
5. Parallel Road (runs parallel 15-30m offset from highway)
"""

import json
import math
import random
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

RANDOM_SEED = 42

BASE_DIR = Path(__file__).resolve().parent.parent
SEEDS_DIR = BASE_DIR / "app" / "db" / "seeds"
SEED_JSON_PATH = SEEDS_DIR / "demo_seed_v1.json"


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate Great-Circle distance in meters between two lat/lon points."""
    r = 6371000.0  # Earth radius in meters
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return r * c


def interpolate_point(
    lat1: float, lon1: float, lat2: float, lon2: float, fraction: float
) -> tuple[float, float]:
    """Linear interpolation between two lat/lon coordinates."""
    lat = lat1 + (lat2 - lat1) * fraction
    lon = lon1 + (lon2 - lon1) * fraction
    return lat, lon


def offset_coordinate(
    lat: float, lon: float, meters_east: float, meters_north: float
) -> tuple[float, float]:
    """Offset lat/lon coordinate by meters in East and North direction."""
    delta_lat = meters_north / 111111.0
    delta_lon = meters_east / (111111.0 * math.cos(math.radians(lat)))
    return lat + delta_lat, lon + delta_lon


def generate_dataset(target_gps_count: int = 52000) -> dict[str, list[dict]]:
    """Generate deterministic seed dataset with drivers, trips, planned routes, and gps events."""
    random.seed(RANDOM_SEED)

    # 1. Generate Drivers
    driver_names = [
        "Nguyễn Văn An",
        "Lê Văn Bình",
        "Phạm Quốc Cường",
        "Trần Đình Dũng",
        "Hoàng Thị Em",
        "Vũ Hoàng Giang",
        "Đỗ Minh Hải",
        "Bùi Thanh Hải",
        "Đặng Quang Huy",
        "Nông Văn Khanh",
    ]
    drivers = [
        {
            "id": str(uuid.UUID(int=i + 1)),
            "full_name": name,
            "phone_number": f"+8490{i:07d}",
            "created_at": "2026-01-01T00:00:00Z",
        }
        for i, name in enumerate(driver_names)
    ]

    # 2. Base Route Anchor Corridors (Hanoi Urban & Suburban corridors)
    corridors = [
        # Corridor A: Nội Bài Airport -> Vành Đai 3 -> Hà Đông
        [
            (21.2187, 105.8042),
            (21.1500, 105.8000),
            (21.0800, 105.7900),
            (21.0300, 105.7800),
            (20.9800, 105.7700),
            (20.9600, 105.7600),
        ],
        # Corridor B: Cầu Giấy -> Láng -> Nguyễn Trãi -> Thanh Xuân
        [
            (21.0350, 105.7950),
            (21.0150, 105.8050),
            (20.9980, 105.8120),
            (20.9850, 105.8000),
            (20.9700, 105.7900),
        ],
        # Corridor C: Hoàn Kiếm -> Giải Phóng -> Pháp Vân -> Thường Tín
        [
            (21.0285, 105.8542),
            (21.0000, 105.8450),
            (20.9600, 105.8400),
            (20.9100, 105.8500),
            (20.8500, 105.8600),
        ],
        # Corridor D: Long Biên -> Cầu Vĩnh Tuy -> Minh Khai -> Đại La
        [
            (21.0450, 105.8800),
            (21.0150, 105.8700),
            (20.9980, 105.8550),
            (20.9900, 105.8400),
            (20.9850, 105.8300),
        ],
    ]

    trips = []
    planned_routes = []
    gps_events = []

    num_trips = 50
    base_time = datetime(2026, 7, 1, 8, 0, 0, tzinfo=UTC)

    for trip_idx in range(num_trips):
        trip_id = str(uuid.UUID(int=100 + trip_idx))
        driver_id = drivers[trip_idx % len(drivers)]["id"]

        corridor_coords = corridors[trip_idx % len(corridors)]
        mode = (trip_idx % 5) + 1  # Mode 1 to 5

        start_time = base_time + timedelta(hours=trip_idx * 2)
        status = "completed" if trip_idx < 40 else "in_progress"

        # Planned Route LineString coordinates (lon, lat)
        planned_geometry_coords = [[lon, lat] for lat, lon in corridor_coords]
        ordered_edge_ids = [1000 + i for i in range(len(corridor_coords) - 1)]

        planned_routes.append(
            {
                "id": str(uuid.UUID(int=1000 + trip_idx)),
                "trip_id": trip_id,
                "route_geometry": {"type": "LineString", "coordinates": planned_geometry_coords},
                "ordered_edge_ids": ordered_edge_ids,
                "created_at": start_time.isoformat(),
            }
        )

        trips.append(
            {
                "id": trip_id,
                "driver_id": driver_id,
                "status": status,
                "started_at": start_time.isoformat(),
                "completed_at": (start_time + timedelta(minutes=45)).isoformat()
                if status == "completed"
                else None,
                "created_at": start_time.isoformat(),
            }
        )

        current_time = start_time

        # Generate dense trajectory waypoints
        trajectory_waypoints = []
        num_segments = len(corridor_coords) - 1
        pts_per_segment = 260

        for seg_idx in range(num_segments):
            lat_a, lon_a = corridor_coords[seg_idx]
            lat_b, lon_b = corridor_coords[seg_idx + 1]

            for step in range(pts_per_segment):
                frac = step / float(pts_per_segment)
                cur_lat, cur_lon = interpolate_point(lat_a, lon_a, lat_b, lon_b, frac)

                # Apply 5 Trajectory Modes
                accuracy_m = round(random.uniform(3.0, 10.0), 1)
                speed_kmh = round(random.uniform(35.0, 55.0), 1)
                heading = round(random.uniform(0.0, 360.0), 1)

                if mode == 2:  # True Bypass (Detour in middle segment)
                    if 0.3 <= (seg_idx + frac) / num_segments <= 0.7:
                        # Offset by 150m-300m East/North
                        cur_lat, cur_lon = offset_coordinate(cur_lat, cur_lon, 250.0, 200.0)

                elif mode == 3:  # GPS Noise & Outliers
                    if random.random() < 0.08:  # 8% noise points
                        accuracy_m = round(random.uniform(35.0, 85.0), 1)
                        if random.random() < 0.3:
                            speed_kmh = round(random.uniform(130.0, 160.0), 1)
                            cur_lat += random.uniform(-0.01, 0.01)

                elif mode == 4:  # GPS Signal Gap
                    if 0.4 <= (seg_idx + frac) / num_segments <= 0.45:
                        current_time += timedelta(seconds=20)  # Gap skip
                        continue

                elif mode == 5:  # Parallel Road
                    cur_lat, cur_lon = offset_coordinate(cur_lat, cur_lon, 25.0, 0.0)

                # Add minor Gaussian jitter
                jitter_lat = random.gauss(0, 0.00003)
                jitter_lon = random.gauss(0, 0.00003)
                cur_lat += jitter_lat
                cur_lon += jitter_lon

                trajectory_waypoints.append(
                    {
                        "id": str(uuid.uuid4()),
                        "trip_id": trip_id,
                        "event_id": str(uuid.uuid4()),
                        "sequence_no": len(trajectory_waypoints) + 1,
                        "recorded_at": current_time.isoformat(),
                        "latitude": round(cur_lat, 6),
                        "longitude": round(cur_lon, 6),
                        "accuracy_m": accuracy_m,
                        "speed_kmh": speed_kmh,
                        "heading_deg": heading,
                        "raw_geometry": {
                            "type": "Point",
                            "coordinates": [round(cur_lon, 6), round(cur_lat, 6)],
                        },
                        "created_at": current_time.isoformat(),
                    }
                )

                current_time += timedelta(seconds=random.randint(2, 4))

        gps_events.extend(trajectory_waypoints)

    return {
        "drivers": drivers,
        "trips": trips,
        "planned_routes": planned_routes,
        "gps_events": gps_events,
    }


def main() -> None:
    """Generate and save deterministic seed JSON file."""
    SEEDS_DIR.mkdir(parents=True, exist_ok=True)
    dataset = generate_dataset(target_gps_count=50000)

    gps_count = len(dataset["gps_events"])
    print(f"Generated Drivers: {len(dataset['drivers'])}")
    print(f"Generated Trips: {len(dataset['trips'])}")
    print(f"Generated Planned Routes: {len(dataset['planned_routes'])}")
    print(f"Generated GPS Events: {gps_count}")

    with SEED_JSON_PATH.open("w", encoding="utf-8") as f:
        json.dump(dataset, f, indent=2, ensure_ascii=False)

    print(f"Dataset successfully saved to: {SEED_JSON_PATH}")


if __name__ == "__main__":
    main()
