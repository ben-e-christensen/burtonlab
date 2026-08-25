import os
import time
from datetime import datetime

import numpy as np
import serial
import matplotlib.pyplot as plt

# ============ CONFIG ============
from pathlib import Path

ROOT_FOLDER = Path(__file__).resolve().parent / 'test_data'
DELAY_MS    = 100          # time between samples
DURATION_S  = 15           # total recording time; set to None for run-until-Ctrl+C
PREFACTOR   = 1e12         # C -> pC
SERIAL_PORT = 'COM18'
BAUDRATE    = 9600
# ================================


class ElectrometerComms:
    SETUP_CMD = (b"*RST; :SYST:ZCH ON; :SENS:FUNC 'CHAR'; CHAR:RANG 20e-12;:SENS:CHAR:NPLC 0.1; "
                 b":FORM:ELEM READ; :SYST:ZCH OFF; :CALC2:NULL:STAT ON\n")

    def __init__(self, root_folder, delay_ms, duration_s=None, prefactor=1.0,
                 port='COM1', baudrate=9600):
        
        self.delay_s = delay_ms / 1000
        self.duration_s = duration_s
        self.prefactor = prefactor
        self.port = port
        self.baudrate = baudrate

        stamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        Path(root_folder).mkdir(parents=True, exist_ok=True)
        self.filepath = Path(root_folder) / f'electrometer_{stamp}.csv'

    def run(self):
        with serial.Serial(self.port, self.baudrate, timeout=2) as em, \
             open(self.filepath, 'w') as f:

            f.write('time,charge\n')
            em.write(self.SETUP_CMD)

            # --- live plot setup ---
            plt.ion()
            fig, ax = plt.subplots()
            line, = ax.plot([], [], 'ro-')
            ax.set_xlabel('time [s]')
            ax.set_ylabel('charge [pC]')

            t_vec, q_vec = [], []
            t0 = time.time()

            try:
                while True:
                    t = time.time() - t0
                    if self.duration_s is not None and t >= self.duration_s:
                        break

                    em.write(b'READ?\r')
                    raw = em.readline()
                    try:
                        q = float(raw)
                    except ValueError:
                        q = np.nan

                    t_vec.append(t)
                    q_vec.append(q)
                    f.write(f'{t},{q}\n')
                    f.flush()

                    # --- update plot ---
                    line.set_data(t_vec, np.array(q_vec) * self.prefactor)
                    ax.relim()
                    ax.autoscale_view()
                    fig.canvas.draw_idle()
                    plt.pause(self.delay_s)   # doubles as the sample delay

            except KeyboardInterrupt:
                pass
            finally:
                print(f'Recording stopped. Saved to {self.filepath}')

            plt.ioff()
            plt.show()


if __name__ == '__main__':
    ElectrometerComms(ROOT_FOLDER, DELAY_MS, duration_s=DURATION_S,
                      prefactor=PREFACTOR, port=SERIAL_PORT,
                      baudrate=BAUDRATE).run()