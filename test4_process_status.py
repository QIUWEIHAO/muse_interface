import subprocess
import time
import threading
import os
from collections import deque


# List of Muse device names
muse_names = [
    "Muse-EFCD", "Muse-00AC", "Muse-0530", "Muse-EB8D",
    "Muse-00AD", "Muse-079C", "Muse-DD90"
]


# Store all subprocesses and their statuses
processes = {}
statuses = [False] * len(muse_names)  # Initialize all statuses as False
messages = {name: deque(maxlen=3) for name in muse_names}  # Store last 3 messages

# Function to launch a command and store its process
def launch_process(index, muse_name):
    cmd = f"muselsl stream --name {muse_name} -ppg"
    print(f"Starting {cmd}...")
    
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"

    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True, text=True, env=env)
    # process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True, text=True)
    processes[index] = process

# Function to monitor a process and restart it if disconnected
def monitor_process(index, muse_name):
    while True:
        process = processes.get(index)

        if process is None:  # If no process exists yet, skip
            time.sleep(1)
            continue

        # Check if the process is still running
        if process.poll() is None:
            statuses[index] = True  # Process is running
            while True:
                output = process.stdout.readline().strip()
                if output:
                    messages[muse_name].append(output)  # Store the message
                    time.sleep(0.1)
                else:
                    break;

        else:
            statuses[index] = False  # Process disconnected
            print(f"{muse_name} disconnected. Restarting...")
            launch_process(index, muse_name)  # Restart the command


        
        time.sleep(1)  # Check every second

# Launch and monitor all commands with a 1-second interval
for i, muse_name in enumerate(muse_names):
    threading.Thread(target=launch_process, args=(i, muse_name), daemon=True).start()
    threading.Thread(target=monitor_process, args=(i, muse_name), daemon=True).start()
    time.sleep(0.2)  # Wait 1 second before starting the next command
    if i == 5:
        time.sleep(1)


# Main loop to print the statuses periodically
try:
    while True:
        for i, muse_name in enumerate(muse_names):
            status = "Running" if statuses[i] else "Disconnected"
            recent_messages = list(messages[muse_name])
            print("")
            print(f"{muse_name}: {status}")
            print(f"Messages:")
            for message in recent_messages:
                print(message)
            print("")        
        time.sleep(1)  # Print status every 5 seconds
except KeyboardInterrupt:
    print("Monitoring interrupted. Terminating all processes...")
    # Terminate all processes if interrupted
    for process in processes.values():
        process.terminate()
