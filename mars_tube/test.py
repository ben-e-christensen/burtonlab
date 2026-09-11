import serial, time
ser = serial.Serial("COM6", 115200, timeout=2)
time.sleep(0.3)

def q(cmd):
    ser.reset_input_buffer()
    ser.write((cmd + "\n").encode())
    time.sleep(0.15)
    r = ser.readline().decode(errors="replace").strip()
    print(f"{cmd:35s} → '{r}'")

q("*IDN?")
q(":MEASure?")           # might list available sub-commands
q(":MEAS1:VAL?")         # measurement slot style
q(":MEAS:VPP?")          # no channel arg
q(":CHANnel1:SCALe?")    # vertical scale — just to confirm queries work

ser.close()