"""Benchmark Dataset v2 Seeder Module for generating >= 1,000,000 GPS points."""

import argparse
import logging
import math
import random
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from geoalchemy2.shape import from_shape
from shapely.geometry import LineString, Point
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.core.models import Driver, GPSEvent, PlannedRoute, Trip

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("seed_large_dataset")

# Center around Hanoi coordinates
HANOI_CENTER_LAT = 21.0285
HANOI_CENTER_LON = 105.8542

# Sample corridor routes around Hanoi
WAYPOINT_CORRIDORS = [
    # Route 1: Ring road 3 (Vanh dai 3)
    [
        (105.780, 21.040),
        (105.790, 21.015),
        (105.800, 20.990),
        (105.825, 20.975),
        (105.850, 20.970),
    ],
    # Route 2: Thang Long Boulevard
    [(105.780, 21.010), (105.730, 21.000), (105.680, 20.990), (105.620, 20.980)],
    # Route 3: Highway CT01 / Nhat Tan Bridge
    [(105.850, 21.020), (105.830, 21.070), (105.820, 21.120), (105.810, 21.170)],
    # Route 4: City center Hoan Kiem -> Hai Ba Trung -> Hoang Mai
    [(105.850, 21.030), (105.855, 21.010), (105.860, 20.990), (105.865, 20.970)],
    # Route 5: Gia Lam -> Long Bien -> Dong Anh
    [(105.880, 21.030), (105.890, 21.050), (105.900, 21.080), (105.910, 21.110)],
]


def generate_drivers(count: int = 100) -> list[dict]:
    """Generate mock driver dicts."""
    drivers = []
    for i in range(1, count + 1):
        drivers.append(
            {
                "id": uuid4(),
                "full_name": f"Driver Benchmark {i:03d}",
                "phone_number": f"+8490{i:07d}",
            }
        )
    return drivers


def generate_trips(drivers: list[dict], count: int = 500) -> list[dict]:
    """Generate mock trip dicts distributed among drivers."""
    trips = []
    statuses = ["completed", "completed", "completed", "active"]
    for _ in range(1, count + 1):
        driver = random.choice(drivers)
        trips.append(
            {
                "id": uuid4(),
                "driver_id": driver["id"],
                "status": random.choice(statuses),
            }
        )
    return trips


def generate_planned_routes(trips: list[dict]) -> list[dict]:
    """Generate planned route geometries for each trip."""
    routes = []
    for trip in trips:
        corridor = random.choice(WAYPOINT_CORRIDORS)
        # Add slight jitter to corridor waypoints for route diversity
        jittered_coords = [
            (lon + random.uniform(-0.005, 0.005), lat + random.uniform(-0.005, 0.005))
            for lon, lat in corridor
        ]
        routes.append(
            {
                "id": uuid4(),
                "trip_id": trip["id"],
                "coords": jittered_coords,
                "ordered_edge_ids": [1000 + i for i in range(len(jittered_coords) - 1)],
            }
        )
    return routes


def interpolated_points_between(
    p1: tuple[float, float], p2: tuple[float, float], num_pts: int
) -> list[tuple[float, float]]:
    """Interpolate coordinates between two points."""
    lons = [p1[0] + (p2[0] - p1[0]) * i / max(1, num_pts) for i in range(num_pts)]
    lats = [p1[1] + (p2[1] - p1[1]) * i / max(1, num_pts) for i in range(num_pts)]
    return list(zip(lons, lats, strict=False))


def generate_gps_events_batch(
    routes: list[dict], total_events_needed: int, start_seq: int = 1
) -> list[dict]:
    """Generate a batch of realistic GPS events along planned routes."""
    events = []
    events_per_route = max(1, math.ceil(total_events_needed / len(routes)))
    base_time = datetime.now(UTC) - timedelta(days=7)

    for route in routes:
        coords = route["coords"]
        trip_id = route["trip_id"]
        # Split events across line segments
        segments_count = len(coords) - 1
        pts_per_segment = max(2, math.ceil(events_per_route / segments_count))

        seq_no = start_seq
        current_time = base_time + timedelta(minutes=random.randint(0, 5000))

        for idx in range(segments_count):
            p1 = coords[idx]
            p2 = coords[idx + 1]
            interp_coords = interpolated_points_between(p1, p2, pts_per_segment)

            for lon, lat in interp_coords:
                if len(events) >= total_events_needed:
                    break

                # Noise injection rules:
                # 85% Clean, 5% High Speed Spike, 5% Low Accuracy Drift, 5% Gap
                roll = random.random()
                accuracy_m = 3.0
                speed_kmh = random.uniform(30.0, 60.0)

                if roll > 0.95:
                    # 5% Gap
                    current_time += timedelta(seconds=random.randint(65, 180))
                elif roll > 0.90:
                    # 5% Drift / Low accuracy
                    lon += random.uniform(-0.002, 0.002)
                    lat += random.uniform(-0.002, 0.002)
                    accuracy_m = random.uniform(45.0, 90.0)
                    current_time += timedelta(seconds=5)
                elif roll > 0.85:
                    # 5% High speed spike
                    speed_kmh = random.uniform(140.0, 200.0)
                    current_time += timedelta(seconds=5)
                else:
                    # Clean GPS
                    lon += random.uniform(-0.0001, 0.0001)
                    lat += random.uniform(-0.0001, 0.0001)
                    current_time += timedelta(seconds=random.randint(3, 10))

                event_id = uuid4()
                events.append(
                    {
                        "id": uuid4(),
                        "trip_id": trip_id,
                        "event_id": event_id,
                        "sequence_no": seq_no,
                        "recorded_at": current_time,
                        "latitude": round(lat, 6),
                        "longitude": round(lon, 6),
                        "accuracy_m": round(accuracy_m, 2),
                        "speed_kmh": round(speed_kmh, 2),
                        "heading_deg": round(random.uniform(0.0, 360.0), 1),
                        "raw_geometry": from_shape(Point(lon, lat), srid=4326),
                    }
                )
                seq_no += 1

            if len(events) >= total_events_needed:
                break
        if len(events) >= total_events_needed:
            break

    return events


def seed_large_dataset(
    database_url: str,
    target_points: int = 1_000_000,
    driver_count: int = 100,
    trip_count: int = 500,
    batch_size: int = 50_000,
) -> dict[str, int]:
    """Idempotently generate and seed benchmark dataset into PostGIS."""
    logger.info("Starting Benchmark Dataset v2 seeding for target: %d points", target_points)
    engine = create_engine(database_url, echo=False, pool_pre_ping=True)
    session_factory = sessionmaker(bind=engine)

    with session_factory() as session:
        # 1. Generate Drivers
        logger.info("Generating %d drivers...", driver_count)
        drivers_data = generate_drivers(driver_count)
        session.bulk_insert_mappings(Driver, drivers_data)
        session.flush()

        # 2. Generate Trips
        logger.info("Generating %d trips...", trip_count)
        trips_data = generate_trips(drivers_data, trip_count)
        session.bulk_insert_mappings(Trip, trips_data)
        session.flush()

        # 3. Generate Planned Routes
        logger.info("Generating planned routes for %d trips...", len(trips_data))
        routes_data = generate_planned_routes(trips_data)
        db_routes = []
        for r in routes_data:
            line = LineString(r["coords"])
            db_routes.append(
                {
                    "id": r["id"],
                    "trip_id": r["trip_id"],
                    "route_geometry": from_shape(line, srid=4326),
                    "ordered_edge_ids": r["ordered_edge_ids"],
                }
            )
        session.bulk_insert_mappings(PlannedRoute, db_routes)
        session.flush()
        session.commit()

        # 4. Generate & Bulk Insert GPS Events in Chunks
        logger.info(
            "Generating and inserting %d GPS events (Batch size: %d)...",
            target_points,
            batch_size,
        )
        total_inserted = 0

        while total_inserted < target_points:
            chunk_needed = min(batch_size, target_points - total_inserted)
            events_chunk = generate_gps_events_batch(routes_data, chunk_needed)

            session.bulk_insert_mappings(GPSEvent, events_chunk)
            session.commit()

            total_inserted += len(events_chunk)
            logger.info("Progress: %d / %d GPS events inserted", total_inserted, target_points)

        logger.info(
            "Seeding completed successfully! Total GPS Events: %d across %d drivers, %d trips.",
            total_inserted,
            driver_count,
            trip_count,
        )

        return {
            "drivers": len(drivers_data),
            "trips": len(trips_data),
            "routes": len(db_routes),
            "gps_events": total_inserted,
        }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Seed Benchmark Dataset v2 (>= 1,000,000 GPS points) into PostGIS"
    )
    parser.add_argument("--points", type=int, default=1_000_000, help="Total GPS points to seed")
    parser.add_argument("--drivers", type=int, default=100, help="Number of drivers to seed")
    parser.add_argument("--trips", type=int, default=500, help="Number of trips to seed")
    parser.add_argument(
        "--batch-size", type=int, default=50_000, help="Batch insertion size per chunk"
    )
    args = parser.parse_args()

    settings = get_settings()
    seed_large_dataset(
        database_url=settings.database_url,
        target_points=args.points,
        driver_count=args.drivers,
        trip_count=args.trips,
        batch_size=args.batch_size,
    )


if __name__ == "__main__":
    main()
