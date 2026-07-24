"""Database Seeder Module for loading demo_seed_v1.json into PostGIS."""

import json
import logging
from pathlib import Path

from geoalchemy2.shape import from_shape
from shapely.geometry import LineString, Point  # type: ignore[import-untyped]
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.models import Driver, GPSEvent, PlannedRoute, Trip

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("seed_db")

BASE_DIR = Path(__file__).resolve().parent.parent.parent
SEED_JSON_PATH = BASE_DIR / "app" / "db" / "seeds" / "demo_seed_v1.json"


def seed_database_from_json(session: Session, json_path: Path = SEED_JSON_PATH) -> dict[str, int]:
    """Populate database from seed JSON file idempotently."""
    if not json_path.exists():
        logger.error("Seed JSON file not found: %s", json_path)
        return {"drivers": 0, "trips": 0, "planned_routes": 0, "gps_events": 0}

    with json_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    # 1. Seed Drivers
    driver_count = 0
    for d in data.get("drivers", []):
        stmt_driver = select(Driver).where(Driver.id == d["id"])
        existing_driver = session.scalar(stmt_driver)
        if not existing_driver:
            session.add(
                Driver(id=d["id"], full_name=d["full_name"], phone_number=d["phone_number"])
            )
            driver_count += 1

    session.flush()

    # 2. Seed Trips
    trip_count = 0
    for t in data.get("trips", []):
        stmt_trip = select(Trip).where(Trip.id == t["id"])
        existing_trip = session.scalar(stmt_trip)
        if not existing_trip:
            session.add(Trip(id=t["id"], driver_id=t["driver_id"], status=t["status"]))
            trip_count += 1

    session.flush()

    # 3. Seed Planned Routes
    route_count = 0
    for r in data.get("planned_routes", []):
        stmt_route = select(PlannedRoute).where(PlannedRoute.id == r["id"])
        existing_route = session.scalar(stmt_route)
        if not existing_route:
            coords = r["route_geometry"]["coordinates"]
            line = LineString(coords)
            session.add(
                PlannedRoute(
                    id=r["id"],
                    trip_id=r["trip_id"],
                    route_geometry=from_shape(line, srid=4326),
                    ordered_edge_ids=r["ordered_edge_ids"],
                )
            )
            route_count += 1

    session.flush()

    # 4. Seed GPS Events
    event_count = 0
    for g in data.get("gps_events", []):
        pt = Point(g["longitude"], g["latitude"])
        session.add(
            GPSEvent(
                id=g["id"],
                trip_id=g["trip_id"],
                event_id=g["event_id"],
                sequence_no=g["sequence_no"],
                recorded_at=g["recorded_at"],
                latitude=g["latitude"],
                longitude=g["longitude"],
                accuracy_m=g["accuracy_m"],
                speed_kmh=g.get("speed_kmh"),
                heading_deg=g.get("heading_deg"),
                raw_geometry=from_shape(pt, srid=4326),
            )
        )
        event_count += 1

    session.commit()
    logger.info(
        "Successfully seeded DB: %d drivers, %d trips, %d routes, %d gps_events",
        driver_count,
        trip_count,
        route_count,
        event_count,
    )
    return {
        "drivers": driver_count,
        "trips": trip_count,
        "planned_routes": route_count,
        "gps_events": event_count,
    }
