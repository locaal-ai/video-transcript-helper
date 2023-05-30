# Video Transcript Helper
This project contains three scripts:
- `transcribe_from_video_XXX.py`: Transcribe a video
- `clean_video_from_transcription.py`: Zap filler words ('uh', 'um') in videos using FFMPEG
- `summary_chapters_blog.py`: Generate a summary, video chapters and a blog post

## Usage
Transcribe the video:

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
