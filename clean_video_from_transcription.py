# this script will read the transcription from the output JSON file and then clean the video
# from filler words (e.g. um, uh, like, etc.)
#
# Usage:
# python clean_video_from_transcription.py <input_video_file> <input_json_file> <output_video_file>
#
# Example:
# python clean_video_from_transcription.py "input_video.mp4" "input_json.json" "output_video.mp4"

import argparse
import json
import subprocess
import os
import re
import string
import uuid

# get the input video file and the output text file
parser = argparse.ArgumentParser()
parser.add_argument("input_video_file", help="input video file")
parser.add_argument("input_json_file", help="input json transcription file")
parser.add_argument("output_video_file", help="output video file")
args = parser.parse_args()

# get the input video file name and the output text file name
input_video_file = args.input_video_file
input_json_file = args.input_json_file
output_video_file = args.output_video_file

# read the input JSON file
print("Parsing the input JSON file...")
with open(input_json_file) as f:
    data = json.load(f)

# get all the items where .results.items.alternatives.content is a filler word
filler_words = ["um", "uh", "like", "you know", "so"]

# get the filler words from the JSON file
filler_words_from_json = []
for item in data["results"]["items"]:
    if item["type"] == "pronunciation":
        # check in lowercase
        if item["alternatives"][0]["content"].lower() in filler_words:
            filler_words_from_json.append(item)

# extract the timings from the filler words items, in (start, end) tuples
# parse float from string
filler_words_timings = [(0, 0)]
for item in filler_words_from_json:
    filler_words_timings.append((float(item["start_time"]), float(item["end_time"])))

# append in the end the duration of the video
# find the duration of the video using ffprobe
print("Finding the duration of the video...")
ffprobe_output = subprocess.check_output(["ffprobe", "-v", "error", "-show_entries",
                                          "format=duration", "-of",
                                          "default=noprint_wrappers=1:nokey=1",
                                         input_video_file])
video_duration = float(ffprobe_output)
filler_words_timings.append((video_duration, video_duration))

# sort the filler words timings by start time
filler_words_timings.sort(key=lambda x: x[0])

print(f"Found {len(filler_words_timings)-2} filler words in the video.")

print("Filler words timings:")
print(filler_words_timings[:5])

# build an ffmpeg filter to remove the filler words by using the timings
# e.g.
#      [0:v]trim=start=10:end=20,setpts=PTS-STARTPTS,format=yuv420p[0v];
#      [0:a]atrim=start=10:end=20,asetpts=PTS-STARTPTS[0a];
#      [0:v]trim=start=30:end=40,setpts=PTS-STARTPTS,format=yuv420p[1v];
#      [0:a]atrim=start=30:end=40,asetpts=PTS-STARTPTS[1a];
#      [0:v]trim=start=30:end=40,setpts=PTS-STARTPTS,format=yuv420p[2v];
#      [0:a]atrim=start=30:end=40,asetpts=PTS-STARTPTS[2a];
# and then concatenate the inputs
#      [0v][0a][1v][1a][2v][2a]concat=n=3:v=1:a=1[outv][outa]

n_filrs = 5 #len(filler_words_timings)

filter = ""
for i in range(1, n_filrs):
    # stagger the start and end time of the video and audio filters
    # so that we take the "non-filler" portion of the video
    start_time = filler_words_timings[i-1][1]
    end_time = filler_words_timings[i][0]

    # add the video filter
    filter += f"[0:v]trim=start={start_time}:end={end_time},setpts=PTS-STARTPTS[{i}v];"

    # add the audio filter
    filter += f"[0:a]atrim=start={start_time}:end={end_time},asetpts=PTS-STARTPTS[{i}a];"

# add the concat filter
filter += f"{''.join([f'[{i}v][{i}a]' for i in range(n_filrs)])}concat=n={n_filrs}:v=1:a=1[outv][outa]"
print("Filter:")
print(filter)

# run ffmpeg to remove the filler words
print("Removing the filler words from the video...")
subprocess.run(["ffmpeg", "-i", input_video_file, "-filter_complex", filter, "-map", "[outv]",
                "-map", "[outa]", "-y", output_video_file])

print("Done.")
