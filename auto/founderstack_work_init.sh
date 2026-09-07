#!/bin/bash

# Script that ensures we select from Apps section, not search providers

sleep 1

# Open GNOME overview
ydotool key 125:1
sleep 0.1
ydotool key 125:0
sleep 0.5

# Type search
ydotool type "wezterm"
sleep 1.5

# Press Enter to open the highlighted app
ydotool key 28:1
sleep 0.1
ydotool key 28:0

# Wait for wezterm to open
sleep 2

# 1. Press Windows key + Up Arrow (full screen)
ydotool key 125:1
sleep 0.1
ydotool key 103:1
sleep 0.1
ydotool key 103:0
sleep 0.1
ydotool key 125:0
sleep 1

# 2. Press Ctrl + Minus two times (smaller font)
for i in {1..2}
do
    ydotool key 29:1
    sleep 0.05
    ydotool key 12:1
    sleep 0.05
    ydotool key 12:0
    sleep 0.05
    ydotool key 29:0
    sleep 0.3
done

# 3. Type "tmux" and press Enter
ydotool type "tmux"
sleep 0.3
ydotool key 28:1
sleep 0.1
ydotool key 28:0

# Wait for tmux to initialize
sleep 1.5

# 4. Press Ctrl + Space then Ctrl + R (load previous tmux session)
# Ctrl+Space
ydotool key 29:1
sleep 0.05
ydotool key 57:1  # Space key
sleep 0.05
ydotool key 57:0
sleep 0.05
ydotool key 29:0
sleep 0.3

# Ctrl+R
ydotool key 29:1
sleep 0.05
ydotool key 19:1  # R key
sleep 0.05
ydotool key 19:0
sleep 0.05
ydotool key 29:0

# Wait for session to load
sleep 2

# 5. Press F1 (go to first window)
ydotool key 59:1  # F1 key
sleep 0.1
ydotool key 59:0
sleep 0.5

# 6. Press Alt + 3 (select third pane)
# Alt key is 56
ydotool key 56:1  # Alt down
sleep 0.05
ydotool key 16:1  # 3 key
sleep 0.05
ydotool key 16:0
sleep 0.05
ydotool key 56:0  # Alt up
sleep 0.5

# 7. Type "djenv" and run it
ydotool type "djenv"
sleep 0.3
ydotool key 28:1  # Enter
sleep 0.1
ydotool key 28:0

# Wait for djenv to complete
sleep 2

# 8. Type "udr" and run it
ydotool type "udr"
sleep 0.3
ydotool key 28:1  # Enter
sleep 0.1
ydotool key 28:0

# 9. Press F2 (next window)
sleep 0.5
ydotool key 60:1  # F2 key
sleep 0.1
ydotool key 60:0
sleep 0.5

# Alt + 3 for third pane (ngrok command)
ydotool key 56:1  # Alt down
sleep 0.05
ydotool key 16:1  # 3 key
sleep 0.05
ydotool key 16:0
sleep 0.05
ydotool key 56:0  # Alt up
sleep 0.5

# Paste ngrok command (without running)
ydotool type "ngrok http --domain=unexpendable-unresponsively-tawana.ngrok-free.dev 8080"
sleep 0.3

# 10. Go to first pane Alt + 1
ydotool key 56:1  # Alt down
sleep 0.05
ydotool key 2:1   # 1 key
sleep 0.05
ydotool key 2:0
sleep 0.05
ydotool key 56:0  # Alt up
sleep 0.5

# Paste uvicorn command
ydotool type "INNGEST_DEV=1 uv run uv run uvicorn main:app --reload --host 0.0.0.0 --port 8080"
sleep 0.5

# 11. Switch to third pane Alt + 3 (fixed)
ydotool key 56:1  # Alt down
sleep 0.05
ydotool key 4:1  # 3 key
sleep 0.05
ydotool key 4:0
sleep 0.05
ydotool key 56:0  # Alt up
sleep 0.5

# Paste docker command
ydotool type "docker run -p 8288:8288 --add-host=host.docker.internal:host-gateway inngest/inngest inngest dev -u http://host.docker.internal:8080/api/inngest --no-discovery"

# 12. Navigate to third window F3
sleep 0.5
ydotool key 61:1  # F3 key
sleep 0.1
ydotool key 61:0
sleep 0.5

# Navigate to first pane Alt + 1
ydotool key 56:1  # Alt down
sleep 0.05
ydotool key 2:1   # 1 key
sleep 0.05
ydotool key 2:0
sleep 0.05
ydotool key 56:0  # Alt up
sleep 0.5

# Run the activate and uvicorn command
ydotool type "source .venv/bin/activate && uvicorn src.server:app --host 0.0.0.0 --port 10000 --reload"
sleep 0.3
ydotool key 28:1  # Enter
sleep 0.1
ydotool key 28:0
sleep 1

# 13. Navigate to 4th window F4
ydotool key 62:1  # F4 key
sleep 0.1
ydotool key 62:0
sleep 0.5

# Go to 3rd pane Alt + 3 (npm command)
ydotool key 56:1  # Alt down
sleep 0.05
ydotool key 4:1  # 3 key
sleep 0.05
ydotool key 4:0
sleep 0.05
ydotool key 56:0  # Alt up
sleep 0.5

# Type npm run dev (without running)
ydotool type "npm run dev"
sleep 0.3

# 14. Navigate to first pane Alt + 1 (zed command)
ydotool key 56:1  # Alt down
sleep 0.05
ydotool key 2:1   # 1 key
sleep 0.05
ydotool key 2:0
sleep 0.05
ydotool key 56:0  # Alt up
sleep 0.5

# Paste and run zed command
ydotool type "zed ~/Desktop/FounderStackCRM/"
sleep 0.3
ydotool key 28:1  # Enter
sleep 0.1
ydotool key 28:0

echo "Wezterm opened, maximized, font reduced, tmux loaded, and custom commands executed!"