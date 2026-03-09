#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
This script imports resolve clip markers
in to fusion page as text+ tool with keyframes.
Iddo Lahman, Bootke color studio, iddolahman@gmail.com
'''
import sys
from pprint import pprint
import time
import numpy as np
import random
from datetime import datetime as dt, timedelta
import pandas as pd
import re

from pydantic import BaseModel, Field, model_validator
from typing import Literal, Optional, Dict


import DaVinciResolveScript as dvr

resolve = dvr.scriptapp("Resolve")

if resolve == None:
    sys.exit(-1)



class UserConfig(BaseModel):
    csv_path: str
    name: str
    daily_base_calories: int
    max_heart_rate_variation: int = 4

class DisplayConfig(BaseModel):
    left: Optional[UserConfig] = None
    right: Optional[UserConfig] = None
    time_offset: int = 0 # in hours, to align the time of the video clips with the time in the csv

class Marker(BaseModel):
    color: str
    note: str
    name: str

class ClipData(BaseModel):
    start_time: dt
    start_frame: int
    end_frame: int
    fps: float
    markers: Optional[Dict[int, Marker]] = {}

    # derived maps
    left_map: Dict[int, int] = Field(default_factory=dict)
    right_map: Dict[int, int] = Field(default_factory=dict)

    left_array: list[float] = Field(default_factory=list)
    right_array: list[float] = Field(default_factory=list)

    @model_validator(mode="after")
    def extract_marker_offsets(self):

        left_map = {}
        right_map = {}

        for marker_idx, marker in self.markers.items():
            for line in marker.note.splitlines():
                l = re.match(r"^left:\s*(-?\d+)", line.strip())
                if l:
                    left_map[marker_idx] = int(l.group(1))

                r = re.match(r"^right:\s*(-?\d+)", line.strip())
                if r:
                    right_map[marker_idx] = int(r.group(1))

        self.left_map = left_map
        self.right_map = right_map

        frame_count = self.end_frame - self.start_frame + 1

        self.left_array = self._interpolate(left_map, frame_count)
        self.right_array = self._interpolate(right_map, frame_count)

        return self

    def _interpolate(self, mapping: Dict[int, int], frame_count: int) -> list[float]:
        if frame_count <= 0:
            return []

        result = [0.0] * frame_count

        if not mapping:
            return result

        points = [(0, 0.0)]
        for frame, val in sorted(mapping.items()):
            rel_frame = frame - self.start_frame
            if 0 <= rel_frame < frame_count:
                points.append((rel_frame, float(val)))

        last_frame = frame_count - 1
        if points[-1][0] != last_frame:
            points.append((last_frame, points[-1][1]))

        for (f0, v0), (f1, v1) in zip(points, points[1:]):
            span = max(f1 - f0, 1)
            for f in range(f0, f1 + 1):
                t = (f - f0) / span
                result[f] = v0 + (v1 - v0) * t

        return result





def heart_rate_noise(mean=0, stddev=1.2, clamp=3):
    x = round(random.gauss(mean, stddev))  # mean=0, stddev=2 (tune this)
    return max(-clamp, min(clamp, x))      # clamp to [-3, 3]


#=-=-=-=-=-=-=-=-= Utils =-=-=-=-=-=-=-=-=-=-=-=-=-=

def set_tool_style(text_tool, size=0.831, center=[0.5, 0.5]):
    text_tool.Font = "Montserrat"
    text_tool.Style = "Black"
    text_tool.HorizontalLeftCenterRight = 0
    text_tool.Size = size
    text_tool.Center = center
    text_tool.Red1, text_tool.Blue1, text_tool.Green1  = 1, 1, 1


def delete_tools(comp, media_out=False):
    """Deletes all tools in the composition"""

    tools = comp.GetToolList()

    for key, tool in tools.items():
        if tool.Name not in ["MediaIn1","MediaOut1"] or media_out==True:
            tool.Delete()

def create_display(comp, name: str, heart_rate_keyframes, calorie_keyframes, position=Literal["left", "right"]):
    """Parse markers dict and apply data to text tool"""
    
    # create new textbox
    name_tool = comp.TextPlus()
    set_tool_style(name_tool, size=0.0772, center=[0.5, 0.585])
    name_tool.StyledText = name
    
    hr_tool = comp.TextPlus()
    set_tool_style(hr_tool, size=0.0772, center=[0.5, 0.5])
    hr_spline = comp.BezierSpline()
    hr_spline.SetKeyFrames({0: {1:0}})
    hr_tool.StyledText = hr_spline
    for idx, val in heart_rate_keyframes.items():
        hr_tool.StyledText[idx] = f"HR {val}"

    cal_tool = comp.TextPlus()
    set_tool_style(cal_tool,size=0.0588, center=[0.5, 0.425])
    calorie_spline = comp.BezierSpline()
    calorie_spline.SetKeyFrames({0: {1:0}})
    cal_tool.StyledText = calorie_spline
    for idx, val in calorie_keyframes.items():
        cal_tool.StyledText[idx] = f"{val} kcal"

    multi_merge = comp.MultiMerge()
    multi_merge.ConnectInput("Background", name_tool)
    multi_merge.ConnectInput("Layer1.Foreground", hr_tool)
    multi_merge.ConnectInput("Layer2.Foreground", cal_tool)

    xf_tool = comp.Transform()
    if position == "left":
        xf_tool.Center = [0.126, 0.27]
    elif position == "right":
        xf_tool.Center = [1-0.126, 0.27]
    xf_tool.ConnectInput("Input", multi_merge)

    return xf_tool


def determine_heart_rate(df: pd.DataFrame, clip_data: ClipData, position: Literal["left", "right"], update_interval=2, max_var=5 ):
    keyframes = {}
    clip_data.markers = clip_data.markers or {}
    if position == "left":
        offset = clip_data.left_array
    elif position == "right":
        offset = clip_data.right_array
    for f in range(0, clip_data.end_frame-clip_data.start_frame+1, int(clip_data.fps*update_interval)):
        current_time = clip_data.start_time + timedelta(seconds = (f/clip_data.fps))
        idx = df["true_time_jst"].searchsorted(current_time)
        before_row = df.iloc[idx-1] if idx > 0 else None
        after_row = df.iloc[idx] if idx < len(df) else None
        if before_row is not None and after_row is not None:
            interval = after_row["true_time_jst"] - before_row["true_time_jst"]
            interval_passed_ratio = (current_time - before_row["true_time_jst"])/interval if interval != timedelta(0) else 0
            heart_rate = (before_row["heart_rate"]* (1 - interval_passed_ratio) + after_row["heart_rate"] * interval_passed_ratio)
            heart_rate += heart_rate_noise(clamp=max_var) + offset[f]
            keyframes[f] = round(heart_rate)
    return keyframes


def determine_calories(df: pd.DataFrame, clip_data: ClipData, daily_base_rate):
    keyframes = {}
    previous_calories = None
    start_of_day = clip_data.start_time.replace(hour=0, minute=0, second=0, microsecond=0)
    for f in range(0, clip_data.end_frame-clip_data.start_frame+1):
        current_time = clip_data.start_time + timedelta(seconds = (f/clip_data.fps))
        percentage_of_day = (current_time - start_of_day)/timedelta(days=1)
        idx = df["true_time_jst"].searchsorted(current_time)
        before_row = df.iloc[idx-1] if idx > 0 else None
        after_row = df.iloc[idx] if idx < len(df) else None
        if before_row is not None and after_row is not None:
            interval = after_row["true_time_jst"] - before_row["true_time_jst"]
            interval_passed_ratio = (current_time - before_row["true_time_jst"])/interval if interval != timedelta(0) else 0
            active_calories = before_row["cum_calories"] + interval_passed_ratio * after_row["calories_spent"] 
            calories = round(daily_base_rate * percentage_of_day + active_calories)
            if calories is None or calories != previous_calories:
                previous_calories = calories
                keyframes[f] = calories
    return keyframes


def load_csv(csv_path):
    df = pd.read_csv(csv_path)
    df["true_time_jst"] = pd.to_datetime(df["true_time_jst"])
    df_cal = df.dropna(subset=["cum_calories"])
    return df, df_cal
    

def generate_calorie_hr_count_per_user(comp, clip_data: ClipData, position: Literal["left", "right"], config: UserConfig):
    
    df_heart, df_cal = load_csv(config.csv_path)
    idx = df_heart["true_time_jst"].searchsorted(clip_data.start_time)
    heart_rate_graph = determine_heart_rate(df_heart, clip_data, position=position, max_var=config.max_heart_rate_variation)
    calorie_graph = determine_calories(df_cal,
                                       clip_data,
                                       config.daily_base_calories)

    idx = df_cal["true_time_jst"].searchsorted(clip_data.start_time)
    row_cal_1 = df_cal.iloc[idx-1] if idx > 0 else None
    row_cal_2 = df_cal.iloc[idx] if idx < len(df_cal) else None
    calories_spent = (clip_data.start_time - row_cal_1["true_time_jst"])/(row_cal_2["true_time_jst"] - row_cal_1["true_time_jst"])*row_cal_2["calories_spent"]

    print("Calories Total:", row_cal_1["cum_calories"],
          "Calories Spent:", calories_spent, "Calories Next Checkpoint", row_cal_2["calories_spent"])
    

    fusion_tool = create_display(comp, config.name, heart_rate_graph, calorie_graph, position=position)
    return fusion_tool




    
def generate_calorie_hr_count(config: DisplayConfig):
    proj = resolve.GetProjectManager().GetCurrentProject()
    #timeline = proj.GetCurrentTimeline()
    clip = proj.GetCurrentTimeline().GetCurrentVideoItem()
    media_pool_item = clip.GetMediaPoolItem()
    media_pool_item_data = media_pool_item.GetClipProperty()

    mpi_date_created_str = media_pool_item_data['Date Created']
    mpi_date_created = dt.strptime(mpi_date_created_str, "%a %b %d %Y %H:%M:%S")
    mpi_fps = media_pool_item_data['FPS']
    print("Date Created:", mpi_date_created)
    print("FPS:", mpi_fps)


    start_frame = clip.GetSourceStartFrame()
    end_frame = clip.GetSourceEndFrame()

    start_time = mpi_date_created + timedelta(seconds = start_frame / mpi_fps) + timedelta(hours = config.time_offset)

    markers = clip.GetMarkers()
    clip_data = ClipData(start_time=start_time, start_frame=start_frame, end_frame=end_frame, fps=mpi_fps, markers=markers)

    fusion_comp_list = clip.GetFusionCompNameList()
    if len(fusion_comp_list) == 0:
        clip.AddFusionComp()
    comp = clip.GetFusionCompByIndex(1)

    delete_tools(comp)

    fusion_node_left = None
    fusion_node_right = None

    if config.left is not None:
        fusion_node_left = generate_calorie_hr_count_per_user(comp, clip_data, "left", config.left)

    if config.right is not None:
        fusion_node_right = generate_calorie_hr_count_per_user(comp, clip_data, "right", config.right)


    media_in = comp.FindTool("MediaIn1")
    media_out = comp.FindTool("MediaOut1")
    merge_tool = comp.MultiMerge()
    input = media_out.FindMainInput(1)

    layer_index = 1
    if fusion_node_left is not None:
        merge_tool.ConnectInput(f"Layer{layer_index}.Foreground", fusion_node_left)
        layer_index+=1
    if fusion_node_right is not None:
        merge_tool.ConnectInput(f"Layer{layer_index}.Foreground", fusion_node_right)
    merge_tool.ConnectInput("Background", media_in)
    media_out.ConnectInput(input.Name,merge_tool)

