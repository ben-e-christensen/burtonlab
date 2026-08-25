import serial, time
p = serial.Serial('COM18', 9600, timeout=2)
p.write(b"*RST\n"); time.sleep(1)
p.write(b"*IDN?\n"); time.sleep(1)
print('waiting:', p.in_waiting, repr(p.read(200)))
p.close()