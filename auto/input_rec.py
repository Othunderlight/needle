import time
from pynput import mouse, keyboard
import pyautogui

# This will store the sequence of events
events = []
start_time = time.time()

print("🔴 Recording started... Do your actions now.")
print("👉 Press 'ESC' on your keyboard to STOP recording and generate the script.")

def get_elapsed():
    return round(time.time() - start_time, 2)

def on_click(x, y, button, pressed):
    if pressed:
        # Record only left and right clicks
        btn_str = 'left' if button == mouse.Button.left else 'right'
        events.append({
            'type': 'click',
            'x': x,
            'y': y,
            'button': btn_str,
            'time': get_elapsed()
        })

def on_press(key):
    # Stop recording if ESC is pressed
    if key == keyboard.Key.esc:
        print("\n🛑 Recording stopped.")
        generate_script()
        return False # Stops the keyboard listener

    try:
        # Standard character keys
        events.append({
            'type': 'type',
            'key': key.char,
            'time': get_elapsed()
        })
    except AttributeError:
        # Special keys (Space, Enter, Backspace, etc.)
        key_str = str(key).replace('Key.', '')
        events.append({
            'type': 'press',
            'key': key_str,
            'time': get_elapsed()
        })

def generate_script():
    if not events:
        print("No events recorded.")
        return

    # Sort events chronologically just in case
    events.sort(key=lambda e: e['time'])

    with open("playback.py", "w") as f:
        # Write headers
        f.write("import pyautogui\n")
        f.write("import time\n\n")
        f.write("print('🚀 Starting playback in 3 seconds... Switch to your target window!')\n")
        f.write("time.sleep(3)\n\n")

        last_time = 0.0

        for event in events:
            # Calculate delays between actions so it reproduces naturally
            delay = round(event['time'] - last_time, 2)
            if delay > 0:
                f.write(f"time.sleep({delay})\n")
            last_time = event['time']

            if event['type'] == 'click':
                f.write(f"pyautogui.click(x={event['x']}, y={event['y']}, button='{event['button']}')\n")
            elif event['type'] == 'type':
                # Escape single quotes if typing
                safe_char = event['key'].replace("'", "\\'")
                f.write(f"pyautogui.write('{safe_char}')\n")
            elif event['type'] == 'press':
                f.write(f"pyautogui.press('{event['key']}')\n")

        f.write("\nprint('✅ Playback finished!')\n")
    print("🎉 Done! Generated 'playback.py'. Run it whenever you want to repeat this task.")

# Start the background watchers
mouse_listener = mouse.Listener(on_click=on_click)
keyboard_listener = keyboard.Listener(on_press=on_press)

mouse_listener.start()
keyboard_listener.start()

# Keep the main script running until keyboard listener stops (ESC pressed)
keyboard_listener.join()
mouse_listener.stop()
