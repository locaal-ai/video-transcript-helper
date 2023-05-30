# this script will transcribe the audio from an input video file
# the output will be a JSON file with the transcription
# use argparse to get the input video file and the output text file
# use whisper from openai to transcribe the audio
#
# Usage:
# python transcribe_from_video.py <input_video_file>
#
# The output JSON file will be saved in the same directory as the input video file
#
# Example:
# python transcribe_from_video.py "input_video.mp4"
#
# The output JSON file will have the name "input_video.json"

import argparse
import json
import subprocess
import os
import re
import uuid
import whisper


# get the input video file and the output text file
parser = argparse.ArgumentParser()
parser.add_argument("input_video_file", help="input video file")
args = parser.parse_args()

# get the input video file name and the output text file name
input_video_file = args.input_video_file

# get the input video file name without the extension
input_video_file_name = os.path.splitext(input_video_file)[0]

# get the input video file name without the extension and without the path
input_video_file_name_without_path = os.path.basename(input_video_file_name)

# transcribe the audio from the input video file
# the output will be a JSON file with the transcription
# use whisper from openai to transcribe the audio
# the output JSON file will be saved in the same directory as the input video file
# the output JSON file will have the name "input_video.json"

# get the audio from the input video file
# the output will be a wav file with the same name as the input video file
# the output wav file will be saved in the same directory as the input video file

# get the input video file name without the extension
input_video_file_name = os.path.splitext(input_video_file)[0]

# get the input video file name without the extension and without the path
input_video_file_name_without_path = os.path.basename(input_video_file_name)

# get the output wav file name
output_wav_file_name = input_video_file_name_without_path + ".wav"

# get the output wav file name with the path
output_wav_file_name_with_path = os.path.join(os.path.dirname(input_video_file), output_wav_file_name)

# get the command to extract the audio from the input video file
# the output will be a wav file with the same name as the input video file
# the output wav file will be saved in the same directory as the input video file
command = "ffmpeg -i " + input_video_file + " -ar 16000 -ac 1 -ar 44100 -vn -loglevel quiet -y " + output_wav_file_name_with_path

# execute the command to extract the audio from the input video file
# the output will be a wav file with the same name as the input video file
# the output wav file will be saved in the same directory as the input video file
subprocess.call(command, shell=True)

model = whisper.load_model("tiny")
# hack the model to produce filler words by adding them as an input prompt
result = model.transcribe(output_wav_file_name_with_path, 
                          initial_prompt='So uhm, yeaah. Uh, um. Uhh, Umm. Like, Okay, ehm, uuuh.',
                          word_timestamps=True)

punctuation_marks = '\"\'.。,，!！?？:：”)]}、'

# split punctuation from words into new items
for segment in result['segments']:
    new_words = []
    for word in segment['words']:
        if len(word['word']) < 1:
            continue
        if word['word'][-1] in punctuation_marks:
            punctuation = word['word'][-1]
            word['word'] = word['word'][:-1].strip()
            new_words.append(word)
            new_words.append({
                'word': punctuation, 
                'start': word['end'], 
                'end': word['end'], 
                'probability': word['probability']
            })
        else:
            new_words.append(word)
    segment['words'] = new_words


# print(json.dumps(result, indent=4))

# get the output json file name
output_json_file_name = input_video_file_name_without_path + ".json"

# get the output json file name with the path
output_json_file_name_with_path = os.path.join(os.path.dirname(input_video_file), output_json_file_name)

# write the output json file where the output format is:
# { 
#     "results": {
#         "text": "the transcription",
#         "items": [
#             {
#                 "alternatives": [
#                     {
#                         "content": "the word",
#                         "confidence": 0.0
#                     }
#                 ],
#                 "start_time": 0.0,
#                 "end_time": 0.0,
#                 "confidence": 0.0,
#                 "type": "pronunciation"
#             },
#             ...
#         ]
#     }
# }
#
# the input forma from whisper is:
# {
#     "segments": [
#         {
#             "words": [
#                 {
#                     "word": "the word",
#                     "start": 0.0,
#                     "end": 0.0,
#                     "probability": 0.0
#                 },
#                 ...
#             ]
#         },
#         ...
#     ]
# }
#
# translate from whisper format to output format
with open(output_json_file_name_with_path, 'w') as outfile:
    json.dump({
            "results": {
                "text": " ".join([word['word'].strip() for segment in result['segments'] for word in segment['words']]),
                "items": [
                    {
                        "alternatives": [
                            {
                                "content": word['word'],
                                "confidence": word['probability']
                            },
                        ],
                        "start_time": word['start'],
                        "end_time": word['end'],
                        "confidence": word['probability'],
                        "type": "pronunciation" if word['word'] not in punctuation_marks else "punctuation"
                    } for segment in result['segments'] for word in segment['words']
                ]
            }
        }, outfile, indent=2)

