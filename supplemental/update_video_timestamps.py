import subprocess
import json
import os
from datetime import datetime, timedelta

# ---- USER CONFIG ----
WRONG_FILE = "GX011631.MP4"
RIGHT_FILE = "DJI_20260218030606_0853_D.MP4"

# Time inside WRONG_FILE that matches start of RIGHT_FILE (MM:SS)
MATCH_TIME = "09:53"

TIMEZONE_SHIFT = 0  # hours
# ---------------------


def get_create_date(file):
    result = subprocess.run(
        ["exiftool", "-json", "-CreateDate", file],
        capture_output=True,
        text=True
    )
    data = json.loads(result.stdout)
    if not data or "CreateDate" not in data[0]:
        raise ValueError(f"Could not read CreateDate from {file}")
    
    date_str = data[0]["CreateDate"]

    try:
        return datetime.strptime(date_str, "%Y:%m:%d %H:%M:%S%z")
    except ValueError:
        return datetime.strptime(date_str, "%Y:%m:%d %H:%M:%S")


def compute_offset():
    wrong_dt = get_create_date(WRONG_FILE)
    right_dt = get_create_date(RIGHT_FILE)

    minutes, seconds = map(int, MATCH_TIME.split(":"))
    match_delta = timedelta(minutes=minutes, seconds=seconds) 

    correct_wrong_dt = right_dt - match_delta #+ timedelta(hours=TIMEZONE_SHIFT)
    offset = correct_wrong_dt - wrong_dt

    print("Reference calculation:")
    print(" Wrong file original:", wrong_dt)
    print(" Right file base:    ", right_dt)
    print(" Match offset:       ", match_delta)
    print(" Correct wrong time: ", correct_wrong_dt)
    print(" Final offset:       ", offset)
    print()

    return offset


def update_file(file, offset):
    metadata = subprocess.run(
        ["exiftool", "-json", "-CreateDate", file],
        capture_output=True,
        text=True
    )
    data = json.loads(metadata.stdout)

    if not data or "CreateDate" not in data[0]:
        return

    original_dt = datetime.strptime(data[0]["CreateDate"], "%Y:%m:%d %H:%M:%S")

    """
    if original_dt.year != 2024:
        return
    """
    if not file.startswith("GX"):
        return

    new_dt = original_dt + offset
    formatted = new_dt.strftime("%Y:%m:%d %H:%M:%S+01:00")

    print(f"Updating {file}")
    print(f"  {original_dt}  →  {new_dt}")

    subprocess.run([
        "exiftool",
        "-overwrite_original",
        f"-QuickTime:CreateDate={formatted}",
        f"-QuickTime:ModifyDate={formatted}",
        f"-QuickTime:MediaCreateDate={formatted}",
        f"-QuickTime:TrackCreateDate={formatted}",
        f"-AllDates={formatted}",
        f"-FileModifyDate={formatted}",
        f"-FileCreateDate={formatted}",
        file
    ])


def main():
    offset = compute_offset()

    confirm = input("Apply this offset to all 2024 files? (y/N): ")
    if confirm.lower() != "y":
        print("Aborted.")
        return

    for file in os.listdir("."):
        if file.lower().endswith(".mp4"):
            update_file(file, offset)

    print("Done.")


if __name__ == "__main__":
    main()