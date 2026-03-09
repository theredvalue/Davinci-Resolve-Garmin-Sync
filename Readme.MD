# Davinci Resolve Fusion - Garmin Calorie and Heartrate Sync

This library is created to help [The Red Value](https://www.youtube.com/@TheRedValue) sync his calorie and heart rate data to his Davinci Resolve Video Editing. It takes Garmin Fit File Data and links it to Video Created Timestamps of Video Files to automatically take data from his Garmin Smartwatch export and display it within Davinci Resolve.


## Install

* Python Libraries: [Pydantic](https://pypi.org/project/pydantic/), [Pandas](https://pypi.org/project/pandas/), [Fitparse](https://pypi.org/project/fitparse/) 

## Usage

To use this code, first export [Garmin Data](https://support.garmin.com/en-US/?faq=W1TvTPW8JZ6LfJSfK512Q8). Then, first use the files in the *supplemental* folder:
* *export_garmin_fit_to_csv.py*: Combines the exported Garmin Data into a single CSV file
* *reconstruct_garmin_hr_calorie_data.py*: Reconstructs Garmin Data timestamps from the obtained CSV file. Reconstructs calorie and heartrate data.
* *update_video_timestamps.py*: Tool used to try and match timestamps from certain videos if for some reason misaligned. Manual code changes required to use in your specific use case

Now make sure you your installed Davinci Resolve Python library is added to your Python Path environment variable. On Windows it would look something like this:
`PYTHONPATH="C:\ProgramData\Blackmagic Design\DaVinci Resolve\Support\Developer\Scripting\Modules"`

Now you can add the calorie and heart rate script with input parameters like this. Add `csv_path`, `name` and `daily_base_calories` parameters and have those be displayed in the video.

```python
from heartrateCaloryDisplay import generate_calorie_hr_count, DisplayConfig

generate_calorie_hr_count(config=DisplayConfig(
    left = {"csv_path":r"path/to/left.csv", "name":"Niko", "daily_base_calories":3000},
    right = {"csv_path":r"path/to/right.csv", "name":"Quinlan", "daily_base_calories":2000},
    time_offset = 8
))
```

## Maintainers
[The Red Value](https://www.youtube.com/@TheRedValue)

## Contributing
Dunno, maybe you can do something?

### Contributors
Me, myself and I


## License
I have no clue what I should put in here
