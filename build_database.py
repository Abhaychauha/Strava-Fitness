"""
build_database.py
------------------
Bellabeat / Strava Fitness Data Analytics Case Study

Reads the raw Fitbit CSV exports and builds a single clean SQLite database
(bellabeat.db) that the Streamlit app queries with SQL.

Design decisions (documented for the case-study write-up):
- dailyActivity_merged.csv already contains all columns found in
  dailyCalories/dailyIntensities/dailySteps, so only the daily table is kept.
- Hourly calories/intensities/steps are merged into ONE hourly_activity table
  on (Id, ActivityHour) since they share the same grain.
- heartrate_seconds_merged.csv (2.4M rows, second-level) is aggregated to
  hourly resolution (avg/min/max/count of readings) so the dashboard and
  ad-hoc SQL queries stay fast. The raw file is far too granular for
  day-to-day analysis and would bloat the DB to ~90MB for little analytic
  value beyond what an hourly average already captures.
- minuteSleep_merged.csv is aggregated into a per-day sleep summary
  (sleepDay_merged.csv is also kept as-is since it's the primary sleep table).
- Dates are parsed and stored as proper SQLite TIMESTAMP/TEXT ISO strings so
  they sort and filter correctly, and weekday name columns are added for the
  weekday-pattern analysis shown in the case study PDF.
- Rows with SedentaryMinutes >= 1440 (i.e. the tracker likely wasn't worn all
  day) are flagged with a `full_day_sedentary` column rather than dropped,
  so analysts can choose to filter them in SQL.
"""

import sqlite3
import pandas as pd
from pathlib import Path

RAW = Path("/mnt/user-data/uploads")
DB_PATH = Path(__file__).parent / "data" / "bellabeat.db"
DB_PATH.parent.mkdir(exist_ok=True)

WEEKDAY_ORDER = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]


def log(msg):
    print(f"[build_database] {msg}")


def connect():
    if DB_PATH.exists():
        DB_PATH.unlink()
    return sqlite3.connect(DB_PATH)


def load_daily_activity(conn):
    log("Loading daily_activity ...")
    df = pd.read_csv(RAW / "dailyActivity_merged.csv")
    df["ActivityDate"] = pd.to_datetime(df["ActivityDate"], format="%m/%d/%Y")
    df["Weekday"] = pd.Categorical(df["ActivityDate"].dt.day_name(), categories=WEEKDAY_ORDER, ordered=True)
    df["full_day_sedentary"] = df["SedentaryMinutes"] >= 1440
    df["TotalActiveMinutes"] = df["VeryActiveMinutes"] + df["FairlyActiveMinutes"] + df["LightlyActiveMinutes"]
    df = df.rename(columns={"Id": "Id"})
    df["ActivityDate"] = df["ActivityDate"].dt.strftime("%Y-%m-%d")
    df.to_sql("daily_activity", conn, index=False, if_exists="replace")
    log(f"  -> {len(df):,} rows, {df['Id'].nunique()} users")


def load_hourly_activity(conn):
    log("Loading hourly_activity (merging calories+intensities+steps) ...")
    cal = pd.read_csv(RAW / "hourlyCalories_merged.csv")
    inten = pd.read_csv(RAW / "hourlyIntensities_merged.csv")
    steps = pd.read_csv(RAW / "hourlySteps_merged.csv")

    for d in (cal, inten, steps):
        d["ActivityHour"] = pd.to_datetime(d["ActivityHour"], format="%m/%d/%Y %I:%M:%S %p")

    merged = cal.merge(inten, on=["Id", "ActivityHour"]).merge(steps, on=["Id", "ActivityHour"])
    merged["Date"] = merged["ActivityHour"].dt.strftime("%Y-%m-%d")
    merged["Hour"] = merged["ActivityHour"].dt.hour
    merged["Weekday"] = pd.Categorical(merged["ActivityHour"].dt.day_name(), categories=WEEKDAY_ORDER, ordered=True)
    merged["ActivityHour"] = merged["ActivityHour"].dt.strftime("%Y-%m-%d %H:%M:%S")
    merged.to_sql("hourly_activity", conn, index=False, if_exists="replace")
    log(f"  -> {len(merged):,} rows")


def load_sleep(conn):
    log("Loading sleep_day ...")
    df = pd.read_csv(RAW / "sleepDay_merged.csv")
    df["SleepDay"] = pd.to_datetime(df["SleepDay"], format="%m/%d/%Y %I:%M:%S %p")
    df["Weekday"] = pd.Categorical(df["SleepDay"].dt.day_name(), categories=WEEKDAY_ORDER, ordered=True)
    df["TotalSleepHours"] = df["TotalMinutesAsleep"] / 60
    df["TimeAwakeInBedMinutes"] = df["TotalTimeInBed"] - df["TotalMinutesAsleep"]
    df["SleepDay"] = df["SleepDay"].dt.strftime("%Y-%m-%d")
    df.to_sql("sleep_day", conn, index=False, if_exists="replace")
    log(f"  -> {len(df):,} rows, {df['Id'].nunique()} users")


def load_weight(conn):
    log("Loading weight_log ...")
    df = pd.read_csv(RAW / "weightLogInfo_merged.csv")
    df["Date"] = pd.to_datetime(df["Date"], format="%m/%d/%Y %I:%M:%S %p")
    df["Date"] = df["Date"].dt.strftime("%Y-%m-%d")
    df.to_sql("weight_log", conn, index=False, if_exists="replace")
    log(f"  -> {len(df):,} rows, {df['Id'].nunique()} users")


def load_heartrate_hourly(conn):
    log("Aggregating heartrate_seconds_merged.csv -> heartrate_hourly (chunked read of 2.4M rows) ...")
    chunks = []
    for chunk in pd.read_csv(RAW / "heartrate_seconds_merged.csv", chunksize=500_000):
        chunk["Time"] = pd.to_datetime(chunk["Time"], format="%m/%d/%Y %I:%M:%S %p")
        chunk["Date"] = chunk["Time"].dt.strftime("%Y-%m-%d")
        chunk["Hour"] = chunk["Time"].dt.hour
        g = chunk.groupby(["Id", "Date", "Hour"])["Value"].agg(["mean", "min", "max", "count"]).reset_index()
        chunks.append(g)
    df = pd.concat(chunks, ignore_index=True)
    df = df.groupby(["Id", "Date", "Hour"]).agg(
        AvgHeartRate=("mean", "mean"),
        MinHeartRate=("min", "min"),
        MaxHeartRate=("max", "max"),
        ReadingCount=("count", "sum"),
    ).reset_index()
    df["AvgHeartRate"] = df["AvgHeartRate"].round(1)
    df.to_sql("heartrate_hourly", conn, index=False, if_exists="replace")
    log(f"  -> {len(df):,} rows, {df['Id'].nunique()} users")


def load_minute_sleep_summary(conn):
    log("Aggregating minuteSleep_merged.csv -> sleep_state_summary (value: 1=asleep,2=restless,3=awake) ...")
    df = pd.read_csv(RAW / "minuteSleep_merged.csv")
    df["date"] = pd.to_datetime(df["date"], format="%m/%d/%Y %I:%M:%S %p")
    df["Date"] = df["date"].dt.strftime("%Y-%m-%d")
    summary = df.groupby(["Id", "Date", "value"]).size().unstack(fill_value=0)
    summary = summary.rename(columns={1: "AsleepMinutes", 2: "RestlessMinutes", 3: "AwakeMinutes"}).reset_index()
    for col in ("AsleepMinutes", "RestlessMinutes", "AwakeMinutes"):
        if col not in summary.columns:
            summary[col] = 0
    summary.to_sql("sleep_state_summary", conn, index=False, if_exists="replace")
    log(f"  -> {len(summary):,} rows")


def build_daily_summary_view(conn):
    log("Creating daily_summary view (activity + sleep + weight joined) ...")
    conn.execute("DROP VIEW IF EXISTS daily_summary")
    conn.execute("""
        CREATE VIEW daily_summary AS
        SELECT
            a.Id,
            a.ActivityDate AS Date,
            a.Weekday,
            a.TotalSteps,
            a.TotalDistance,
            a.VeryActiveMinutes,
            a.FairlyActiveMinutes,
            a.LightlyActiveMinutes,
            a.SedentaryMinutes,
            a.TotalActiveMinutes,
            a.Calories,
            a.full_day_sedentary,
            s.TotalMinutesAsleep,
            s.TotalSleepHours,
            s.TotalTimeInBed,
            w.WeightKg,
            w.BMI
        FROM daily_activity a
        LEFT JOIN sleep_day s ON a.Id = s.Id AND a.ActivityDate = s.SleepDay
        LEFT JOIN weight_log w ON a.Id = w.Id AND a.ActivityDate = w.Date
    """)


def add_indexes(conn):
    log("Adding indexes ...")
    stmts = [
        "CREATE INDEX IF NOT EXISTS idx_daily_id ON daily_activity(Id)",
        "CREATE INDEX IF NOT EXISTS idx_daily_date ON daily_activity(ActivityDate)",
        "CREATE INDEX IF NOT EXISTS idx_hourly_id ON hourly_activity(Id)",
        "CREATE INDEX IF NOT EXISTS idx_hourly_date ON hourly_activity(Date)",
        "CREATE INDEX IF NOT EXISTS idx_sleep_id ON sleep_day(Id)",
        "CREATE INDEX IF NOT EXISTS idx_hr_id ON heartrate_hourly(Id)",
        "CREATE INDEX IF NOT EXISTS idx_hr_date ON heartrate_hourly(Date)",
        "CREATE INDEX IF NOT EXISTS idx_weight_id ON weight_log(Id)",
    ]
    for s in stmts:
        conn.execute(s)


def main():
    conn = connect()
    load_daily_activity(conn)
    load_hourly_activity(conn)
    load_sleep(conn)
    load_weight(conn)
    load_heartrate_hourly(conn)
    load_minute_sleep_summary(conn)
    build_daily_summary_view(conn)
    add_indexes(conn)
    conn.commit()
    conn.close()
    log(f"Done. Database written to {DB_PATH.resolve()}")


if __name__ == "__main__":
    main()
