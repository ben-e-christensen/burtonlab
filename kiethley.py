import time
from datetime import datetime
from pathlib import Path

import numpy as np
import serial
import matplotlib.pyplot as plt

# ============ CONFIG ============
ROOT_FOLDER = Path(__file__).resolve().parent / 'test_data'
DELAY_MS    = 100          # time between samples
DURATION_S  = 15           # total recording time; None = run until Ctrl+C
PREFACTOR   = 1e12         # C -> pC
SERIAL_PORT = 'COM18'
BAUDRATE    = 9600
NPLC        = 0.1          # 0.01 fast | 0.1 medium | 1.0 normal | 10 hi-accuracy
CHAR_RANGE  = 20e-9        # valid: 20e-9, 200e-9, 2e-6, 20e-6
# ================================


class ElectrometerComms:

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

    # ---------- serial helpers ----------

    def _write(self, em, cmd):
        em.write(cmd.encode() + b'\n')
        em.flush()

    def _query(self, em, cmd):
        em.reset_input_buffer()
        self._write(em, cmd)
        return em.readline().strip()

    def _check_link(self, em):
        idn = self._query(em, '*IDN?')
        if not idn:
            raise RuntimeError(
                "No response to *IDN?. The link is down, not the script — "
                "check the null-modem crossover and that COM18 is the Keithley."
            )
        print(f'Connected: {idn.decode(errors="replace")}')

    def _check_errors(self, em, label):
        err = self._query(em, ':SYST:ERR?')
        if err and not err.startswith(b'0,'):
            print(f'[{label}] instrument error: {err.decode(errors="replace")}')

    def _configure(self, em):
        self._write(em, '*RST')
        time.sleep(0.6)                       # reset needs time before more commands
        for cmd in [':SYST:ZCH ON',
                    ":SENS:FUNC 'CHAR'",
                    f':SENS:CHAR:RANG {CHAR_RANGE}',
                    f':SENS:CHAR:NPLC {NPLC}',
                    ':FORM:ELEM READ',
                    ':SYST:ZCH OFF']:
            self._write(em, cmd)
            time.sleep(0.05)

        self._write(em, ':CALC2:NULL:ACQ')
        time.sleep(0.2)
        self._write(em, ':CALC2:NULL:STAT ON')
        time.sleep(0.1)

        self._check_errors(em, 'setup')

    # ---------- acquisition ----------

    def run(self):
        t_vec, q_vec = [], []

        with serial.Serial(self.port, self.baudrate, timeout=2) as em, \
             open(self.filepath, 'w') as f:

            time.sleep(0.2)
            em.reset_input_buffer()
            em.reset_output_buffer()

            self._check_link(em)
            self._configure(em)

            f.write('time,charge\n')
            t0 = time.time()
            empty_streak = 0

            try:
                while True:
                    t = time.time() - t0
                    if self.duration_s is not None and t >= self.duration_s:
                        break

                    raw = self._query(em, 'READ?')

                    if not raw:
                        empty_streak += 1
                        if empty_streak == 5:
                            print('5 empty reads in a row — aborting.')
                            self._check_errors(em, 'read')
                            break
                        q = np.nan
                    else:
                        empty_streak = 0
                        try:
                            q = float(raw.split(b',')[0])
                        except ValueError:
                            print(f'unparseable: {raw!r}')
                            q = np.nan

                    t_vec.append(t)
                    q_vec.append(q)
                    f.write(f'{t},{q}\n')
                    f.flush()

                    time.sleep(self.delay_s)

            except KeyboardInterrupt:
                pass
            finally:
                good = int(np.count_nonzero(~np.isnan(q_vec))) if q_vec else 0
                print(f'Recording stopped. {good}/{len(q_vec)} valid. '
                      f'Saved to {self.filepath}')

        if t_vec and any(not np.isnan(q) for q in q_vec):
            plt.plot(t_vec, np.array(q_vec) * self.prefactor, 'ro-')
            plt.xlabel('time [s]')
            plt.ylabel('charge [pC]')
            plt.title(self.filepath.name)
            plt.grid(True, alpha=0.3)
            plt.show()


if __name__ == '__main__':
    ElectrometerComms(ROOT_FOLDER, DELAY_MS, duration_s=DURATION_S,
                      prefactor=PREFACTOR, port=SERIAL_PORT,
                      baudrate=BAUDRATE).run()