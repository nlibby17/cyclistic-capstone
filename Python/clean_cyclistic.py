"""
Cyclistic capstone cleaning script.

Purpose: read the twelve monthly Divvy CSVs one file at a time, apply the
same cleaning rules to each, and write one cleaned CSV plus a cleaning log.
The log is the audit trail for deliverable 3, so every rule prints how many
rows it caught, per file and in total.

Decisions Nick still owns (edit the constants below before the real run):
- MIN_RIDE_MINUTES and MAX_RIDE_MINUTES set the duration rules.
- Null station names are kept and counted, because some rides legitimately
  end off dock. Dropping them would erase real trips.

Usage:
    python clean_cyclistic.py --input-dir path/to/unzipped/csvs
    python clean_cyclistic.py --input-dir path/to/unzipped/csvs --output-dir output

Outputs (in the output folder):
    cyclistic_cleaned.csv   one cleaned file, ready for Power BI
    cleaning_log.txt        rows in, rows dropped per rule, rows out
    summary_by_group.csv    headline descriptives to start the analysis talk

The raw CSVs are only read. Nothing in the input folder is changed.
"""

import argparse
import glob
import os
import sys

import pandas as pd

# Duration rules. Change these two numbers if Nick rules differently Sunday.
MIN_RIDE_MINUTES = 1.0        # drop rides shorter than one minute
MAX_RIDE_MINUTES = 24 * 60.0  # drop rides longer than 24 hours

EXPECTED_COLUMNS = [
    "ride_id", "rideable_type", "started_at", "ended_at",
    "start_station_name", "start_station_id",
    "end_station_name", "end_station_id",
    "start_lat", "start_lng", "end_lat", "end_lng",
    "member_casual",
]


def course_day_of_week(started_at):
    """Course convention: 1 = Sunday through 7 = Saturday.

    pandas dayofweek counts Monday as 0 through Sunday as 6, so convert.
    Sunday (6) -> 1, Monday (0) -> 2, Saturday (5) -> 7.
    """
    return (started_at.dt.dayofweek + 1) % 7 + 1


def clean_one_file(path, seen_ride_ids, log):
    """Clean one monthly file. Returns a cleaned DataFrame."""
    name = os.path.basename(path)
    df = pd.read_csv(path, dtype=str, low_memory=False)
    rows_in = len(df)
    log.append(f"{name}: rows in = {rows_in:,}")

    missing = [c for c in EXPECTED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"{name} is missing expected columns: {missing}")

    # Timestamps first, because every later rule depends on them.
    df["started_at"] = pd.to_datetime(df["started_at"], errors="coerce")
    df["ended_at"] = pd.to_datetime(df["ended_at"], errors="coerce")
    bad_times = int(df["started_at"].isna().sum() + df["ended_at"].isna().sum())
    df = df.dropna(subset=["started_at", "ended_at"])
    log.append(f"  unparseable timestamps dropped: {bad_times:,}")

    # Derived columns, per the case study.
    df["ride_length_minutes"] = (
        df["ended_at"] - df["started_at"]
    ).dt.total_seconds() / 60.0
    df["day_of_week"] = course_day_of_week(df["started_at"])
    df["month"] = df["started_at"].dt.month
    df["is_weekend"] = df["day_of_week"].isin([1, 7])

    # Rule: ended before it started.
    n = int((df["ride_length_minutes"] < 0).sum())
    df = df[df["ride_length_minutes"] >= 0]
    log.append(f"  negative ride length dropped: {n:,}")

    # Rule: duration bounds, using the constants at the top of this file.
    n_short = int((df["ride_length_minutes"] < MIN_RIDE_MINUTES).sum())
    df = df[df["ride_length_minutes"] >= MIN_RIDE_MINUTES]
    n_long = int((df["ride_length_minutes"] > MAX_RIDE_MINUTES).sum())
    df = df[df["ride_length_minutes"] <= MAX_RIDE_MINUTES]
    log.append(f"  under {MIN_RIDE_MINUTES:g} minute dropped: {n_short:,}")
    log.append(f"  over {MAX_RIDE_MINUTES:g} minutes dropped: {n_long:,}")

    # Rule: duplicate ride_id, tracked across all twelve files.
    before = len(df)
    df = df[~df["ride_id"].isin(seen_ride_ids)]
    df = df.drop_duplicates(subset=["ride_id"])
    seen_ride_ids.update(df["ride_id"].tolist())
    log.append(f"  duplicate ride_id dropped: {before - len(df):,}")

    # Counts only, no drops: these get reported, and the rows stay.
    null_start = int(df["start_station_name"].isna().sum())
    null_end = int(df["end_station_name"].isna().sum())
    log.append(f"  null start station names kept: {null_start:,}")
    log.append(f"  null end station names kept: {null_end:,}")
    groups = sorted(df["member_casual"].dropna().unique().tolist())
    log.append(f"  member_casual values found: {groups}")
    unexpected = [g for g in groups if g not in ("member", "casual")]
    if unexpected:
        log.append(f"  WARNING unexpected member_casual values: {unexpected}")

    log.append(f"  rows out = {len(df):,}")
    return df


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", required=True,
                        help="Folder holding the twelve unzipped monthly CSVs")
    parser.add_argument("--output-dir", default="output",
                        help="Folder for the cleaned CSV, log, and summary")
    args = parser.parse_args()

    files = sorted(glob.glob(os.path.join(args.input_dir, "*.csv")))
    if not files:
        print(f"No CSV files found in {args.input_dir}", file=sys.stderr)
        return 1
    os.makedirs(args.output_dir, exist_ok=True)

    log = [f"Files to process: {len(files)}",
           f"Duration rules: keep {MIN_RIDE_MINUTES:g} to "
           f"{MAX_RIDE_MINUTES:g} minutes"]
    seen_ride_ids = set()
    cleaned_path = os.path.join(args.output_dir, "cyclistic_cleaned.csv")
    total_in_marker = 0
    first_write = True
    summaries = []

    for path in files:
        cleaned = clean_one_file(path, seen_ride_ids, log)
        total_in_marker += len(cleaned)
        cleaned.to_csv(cleaned_path, mode="w" if first_write else "a",
                       header=first_write, index=False)
        first_write = False
        if len(cleaned):
            summaries.append(cleaned.groupby("member_casual").agg(
                rides=("ride_id", "count"),
                sum_ride_minutes=("ride_length_minutes", "sum"),
                max_ride_minutes=("ride_length_minutes", "max"),
            ))

    log.append(f"TOTAL rows out across all files: {total_in_marker:,}")
    log_text = "\n".join(log)
    print(log_text)
    with open(os.path.join(args.output_dir, "cleaning_log.txt"), "w") as f:
        f.write(log_text + "\n")

    if summaries:
        # Combine per-file summaries by total minutes, not by averaging the
        # per-file means. Months carry very different ride counts, so a mean
        # of monthly means would overweight low-volume months.
        combined = pd.concat(summaries).groupby(level=0).agg(
            rides=("rides", "sum"),
            sum_ride_minutes=("sum_ride_minutes", "sum"),
            max_ride_minutes=("max_ride_minutes", "max"),
        )
        combined["mean_ride_minutes"] = (
            combined["sum_ride_minutes"] / combined["rides"]
        )
        summary = combined[["rides", "mean_ride_minutes", "max_ride_minutes"]]
        summary.to_csv(os.path.join(args.output_dir, "summary_by_group.csv"))
    print(f"\nCleaned data: {cleaned_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
