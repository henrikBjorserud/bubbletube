import subprocess
import signal
import threading
import time
import json
import logging
import httpx
from pynput import keyboard

SC_SCRIPT  = "/Users/tactile/bubble/sc/07_material_inputs_8ch.scd"
SENSOR_PY  = "/Users/tactile/bubble/sensor.py"
SCLANG     = "/Applications/SuperCollider.app/Contents/MacOS/sclang"
FOCUSRITE  = "/Applications/Focusrite Control 2.app"
SC_BOOT_WAIT     = 6   # seconds to let SC boot before starting sensor
SCARLETT_TIMEOUT = 60  # max seconds to wait for Scarlett to appear in CoreAudio
FC2_MIN_WAIT     = 60   # seconds after FC2 launch before starting sclang
SC_RESTART_DELAY = 9999  # disabled
TUBE_BOOT_WAIT   = 10  # seconds after tube plug on before sensor.py scans for it

# Philips Hue — keep in sync with sensor.py
HUE_BRIDGE_IP = "0017887feafe.local"
HUE_API_KEY   = "x9UmOUv-vtRKY1tRreeFBNaWYFHsUQEFxUJSo0S4"
TUBE_PLUG     = "Bubbletube"   # plug names as set on the bridge
AUDIO_PLUG    = "Audio"        # OctoPre + Scarlett
REMOTE_ON     = 1              # dimmer switch button control_id
REMOTE_OFF    = 4

# needs sudoers rule: tactile ALL=(root) NOPASSWD: /sbin/shutdown
SHUTDOWN_CMD = ["sudo", "-n", "/sbin/shutdown", "-h", "now"]

logging.basicConfig(
    filename="/tmp/launcher.log",
    level=logging.INFO,
    format="%(asctime)s  %(message)s",
    datefmt="%H:%M:%S",
)

_sc_proc     = None
_sensor_proc = None
_running     = False
_lock        = threading.RLock()  # hotkey and remote both call start/stop


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


# --- Hue plugs ---------------------------------------------------------------

def set_plug(name, on, retries=30):
    """Switch a Hue plug by name. Retries so it survives the bridge being slow at boot."""
    base = f"https://{HUE_BRIDGE_IP}/api/{HUE_API_KEY}/lights"
    for attempt in range(retries):
        try:
            lights = httpx.get(base, verify=False, timeout=5.0).json()
            light_id = next(k for k, v in lights.items() if v["name"] == name)
            httpx.put(f"{base}/{light_id}/state", json={"on": on}, verify=False, timeout=5.0)
            logging.info(f"plug {name} {'on' if on else 'off'}")
            return
        except StopIteration:
            logging.warning(f"plug {name} not found on bridge")
            return
        except Exception as e:
            if attempt == retries - 1:
                logging.warning(f"plug {name} failed: {e}")
            else:
                time.sleep(2)


# --- sensor.py ---------------------------------------------------------------

def _start_sensor():
    global _sensor_proc
    if _sensor_proc and _sensor_proc.poll() is None:
        return
    _sensor_proc = subprocess.Popen(
        ["python3", "-u", SENSOR_PY],
        stdout=open("/tmp/sensor.log", "w"),
        stderr=subprocess.STDOUT,
    )
    logging.info(f"sensor PID {_sensor_proc.pid}")


def _stop_sensor():
    if _sensor_proc and _sensor_proc.poll() is None:
        _sensor_proc.send_signal(signal.SIGTERM)  # sensor.py puts tube in standby + lamps off
        try:
            _sensor_proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            _sensor_proc.kill()
        logging.info("sensor stopped")


# --- start / stop ------------------------------------------------------------

def start():
    global _sc_proc, _running
    with _lock:
        if _running:
            return
        logging.info("START")

        # Scarlett must have power before we wait for it in CoreAudio
        set_plug(AUDIO_PLUG, True)
        set_plug(TUBE_PLUG, True)

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

        _start_sensor()
        _running = True

        # First sclang connection after cold boot has broken Scarlett output.
        # A full sclang restart (not just scsynth) fixes it — same as manual Ctrl+F12 twice.
        threading.Thread(target=_sc_restart_worker, daemon=True).start()


def stop():
    global _running
    with _lock:
        if not _running:
            return
        logging.info("STOP")

        _stop_sensor()
        set_plug(TUBE_PLUG, False, retries=3)

        if _sc_proc and _sc_proc.poll() is None:
            _sc_proc.send_signal(signal.SIGTERM)
            try:
                _sc_proc.wait(timeout=8)
            except subprocess.TimeoutExpired:
                _sc_proc.kill()
            logging.info("sclang stopped")

        # kill any stale scsynth — it can survive sclang's exit and block the UDP port
        subprocess.call(["pkill", "-f", "scsynth"], stderr=subprocess.DEVNULL)

        # Scarlett loses power last; quit FC2 so start() relaunches it fresh and reapplies routing
        set_plug(AUDIO_PLUG, False, retries=3)
        subprocess.call(["osascript", "-e", 'quit app "Focusrite Control 2"'], stderr=subprocess.DEVNULL)

        _running = False


# --- remote (Hue dimmer switch) ----------------------------------------------

def tube_on():
    with _lock:
        if not _running:
            logging.info("remote: tube on ignored — installation not running")
            return
        logging.info("remote: tube on")
        set_plug(TUBE_PLUG, True)
        if not (_sensor_proc and _sensor_proc.poll() is None):
            time.sleep(TUBE_BOOT_WAIT)
            _start_sensor()


def tube_off():
    with _lock:
        logging.info("remote: tube off")
        _stop_sensor()
        set_plug(TUBE_PLUG, False)


def shutdown_all():
    with _lock:
        logging.info("remote: SHUTDOWN")
        stop()
        set_plug(TUBE_PLUG, False, retries=3)   # in case we were already stopped
        set_plug(AUDIO_PLUG, False, retries=3)
        r = subprocess.run(SHUTDOWN_CMD, capture_output=True, text=True)
        if r.returncode != 0:
            logging.error(f"shutdown failed: {r.stderr.strip()} — is the sudoers rule installed?")


def _on_button(control_id, event):
    if control_id == REMOTE_ON and event == "short_release":
        tube_on()
    elif control_id == REMOTE_OFF and event == "short_release":
        tube_off()
    elif control_id == REMOTE_OFF and event == "long_press":
        shutdown_all()


def _remote_listener():
    """Follow the bridge's v2 event stream and act on dimmer switch presses."""
    headers = {"hue-application-key": HUE_API_KEY}
    while True:
        try:
            buttons = httpx.get(
                f"https://{HUE_BRIDGE_IP}/clip/v2/resource/button",
                headers=headers, verify=False, timeout=5.0,
            ).json()["data"]
            control_ids = {b["id"]: b["metadata"]["control_id"] for b in buttons}
            logging.info(f"remote listener connected ({len(control_ids)} buttons)")

            # read timeout just forces a periodic reconnect in case the stream died silently
            with httpx.stream(
                "GET", f"https://{HUE_BRIDGE_IP}/eventstream/clip/v2",
                headers={**headers, "Accept": "text/event-stream"},
                verify=False, timeout=httpx.Timeout(5.0, read=300.0),
            ) as r:
                for line in r.iter_lines():
                    if not line.startswith("data:"):
                        continue
                    for msg in json.loads(line[5:]):
                        for item in msg.get("data", []):
                            if item.get("type") != "button" or item["id"] not in control_ids:
                                continue
                            btn = item.get("button", {})
                            event = btn.get("button_report", {}).get("event") or btn.get("last_event")
                            # own thread so a long start/stop doesn't stall the stream
                            threading.Thread(
                                target=_on_button, args=(control_ids[item["id"]], event), daemon=True,
                            ).start()
        except httpx.ReadTimeout:
            continue
        except Exception as e:
            logging.warning(f"remote listener error ({e}) — reconnecting in 5s")
            time.sleep(5)


# --- hotkey ------------------------------------------------------------------

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


httpx_logger = logging.getLogger("httpx")
httpx_logger.setLevel(logging.WARNING)  # don't log every request

threading.Thread(target=_remote_listener, daemon=True).start()

logging.info("Launcher ready — auto-starting, Ctrl+F12 to toggle")
start()

with keyboard.Listener(on_press=on_press_track, on_release=on_release_track) as listener:
    listener.join()
