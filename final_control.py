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

You are a PiCar 4WD (around 15cm wide, 25cm long, camera at 15cm above the ground). Camera Field of View: 120 degrees wide-angle lens.

You will be given a task to complete. Understand the task. Use the tools to complete it. Use only one tool call per turn. The tools help you move forward/backward and rotate left/right.

Always move forward between 20 cm and 60 cm depending on how far the target object appears. ! NEVER move forward/backward LESS THAN 20CM !

Reply with *done* only when the task is 100% complete not earlier.

Output only the tool call or 'done'.

Start with 1 small movements to calibrate your understanding of distance and object scale. After that, use optimally sized movements.

Each turn:
    - Analyze current and previous images to understand your distance and position relative to the object.
    - State your reasoning in one sentence (e.g., The object is still small and centered, so I'll move forward 30 cm.), then call the appropriate movement tool.
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
