# filler-word-video-zapper
Zap filler words ('uh', 'um') in videos using AWS Transcribe and FFMPEG

## Usage
Transcribe the video:

```sh
$ python transcribe.py <path-to-video>
```

The output will be a file called `<video-name>.json` in the same directory as the video.

Zap the filler words:

```sh
$ python clean_video_from_transcription.py <path-to-video> <path-to-transcript>
```

The output will be a file called `<video-name>-clean.mp4` in the same directory as the video.

## Dependencies
- Python 3.6+
- [FFMPEG](https://ffmpeg.org/)
- [AWS CLI](https://aws.amazon.com/cli/)

Make sure to configure your AWS CLI with your credentials and region.
