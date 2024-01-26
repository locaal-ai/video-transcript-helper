# Video Transcript Helper

<div align="center">

[![Discord](https://img.shields.io/discord/1200229425141252116)](https://discord.gg/KbjGU2vvUz)

</div>

A comprehensive toolkit designed for content creators, educators, digital marketers, and video editing enthusiasts. 
It harnesses the power of AI and video processing through a suite of Python scripts that simplify the post-production process. 
This free open-source project aims to transform the way users handle video content, turning hours of editing into a task of a few command lines.

This project contains three scripts:
- `transcribe_from_video_XXX.py`: Transcribe a video
- `clean_video_from_transcription.py`: Zap filler words ('uh', 'um') in videos using FFMPEG
- `summary_chapters_blog.py`: Generate a summary, video chapters and a blog post

Roadmap of future features:
- Remove or speedup (shorten) periods of "silence"
- Enhance speech by voice separation models
- Generate a supercut for a quick video snippet
- Add Audiogram / Kareoke kind of subtitles on the video
- Translate the subtitles to any language

## Usage
Transcribe the video: (either AWS Transcribe API or [Faster-Whisper](https://github.com/guillaumekln/faster-whisper))

```sh
$ python transcribe_from_video_XXX.py <path-to-video>
```

The output will be a file called `<video-name>.json` in the same directory as the video.

Zap the filler words:

```sh
$ python clean_video_from_transcription.py <path-to-video> <path-to-transcript>
```

The output will be a file called `<video-name>-clean.mp4` in the same directory as the video.

Generate the summary, chapters and blog post:

```sh
$ python summary_chapters_blog.py --generate_summary --generate_chapters --generate_blog <path-to-transcript>
```

## Dependencies
- Python 3.6+
- [FFMPEG](https://ffmpeg.org/)
- [AWS CLI](https://aws.amazon.com/cli/)

Make sure to configure your AWS CLI with your credentials and region.
