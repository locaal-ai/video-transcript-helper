# this script will add fade-in, fade-out effects and captions to a video
# based on the input timed chapters (output from summary_chapters_blog.py file)

import argparse
import json
import subprocess
import os

# get the input video file and the output text file
parser = argparse.ArgumentParser()
parser.add_argument("input_video_file", help="input video file")
parser.add_argument(
    "input_timed_chapters_file", help="input text file with timed chapters"
)
args = parser.parse_args()

# get the input video file name and the output text file name
input_video_file = args.input_video_file
input_timed_chapters_file = args.input_timed_chapters_file

chapters = []

# read the input text file
print("Parsing the input text file...")
with open(input_timed_chapters_file) as f:
    # each line in the file is a chapter, in the format:
    # <start_time> - <end_time> <chapter_title>
    # e.g.
    # 00:00 - 00:10 Introduction
    # 00:10 - 00:20 Chapter 1

    # read the lines
    lines = f.readlines()

    # split each line into start_time, end_time and chapter_title
    # and convert the start_time and end_time to seconds
    for line in lines:
        if line == "\n" or line == "":
            continue
        # split the line into start_time, end_time and chapter_title
        start_time, end_time_and_chapter_title = line.split(" - ")
        end_time, chapter_title = end_time_and_chapter_title.split(" ", 1)

        # convert the start_time and end_time to seconds
        start_time_seconds = sum(
            x * float(t) for x, t in zip([60, 1], start_time.split(":"))
        )
        end_time_seconds = sum(
            x * float(t) for x, t in zip([60, 1], end_time.split(":"))
        )

        # add the chapter to the list of chapters
        chapters.append((start_time_seconds, end_time_seconds, chapter_title.strip()))

print(f"Found {len(chapters)} chapters.")

# sort the chapters by start_time
chapters.sort(key=lambda x: x[0])

# create an .ass file with the captions in Advanced SSA format
# each chapter will have a caption at the beginning of the chapter

# create the output file name
output_srt_file = os.path.splitext(input_video_file)[0] + ".ass"
print(f"Creating the output file {output_srt_file}...")

# write a times in seconds in HH:MM:SS,MS format
write_srt_format = (
    lambda x: f"{str(int(x//3600)).zfill(2)}:{str(int((x%3600)//60)).zfill(2)}:{str(int(x%60)).zfill(2)},000"
)

ssa_prefix = """
[Script Info]
Title: <untitled>
ScriptType: v4.00+
Collisions: Normal
PlayDepth: 0

[v4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,20,&H00FFFFFF,&H000080FF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,2,2,2,10,10,20,0

[Events]
Format: Layer, Start, End, Style, Actor, MarginL, MarginR, MarginV, Effect, Text
"""

# create the output file
with open(output_srt_file, "w") as f:
    # write the prefix
    f.write(ssa_prefix)
    # write the captions
    for i, chapter in enumerate(chapters):
        # each subtitle is of the form e.g.
        # Dialogue: 0,0:00:03.00,0:00:08.00,Default,,0,0,0,,subtitle text

        # write the subtitle line to the file. The subtitle will be shown for 5 seconds
        f.write(
            f"Dialogue: 0,{write_srt_format(chapter[0])},{write_srt_format(chapter[0]+5)},Default,,0,0,0,,{'{'}\\fad(1200,250){'}'}{chapter[2]}\n"
        )

    f.close()

# get the duration of the video
print("Getting the duration of the video...")
result = subprocess.run(
    [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        input_video_file,
    ],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
)
duration = int(float(result.stdout))

print(f"Video duration: {duration} seconds.")

output_video_file_path = os.path.splitext(input_video_file)[0] + "_with_captions.mp4"

# add the captions to the video with ffmpeg
print("Adding captions and fades to the video...")
subprocess.run(
    [
        "ffmpeg",
        "-i",
        input_video_file,
        "-vf",
        f"subtitles={output_srt_file}:force_style='Fontsize=24,PrimaryColour=&Hffffff&'[v];[v]fade=in:st=0:n=30,fade=out:st={duration-30}:n=30",
        "-c:v",
        "libx264",
        "-c:a",
        "copy",
        "-y",
        output_video_file_path,
    ]
)

# delete the temporary files
print("Deleting the temporary files...")
os.remove(output_srt_file)

print("Done!")
