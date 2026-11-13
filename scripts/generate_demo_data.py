#!/usr/bin/env python3
"""crowdwise/scripts/generate_demo_data.py
Feature F10: Synthetic Ticket Simulator with Ground-Truth Passenger Loads.

Simulates 28 consecutive days of transit ticketing transactions and physical passenger
movements across Delhi bus corridors, calibrated against Delhi NCT metropolitan diurnal
commute curves with morning (08:00–10:30) and evening (17:00–20:00) rush-hour peaks.

Outputs:
  - data/synthetic/demo_tickets.parquet (ETM transaction feed)
  - data/synthetic/truth_loads_demo.parquet (Ground-truth trip-zone passenger loads)
  - data/synthetic/zone_hourly_loads.parquet (Hourly aggregated zone loads for ML)
"""
import os
import sys
import math
import random
import argparse
import logging
from collections import defaultdict
from datetime import datetime, date, timedelta, timezone
from typing import Dict, Any, List, Optional, Tuple, Set

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

# Ensure backend and crowdwise root in sys.path
script_dir = os.path.dirname(os.path.abspath(__file__))
crowdwise_root = os.path.abspath(os.path.join(script_dir, ".."))
backend_dir = os.path.join(crowdwise_root, "backend")
for p in [crowdwise_root, backend_dir]:
    if p not in sys.path:
        sys.path.insert(0, p)

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.models.transit import (
    DimStop,
    DimRoute,
    DimRoutePattern,
    RelPatternStop,
    DimTripStart,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("generate_demo_data")


# ---------------------------------------------------------------------------
# Diurnal Profile Mathematical Formulation
# ---------------------------------------------------------------------------

def compute_diurnal_intensity(hour_float: float) -> float:
    """Calculates normalized hourly demand intensity I(h) using a Gaussian mixture model.

    Morning peak: mu=9.0, sigma=1.0, amplitude=0.85
    Evening peak: mu=18.5, sigma=1.2, amplitude=0.80
    Midday plateau: 11:00-16:00, amplitude=0.38
    Base: 0.15 for shoulder hours, 0.05 for late night
    """
    h = float(hour_float)
    # Off-peak base
    if 22.0 <= h or h < 5.0:
        base = 0.05
    elif (5.0 <= h < 7.0) or (20.0 <= h < 22.0):
        base = 0.15
    else:
        base = 0.22

    # Morning rush peak
    morn = 0.85 * math.exp(-((h - 9.0) ** 2) / (2.0 * (1.0 ** 2)))

    # Midday commercial plateau
    midday = 0.38 if 11.0 <= h <= 16.0 else 0.0

    # Evening return rush peak
    eve = 0.80 * math.exp(-((h - 18.5) ** 2) / (2.0 * (1.2 ** 2)))

    return base + morn + midday + eve


def get_zone_id(stop_sequence: int, total_stops: int) -> int:
    """Closed-form 8-zone partition formula: min(7, floor(8 * s / N))."""
    if total_stops <= 0:
        return 0
    if total_stops <= 8:
        return min(7, max(0, stop_sequence))
    return min(7, max(0, math.floor((stop_sequence * 8) / total_stops)))


# ---------------------------------------------------------------------------
# Route Pattern Topology Extraction
# ---------------------------------------------------------------------------

def load_network_topology(engine: Any, sample_routes: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """Loads route patterns and stop sequences from database or fallback fixture."""
    patterns_data: List[Dict[str, Any]] = []

    try:
        with Session(engine) as session:
            stmt = select(DimRoutePattern)
            if sample_routes:
                stmt = stmt.where(DimRoutePattern.route_id.in_(sample_routes))
            patterns = session.execute(stmt).scalars().all()

            for pat in patterns:
                stop_stmt = (
                    select(RelPatternStop)
                    .where(RelPatternStop.pattern_id == pat.pattern_id)
                    .order_by(RelPatternStop.stop_sequence)
                )
                p_stops = session.execute(stop_stmt).scalars().all()
                if not p_stops:
                    continue

                stops_list = [
                    {
                        "seq": ps.stop_sequence,
                        "stop_id": ps.stop_id,
                        "zone_id": ps.zone_id,
                        "cum_dist_km": ps.cum_dist_km,
                    }
                    for ps in p_stops
                ]

                # Trip departures from dim_trip_starts
                trip_stmt = (
                    select(DimTripStart)
                    .where(DimTripStart.pattern_id == pat.pattern_id)
                    .order_by(DimTripStart.departure_hour, DimTripStart.departure_time)
                )
                trips = session.execute(trip_stmt).scalars().all()
                scheduled_trips = [
                    {
                        "trip_id": t.trip_id,
                        "service_id": t.service_id,
                        "departure_time": t.departure_time,
                        "departure_hour": t.departure_hour,
                        "day_type": t.day_type,
                    }
                    for t in trips
                ]

                patterns_data.append({
                    "pattern_id": pat.pattern_id,
                    "route_id": pat.route_id,
                    "direction_id": pat.direction_id,
                    "stop_count": pat.stop_count,
                    "stops": stops_list,
                    "trips": scheduled_trips,
                })
    except Exception as e:
        logger.warning(f"Could not load full topology from database ({e}). Using synthetic fixture corridors.")

    if not patterns_data:
        # Fallback representative 30-stop corridor (Route 502)
        n = 30
        stops_dir0 = [
            {
                "seq": i,
                "stop_id": f"DEL_502_{i:02d}",
                "zone_id": get_zone_id(i, n),
                "cum_dist_km": round(i * 0.95, 2),
            }
            for i in range(n)
        ]
        stops_dir1 = [
            {
                "seq": i,
                "stop_id": f"DEL_502_{n - 1 - i:02d}",
                "zone_id": get_zone_id(i, n),
                "cum_dist_km": round(i * 0.95, 2),
            }
            for i in range(n)
        ]
        trips = []
        for hr in range(6, 23):
            for m in [0, 30]:
                trips.append({
                    "trip_id": f"TRIP_502_0_{hr:02d}{m:02d}",
                    "service_id": "DAILY",
                    "departure_time": f"{hr:02d}:{m:02d}:00",
                    "departure_hour": hr,
                    "day_type": "WEEKDAY",
                })
        patterns_data = [
            {
                "pattern_id": "PAT_502_0",
                "route_id": "502",
                "direction_id": 0,
                "stop_count": n,
                "stops": stops_dir0,
                "trips": trips,
            },
            {
                "pattern_id": "PAT_502_1",
                "route_id": "502",
                "direction_id": 1,
                "stop_count": n,
                "stops": stops_dir1,
                "trips": trips,
            },
        ]

    return patterns_data


# ---------------------------------------------------------------------------
# Synthetic Simulation Core
# ---------------------------------------------------------------------------

def run_simulation(
    patterns_data: List[Dict[str, Any]],
    start_date: date,
    num_days: int = 28,
    seed: int = 42,
    rated_capacity: int = 60,
    max_capacity: int = 75,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Generates synthetic ETM tickets, truth loads, and hourly zone loads."""
    np.random.seed(seed)
    random.seed(seed)

    all_tickets: List[Dict[str, Any]] = []
    all_truth_loads: List[Dict[str, Any]] = []

    # Fare stage table in INR for DTC
    fare_tiers = [5.0, 10.0, 15.0, 20.0, 25.0]

    for day_idx in range(num_days):
        sim_date = start_date + timedelta(days=day_idx)
        date_str = sim_date.strftime("%Y-%m-%d")
        day_of_week = sim_date.weekday()

        if day_of_week < 5:
            day_type = "WEEKDAY"
            day_mult = 1.00
        elif day_of_week == 5:
            day_type = "SATURDAY"
            day_mult = 0.85
        else:
            day_type = "SUNDAY"
            day_mult = 0.65

        for pat in patterns_data:
            route_id = pat["route_id"]
            direction_id = pat["direction_id"]
            stops = pat["stops"]
            n_stops = len(stops)
            if n_stops < 2:
                continue

            scheduled_trips = pat.get("trips", [])
            # If no trips scheduled for this specific day_type, generate hourly baseline trips
            trips_for_day = [t for t in scheduled_trips if t.get("day_type") == day_type]
            if not trips_for_day:
                trips_for_day = [
                    {
                        "trip_id": f"TRIP_{route_id}_{direction_id}_{hr:02d}00",
                        "departure_hour": hr,
                        "departure_time": f"{hr:02d}:15:00",
                        "day_type": day_type,
                    }
                    for hr in range(5, 24)
                ]

            for trip in trips_for_day:
                hour = int(trip["departure_hour"])
                dep_time_str = trip.get("departure_time", f"{hour:02d}:00:00")
                trip_id = f"{trip['trip_id']}_{date_str.replace('-', '')}"

                # Demand intensity
                intensity = compute_diurnal_intensity(hour)

                # Directional tidal bias
                # UP (0) heads to Central Delhi -> higher in morning
                # DOWN (1) heads to sub-cities -> higher in evening
                if direction_id == 0:
                    dir_factor = 1.35 if (7 <= hour <= 10) else (0.85 if (17 <= hour <= 20) else 1.0)
                else:
                    dir_factor = 0.85 if (7 <= hour <= 10) else (1.35 if (17 <= hour <= 20) else 1.0)

                base_lambda = 3.2 * intensity * day_mult * dir_factor

                # Stop-level physical simulation
                current_onboard = 0
                stop_boardings = [0] * n_stops
                stop_alightings = [0] * n_stops
                stop_loads = [0.0] * n_stops

                for s_idx in range(n_stops):
                    # 1. Alightings at stop s_idx (from passengers on-board)
                    if s_idx == 0:
                        alight_count = 0
                    elif s_idx == n_stops - 1:
                        # Terminal stop clearance: ALL remaining passengers alight
                        alight_count = current_onboard
                    else:
                        # Interior alightings based on travel progress
                        p_alight = min(0.40, max(0.08, 0.15 + 0.01 * s_idx))
                        alight_count = min(current_onboard, np.random.binomial(current_onboard, p_alight))

                    stop_alightings[s_idx] = alight_count
                    current_onboard = max(0, current_onboard - alight_count)

                    # 2. Boardings at stop s_idx
                    if s_idx < n_stops - 1:
                        # Stop weight (elevated for interchanges/terminals)
                        stop_weight = 1.8 if (s_idx < 3 or s_idx > n_stops - 4) else 1.0
                        exp_board = base_lambda * stop_weight
                        raw_board = int(np.random.poisson(exp_board))

                        # Crush capacity throttling (rated=60, max=75)
                        avail_capacity = max(0, max_capacity - current_onboard)
                        actual_board = min(raw_board, avail_capacity)
                    else:
                        actual_board = 0  # Zero boardings at terminal stop

                    stop_boardings[s_idx] = actual_board
                    current_onboard += actual_board
                    stop_loads[s_idx] = float(current_onboard)

                    # Generate individual ticketing transactions for actual boardings
                    if actual_board > 0:
                        # Break actual_board into group tickets (1-3 pax)
                        rem_pax = actual_board
                        ticket_seq = 0
                        while rem_pax > 0:
                            pax_on_ticket = min(rem_pax, random.choices([1, 2, 3], weights=[0.90, 0.08, 0.02])[0])
                            rem_pax -= pax_on_ticket
                            ticket_seq += 1

                            ticket_id = f"TK_{date_str.replace('-', '')}_{route_id}_{trip['trip_id']}_{s_idx:02d}_{ticket_seq:02d}"
                            fare_val = random.choice(fare_tiers)

                            # Ticket timestamp (within hour)
                            min_offset = min(59, max(0, int(s_idx * (45.0 / n_stops))))
                            sec_offset = random.randint(0, 59)
                            ticket_time_str = f"{date_str} {hour:02d}:{min_offset:02d}:{sec_offset:02d}"

                            all_tickets.append({
                                "ticket_id": ticket_id,
                                "timestamp": ticket_time_str,
                                "route_id": route_id,
                                "direction_id": direction_id,
                                "trip_id": trip_id,
                                "boarding_stop_id": stops[s_idx]["stop_id"],
                                "passenger_count": pax_on_ticket,
                                "fare": fare_val,
                            })

                # Terminal Stop Clearance Verification
                stop_loads[n_stops - 1] = 0.0
                assert sum(stop_boardings) == sum(stop_alightings)

                # Zone-Level Aggregation for this trip
                zone_stop_indices: Dict[int, List[int]] = defaultdict(list)
                for s_idx in range(n_stops):
                    z_id = stops[s_idx].get("zone_id", get_zone_id(s_idx, n_stops))
                    zone_stop_indices[z_id].append(s_idx)

                for z_id in sorted(zone_stop_indices.keys()):
                    idx_list = zone_stop_indices[z_id]
                    z_loads = [stop_loads[i] for i in idx_list]
                    z_b = sum(stop_boardings[i] for i in idx_list)
                    z_a = sum(stop_alightings[i] for i in idx_list)

                    all_truth_loads.append({
                        "trip_id": trip_id,
                        "route_id": route_id,
                        "direction_id": direction_id,
                        "day_type": day_type,
                        "date": date_str,
                        "trip_date": sim_date,
                        "hour": hour,
                        "zone_id": z_id,
                        "mean_load": round(float(np.mean(z_loads)), 2),
                        "max_load": int(np.max(z_loads)),
                        "boardings_total": int(z_b),
                        "alightings_total": int(z_a),
                        "trip_count": 1,
                    })

    df_tickets = pd.DataFrame(all_tickets)
    df_truth = pd.DataFrame(all_truth_loads)

    # Hourly aggregated zone loads for M3 ML modeling
    if not df_truth.empty:
        df_hourly = df_truth.groupby(
            ["route_id", "direction_id", "zone_id", "day_type", "hour", "trip_date"],
            as_index=False
        ).agg(
            mean_load=("mean_load", "mean"),
            trip_count=("trip_count", "sum"),
        )
        df_hourly["mean_load"] = df_hourly["mean_load"].round(2)
    else:
        df_hourly = pd.DataFrame(columns=[
            "route_id", "direction_id", "zone_id", "day_type", "hour", "trip_date", "mean_load", "trip_count"
        ])

    return df_tickets, df_truth, df_hourly


# ---------------------------------------------------------------------------
# CLI & Artifact Writer
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="CrowdWise Synthetic Ticket Simulator")
    parser.add_argument("--db-url", type=str, default=None, help="Database connection URL")
    parser.add_argument("--output-dir", type=str, default=None, help="Output directory for Parquet files")
    parser.add_argument("--start-date", type=str, default="2026-10-01", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--days", type=int, default=28, help="Number of consecutive days (default: 28)")
    parser.add_argument("--seed", type=int, default=42, help="Pseudorandom generator seed (default: 42)")
    parser.add_argument("--sample-routes", type=str, default=None, help="Comma-separated route IDs filter")

    args = parser.parse_args()

    # Determine default paths
    if args.output_dir:
        out_dir = os.path.abspath(args.output_dir)
    else:
        out_dir = os.path.join(crowdwise_root, "data", "synthetic")
    os.makedirs(out_dir, exist_ok=True)

    if args.db_url:
        db_url = args.db_url
    else:
        db_file = os.path.join(backend_dir, "crowdwise.db").replace("\\", "/")
        db_url = f"sqlite:///{db_file}"

    sample_routes = [r.strip() for r in args.sample_routes.split(",")] if args.sample_routes else None
    start_dt = datetime.strptime(args.start_date, "%Y-%m-%d").date()

    logger.info(f"Connecting to database: {db_url}")
    engine = create_engine(db_url)

    logger.info(f"Loading network topology (sample_routes={sample_routes})...")
    patterns = load_network_topology(engine, sample_routes=sample_routes)
    logger.info(f"Loaded {len(patterns)} patterns for simulation.")

    logger.info(f"Running simulation: {args.days} days starting {start_dt} with seed {args.seed}...")
    df_tickets, df_truth, df_hourly = run_simulation(
        patterns_data=patterns,
        start_date=start_dt,
        num_days=args.days,
        seed=args.seed,
    )

    # Save to Parquet
    tickets_path = os.path.join(out_dir, "demo_tickets.parquet")
    truth_path = os.path.join(out_dir, "truth_loads_demo.parquet")
    hourly_path = os.path.join(out_dir, "zone_hourly_loads.parquet")

    logger.info(f"Writing {len(df_tickets)} ticket rows to {tickets_path}...")
    df_tickets.to_parquet(tickets_path, engine="pyarrow", index=False)

    logger.info(f"Writing {len(df_truth)} truth load rows to {truth_path}...")
    df_truth.to_parquet(truth_path, engine="pyarrow", index=False)

    logger.info(f"Writing {len(df_hourly)} hourly zone rows to {hourly_path}...")
    df_hourly.to_parquet(hourly_path, engine="pyarrow", index=False)

    logger.info("Synthetic data generation completed successfully!")
    logger.info(f"  - Tickets       : {len(df_tickets)} records ({tickets_path})")
    logger.info(f"  - Truth Loads   : {len(df_truth)} records ({truth_path})")
    logger.info(f"  - Hourly Loads  : {len(df_hourly)} records ({hourly_path})")


if __name__ == "__main__":
    main()
