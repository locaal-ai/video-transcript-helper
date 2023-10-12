# this script will read the transcription from the output JSON file and then clean the video
# from filler words (e.g. um, uh, like, etc.)
#
# Usage:
# python clean_video_from_transcription.py <input_video_file> <input_json_file>
#
# The output video file will be saved in the same directory as the input video file
#
# Example:
# python clean_video_from_transcription.py "input_video.mp4" "input_json.json"

import argparse
import json
import subprocess
import os

# get the input video file and the output text file
parser = argparse.ArgumentParser()
parser.add_argument("input_video_file", help="input video file")
parser.add_argument("input_json_file", help="input json transcription file")
args = parser.parse_args()

# get the input video file name and the output text file name
input_video_file = args.input_video_file
input_json_file = args.input_json_file

# read the input JSON file
print("Parsing the input JSON file...")
with open(input_json_file) as f:
    data = json.load(f)

# get all the items where .results.items.alternatives.content is a filler word
filler_words = ["um", "uh", "so"]

# filter to keep only pronunciations
pronunciation_items = list(
    filter(lambda x: x["type"] == "pronunciation", data["results"]["items"])
)

# merge consecutive filler words in pronunciation_items
i = 0
while i < len(pronunciation_items) - 1:
    if (
        pronunciation_items[i]["alternatives"][0]["content"].lower() in filler_words
        and pronunciation_items[i + 1]["alternatives"][0]["content"].lower()
        in filler_words
    ):
        print(
            "Found consecutive filler words: "
            "{pronunciation_items[i]['alternatives'][0]['content']} "
            f"{pronunciation_items[i+1]['alternatives'][0]['content']} "
            "at "
            f"{pronunciation_items[i]['start_time']} "
            f"{pronunciation_items[i+1]['start_time']}"
        )
        # merge the start and end timings of the two items
        pronunciation_items[i]["end_time"] = pronunciation_items[i + 1]["end_time"]

        # remove the second item
        pronunciation_items.pop(i + 1)
    else:
        i += 1

# extract the timings from the filler words items, in (start, end) tuples
# parse float from string
# the end time of a filler word is the start time of the next pronunciation
# unless the next pronunciation is also a filler word, in which case the end time is the end time
# of the next pronunciation
filler_words_timings = [(0.0, 0.0)]
for i, item in enumerate(pronunciation_items[:-1]):
    # check in lowercase
    if item["alternatives"][0]["content"].lower() in filler_words:
        # get the start & end time of the filler word
        start_time = float(item["start_time"])
        # end_time = float(pronunciation_items[i+1]["start_time"]) + 0.1
        end_time = float(item["end_time"])
        # the duration of a filler word is at least 0.3 seconds
        if end_time - start_time < 0.3:
            end_time = start_time + 0.3
        # if the next pronunciation is farther ahead than 0.3 seconds, then the start time of the
        # next pronunciation as the end time of this filler word
        if float(pronunciation_items[i + 1]["start_time"]) > end_time:
            end_time = float(pronunciation_items[i + 1]["start_time"])

        if start_time >= end_time:
            continue

        filler_words_timings.append((start_time, end_time))

# append in the end the duration of the video
# find the duration of the video using ffprobe
print("Finding the duration of the video...")
ffprobe_output = subprocess.check_output(
    [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        input_video_file,
    ]
)
video_duration = float(ffprobe_output)
filler_words_timings.append((video_duration, video_duration))

# sort the filler words timings by start time
filler_words_timings.sort(key=lambda x: x[0])

print(f"Found {len(filler_words_timings)-2} filler words in the video.")

print("Filler words timings:")
print(filler_words_timings[:5] + ["..."] + filler_words_timings[-5:])

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



def build_ffmpeg_cmd_with_filter():
    n_filrs = len(filler_words_timings)
    filter = ""
    for i in range(1, n_filrs):
        # stagger the start and end time of the video and audio filters
        # so that we take the "non-filler" portion of the video
        start_time = filler_words_timings[i - 1][1]
        end_time = filler_words_timings[i][0]

        # add the video filter
        filter += (
            f"[0:v]trim=start={start_time}:end={end_time},setpts=PTS-STARTPTS[{i}v];"
        )

        # add the audio filter
        filter += (
            f"[0:a]atrim=start={start_time}:end={end_time},asetpts=PTS-STARTPTS[{i}a];"
        )

    # add the concat filter
    all_inputs = "".join([f"[{i}v][{i}a]" for i in range(n_filrs)])
    filter += f"{all_inputs}concat=n={n_filrs}:v=1:a=1[outv][outa]"
    print("Filter:")
    print(filter)

    return [
        "ffmpeg",
        "-i",
        input_video_file,
        "-filter_complex",
        filter,
        "-map",
        "[outv]",
        "-map",
        "[outa]",
        "-avoid_negative_ts",
        "1",
        "-y",
    ]


def build_ffmpeg_cmd_with_ss_to():
    n_filrs = len(filler_words_timings)
    cmd = ["ffmpeg"]
    remove_fillers = 0
    for i in range(1, n_filrs):
        # stagger the start and end time of the video and audio filters
        # so that we take the "non-filler" portion of the video
        start_time = filler_words_timings[i - 1][1]  # end of last filler word
        end_time = filler_words_timings[i][0]  # start of next filler word

        if start_time >= end_time:
            remove_fillers += 1
            continue

        # add the start and end time to the ffmpeg command
        cmd += [
            "-ss",
            str(start_time) + "s",
            "-to",
            str(end_time) + "s",
            "-i",
            input_video_file,
        ]

    # add the number of filler words to remove
    print(f"Found {remove_fillers} inconsistent-timing filler words.")
    n_filrs -= remove_fillers

    # add the concat filter
    all_inputs = "".join([f"[{i}:v][{i}:a]" for i in range(n_filrs - 1)])
    filter = f"{all_inputs}concat=n={n_filrs-1}:v=1:a=1[outv][outa]"

    cmd += [
        "-filter_complex",
        filter,
        "-map",
        "[outv]",
        "-map",
        "[outa]",
        "-avoid_negative_ts",
        "1",
        "-y",
        "-loglevel",
        "error",
    ]
    return cmd


# build the ffmpeg command
ffmpeg_cmd = build_ffmpeg_cmd_with_ss_to()

output_video_file = os.path.splitext(input_video_file)[0] + "_cleaned.mp4"

# run ffmpeg to remove the filler words
print("Removing the filler words from the video...")
subprocess.run([*ffmpeg_cmd, output_video_file])

print("Done.")
