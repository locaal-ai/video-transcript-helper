# this script will transcribe the audio from an input video file
# the output will be a JSON file with the transcription
# use argparse to get the input video file and the output text file
# use the AWS transcribe using the AWS CLI to transcribe the audio
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


def cleanup(job_name, s3_uri, flac_audio_file):
    if s3_uri is not None:
        # delete the temporary S3 audio file
        print("Deleting the temporary S3 audio file...")
        subprocess.run(["aws", "s3", "rm", s3_uri])

    if job_name is not None:
        # delete the trascription job in AWS Transcribe
        print("Deleting the transcription job in AWS Transcribe...")
        subprocess.run(["aws", "transcribe", "delete-transcription-job",
                        "--region", "us-east-1", "--transcription-job-name", job_name])

        # delete the temporary S3 bucket
        print("Deleting the temporary S3 bucket...")
        subprocess.run(["aws", "s3", "rb", f"s3://{job_name}", "--force"])

    if flac_audio_file is not None:
        # delete the FLAC audio file
        print("Deleting the local FLAC audio file...")
        subprocess.run(["rm", flac_audio_file])


# convert the video file to a FLAC audio file using ffmpeg (quiet mode)
# the FLAC audio file will be saved in the same directory as the input video file
# the FLAC audio file will have the same name as the input video file but with a FLAC extension
flac_audio_file = input_video_file_name_without_path
# make sure the file has s3 compatible name..
flac_audio_file = re.sub('[^0-9a-zA-Z]+', '-', flac_audio_file)
flac_audio_file_without_path = flac_audio_file + ".flac"
# add the path to the FLAC audio file
flac_audio_file = os.path.join(os.path.dirname(input_video_file), flac_audio_file_without_path)

print(f"Converting video file to FLAC audio file using ffmpeg... {flac_audio_file}")
subprocess.run(["ffmpeg", "-i", input_video_file, "-vn", "-ac", "1", "-ar", "16000", "-c:a", "flac",
                "-qscale:a", "0", "-loglevel", "quiet", "-copyts", "-y", flac_audio_file])

# generate a UUID for the job name
job_name = f"transcribe-job-{uuid.uuid4().hex}"

# create a temporary S3 bucket for the transcription job
# the bucket name will be the same as the job name
print("Creating temporary S3 bucket for the transcription job...")
process = subprocess.run(["aws", "s3", "mb", f"s3://{job_name}"])

if process.returncode != 0:
    print("Error creating temporary S3 bucket for the transcription job")
    exit(1)

# upload the FLAC audio file to the temporary S3 bucket
print("Uploading FLAC audio file to the temporary S3 bucket...")
process = subprocess.run(["aws", "s3", "cp", flac_audio_file, f"s3://{job_name}"])

if process.returncode != 0:
    print("Error uploading FLAC audio file to the temporary S3 bucket")
    cleanup(job_name, None, flac_audio_file)
    exit(1)

# get the S3 URI for the FLAC audio file
s3_uri = f"s3://{job_name}/{flac_audio_file_without_path}"

print(s3_uri)

# start the transcription job
# aws transcribe start-transcription-job \
#  --region us-east-1 \
#  --transcription-job-name "$TEMP_NAME" \
#  --media "MediaFileUri=$S3_URI" \
#  --language-code en-U
print("Starting the transcription job...")
process = subprocess.run(["aws", "transcribe", "start-transcription-job",
                          "--region", "us-east-1", "--transcription-job-name", job_name,
                          "--media", f"MediaFileUri={s3_uri}",
                          "--language-code", "en-US"])

if process.returncode != 0:
    print("Error starting the transcription job")
    cleanup(job_name, s3_uri, flac_audio_file)
    exit(1)

# wait for the transcription job to complete
# run `aws transcribe get-transcription-job`` and capture the output JSON
# e.g. aws transcribe get-transcription-job \
#  --region us-east-1 \
#  --transcription-job-name "$TEMP_NAME"
# check the `TranscriptionJobStatus` field in the JSON if it is `COMPLETED`
# if it is not `COMPLETED`, wait for 5 seconds and then check again
# if it is `COMPLETED`, then break out of the loop
print("Waiting for the transcription job to complete...")
while True:
    process = subprocess.run(["aws", "transcribe", "get-transcription-job",
                              "--region", "us-east-1", "--transcription-job-name", job_name],
                             capture_output=True)
    output = process.stdout.decode("utf-8")
    if "COMPLETED" in output:
        break
    else:
        print("Transcription job not completed yet. Waiting for 5 seconds...")
        subprocess.run(["sleep", "5"])

# get the transcription job output JSON
# use the last output JSON from the previous loop iteration to get the output JSON
# from the `TranscriptionJob.Transcript.TranscriptFileUri` field
# parse the JSON and get the `TranscriptFileUri` field
parsed = json.loads(output)
output_uri = parsed["TranscriptionJob"]["Transcript"]["TranscriptFileUri"]

# download the transcription job output JSON file using regular `curl`
# the transcription job output JSON file will be saved in the same directory as the input video file
# and have the same name as the input video file but with a JSON extension
output_json_file = input_video_file_name + ".json"
print("Downloading the transcription job output JSON file...")
subprocess.run(["curl", "-o", output_json_file, output_uri])

cleanup(job_name, s3_uri, flac_audio_file)
