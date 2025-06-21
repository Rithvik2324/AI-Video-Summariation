import moviepy.editor as mp
import subprocess
import os
import time
from pydub import AudioSegment
import requests
import json

def extract_audio_from_youtube(youtube_url, output_audio_filename="output_audio.wav"):
    """Downloads a YouTube video and extracts audio, handling .webm."""

    video_file_webm = "temp_video.mp4.webm"
    video_file_mp4 = "temp_video.mp4"
    audio_filename = "temp_audio.wav"
    converted_audio = "converted_audio.wav"

    try:
        # Download the YouTube video using yt-dlp
        result = subprocess.run(['yt-dlp', '-o', video_file_mp4, youtube_url], check=True, capture_output=True, text=True)

        if os.path.exists(video_file_mp4):
            video_file = video_file_mp4
        elif os.path.exists(video_file_webm):
            video_file = video_file_webm
        else:
            return f"Error: yt-dlp completed, but neither {video_file_webm} nor {video_file_mp4} was created. yt-dlp output: {result.stderr if result.stderr else result.stdout}"

        # Load the video using moviepy
        video = mp.VideoFileClip(video_file)

        # Extract the audio
        audio_file_clip = video.audio
        audio_file_clip.write_audiofile(audio_filename)

        # Convert to 16000hz using pydub.
        sound = AudioSegment.from_wav(audio_filename)
        sound = sound.set_frame_rate(16000)
        sound.export(converted_audio, format="wav")

        # Save the audio file to the desired output filename
        sound.export(output_audio_filename, format="wav")

        return os.path.abspath(output_audio_filename)

    except subprocess.CalledProcessError as e:
        return f"yt-dlp Error: {e.stderr if e.stderr else e}"
    except Exception as e:
        return f"An error occurred: {e}"
    finally:
        # Cleanup: Remove temporary files
        if 'video' in locals():
            video.close()
        time.sleep(1)
        if os.path.exists(video_file_webm):
            os.remove(video_file_webm)
        if os.path.exists(video_file_mp4):
            os.remove(video_file_mp4)
        if os.path.exists(audio_filename):
            os.remove(audio_filename)
        if os.path.exists(converted_audio):
            os.remove(converted_audio)

def transcribe_assemblyai(audio_file_path, api_key):
    """Transcribes audio using AssemblyAI."""

    try:
        with open(audio_file_path, "rb") as f:
            response = requests.post(
                "https://api.assemblyai.com/v2/upload",
                headers={"authorization": api_key},
                data=f,
            )
        response.raise_for_status()

        upload_url = response.json()["upload_url"]

        transcript_request = {
            "audio_url": upload_url,
        }

        transcript_response = requests.post(
            "https://api.assemblyai.com/v2/transcript",
            json=transcript_request,
            headers={"authorization": api_key},
        )
        transcript_response.raise_for_status()

        transcript_id = transcript_response.json()["id"]

        polling_endpoint = f"https://api.assemblyai.com/v2/transcript/{transcript_id}"
        while True:
            polling_response = requests.get(polling_endpoint, headers={"authorization": api_key})
            polling_response.raise_for_status()

            if polling_response.json()["status"] == "completed":
                return polling_response.json()["text"]
            elif polling_response.json()["status"] == "error":
                raise Exception(f"Transcription failed: {polling_response.json()['error']}")
            time.sleep(1)

    except requests.exceptions.RequestException as e:
        return f"Request error: {e}"
    except json.JSONDecodeError as e:
        return f"JSON decode error: {e}"
    except FileNotFoundError:
        return "Error: Audio file not found."
    except Exception as e:
        return f"An error occurred: {e}"

def summarize_with_ollama(text, model_name="llama2"):
    """Summarizes text using Ollama."""
    try:
        import ollama
        prompt = f"Summarize the following text:\n{text}\n\nSummary:"
        response = ollama.chat(model=model_name, messages=[{'role': 'user', 'content': prompt}])
        return response['message']['content'].strip()
    except ImportError:
        return "Ollama library not installed. Please install it using 'pip install ollama'"
    except Exception as e:
        return f"Ollama summarization error: {e}"

# Get YouTube URL from the user
youtube_url = input("Enter YouTube video URL: ")
output_audio_filename = input("Enter output audio filename (or press Enter for output_audio.wav): ") or "output_audio.wav"

# Extract audio and save file path to variable.
audio_file_path = extract_audio_from_youtube(youtube_url, output_audio_filename)

if isinstance(audio_file_path, str) and (audio_file_path.startswith("yt-dlp Error") or audio_file_path.startswith("An error occurred")):
    print(audio_file_path)
else:
    print(f"Audio file saved as: {audio_file_path}")

    api_key = "a42dc409a1db491a80ded63ada999301" # Replace with your API key.

    result = transcribe_assemblyai(audio_file_path, api_key)

    if isinstance(result, str) and result.startswith(("Request error", "JSON decode error", "Error", "Transcription failed")):
        print(result)
    else:
        print("Text from audio:\n", result)

        summary = summarize_with_ollama(result)
        if isinstance(summary, str) and summary.startswith("Ollama summarization error"):
            print(summary)
        else:
            print("\nSummary:\n", summary)


