# PiCar Control with Gemini and Voice Input

This project allows controlling a PiCar-4WD using natural language commands, processed by Google's Gemini model, with an option for voice input transcribed via OpenAI's Whisper API.

![image](https://github.com/user-attachments/assets/151dfcba-1507-447f-ae90-738e11b346a5)

![image](https://github.com/user-attachments/assets/336d71bb-53e0-4cca-8bba-2ce203a9cd82)


[![Demo Video](https://img.youtube.com/vi/jg3ih08Asls/maxresdefault.jpg)](https://youtu.be/jg3ih08Asls)


## Project Structure

- `final_control.py`: Main script to run the PiCar control loop. It captures images, sends them to Gemini for instructions, and executes movement commands. Handles text and voice task input.
- `recording.py`: Handles audio recording, saving, and transcription using the Whisper API.
- `tools.py`: Contains helper functions for PiCar movement (forward, backward, left, right) and their corresponding declarations for the Gemini API.
- `requirements.txt`: Lists the Python dependencies for this project.

## Setup Instructions

### 1. Prerequisites

- A Raspberry Pi with a camera module, set up to work with `picamera2`.
- A configured PiCar-4WD.
- Python 3.x installed on the Raspberry Pi.
- Microphone for voice input (Bluetooth headphones can be connected for the microphone).


### 3. Install Dependencies

Install the required Python packages (virtual environment recommended):

```bash
pip install -r requirements.txt
```

### 4. Set Environment Variables

This project requires API keys for Google Gemini and OpenAI Whisper. You need to set these as environment variables.

-   `GEMINI_API_KEY`: Your API key for Google Gemini.
-   `OPENAI_WHISPER_API_KEY_NEW`: Your API key for OpenAI Whisper.

You can set these in your terminal session before running the script:

-   **On Windows (PowerShell):**
    ```bash
    $env:GEMINI_API_KEY="YOUR_GEMINI_API_KEY"
    $env:OPENAI_WHISPER_API_KEY_NEW="YOUR_OPENAI_API_KEY"
    ```
-   **On macOS and Linux:**
    ```bash
    export GEMINI_API_KEY="YOUR_GEMINI_API_KEY"
    export OPENAI_WHISPER_API_KEY_NEW="YOUR_OPENAI_API_KEY"
    ```


## Running the Project

1.  Ensure your PiCar-4WD is powered on, and the Raspberry Pi is connected to Internet (for API calls).
2.  Activate your virtual environment (if not already active):
    -   macOS/Linux: `source .venv/bin/activate`
3.  Set the required environment variables as described above
4.  Navigate to the project directory and run the main control script:

    ```bash
    python final_control.py
    ```

5.  The script will initialize. You will be prompted to enter a task:
    -   Type your task directly (e.g., "move forward 10 cm and then turn left").
    -   If voice input is enabled and a microphone is connected, press Enter at the prompt to start voice recording. Follow the on-screen instructions to record and confirm your voice command.
    -   Type `exit!` to quit the program.

The PiCar will then attempt to execute the task based on the instructions from the Gemini model, using the camera feed for context.
