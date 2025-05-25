import picar_4wd as fc
import sys
import tty
import termios
import asyncio
import time

power_val = 100
key = 'status'
print("If you want to quit.Please press q")
def readchar():
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(sys.stdin.fileno())
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return ch

def readkey(getchar_fn=None):
    getchar = getchar_fn or readchar
    c1 = getchar()
    if ord(c1) != 0x1b:
        return c1
    c2 = getchar()
    if ord(c2) != 0x5b:
        return c1
    c3 = getchar()
    return chr(0x10 + ord(c3) - 65)


move_forward_declaration = {
    "name": "move_forward",
    "description": "Moves the car forward for a specified distance in centimeters.",
    "parameters": {
        "type": "object",
        "properties": {
            "cm": {
                "type": "number",
                "description": "The distance in centimeters for the car to move forward.",
            }
        },
        "required": ["cm"],
    },
}

def move_forward(cm: float):
  """Moves the car forward for a specified distance.

  Args:
    cm: The distance in centimeters for the car to move forward.

  Returns:
    A dictionary indicating the distance moved, e.g., {"moved_forward": 10.0}.
  """
  duration = (cm / 22) * 0.5
  power_val = 100
  print(f"Moving forward for {cm} cm ({duration} seconds) at power {power_val}...")
  fc.forward(power_val)
  time.sleep(duration)
  fc.stop()
  print("Stopped.")
  return {"moved_forward": cm}

move_backward_declaration = {
    "name": "move_backward",
    "description": "Moves the car backward for a specified distance in centimeters.",
    "parameters": {
        "type": "object",
        "properties": {
            "cm": {
                "type": "number",
                "description": "The distance in centimeters for the car to move backward.",
            }
        },
        "required": ["cm"],
    },
}

def move_backward(cm: float):
  """Moves the car backward for a specified distance.

  Args:
    cm: The distance in centimeters for the car to move backward.

  Returns:
    A dictionary indicating the distance moved, e.g., {"moved_backward": 10.0}.
  """
  duration = (cm / 22) * 0.5
  power_val = 100
  print(f"Moving backward for {cm} cm ({duration} seconds) at power {power_val}...")
  fc.backward(power_val)
  time.sleep(duration)
  fc.stop()
  print("Stopped.")
  return {"moved_backward": cm}

rotate_left_declaration = {
    "name": "rotate_left",
    "description": "Turns the car left by a specified angle in degrees.",
    "parameters": {
        "type": "object",
        "properties": {
            "degrees": {
                "type": "number",
                "description": "The angle in degrees for the car to turn left.",
            }
        },
        "required": ["degrees"],
    },
}

def rotate_left(degrees: float):
  """Turns the car left for a specified angle.

  Args:
    degrees: The angle in degrees for the car to turn left.

  Returns:
    A dictionary indicating the angle rotated, e.g., {"rotated_left": 90.0}.
  """
  duration = (degrees / 18) * 0.1
  power_val = 100
  print(f"Turning left for {degrees} degrees ({duration} seconds) at power {power_val}...")
  fc.turn_left(power_val)
  time.sleep(duration)
  fc.stop()
  print("Stopped.")
  return {"rotated_left": degrees}

rotate_right_declaration = {
    "name": "rotate_right",
    "description": "Turns the car right by a specified angle in degrees.",
    "parameters": {
        "type": "object",
        "properties": {
            "degrees": {
                "type": "number",
                "description": "The angle in degrees for the car to turn right.",
            }
        },
        "required": ["degrees"],
    },
}

def rotate_right(degrees: float):
  """Turns the car right for a specified angle.

  Args:
    degrees: The angle in degrees for the car to turn right.

  Returns:
    A dictionary indicating the angle rotated, e.g., {"rotated_right": 90.0}.
  """
  duration = (degrees / 18) * 0.1
  power_val = 100
  print(f"Turning right for {degrees} degrees ({duration} seconds) at power {power_val}...")
  fc.turn_right(power_val)
  time.sleep(duration)
  fc.stop()
  print("Stopped.")
  return {"rotated_right": degrees}
