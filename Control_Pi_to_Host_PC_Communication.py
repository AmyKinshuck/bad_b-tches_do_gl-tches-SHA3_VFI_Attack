
import serial
import time
from datetime import datetime
import os


'''  SETUP UART COMMUNICATION  '''

# The Control Pi is on and plugged into the host PC and already "on"
# UART Setup for the Control Pi

# CHANGE THE FOLLOWING PORT DEPENDING ON YOUR COMPUTER AND PI
serial_port = "/dev/cu.usbmodem1301"
baudrate = 115200

# Open the serial connection from the Host PC to the Control Pi
ser = serial.Serial(serial_port, baudrate, timeout=1)
time.sleep(2)

# Clear any data from the buffer
ser.reset_input_buffer()
time.sleep(2)

# Send the scan command to the Pico
attempts = 10000000000000000000000
ser.write(("scan %d\n" % attempts).encode()) 

'''  SETUP CSV FILE FOR RESULTS TO BE STORED  '''

# Build a dated filename so each run is saved separately
date_str = datetime.now().strftime("%Y-%m-%d_%H-%M")
script_dir = os.path.dirname(os.path.abspath(__file__))
csv_name = os.path.join(script_dir, "WideScanResults_%s.csv" % date_str)

# Create / open a csv file on host PC
with open(csv_name, "w", newline="") as f:
    f.write("result,delay_ns,length_ns,SHA3output\n")
    f.flush()

    print("Listening to Control Pi")

    try:
        while True:
            data = ser.readline()
            if not data:
                continue
            line = data.decode("utf-8", "replace").strip()
            if not line:
                continue
            if line.count(",") == 3 and line.split(",")[0] in ("green","red","cyan","gray","NoGlitchFired"):
                f.write(line + "\n")
                f.flush()
                print(line)

    except KeyboardInterrupt:
        print("\nStopped by user")

ser.close()
print("Results written to", csv_name)
