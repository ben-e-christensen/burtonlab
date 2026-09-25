"""
phantom_capture.py — minimal capture script for a Vision Research Phantom v711

Talks the PH16 text protocol over TCP.  The exact command names below come
from third-party references (phantom-cli, uca-phantom, iPhantom) and the
general shape of Vision Research's protocol docs.  If a command comes back
ERR, check the SDK/PCC docs that shipped with your camera for the right
spelling — the structure of the script won't change, just the string.

Usage:
    python phantom_capture.py                       # defaults
    python phantom_capture.py --ip 100.100.1.1 --fps 5000 --width 1280 --height 800
    python phantom_capture.py --trigger hardware    # wait for BNC trigger
"""

import argparse
import socket
import struct
import time
import sys
import os
from pathlib import Path

import numpy as np

# optional — only needed for PNG/TIFF save
try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    print("PIL not found — frames will be saved as raw .npy files.  "
          "pip install Pillow if you want PNGs.")


# ---------------------------------------------------------------------------
#  low-level protocol helpers
# ---------------------------------------------------------------------------

class PhantomError(Exception):
    """Camera returned an error response."""


class PhantomCamera:
    """
    Thin wrapper around the PH16 text-command protocol.

    Every public method that talks to the camera prints the exchange so you
    can see exactly what's going over the wire.  If a command doesn't work,
    the print will show you the camera's response — adjust the command
    string and re-run.
    """

    CTRL_PORT = 7115          # default PH16 control port
    DATA_PORT = 7116          # secondary port for image data
    TIMEOUT   = 5.0           # seconds
    BUFSIZE   = 4096

    def __init__(self, ip: str, ctrl_port: int = CTRL_PORT):
        self.ip = ip
        self.ctrl_port = ctrl_port
        self._sock: socket.socket | None = None

    # -- connection ---------------------------------------------------------

    def connect(self):
        """Open TCP control connection to the camera."""
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.settimeout(self.TIMEOUT)
        print(f"[conn] connecting to {self.ip}:{self.ctrl_port} …")
        self._sock.connect((self.ip, self.ctrl_port))
        # camera may send a greeting line on connect
        try:
            greeting = self._recv()
            print(f"[conn] camera says: {greeting}")
        except socket.timeout:
            print("[conn] (no greeting — that's OK)")
        print("[conn] connected.\n")

    def close(self):
        if self._sock:
            self._sock.close()
            self._sock = None

    # -- raw send / receive -------------------------------------------------

    def _send(self, cmd: str):
        """Send one command (adds \\r\\n terminator)."""
        line = cmd.strip() + "\r\n"
        self._sock.sendall(line.encode("ascii"))

    def _recv(self) -> str:
        """
        Read until we get a complete response.  PH16 responses are
        newline-terminated text.  Some multi-line responses end with 'OK'
        or 'ERR' on their own line.
        """
        data = b""
        while True:
            try:
                chunk = self._sock.recv(self.BUFSIZE)
            except socket.timeout:
                break
            if not chunk:
                break
            data += chunk
            # simple heuristic: stop when we see a newline at the end
            if data.endswith(b"\r\n") or data.endswith(b"\n"):
                break
        return data.decode("ascii", errors="replace").strip()

    def cmd(self, command: str) -> str:
        """
        Send a command string, print the exchange, return the response.
        Raises PhantomError if the response starts with 'ERR'.
        """
        print(f"  >> {command}")
        self._send(command)
        resp = self._recv()
        for line in resp.splitlines():
            print(f"  << {line}")
        if resp.upper().startswith("ERR"):
            raise PhantomError(resp)
        return resp

    # -- convenience getters / setters --------------------------------------

    def get(self, prop: str) -> str:
        return self.cmd(f"get {prop}")

    def set(self, prop: str, value) -> str:
        return self.cmd(f"set {prop} {value}")

    # -- high-level capture workflow ----------------------------------------

    def info(self):
        """Print basic camera info to confirm communication."""
        print("=== camera info ===")
        for prop in ("info.name", "info.serial", "info.hwver",
                     "info.swver", "info.sensor"):
            try:
                self.get(prop)
            except (PhantomError, socket.timeout):
                pass  # not all cameras expose every property
        print()

    def configure(self, width: int, height: int, fps: int,
                  exposure_us: int, post_trigger_frames: int | None = None):
        """
        Set resolution, frame rate, and exposure for the *default cine*.

        These property names are the most common PH16 spellings.  If your
        camera complains, try the alternate names in the comments.
        """
        print("=== configuring ===")
        # resolution — some firmware versions use "defc.res" as two fields,
        # others use "defc.xmax" / "defc.ymax" separately
        try:
            self.set("defc.res", f"{width} x {height}")
        except PhantomError:
            self.set("defc.xmax", width)
            self.set("defc.ymax", height)

        # frame rate
        self.set("defc.rate", fps)

        # exposure in microseconds
        self.set("defc.exp", exposure_us)

        # post-trigger frame count (how many frames *after* the trigger
        # to keep; the rest of the circular buffer is pre-trigger)
        if post_trigger_frames is not None:
            self.set("defc.ptframes", post_trigger_frames)

        print()

    def black_reference(self):
        """
        Run a Current Session Reference (CSR) — the camera closes its
        internal mechanical shutter, samples the dark frame, and re-opens.
        Always do this after changing resolution / fps / exposure.
        """
        print("=== black reference (CSR) ===")
        # NOTE: cover the lens or just trust the internal shutter.
        # "csref" is the most common command; alternatives: "bref", "csr"
        self.cmd("csref")
        print("  (waiting for CSR to finish …)")
        time.sleep(3)  # CSR typically takes 1-3 s
        print()

    def arm(self):
        """
        Start recording into the circular RAM buffer.
        The camera is now waiting for a trigger.
        """
        print("=== arming (recording to RAM) ===")
        # "rec" is the usual command.  Alternatives: "startrecording"
        self.cmd("rec")
        print("  camera is armed — waiting for trigger\n")

    def trigger(self):
        """Send a software trigger."""
        print("=== software trigger ===")
        self.cmd("trig")
        print("  triggered — post-trigger capture in progress …")
        time.sleep(1)  # let post-trigger frames accumulate
        print()

    def wait_for_hardware_trigger(self, poll_interval: float = 0.5,
                                  timeout: float = 300):
        """
        Poll the camera state until it reports the trigger has fired
        (i.e. it transitions out of 'recording' into 'triggered' or
        'preview' or similar).  Adjust the state-check property if
        needed for your firmware.
        """
        print("=== waiting for hardware trigger ===")
        print(f"  (timeout {timeout}s — trigger via BNC on the back panel)")
        t0 = time.time()
        while time.time() - t0 < timeout:
            try:
                state = self.get("state")
            except (PhantomError, socket.timeout):
                state = ""
            # The state strings vary by firmware.  Common post-trigger
            # states: "Wtrig" -> waiting, transitions to something else.
            # Adjust this check for your camera.
            if "wtrig" not in state.lower() and "rec" not in state.lower():
                print(f"  trigger detected (state: {state})\n")
                return
            time.sleep(poll_interval)
        raise TimeoutError("timed out waiting for hardware trigger")

    # -- frame download -----------------------------------------------------

    def get_cine_info(self) -> dict:
        """
        Ask the camera about the recorded cine (first partition).
        Returns a dict with what we can parse.
        """
        print("=== cine info ===")
        info = {}
        for prop in ("c1.res", "c1.rate", "c1.exp",
                     "c1.firstfr", "c1.lastfr", "c1.trigfr"):
            try:
                resp = self.get(prop)
                info[prop] = resp
            except (PhantomError, socket.timeout):
                pass
        print()
        return info

    def download_frames(self, first_frame: int, count: int,
                        width: int, height: int,
                        bit_depth: int = 8) -> list[np.ndarray]:
        """
        Download `count` frames starting at `first_frame` from the
        camera's RAM over the data port.

        The img / startdata command syntax varies a lot between firmware
        versions.  This tries the most common PH16 form.  If it doesn't
        work, consult your SDK docs for the exact 'img' command format.

        Returns a list of numpy arrays (grayscale uint8 or uint16).
        """
        print(f"=== downloading {count} frames starting at {first_frame} ===")

        frames = []
        bytes_per_pixel = 2 if bit_depth > 8 else 1
        frame_bytes = width * height * bytes_per_pixel

        for i in range(count):
            fn = first_frame + i
            # Most common PH16 image request format.
            # Some cameras want: img { cine 1, start <fn>, cnt 1 }
            # Others want: startdata <fn> 1
            img_cmd = f"img {{ cine 1, start {fn}, cnt 1 }}"
            print(f"  requesting frame {fn} …")
            self._send(img_cmd)

            # open data port to receive pixel data
            dsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            dsock.settimeout(10.0)
            try:
                dsock.connect((self.ip, self.DATA_PORT))
                raw = b""
                while len(raw) < frame_bytes:
                    chunk = dsock.recv(min(65536, frame_bytes - len(raw)))
                    if not chunk:
                        break
                    raw += chunk
            finally:
                dsock.close()

            if len(raw) < frame_bytes:
                print(f"  !! got {len(raw)}/{frame_bytes} bytes — "
                      f"frame {fn} may be incomplete")

            dtype = np.uint16 if bytes_per_pixel == 2 else np.uint8
            frame = np.frombuffer(raw[:frame_bytes], dtype=dtype)
            frame = frame.reshape((height, width))
            frames.append(frame)
            print(f"  frame {fn} OK ({frame.shape})")

        print()
        return frames


# ---------------------------------------------------------------------------
#  frame saving
# ---------------------------------------------------------------------------

def save_frames(frames: list[np.ndarray], out_dir: str = "phantom_capture"):
    """Save captured frames as PNG (if Pillow available) or .npy."""
    Path(out_dir).mkdir(parents=True, exist_ok=True)

    for i, frame in enumerate(frames):
        if HAS_PIL:
            fname = os.path.join(out_dir, f"frame_{i:05d}.png")
            Image.fromarray(frame).save(fname)
        else:
            fname = os.path.join(out_dir, f"frame_{i:05d}.npy")
            np.save(fname, frame)
        print(f"  saved {fname}")

    print(f"\n  {len(frames)} frames saved to {out_dir}/")


# ---------------------------------------------------------------------------
#  main
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(
        description="Capture high-speed video from a Phantom v711")
    ap.add_argument("--ip", default="100.100.1.1",
                    help="Camera IP (default %(default)s)")
    ap.add_argument("--port", type=int, default=PhantomCamera.CTRL_PORT,
                    help="Control port (default %(default)s)")
    ap.add_argument("--width", type=int, default=1280)
    ap.add_argument("--height", type=int, default=800)
    ap.add_argument("--fps", type=int, default=1000,
                    help="Frame rate (default %(default)s)")
    ap.add_argument("--exposure", type=int, default=None,
                    help="Exposure in µs (default: auto = 1e6/fps - 1)")
    ap.add_argument("--post-trigger", type=int, default=None,
                    help="Frames to keep after trigger (default: half buffer)")
    ap.add_argument("--trigger", choices=["software", "hardware"],
                    default="software",
                    help="Trigger source (default %(default)s)")
    ap.add_argument("--frames", type=int, default=100,
                    help="Number of frames to download (default %(default)s)")
    ap.add_argument("--bit-depth", type=int, choices=[8, 12], default=8,
                    help="Download bit depth (default %(default)s)")
    ap.add_argument("--outdir", default="phantom_capture",
                    help="Output directory (default %(default)s)")
    ap.add_argument("--skip-csr", action="store_true",
                    help="Skip black reference (if you already did one)")
    args = ap.parse_args()

    if args.exposure is None:
        args.exposure = int(1e6 / args.fps) - 1  # max exposure for the fps

    cam = PhantomCamera(args.ip, args.port)

    try:
        # 1. connect and check we're talking
        cam.connect()
        cam.info()

        # 2. configure acquisition
        cam.configure(
            width=args.width,
            height=args.height,
            fps=args.fps,
            exposure_us=args.exposure,
            post_trigger_frames=args.post_trigger,
        )

        # 3. black reference
        if not args.skip_csr:
            cam.black_reference()

        # 4. arm and trigger
        cam.arm()

        if args.trigger == "software":
            input("  press ENTER to software-trigger (or Ctrl-C to abort) … ")
            cam.trigger()
        else:
            cam.wait_for_hardware_trigger()

        # 5. figure out what we captured
        cine_info = cam.get_cine_info()

        # 6. download frames
        # default: download from the trigger frame backwards (pre-trigger)
        # parse firstfr if we can, otherwise start at 0
        start_frame = 0
        for k in ("c1.trigfr", "c1.firstfr"):
            if k in cine_info:
                try:
                    start_frame = int(cine_info[k].split()[-1])
                except (ValueError, IndexError):
                    pass
                break

        frames = cam.download_frames(
            first_frame=start_frame,
            count=args.frames,
            width=args.width,
            height=args.height,
            bit_depth=args.bit_depth,
        )

        # 7. save
        save_frames(frames, args.outdir)

    except KeyboardInterrupt:
        print("\naborted.")
    except PhantomError as e:
        print(f"\n!! camera error: {e}")
        print("   check the command spelling against your PCC/SDK docs")
    except ConnectionRefusedError:
        print(f"\n!! can't connect to {args.ip}:{args.port}")
        print("   is the camera powered on and on the right subnet?")
    finally:
        cam.close()


if __name__ == "__main__":
    main()