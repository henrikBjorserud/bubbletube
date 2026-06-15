import subprocess
import signal
import time
import logging
from pynput import keyboard

SC_SCRIPT  = "/Users/tactile/sc/07_material_inputs_8ch.scd"
SENSOR_PY  = "/Users/tactile/bubble/sensor.py"
SCLANG     = "/Applications/SuperCollider.app/Contents/MacOS/sclang"
SC_BOOT_WAIT = 6  # seconds to let SC boot before starting sensor

logging.basicConfig(
    filename="/tmp/launcher.log",
    level=logging.INFO,
    format="%(asctime)s  %(message)s",
    datefmt="%H:%M:%S",
)

_sc_proc     = None
_sensor_proc = None
_running     = False


def start():
    global _sc_proc, _sensor_proc, _running
    if _running:
        return
    logging.info("START")

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


logging.info("Launcher ready — Ctrl+F12 to toggle")

with keyboard.Listener(on_press=on_press_track, on_release=on_release_track) as listener:
    listener.join()
