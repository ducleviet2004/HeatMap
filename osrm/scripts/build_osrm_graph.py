#!/usr/bin/env python3
"""Build OSRM routing graph from pinned OSM snapshot PBF data."""

import argparse
import json
import logging
import subprocess
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("osrm_builder")

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
METADATA_FILE = DATA_DIR / "routing_metadata.json"


def load_metadata() -> dict[str, str]:
    """Load metadata pinning OSM snapshot information."""
    if not METADATA_FILE.exists():
        logger.error("Metadata file not found: %s", METADATA_FILE)
        sys.exit(1)
    with METADATA_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)  # type: ignore[no-any-return]


def run_docker_osrm(command: str, osrm_args: list[str]) -> None:
    """Run an OSRM CLI command inside docker ghcr.io/project-osrm/osrm-backend container."""
    docker_cmd = [
        "docker",
        "run",
        "--rm",
        "-t",
        "-v",
        f"{DATA_DIR}:/data",
        "ghcr.io/project-osrm/osrm-backend:v5.27.1",
        command,
        *osrm_args,
    ]
    logger.info("Executing: %s", " ".join(docker_cmd))
    result = subprocess.run(docker_cmd, check=False)
    if result.returncode != 0:
        logger.error("Command failed with exit code %d: %s", result.returncode, command)
        sys.exit(result.returncode)


def main() -> None:
    """CLI Entrypoint for building OSRM routing graph."""
    parser = argparse.ArgumentParser(description="OSRM Graph Builder Tool")
    parser.add_argument("--pbf", type=str, default="data.osm.pbf", help="PBF filename inside osrm/data")
    parser.add_argument("--profile", type=str, default="car.lua", help="OSRM profile (car.lua)")
    args = parser.parse_args()

    metadata = load_metadata()
    logger.info("Loaded OSRM Metadata: %s", metadata.get("routing_data_version"))

    logger.info("Step 1: osrm-extract")
    run_docker_osrm("osrm-extract", ["-p", f"/opt/{args.profile}", f"/data/{args.pbf}"])

    logger.info("Step 2: osrm-partition")
    run_docker_osrm("osrm-partition", [f"/data/{args.pbf.replace('.osm.pbf', '.osrm')}"])

    logger.info("Step 3: osrm-customize")
    run_docker_osrm("osrm-customize", [f"/data/{args.pbf.replace('.osm.pbf', '.osrm')}"])

    logger.info("OSRM graph processing complete!")


if __name__ == "__main__":
    main()
