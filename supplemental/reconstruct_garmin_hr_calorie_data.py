import pandas as pd
import numpy as np

df = pd.read_csv("combined_monitoring.csv")
df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
df["timestamp"] = df["timestamp"].ffill()


df["timestamp_16"] = pd.to_numeric(df["timestamp_16"], downcast='integer', errors="coerce")
df["timestamp_16"] = df["timestamp_16"].astype("Int64")

df["heart_rate"] = pd.to_numeric(df["heart_rate"], errors="coerce")
df["heart_rate"] = df["heart_rate"].ffill()
df["active_calories"] = pd.to_numeric(df["active_calories"], errors="coerce")


resting_calories_per_day = 2629

garmin_epoch = 631065600

# base timestamp
df["ts"] = pd.to_numeric(df["timestamp"], errors="coerce")//10**6 - garmin_epoch
df["true_time"] = df["timestamp"]
# rows where timestamp_16 exists
mask = df["timestamp_16"].notna()

ts16 = pd.to_numeric(df.loc[mask, "timestamp_16"], errors="coerce")
ts = df.loc[mask, "ts"]

df.loc[mask, "ts_temp"] = ts + ((ts16 - ts) & 0xFFFF)

df.loc[mask, "true_time"] = pd.to_datetime(
    df.loc[mask, "ts_temp"] + garmin_epoch,
    unit="s"
)

print(df["true_time"])

# add 9 hours
df["true_time_jst"] = df["true_time"] + pd.Timedelta(hours=9)

# extract day in JST
df["day_jst"] = df["true_time_jst"].dt.date


df["calories_spent"] = (
    df.groupby(["source_folder", "activity_type"])["active_calories"]
      .diff()
)
df["cum_calories"] = df.groupby("day_jst")["calories_spent"].cumsum()

# seconds since midnight JST
seconds_since_midnight = (
    df["true_time_jst"] - df["true_time_jst"].dt.floor("D")
).dt.total_seconds()

# resting calories accumulated so far in the day
df["resting_calories"] = (
    resting_calories_per_day * seconds_since_midnight / 86400
)

# total calories = activity cumulative + resting portion
df["total_calories"] = df["cum_calories"] + df["resting_calories"]


print(df[["true_time_jst", "day_jst", "activity_type", "active_calories", "calories_spent", "cum_calories", "total_calories", "heart_rate"]])
new_df = df[["true_time_jst", "day_jst", "activity_type", "active_calories", "calories_spent", "cum_calories", "total_calories", "heart_rate"]]
new_df.to_csv("calories_spent.csv", index=False)