import subprocess
import signal
import threading
import time
import logging
from pynput import keyboard

SC_SCRIPT  = "/Users/tactile/sc/07_material_inputs_8ch.scd"
SENSOR_PY  = "/Users/tactile/bubble/sensor.py"
SCLANG     = "/Applications/SuperCollider.app/Contents/MacOS/sclang"
FOCUSRITE  = "/Applications/Focusrite Control 2.app"
SC_BOOT_WAIT     = 6   # seconds to let SC boot before starting sensor
SCARLETT_TIMEOUT = 60  # max seconds to wait for Scarlett to appear in CoreAudio
FC2_MIN_WAIT     = 60   # seconds after FC2 launch before starting sclang
SC_RESTART_DELAY = 9999  # disabled

logging.basicConfig(
    filename="/tmp/launcher.log",
    level=logging.INFO,
    format="%(asctime)s  %(message)s",
    datefmt="%H:%M:%S",
)

_sc_proc     = None
_sensor_proc = None
_running     = False


def _wait_for_scarlett():
    """Wait for Scarlett to appear in CoreAudio, then enforce FC2_MIN_WAIT from launch."""
    t0 = time.time()
    for i in range(SCARLETT_TIMEOUT):
        r = subprocess.run(
            ["system_profiler", "SPAudioDataType"],
            capture_output=True, text=True, timeout=10,
        )
        if "Scarlett 18i8 USB" in r.stdout:
            logging.info(f"Scarlett detected after {i}s")
            break
        time.sleep(1)
    else:
        logging.warning("Scarlett not detected after timeout — starting anyway")

    # FC2 needs time to restore its internal mixer routing after launch
    elapsed = time.time() - t0
    remaining = max(0, FC2_MIN_WAIT - elapsed)
    if remaining > 0:
        logging.info(f"Waiting {remaining:.0f}s more for FC2 routing to apply")
        time.sleep(remaining)
    logging.info(f"Total FC2 wait: {time.time() - t0:.0f}s")


def _restart_sclang():
    """Kill sclang + scsynth and start fresh — fixes Scarlett output on cold boot."""
    global _sc_proc
    logging.info(f"Restarting sclang to wake Scarlett output (after {SC_RESTART_DELAY}s)")
    if _sc_proc and _sc_proc.poll() is None:
        _sc_proc.send_signal(signal.SIGTERM)
        try:
            _sc_proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            _sc_proc.kill()
    subprocess.call(["pkill", "-f", "scsynth"], stderr=subprocess.DEVNULL)
    time.sleep(2)
    _sc_proc = subprocess.Popen(
        [SCLANG, SC_SCRIPT],
        stdout=open("/tmp/sc.log", "w"),
        stderr=subprocess.STDOUT,
    )
    logging.info(f"sclang restarted PID {_sc_proc.pid}")


def _sc_restart_worker():
    """Background thread: wait SC_RESTART_DELAY seconds then restart sclang."""
    time.sleep(SC_RESTART_DELAY)
    if _running:
        _restart_sclang()


def start():
    global _sc_proc, _sensor_proc, _running
    if _running:
        return
    logging.info("START")

    # Focusrite Control 2 must be running before sclang — it sets the ADAT routing
    subprocess.Popen(["open", FOCUSRITE])
    logging.info("Focusrite Control 2 launched, waiting for Scarlett to appear in CoreAudio")
    _wait_for_scarlett()

    _sc_proc = subprocess.Popen(
        [SCLANG, SC_SCRIPT],
        stdout=open("/tmp/sc.log", "w"),
        stderr=subprocess.STDOUT,
    )
    logging.info(f"sclang PID {_sc_proc.pid}")

    time.sleep(SC_BOOT_WAIT)

    _sensor_proc = subprocess.Popen(
        ["python3", "-u", SENSOR_PY],
        stdout=open("/tmp/sensor.log", "w"),
        stderr=subprocess.STDOUT,
    )
    logging.info(f"sensor PID {_sensor_proc.pid}")
    _running = True

    # First sclang connection after cold boot has broken Scarlett output.
    # A full sclang restart (not just scsynth) fixes it — same as manual Ctrl+F12 twice.
    threading.Thread(target=_sc_restart_worker, daemon=True).start()


def stop():
    global _sc_proc, _sensor_proc, _running
    if not _running:
        return
    logging.info("STOP")

    if _sensor_proc and _sensor_proc.poll() is None:
        _sensor_proc.send_signal(signal.SIGTERM)
        try:
            _sensor_proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            _sensor_proc.kill()
        logging.info("sensor stopped")

    if _sc_proc and _sc_proc.poll() is None:
        _sc_proc.send_signal(signal.SIGTERM)
        try:
            _sc_proc.wait(timeout=8)
        except subprocess.TimeoutExpired:
            _sc_proc.kill()
        logging.info("sclang stopped")

    # kill any stale scsynth — it can survive sclang's exit and block the UDP port
    subprocess.call(["pkill", "-f", "scsynth"], stderr=subprocess.DEVNULL)

    _running = False


def on_press(key):
    try:
        if key == keyboard.Key.f12 and _ctrl_held():
            if _running:
                stop()
            else:
                start()
    except Exception as e:
        logging.error(f"hotkey error: {e}")


_ctrl = set()

def _ctrl_held():
    return bool(_ctrl)

def on_press_track(key):
    if key in (keyboard.Key.ctrl_l, keyboard.Key.ctrl_r):
        _ctrl.add(key)
    on_press(key)

def on_release_track(key):
    _ctrl.discard(key)


logging.info("Launcher ready — auto-starting, Ctrl+F12 to toggle")
start()

with keyboard.Listener(on_press=on_press_track, on_release=on_release_track) as listener:
    listener.join()
