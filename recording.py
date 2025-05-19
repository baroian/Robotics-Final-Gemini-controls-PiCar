import os
import sys
import sounddevice as sd
import soundfile as sf
import numpy as np
from openai import OpenAI

# Recording parameters
SAMPLERATE = 44100  # Samples per second (Hz)
CHANNELS = 1        # Mono audio
FILENAME = "voice_task_recording.wav" # Changed filename to be more specific

# Special return value to indicate user wants to retry input method selection
RETRY_INPUT_SIGNAL = "RETRY_INPUT_REQUESTED_BY_USER"
OPENAI_WHISPER_API_KEY = os.getenv("OPENAI_WHISPER_API_KEY_NEW")

def _record_audio_segment():
    """Internal function to record audio from the microphone until Enter is pressed."""
    recorded_frames = []

    def callback(indata, frames, time, status):
        if status:
            print(status, file=sys.stderr)
        recorded_frames.append(indata.copy())

    print("Recording... Press Enter to stop.")
    sys.stdout.flush()

    # Ensure microphone is available
    try:
        sd.check_input_settings(samplerate=SAMPLERATE, channels=CHANNELS)
    except Exception as e:
        print(f"Error with microphone settings: {e}", file=sys.stderr)
        print("Please ensure a microphone is connected and configured correctly.", file=sys.stderr)
        return None


    stream = sd.InputStream(samplerate=SAMPLERATE, channels=CHANNELS, callback=callback)
    with stream:
        input() # Blocks until Enter is pressed again

    print("Recording finished.")
    
    if not recorded_frames:
        return None
    
    recording = np.concatenate(recorded_frames, axis=0)
    return recording

def _save_audio_segment(recording, filename, samplerate):
    """Internal function to save the recorded audio to a file."""
    try:
        sf.write(filename, recording, samplerate)
        print(f"Recording saved as {filename}")
        return True
    except Exception as e:
        print(f"Error saving audio file: {e}", file=sys.stderr)
        return False

def _transcribe_audio_segment(client, filename):
    """Internal function to transcribe the audio file using OpenAI Whisper API."""
    print("Transcribing...")
    try:
        with open(filename, "rb") as audio_file:
            transcription_response = client.audio.transcriptions.create(
                model="gpt-4o-transcribe", 
                file=audio_file,
                response_format="text"
            )
        transcribed_text = str(transcription_response).strip()
        print("\nTranscription:")
        print(f"'{transcribed_text}'")
        return transcribed_text
    except FileNotFoundError:
        print(f"Error: Audio file {filename} not found for transcription.", file=sys.stderr)
        return None
    except Exception as e:
        print(f"Error during transcription: {e}", file=sys.stderr)
        return None

def get_task_via_voice(api_key):
    """
    Handles the process of recording audio, transcribing it, and confirming with the user.
    Returns the transcribed text if confirmed, or RETRY_INPUT_SIGNAL if the user wants to re-select input,
    or None if a critical error occurs.
    """
    if not api_key:
        print("Error: OpenAI API key for Whisper is not provided.", file=sys.stderr)
        return None # Critical error, cannot proceed

    try:
        whisper_client = OpenAI(api_key=api_key)
    except Exception as e:
        print(f"Error initializing OpenAI client for Whisper: {e}", file=sys.stderr)
        return None # Critical error

    # This function is called when the user has already opted for voice input.
    # We directly start the recording process.
    
    recording = _record_audio_segment()
    
    if recording is None or len(recording) == 0:
        print("No audio recorded.")
        # If recording fails (e.g. no mic), allow user to go back to input selection
        return RETRY_INPUT_SIGNAL 

    if not _save_audio_segment(recording, FILENAME, SAMPLERATE):
        # If saving fails, allow user to go back
        return RETRY_INPUT_SIGNAL 
        
    transcribed_text = _transcribe_audio_segment(whisper_client, FILENAME)

    if transcribed_text is None or transcribed_text == "":
        print("Transcription failed or resulted in empty text.")
        # If transcription fails, allow user to go back
        return RETRY_INPUT_SIGNAL 

    while True:
        choice = input("\nDo you like this transcription? (Press Enter to accept, 'r' to retry input method): ").lower()
        if choice == "":
            print("Transcription accepted.")
            # Clean up the recording file
            try:
                if os.path.exists(FILENAME):
                    os.remove(FILENAME)
            except Exception as e:
                print(f"Warning: Could not delete temporary recording file {FILENAME}: {e}", file=sys.stderr)
            return transcribed_text
        elif choice == 'r':
            print("Retry input method selected.")
            # Clean up the recording file
            try:
                if os.path.exists(FILENAME):
                    os.remove(FILENAME)
            except Exception as e:
                print(f"Warning: Could not delete temporary recording file {FILENAME}: {e}", file=sys.stderr)
            return RETRY_INPUT_SIGNAL
        else:
            print("Invalid choice. Press Enter or 'r'.")

if __name__ == "__main__":
    print("Testing voice task input module...")
    # Make sure OPENAI_WHISPER_API_KEY_NEW is set as an environment variable for testing
    if 'OPENAI_WHISPER_API_KEY' in globals() and OPENAI_WHISPER_API_KEY:
        task = get_task_via_voice(OPENAI_WHISPER_API_KEY)
        if task and task != RETRY_INPUT_SIGNAL:
            print(f"\nReceived task for testing: '{task}'")
        elif task == RETRY_INPUT_SIGNAL:
            print("\nUser opted to retry input method during testing.")
        else:
            print("\nCould not get task via voice during testing.")
    else:
        print("Please set your OPENAI_WHISPER_API_KEY_NEW environment variable to test.")
        print("Example: export OPENAI_WHISPER_API_KEY_NEW=\"sk-yourkeyhere...\"")


