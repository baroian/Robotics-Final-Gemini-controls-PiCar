#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Low-latency PiCar control via ONE persistent chat session, YES, with optional voice input for tasks."""
import os, time, cv2, json, re, sys
from contextlib import contextmanager
from google import genai
from google.genai import types
from picamera2 import Picamera2
from tools import (                       # ← your motor helpers + declarations
    move_forward, move_backward, rotate_left, rotate_right,
    move_forward_declaration, move_backward_declaration,
    rotate_left_declaration, rotate_right_declaration,
)

# Attempt to import voice recording functionality
try:
    from recording import get_task_via_voice, RETRY_INPUT_SIGNAL, OPENAI_WHISPER_API_KEY
    VOICE_INPUT_ENABLED = True
    if not OPENAI_WHISPER_API_KEY: # Simplified check for the API key
        print("Warning: Voice input might not work. Please set your OPENAI_WHISPER_API_KEY_NEW environment variable.")
        # VOICE_INPUT_ENABLED = False # Optionally disable if key is placeholder
except ImportError:
    print("Warning: recording.py not found or missing required components. Voice input will be disabled.")
    VOICE_INPUT_ENABLED = False
    RETRY_INPUT_SIGNAL = "RETRY_INPUT_REQUESTED_BY_USER" # Define for safety, though not used if disabled
    OPENAI_WHISPER_API_KEY = None


# ---------- camera ------------------------------------------------------------
FRAMERATE, SIZE, QUALITY = 10, (480, 270), 80
picam2 = Picamera2()
picam2.configure(picam2.create_video_configuration(
        main={"size": SIZE, "format": "RGB888"},
        controls={'FrameRate': FRAMERATE},
        buffer_count=2))
picam2.start();  time.sleep(0.3)

def jpeg_bytes(frame):
    ok, buf = cv2.imencode(".jpg", cv2.resize(frame, SIZE),
                           [int(cv2.IMWRITE_JPEG_QUALITY), QUALITY])
    return buf.tobytes() if ok else b''

# ---------- Gemini client -----------------------------------------------------
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

tool = types.Tool(function_declarations=[
        move_forward_declaration, move_backward_declaration,
        rotate_left_declaration, rotate_right_declaration])


# should we say to
system_prompt = """
You are a PiCar 4WD (around 15cm wide, 25cm long, camera at 15cm above the ground ,Field of View: 120 degree wide-angle lens).
You will be given a task to complete. Understand the task. Use the tools to complete it.
Use only one tool call per turn. The tools help you move forward/backward and rotate left/right.
Reply with **done** when the task is complete. You have to decide when the task is complete. be confident.

Each time explain your reasoning for the movement in detail BEFORE calling the tool (what is the task, what did you do so far, what needs to be done to complete the task; only then call the tool)
At each turn, analyze current and previous photos to understand where you are and if the task is complete or not.
**DONT STOP UNTIL YOU ARE DONE WITH THE TASK. Realize where you are in space and don't stop early.**



When the task involves going to an object (e.g., go to the cup):
- if you dont see the object in the photo, rotate until you see the object
- if you see the object, face it - MAKE SURE you are alligned with it
- once aligned, move forward, get to it very very close (until you see the object big)
- If the object is still small in the image you are NOT close enough. Keep going.
"""



cfg = types.GenerateContentConfig(
        system_instruction=system_prompt,
        tools=[tool],
        temperature=0,
        candidate_count=1,
        thinking_config=types.ThinkingConfig(thinking_budget=0)
    )

chat = client.chats.create(model="gemini-2.5-flash-preview-04-17", config=cfg)

# ---------- profiler helper ---------------------------------------------------
@contextmanager
def lap(tag, log):
    t0 = time.perf_counter();  yield
    log[tag] = (time.perf_counter() - t0)*1000  # ms

# ---------- main control loop -------------------------------------------------
print("PiCar Control Initialized.")
if VOICE_INPUT_ENABLED:
    print("Voice input for tasks is enabled.")
else:
    print("Voice input for tasks is disabled (recording.py or API key issue).")

while True:  # Outer loop for continuous task input
    TASK = None
    while TASK is None: # Inner loop to ensure a task is obtained
        prompt_message = "Enter task, type 'exit!' to quit"
        if VOICE_INPUT_ENABLED:
            prompt_message += ", or press Enter for voice input: "
        else:
            prompt_message += ": "

        user_choice = input(prompt_message)

        if user_choice == "exit!":
            print("Exiting program.")
            picam2.stop()
            sys.exit(0)
        elif user_choice == "" and VOICE_INPUT_ENABLED:
            print("Starting voice input...")
            # Ensure OPENAI_WHISPER_API_KEY is the one from recording.py
            task_from_voice = get_task_via_voice(OPENAI_WHISPER_API_KEY)
            if task_from_voice and task_from_voice != RETRY_INPUT_SIGNAL:
                TASK = task_from_voice
                print(f"Voice task confirmed: \"{TASK}\"")
            elif task_from_voice == RETRY_INPUT_SIGNAL:
                print("Voice input cancelled or retry requested. Please choose input method again.")
                # Continue in the inner while TASK is None loop
            else: # None or other unexpected return from get_task_via_voice
                print("Could not et task via voice. Please try again or use text input.")
                # Continue in the inner while TASK is None loop
        elif user_choice != "":
            TASK = user_choice
        else: # Empty input but voice is not enabled
             print("No task entered. Please type a tas or enable voice input.")


    print(f"Using task: {TASK}")

    parts = [types.Part(text="TASK:"+ TASK)]
    done, i, MAX = False, 0, 15

    while not done and i < MAX:
        log, t_iter = {}, time.perf_counter()

        with lap("CAP", log):   frame = picam2.capture_array()
        with lap("ENC", log):   img  = jpeg_bytes(frame)

        stream = chat.send_message_stream(parts + [types.Part.from_bytes(data=img,mime_type="image/jpeg")])

        fn_name = fn_args = None
        chunks = ""
        for chunk in stream:                 # earliest chunk → act fast
            if chunk.function_calls:
                call = chunk.function_calls[0]
                fn_name, fn_args = call.name, dict(call.args)
                break
            chunks = ((chunks or "") + ((chunk.text or "") + " ") if chunk else chunks)

        log["API"] = chunk.candidate.finish_reason.value.time_ms  if hasattr(chunk,'candidate') else 0

        print(chunks)
        with lap("MOVE", log):
            if   fn_name == "move_forward":  res = move_forward(**fn_args)
            elif fn_name == "move_backward": res = move_backward(**fn_args)
            elif fn_name == "rotate_left":   res = rotate_left(**fn_args)
            elif fn_name == "rotate_right":  res = rotate_right(**fn_args)
            else:                            res = chunks

        done = any((c.text or "").strip().lower()=="done" for c in stream)

        parts = [types.Part(text=f"{res}  (say 'done' if finished)")]
        log["ITER"] = (time.perf_counter()-t_iter)*1000
        print(f"[{i}] " + " | ".join(f"{k}:{v:.0f}ms" for k,v in log.items()))
        i += 1
        if isinstance(res,str):
            if re.search(r'\bdone\b', res, flags=re.IGNORECASE):
                done = True

picam2.stop()

#openai_key = "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"