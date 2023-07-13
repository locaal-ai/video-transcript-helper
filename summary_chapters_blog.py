# Description: This script takes a JSON file as input and outputs a summary of the video and the
# chapters for adding to the video description on YouTube.
#
# Usage:
# python summary_and_chapters.py <input_json_file> [--generate_summary] [--generate_chapters] \
#     [--generate_blog] [--print_prompts] [--trim_length]
#
# Example:
# python summary_and_chapters.py "input_json.json"

import argparse
import json

import openai


# get the input video file and the output text file
parser = argparse.ArgumentParser()
parser.add_argument("input_json_file", help="input json transcription file")
# non positional arguments for generating summary and chapters
parser.add_argument("--generate_summary", action="store_true", help="generate summary")
parser.add_argument(
    "--generate_chapters", action="store_true", help="generate chapters"
)
parser.add_argument("--generate_blog", action="store_true", help="generate blog")
parser.add_argument("--print_prompts", action="store_true", help="print prompts")
parser.add_argument("--trim_length", type=int, default=100, help="trim length")
parser.add_argument(
    "--wshiper_cpp_json", action="store_true", help="is this a whisper cpp json file?"
)
# optional arguments for generating summary and chapters
parser.add_argument("--summary_prompt", type=str, default="", help="prompt to use for summary")
args = parser.parse_args()

# get the input video file name and the output text file name
input_json_file = args.input_json_file

# read the input JSON file
# print("Parsing the input JSON file...")
with open(input_json_file) as f:
    data = json.load(f)

# combine words into sentences and keep the timings, using the start time of the first word
# and the end time of the last word.
# sentences are separated by a `punctuation` type item in the JSON file.
# collect sentences in a list of lists of items from the JSON file.
sentences = []

if not args.wshiper_cpp_json:
    sentence = []
    for item in data["results"]["items"]:
        # if the item is a punctuation, then it's the end of the sentence
        if item["type"] == "punctuation" and item["alternatives"][0]["content"] in [
            ".",
            "?",
            "!",
        ]:
            # add an 'end_time' to the punctuation item by using the end time of the last word
            item["end_time"] = (
                sentence[-1]["end_time"] if len(sentence) > 0 else item["start_time"]
            )

            # add the punctuation to the sentence
            sentence.append(item)

            # add the sentence to the list of sentences
            sentences.append(sentence)

            # start a new sentence
            sentence = []
        else:
            # filter out the filler words
            if item["type"] == "pronunciation" and item["alternatives"][0][
                "content"
            ].lower() in ["um", "uh", "so", "hmm", "like"]:
                continue

            # filter out punctuation
            if item["type"] == "punctuation":
                continue

            # add the word to the sentence
            sentence.append(item)

    # get the timings of the sentences
    sentences_timings = []
    for sentence in sentences:
        # get the start time of the sentence
        start_time = float(sentence[0]["start_time"])

        # get the end time of the sentence
        end_time = float(sentence[-1]["end_time"])

        # add the timings to the list of timings
        sentences_timings.append((start_time, end_time))


def convert_senconds_to_mmss(seconds):
    return f"{int(seconds // 60):02d}:{int(seconds % 60):02d}"


def build_summary(trim=True, remove_filler_words=True):
    # build a summary list from the senstences and their timings
    summary = []
    if not args.wshiper_cpp_json:
        for sentence, timings in zip(sentences, sentences_timings):
            # get the pronounciations from the sentence
            pronounciations = [
                item["alternatives"][0]["content"].strip()
                for item in sentence
                if item["type"] == "pronunciation"
            ]

            if remove_filler_words:
                # remove the filler words from the sentence
                pronounciations = [
                    word
                    for word in pronounciations
                    if word.lower() not in ["um", "uh", "so", "hmm", "like"]
                ]

            # get the sentence text
            sentence_text = " ".join(pronounciations) + "."

            if trim:
                # trim the sentence text to a maximum of 100 characters
                sentence_text = sentence_text[: args.trim_length]

            # get the sentence start and end timings
            sentence_start_time, sentence_end_time = timings

            # convert the timings to strings in the format MM:SS
            sentence_start_time = f"{convert_senconds_to_mmss(sentence_start_time)}"
            sentence_end_time = f"{convert_senconds_to_mmss(sentence_end_time)}"

            # add the sentence to the summary
            summary.append(
                {
                    "text": sentence_text,
                    "start_time": sentence_start_time,
                    "end_time": sentence_end_time,
                }
            )
    else:
        for sentence in data["transcription"]:
            # get the sentence text
            sentence_text = sentence["text"]

            if trim:
                # trim the sentence text to a maximum of 100 characters
                sentence_text = sentence_text[: args.trim_length]

            # get the sentence start and end timings
            sentence_start_time = sentence["timestamps"]["from"]
            sentence_end_time = sentence["timestamps"]["to"]

            # add the sentence to the summary
            summary.append(
                {
                    "text": sentence_text,
                    "start_time": sentence_start_time,
                    "end_time": sentence_end_time,
                }
            )

    return summary


if args.generate_summary:
    # build a prompt for OpenAI generation:
    prompt = "transcript for the video:\n"
    prompt += "---\n"
    for sentence in build_summary(trim=args.trim_length > 0):
        prompt += f"{sentence['text']}\n"
    prompt += "---\n"
    if args.summary_prompt is not None and args.summary_prompt != "":
        prompt += args.summary_prompt
    else:
        prompt += (
            "write a short summary description paragraph for the above video on YouTube.\n"
        )
        prompt += "Summary for the video:\n"

    if args.print_prompts:
        print(prompt)

    history = [{"role": "user", "content": prompt}]

    # send a request to the OpenAI API (model gpt-3.5-turbo) to generate the summary
    # print("Sending a request to the OpenAI API to generate the summary...")
    print("Generating the summary...")
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo-16k",
        messages=history,
    )

    # get the generated summary
    generated_summary = response["choices"][0]["message"]["content"]
    history += [{"role": "assistant", "content": generated_summary}]

    # print the generated summary
    print("----------------------")
    print(generated_summary)
    print("----------------------")

if args.generate_chapters:
    prompt = "transcript for the video:\n"
    prompt += "---\n"
    for sentence in build_summary(trim=True):
        prompt += (
            f"[{sentence['start_time']} - {sentence['end_time']}] {sentence['text']}\n"
        )
    prompt += "---\n"
    prompt += (
        "write up to 10 high-level chapters for the video on YouTube in the format: "
        + "'MM:SS <chapter-title>.'\n"
    )
    prompt += "Chapters for the video:\n"

    if args.print_prompts:
        print(prompt)

    history = [{"role": "user", "content": prompt}]

    # send a request to the OpenAI API (model gpt-3.5-turbo) to generate the chapters
    print("Sending a request to the OpenAI API to generate the chapters...")
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=history,
    )

    # get the generated chapters
    generated_chapters = response["choices"][0]["message"]["content"]
    history += [{"role": "assistant", "content": generated_chapters}]

    # print the generated chapters
    print("----------------------")
    print(generated_chapters)
    print("----------------------")

if args.generate_blog:
    prompt = "transcript for the video:\n"
    prompt += "---\n"
    for sentence in build_summary(trim=False):
        prompt += f"{sentence['text']}\n"
    prompt += "---\n"
    prompt += "write a blog post of at least 500 words for the above video. write the title and then the post body.\n"
    prompt += "Title of the blog post:\n"

    if args.print_prompts:
        print(prompt)

    history = [{"role": "user", "content": prompt}]

    # send a request to the OpenAI API (model gpt-3.5-turbo) to generate the blog post
    print("Sending a request to the OpenAI API to generate the blog post...")
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=history,
    )

    # get the generated blog post
    generated_blog = response["choices"][0]["message"]["content"]
    history += [{"role": "assistant", "content": generated_blog}]

    # print the generated blog post
    print("----------------------")
    print(generated_blog)
    print("----------------------")

print("Done.")
