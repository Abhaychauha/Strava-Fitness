"""
Bellabeat Fitness Data Analytics Dashboard
===========================================
Streamlit app covering the Bellabeat / Fitbit case study:
  - Overview KPIs
  - Activity analysis (steps, intensity, calories by weekday/hour)
  - Sleep analysis
  - Heart rate analysis
  - Weight log
  - A built-in SQL Analysis workbench (query the SQLite DB directly)
  - Key findings & marketing recommendations

Run locally with:  streamlit run app.py
"""

import sqlite3
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

DB_PATH = Path(__file__).parent / "data" / "bellabeat.db"
WEEKDAY_ORDER = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]

st.set_page_config(page_title="Bellabeat Fitness Analytics", page_icon="🏃", layout="wide")


# ---------------------------------------------------------------- helpers --
@st.cache_resource
def get_connection():
    return sqlite3.connect(DB_PATH, check_same_thread=False)


@st.cache_data
def run_query(sql: str) -> pd.DataFrame:
    conn = get_connection()
    return pd.read_sql_query(sql, conn)


def weekday_sort(df: pd.DataFrame, col: str = "Weekday") -> pd.DataFrame:
    df[col] = pd.Categorical(df[col], categories=WEEKDAY_ORDER, ordered=True)
    return df.sort_values(col)


PRIMARY = "#2E86AB"
ACCENT = "#F26430"


# ------------------------------------------------------------------ sidebar
st.sidebar.title("🏃 Bellabeat Analytics")
st.sidebar.caption("Fitbit smart-device usage study")
page = st.sidebar.radio(
    "Navigate",
    ["Overview", "Activity", "Sleep", "Heart Rate", "Weight", "SQL Analysis", "Insights & Recommendations", "About the Data"],
)

all_ids = run_query("SELECT DISTINCT Id FROM daily_activity ORDER BY Id")["Id"].astype(str).tolist()
st.sidebar.markdown("---")
st.sidebar.markdown(f"**Users in dataset:** {len(all_ids)}")
selected_users = st.sidebar.multiselect("Filter by user ID (optional)", all_ids, default=[])
user_filter_sql = ""
if selected_users:
    ids_csv = ",".join(selected_users)
    user_filter_sql = f"AND Id IN ({ids_csv})"


# ===================================================================== 1 ==
if page == "Overview":
    st.title("Bellabeat Fitness Data — Overview")
    st.caption("Fitbit fitness-tracker data from 30+ users, April–May 2016. Source: Mobius / Kaggle, CC0.")

    kpi_sql = f"""
        SELECT
            COUNT(DISTINCT Id) AS users,
            ROUND(AVG(TotalSteps),0) AS avg_steps,
            ROUND(AVG(Calories),0) AS avg_calories,
            ROUND(AVG(SedentaryMinutes)/60.0,1) AS avg_sedentary_hrs,
            ROUND(AVG(TotalActiveMinutes),1) AS avg_active_minutes
        FROM daily_activity WHERE 1=1 {user_filter_sql}
    """
    k = run_query(kpi_sql).iloc[0]
    sleep_avg = run_query(f"SELECT ROUND(AVG(TotalSleepHours),1) AS h FROM sleep_day WHERE 1=1 {user_filter_sql}").iloc[0, 0]

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Users", int(k["users"]))
    c2.metric("Avg. Daily Steps", f"{int(k['avg_steps']):,}")
    c3.metric("Avg. Daily Calories", f"{int(k['avg_calories']):,}")
    c4.metric("Avg. Sedentary Time", f"{k['avg_sedentary_hrs']} hrs")
    c5.metric("Avg. Sleep", f"{sleep_avg if sleep_avg else '—'} hrs")

    st.markdown("---")
    col1, col2 = st.columns(2)

    with col1:
        df = weekday_sort(run_query(f"""
            SELECT Weekday, ROUND(AVG(TotalSteps),0) AS AvgSteps
            FROM daily_activity WHERE 1=1 {user_filter_sql} GROUP BY Weekday
        """))
        fig = px.bar(df, x="Weekday", y="AvgSteps", title="Average Steps by Weekday",
                     color="AvgSteps", color_continuous_scale="Blues", text="AvgSteps")
        fig.add_hline(y=10000, line_dash="dot", line_color=ACCENT, annotation_text="CDC 10,000-step goal")
        fig.update_traces(textposition="outside")
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        df = weekday_sort(run_query(f"""
            SELECT Weekday, ROUND(AVG(SedentaryMinutes)/60.0,1) AS AvgSedentaryHrs
            FROM daily_activity WHERE 1=1 {user_filter_sql} GROUP BY Weekday
        """))
        fig = px.bar(df, x="Weekday", y="AvgSedentaryHrs", title="Average Sedentary Hours by Weekday",
                     color="AvgSedentaryHrs", color_continuous_scale="Reds", text="AvgSedentaryHrs")
        fig.update_traces(textposition="outside")
        st.plotly_chart(fig, use_container_width=True)

    df = weekday_sort(run_query(f"""
        SELECT Weekday, ROUND(AVG(VeryActiveMinutes),1) AS VeryActive,
               ROUND(AVG(FairlyActiveMinutes),1) AS FairlyActive,
               ROUND(AVG(LightlyActiveMinutes),1) AS LightlyActive
        FROM daily_activity WHERE 1=1 {user_filter_sql} GROUP BY Weekday
    """))
    fig = px.bar(df, x="Weekday", y=["LightlyActive", "FairlyActive", "VeryActive"],
                 title="Time Spent in Each Activity Intensity, by Weekday", barmode="group")
    st.plotly_chart(fig, use_container_width=True)


# ===================================================================== 2 ==
elif page == "Activity":
    st.title("Activity Analysis")

    tab1, tab2, tab3 = st.tabs(["By Weekday", "By User", "By Hour"])

    with tab1:
        df = weekday_sort(run_query(f"""
            SELECT Weekday, ROUND(AVG(TotalSteps),0) AS AvgSteps, ROUND(AVG(Calories),0) AS AvgCalories,
                   ROUND(AVG(TotalActiveMinutes),1) AS AvgActiveMinutes
            FROM daily_activity WHERE 1=1 {user_filter_sql} GROUP BY Weekday
        """))
        fig = go.Figure()
        fig.add_bar(x=df["Weekday"], y=df["AvgActiveMinutes"], name="Avg Active Minutes", marker_color=PRIMARY)
        fig.add_trace(go.Scatter(x=df["Weekday"], y=df["AvgCalories"], name="Avg Calories",
                                  yaxis="y2", mode="lines+markers", line=dict(color=ACCENT, width=3)))
        fig.update_layout(
            title="Active Minutes vs. Calories Burnt by Weekday",
            yaxis=dict(title="Active Minutes"),
            yaxis2=dict(title="Calories", overlaying="y", side="right"),
        )
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(df, use_container_width=True, hide_index=True)

    with tab2:
        df = run_query(f"""
            SELECT Id, Weekday, ROUND(AVG(TotalSteps),0) AS AvgSteps
            FROM daily_activity WHERE 1=1 {user_filter_sql} GROUP BY Id, Weekday
        """)
        pivot = df.pivot(index="Id", columns="Weekday", values="AvgSteps")[WEEKDAY_ORDER]
        pivot["Grand Total"] = pivot.mean(axis=1).round(0)
        pivot = pivot.sort_values("Grand Total")
        st.markdown("**Average steps taken by each participant, by weekday** — heat-mapped like the original Tableau study.")
        st.dataframe(pivot.style.background_gradient(cmap="RdYlBu_r", axis=None).format("{:.0f}"), use_container_width=True)

        st.markdown("**Sedentary days per user** — days where SedentaryMinutes ≥ 1440 (tracker likely not worn / no movement logged)")
        sed = run_query(f"""
            SELECT Id, COUNT(*) AS FullDaySedentaryCount
            FROM daily_activity WHERE full_day_sedentary = 1 {user_filter_sql}
            GROUP BY Id ORDER BY FullDaySedentaryCount DESC
        """)
        if len(sed):
            st.dataframe(sed, use_container_width=True, hide_index=True)
        else:
            st.info("No full-day sedentary (≥1440 min) records for current filter.")

    with tab3:
        df = run_query(f"""
            SELECT Hour, ROUND(AVG(Calories),1) AS AvgCalories, ROUND(AVG(StepTotal),0) AS AvgSteps,
                   ROUND(AVG(TotalIntensity),2) AS AvgIntensity
            FROM hourly_activity WHERE 1=1 {user_filter_sql} GROUP BY Hour ORDER BY Hour
        """)
        fig = px.bar(df, x="Hour", y="AvgCalories", title="Average Calories Burnt by Hour of Day",
                     color="AvgCalories", color_continuous_scale="Blues")
        st.plotly_chart(fig, use_container_width=True)
        fig2 = px.line(df, x="Hour", y="AvgSteps", markers=True, title="Average Steps by Hour of Day")
        fig2.update_traces(line_color=ACCENT)
        st.plotly_chart(fig2, use_container_width=True)


# ===================================================================== 3 ==
elif page == "Sleep":
    st.title("Sleep Analysis")
    n_sleep_users = run_query(f"SELECT COUNT(DISTINCT Id) AS n FROM sleep_day WHERE 1=1 {user_filter_sql}").iloc[0, 0]
    st.caption(f"{n_sleep_users} of {len(all_ids)} users logged sleep data at least once.")

    df = weekday_sort(run_query(f"""
        SELECT Weekday, ROUND(AVG(TotalSleepHours),2) AS AvgSleepHours,
               ROUND(AVG(TotalTimeInBed - TotalMinutesAsleep),1) AS AvgAwakeInBedMin
        FROM sleep_day WHERE 1=1 {user_filter_sql} GROUP BY Weekday
    """))
    col1, col2 = st.columns(2)
    with col1:
        fig = px.bar(df, x="Weekday", y="AvgSleepHours", title="Average Sleep Duration by Weekday",
                     color="AvgSleepHours", color_continuous_scale="Purples", text="AvgSleepHours")
        fig.add_hline(y=8, line_dash="dot", line_color=ACCENT, annotation_text="8-hr recommendation")
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        fig = px.bar(df, x="Weekday", y="AvgAwakeInBedMin", title="Avg. Minutes Awake-in-Bed by Weekday",
                     color="AvgAwakeInBedMin", color_continuous_scale="Oranges")
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("**Sleep efficiency by user** (minutes asleep ÷ minutes in bed)")
    eff = run_query(f"""
        SELECT Id, ROUND(AVG(TotalMinutesAsleep),0) AS AvgMinutesAsleep,
               ROUND(AVG(TotalTimeInBed),0) AS AvgMinutesInBed,
               ROUND(100.0*AVG(TotalMinutesAsleep)/AVG(TotalTimeInBed),1) AS SleepEfficiencyPct
        FROM sleep_day WHERE 1=1 {user_filter_sql} GROUP BY Id ORDER BY SleepEfficiencyPct ASC
    """)
    st.dataframe(eff, use_container_width=True, hide_index=True)

    st.markdown("**Steps vs. sleep relationship** (does a more active day correlate with more sleep?)")
    corr_df = run_query(f"""
        SELECT a.TotalSteps, s.TotalSleepHours
        FROM daily_activity a JOIN sleep_day s ON a.Id = s.Id AND a.ActivityDate = s.SleepDay
        WHERE 1=1 {user_filter_sql.replace('Id', 'a.Id')}
    """)
    if len(corr_df):
        fig = px.scatter(corr_df, x="TotalSteps", y="TotalSleepHours", trendline="ols",
                          title="Daily Steps vs. Sleep Hours (per user-day)", opacity=0.6)
        st.plotly_chart(fig, use_container_width=True)
        st.caption(f"Pearson correlation: **{corr_df['TotalSteps'].corr(corr_df['TotalSleepHours']):.2f}**")


# ===================================================================== 4 ==
elif page == "Heart Rate":
    st.title("Heart Rate Analysis")
    hr_users = run_query(f"SELECT COUNT(DISTINCT Id) AS n FROM heartrate_hourly WHERE 1=1 {user_filter_sql}").iloc[0, 0]
    st.caption(f"Heart-rate data (aggregated from second-level readings to hourly) is available for {hr_users} users.")

    if hr_users == 0:
        st.warning("No heart-rate data for the selected user filter. Clear the filter or pick a user with HR data.")
    else:
        df = run_query(f"""
            SELECT Hour, ROUND(AVG(AvgHeartRate),1) AS AvgHR, ROUND(AVG(MaxHeartRate),1) AS AvgMaxHR
            FROM heartrate_hourly WHERE 1=1 {user_filter_sql} GROUP BY Hour ORDER BY Hour
        """)
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df["Hour"], y=df["AvgHR"], name="Avg Heart Rate", line=dict(color=PRIMARY)))
        fig.add_trace(go.Scatter(x=df["Hour"], y=df["AvgMaxHR"], name="Avg Peak Heart Rate", line=dict(color=ACCENT, dash="dot")))
        fig.update_layout(title="Heart Rate by Hour of Day (all users)", xaxis_title="Hour", yaxis_title="BPM")
        st.plotly_chart(fig, use_container_width=True)

        by_user = run_query(f"""
            SELECT Id, ROUND(AVG(AvgHeartRate),1) AS AvgHR, MAX(MaxHeartRate) AS MaxHR, MIN(MinHeartRate) AS MinHR
            FROM heartrate_hourly WHERE 1=1 {user_filter_sql} GROUP BY Id ORDER BY AvgHR DESC
        """)
        st.markdown("**Per-user heart-rate summary**")
        st.dataframe(by_user, use_container_width=True, hide_index=True)


# ===================================================================== 5 ==
elif page == "Weight":
    st.title("Weight Log")
    w = run_query(f"SELECT * FROM weight_log WHERE 1=1 {user_filter_sql} ORDER BY Id, Date")
    st.caption(f"Only {w['Id'].nunique() if len(w) else 0} of {len(all_ids)} users logged weight — mostly manual entries, so this is the weakest signal in the dataset.")
    if len(w):
        fig = px.line(w, x="Date", y="WeightKg", color="Id", markers=True, title="Weight (kg) Over Time by User")
        st.plotly_chart(fig, use_container_width=True)

        bmi = w.dropna(subset=["BMI"]).groupby("Id", as_index=False)["BMI"].mean().round(1)
        fig2 = px.bar(bmi, x="Id", y="BMI", title="Average BMI by User")
        fig2.add_hline(y=25, line_dash="dot", line_color=ACCENT, annotation_text="Overweight threshold (25)")
        st.plotly_chart(fig2, use_container_width=True)
        st.dataframe(w, use_container_width=True, hide_index=True)
    else:
        st.info("No weight-log rows for current filter.")


# ===================================================================== 6 ==
elif page == "SQL Analysis":
    st.title("🗄️ SQL Analysis Workbench")
    st.caption("Query the cleaned SQLite database (`data/bellabeat.db`) directly. Read-only SELECT statements only.")

    with st.expander("📋 Database schema", expanded=False):
        schema = run_query("SELECT name, type FROM sqlite_master WHERE type IN ('table','view') ORDER BY type, name")
        for _, row in schema.iterrows():
            cols = run_query(f"PRAGMA table_info({row['name']})")
            st.markdown(f"**{row['name']}** ({row['type']}): " + ", ".join(cols["name"].tolist()))

    examples = {
        "Average steps by weekday": "SELECT Weekday, ROUND(AVG(TotalSteps),0) AS AvgSteps\nFROM daily_activity\nGROUP BY Weekday\nORDER BY AvgSteps DESC;",
        "Users not meeting 10,000 steps/day on average": "SELECT Id, ROUND(AVG(TotalSteps),0) AS AvgSteps\nFROM daily_activity\nGROUP BY Id\nHAVING AvgSteps < 10000\nORDER BY AvgSteps;",
        "Sleep vs. sedentary minutes": "SELECT a.Id, a.ActivityDate, a.SedentaryMinutes, s.TotalMinutesAsleep\nFROM daily_activity a\nJOIN sleep_day s ON a.Id = s.Id AND a.ActivityDate = s.SleepDay\nORDER BY a.SedentaryMinutes DESC\nLIMIT 20;",
        "Peak activity hour across all users": "SELECT Hour, ROUND(AVG(StepTotal),0) AS AvgSteps\nFROM hourly_activity\nGROUP BY Hour\nORDER BY AvgSteps DESC\nLIMIT 5;",
        "Calorie burn vs. avg heart rate by user": "SELECT d.Id, ROUND(AVG(d.Calories),0) AS AvgCalories, ROUND(AVG(h.AvgHeartRate),1) AS AvgHR\nFROM daily_activity d\nJOIN heartrate_hourly h ON d.Id = h.Id AND d.ActivityDate = h.Date\nGROUP BY d.Id\nORDER BY AvgHR DESC;",
    }
    choice = st.selectbox("Load an example query (optional)", ["— custom —"] + list(examples.keys()))
    default_sql = examples.get(choice, "SELECT *\nFROM daily_activity\nLIMIT 20;")

    sql = st.text_area("SQL query", value=default_sql, height=180)
    run = st.button("▶ Run query", type="primary")

    if run:
        stripped = sql.strip().rstrip(";").lower()
        if not stripped.startswith(("select", "with", "pragma")):
            st.error("Only read-only SELECT / WITH / PRAGMA statements are allowed in this workbench.")
        else:
            try:
                result = run_query(sql)
                st.success(f"{len(result):,} rows returned")
                st.dataframe(result, use_container_width=True)
                st.download_button("Download results as CSV", result.to_csv(index=False), "query_results.csv", "text/csv")

                numeric_cols = result.select_dtypes("number").columns.tolist()
                if len(result.columns) >= 2 and numeric_cols and len(result) <= 200:
                    x_col = result.columns[0]
                    y_col = st.selectbox("Chart Y-axis (optional)", ["(none)"] + numeric_cols)
                    if y_col != "(none)":
                        fig = px.bar(result, x=x_col, y=y_col, title=f"{y_col} by {x_col}")
                        st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.error(f"Query error: {e}")


# ===================================================================== 7 ==
elif page == "Insights & Recommendations":
    st.title("Key Findings & Marketing Recommendations")

    st.subheader("Key findings")
    st.markdown("""
1. **Most users fall short of the CDC's 10,000-step benchmark.** Average daily steps hover around 7,000–8,000, peaking on Tuesdays and Saturdays and dipping on Sundays.
2. **Sedentary time dominates the day.** Users average well over 15 hours/day sedentary — roughly a third of participants log 1,000+ sedentary minutes daily, and some days show a full 1,440 sedentary minutes, suggesting the tracker wasn't worn continuously.
3. **"Lightly active" minutes dwarf moderate/vigorous activity.** ~190 minutes/day are lightly active versus only ~15–20 minutes each of fairly/very active — activity is happening, but rarely at an intensity that meaningfully improves fitness.
4. **Sleep is inconsistent and under-logged.** Only a subset of users log sleep at all, and average sleep is under 8 hours even on the best day (Sunday, ~7 hrs).
5. **Weight logging is the weakest data point** — only ~8 of 33 users logged weight, mostly manually, limiting its usefulness as a behavioral signal.
6. **Engagement, not raw activity, is the real opportunity.** The data suggests the biggest gap isn't awareness of activity — it's *consistency* of tracker wear and follow-through on light activity turning into moderate activity.
    """)

    st.subheader("Recommendations for Bellabeat marketing strategy")
    st.markdown("""
1. **Position the product around consistency, not intensity.** Since most users already move lightly throughout the day, market smart nudges ("stand up," "you're 20 min from your goal") that convert light activity into moderate activity, rather than competing on intensity-tracking accuracy.
2. **Build a "wear-time" or gentle re-engagement nudge.** High full-day-sedentary counts likely reflect the device not being worn, not inactivity. A Bellabeat wellness feature that reminds users to wear the device (framed positively, e.g. a streak/habit feature) could close this gap and improve data quality simultaneously.
3. **Lead with sleep & recovery content.** Sleep is the most improvable, most under-tracked metric — Bellabeat's positioning as a *wellness* (not just fitness) brand is well suited to sleep-coaching content, wind-down reminders, and weekly sleep-consistency scores.
4. **Weekend-specific campaigns.** Saturday shows the highest steps but Sunday the lowest — a "recover well, restart strong" weekend campaign (Saturday activity, Sunday recovery/sleep) aligns messaging to the data's natural weekly rhythm.
5. **De-emphasize manual weight logging; automate what you can.** Given how rarely weight was logged, marketing/product energy is better spent on passive signals (steps, heart rate, sleep) than manually-entered ones.
    """)

    st.info("These are high-level, directional recommendations based on a small (33-user), short (≈1 month), demographically-unknown sample — see the *About the Data* page for limitations.")


# ===================================================================== 8 ==
elif page == "About the Data":
    st.title("About the Data")
    st.markdown("""
**Source:** Fitbit Fitness Tracker Data, made available by Kaggle user *Möbius* under a CC0 (public domain) license,
originally collected via Amazon Mechanical Turk between 03.12.2016 and 05.12.2016 for 30 eligible users
(this export contains 33 unique IDs across the daily-activity table).
DOI: `10.5281/zenodo.53894`.

**Business task:** How are consumers using their smart devices? Insights are used to inform Bellabeat's
marketing strategy for a wellness product aimed at women (case-study brief: Bellabeat, Urška Sršen / Sando Mur).

### Known limitations (documented in the source case study)
- **No demographic data** — age, sex, height, or profession of participants is unknown, so results can't
  be segmented or validated against a target demographic.
- **Small, short, dated sample** — 30–33 users over roughly a month in 2016; device usage patterns and
  wearable technology have both changed materially since.
- **Inconsistent logging** — not all users have a full 30/31 days of data; sleep and weight are logged by
  only a subset of users.
- **Distance unit is unspecified** in the original files (assumed miles/km per Fitbit's standard export, not verified).
- **`full_day_sedentary` flag** — days with ≥1,440 sedentary minutes (a full 24 hrs) most likely indicate the
  tracker wasn't worn, not that the user was awake and motionless all day; these are flagged, not dropped.

### Cleaning steps applied when building `bellabeat.db`
- Parsed all date/time strings into consistent ISO date formats.
- Added a `Weekday` column throughout for weekday-pattern analysis.
- Merged `dailyCalories` / `dailyIntensities` / `dailySteps` are **not** loaded separately since
  `dailyActivity_merged.csv` is a strict superset of their columns.
- Merged the three hourly files (calories, intensities, steps) into one `hourly_activity` table on (Id, ActivityHour).
- Aggregated the 2.4M-row, second-level `heartrate_seconds_merged.csv` into hourly avg/min/max/count —
  full second-level granularity isn't needed for behavioral analysis and would make the DB and queries far slower.
- Aggregated `minuteSleep_merged.csv` (sleep state per minute) into a per-day count of asleep/restless/awake minutes.
- Checked for and confirmed **no missing or negative values** in the core numeric fields.
- Built a `daily_summary` SQL **view** joining activity + sleep + weight per user/day for convenient querying.

### Files loaded into the database
`dailyActivity_merged.csv`, `hourlyCalories/Intensities/Steps_merged.csv`, `sleepDay_merged.csv`,
`weightLogInfo_merged.csv`, `heartrate_seconds_merged.csv` (aggregated), `minuteSleep_merged.csv` (aggregated).

The minute-level Narrow/Wide calories, intensities, and METs files were **not** loaded — their information is
already represented at hourly and daily grain, which is sufficient for the marketing-strategy business task.
    """)
