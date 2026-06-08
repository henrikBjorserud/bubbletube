import asyncio
import httpx
import serial
from bleak import BleakClient, BleakScanner

SERIAL_PORT = "/dev/cu.usbserial-0163A9A7"    # macOS (Mac Mini)
# SERIAL_PORT = "/dev/ttyUSB0"                 # Linux
SERIAL_BAUD = 115200

TFH_DEVICE_NAME = "TFH Bubble Column"

# Characteristic UUIDs — discovered by scanning device BE473255-7863-EEFE-5CAC-7C583CCB9AE6
UUID_MODE_OPTIONS     = "b074725b-e0dd-dfb0-e842-8e5ae2dd64f4"  # read only
UUID_MODE             = "549c23a4-8bd6-f883-0843-d311373eb222"
UUID_GROUP            = "cc588e94-e480-a289-c04a-7532f921e133"
UUID_SPEED            = "7edff190-963a-f1bb-6346-62e06d28dd38"  # 1–5
UUID_ACTION           = "9deebe9d-b52b-4acf-83f6-2d63a052d20e"  # 0 or 1
UUID_REL_BRIGHTNESS   = "00ac0924-b5a3-cf89-7646-9ebbb985c62c"  # 0–255
UUID_BRIGHTNESS       = "764b3935-953e-ffa1-734a-2e2f1c5e116a"  # 0–255
UUID_COLOUR           = "f177fa2a-2c95-7495-0340-abcd84b721c2"  # R,G,B,pressed(0/1)
UUID_STANDBY          = "020012ac-4202-998c-ee11-1056e8db2afb"  # 0=on, 1=standby

TRIGGER_MM      = 1500  # mm — body within 1.5m triggers
RELEASE_MM      = 1600  # mm — must be below empty-room reading (~2200mm)
READ_TIMEOUT    = 2.0   # seconds of sensor silence = out of range
UPDATE_MM       = 50    # mm — re-send to lights when proximity shifts by this much
IDLE_DIM_SECS   = 120   # seconds after last trigger with no new activity → black

DIM_DELAY      = 3.0
DIM_DURATION   = 4.0
DIM_STEPS      = 20
WAKE_BRIGHTNESS = 200
DIM_BRIGHTNESS  = 15

# Philips Hue — fill in once bridge is ready
HUE_BRIDGE_IP = "192.168.68.50"
HUE_API_KEY   = "U6ocVEFwwTo8umGXR4OfTPKZr3onH-1jlrYrp4Af"


# --- value helpers -----------------------------------------------------------

def proximity_to_speed(distance_mm):
    t = min(distance_mm, TRIGGER_MM) / TRIGGER_MM  # 0=close, 1=at threshold
    return max(1, min(5, round(5 - t * 4)))


def proximity_to_colour(distance_mm):
    t = 1.0 - min(distance_mm, TRIGGER_MM) / TRIGGER_MM  # 1=close, 0=far
    r = int(t * 255)
    g = int(t * 60)
    b = int((1.0 - t) * 200)
    return bytes([r, g, b, 1])


# --- bubble tube -------------------------------------------------------------

async def _write(client: BleakClient, uuid: str, data: bytes):
    await client.write_gatt_char(uuid, data)
    await asyncio.sleep(0.05)


async def tube_wake(client: BleakClient):
    await _write(client, UUID_STANDBY, bytes([0]))
    await _write(client, UUID_BRIGHTNESS, bytes([WAKE_BRIGHTNESS]))
    await _write(client, UUID_REL_BRIGHTNESS, bytes([255]))
    await _write(client, UUID_SPEED, bytes([2]))
    await _write(client, UUID_ACTION, bytes([0]))


async def tube_trigger(client: BleakClient, proximity: int):
    speed = proximity_to_speed(proximity)
    colour = proximity_to_colour(proximity)
    await _write(client, UUID_BRIGHTNESS, bytes([WAKE_BRIGHTNESS]))
    await _write(client, UUID_SPEED, bytes([speed]))
    await _write(client, UUID_COLOUR, colour)
    await _write(client, UUID_ACTION, bytes([1]))


async def tube_release(client: BleakClient):
    await _write(client, UUID_ACTION, bytes([0]))
    await _write(client, UUID_COLOUR, bytes([0, 0, 80, 0]))
    await _write(client, UUID_SPEED, bytes([2]))


async def tube_dim(client: BleakClient, stop: asyncio.Event):
    try:
        await asyncio.wait_for(stop.wait(), timeout=DIM_DELAY)
        return
    except asyncio.TimeoutError:
        pass

    await _write(client, UUID_COLOUR, bytes([0, 0, 80, 0]))

    for i in range(DIM_STEPS, -1, -1):
        if stop.is_set():
            return
        brightness = DIM_BRIGHTNESS + int((WAKE_BRIGHTNESS - DIM_BRIGHTNESS) * i / DIM_STEPS)
        await _write(client, UUID_BRIGHTNESS, bytes([brightness]))
        await asyncio.sleep(DIM_DURATION / DIM_STEPS)


# --- Hue ---------------------------------------------------------------------

_hue_light_ids: list = []


def _rgb_to_xy(r, g, b):
    r, g, b = r / 255, g / 255, b / 255
    r = pow((r + 0.055) / 1.055, 2.4) if r > 0.04045 else r / 12.92
    g = pow((g + 0.055) / 1.055, 2.4) if g > 0.04045 else g / 12.92
    b = pow((b + 0.055) / 1.055, 2.4) if b > 0.04045 else b / 12.92
    X = r * 0.4124 + g * 0.3576 + b * 0.1805
    Y = r * 0.2126 + g * 0.7152 + b * 0.0722
    Z = r * 0.0193 + g * 0.1192 + b * 0.9505
    total = X + Y + Z
    return [round(X / total, 4), round(Y / total, 4)] if total else [0.3227, 0.3290]


async def _hue_fetch_light_ids():
    global _hue_light_ids
    url = f"https://{HUE_BRIDGE_IP}/api/{HUE_API_KEY}/lights"
    async with httpx.AsyncClient(verify=False) as client:
        r = await client.get(url, timeout=5.0)
        _hue_light_ids = list(r.json().keys())
    print(f"Hue lights: {_hue_light_ids}")


async def _hue_set_all(state: dict):
    if not _hue_light_ids:
        return
    base = f"https://{HUE_BRIDGE_IP}/api/{HUE_API_KEY}/lights"
    async with httpx.AsyncClient(verify=False) as client:
        for light_id in _hue_light_ids:
            await client.put(f"{base}/{light_id}/state", json=state, timeout=5.0)


async def hue_trigger(proximity: int):
    if not HUE_BRIDGE_IP or not HUE_API_KEY:
        return
    colour = proximity_to_colour(proximity)
    xy = _rgb_to_xy(colour[0], colour[1], colour[2])
    await _hue_set_all({"on": True, "bri": WAKE_BRIGHTNESS, "xy": xy, "transitiontime": 1})


async def hue_release():
    if not HUE_BRIDGE_IP or not HUE_API_KEY:
        return
    xy = _rgb_to_xy(0, 0, 80)
    await _hue_set_all({"on": True, "bri": DIM_BRIGHTNESS, "xy": xy, "transitiontime": 10})


# --- main loop ---------------------------------------------------------------

async def run(tube: BleakClient | None):
    if tube:
        opts = await tube.read_gatt_char(UUID_MODE_OPTIONS)
        print(f"Modes available: {opts.decode('utf-8', errors='replace')}")
        await tube_wake(tube)
        print(f"Bubble tube ready  (trigger < {TRIGGER_MM}mm)")
    else:
        print("Running without bubble tube")

    if HUE_BRIDGE_IP and HUE_API_KEY:
        await _hue_fetch_light_ids()

    active = False
    last_proximity = None
    last_trigger_at = None
    idle_dimmed = False
    dim_stop = asyncio.Event()
    dim_stop.set()

    while True:
        # inner loop: reconnect serial without re-scanning BLE
        try:
            ser = serial.Serial(SERIAL_PORT, SERIAL_BAUD, dsrdtr=False, timeout=READ_TIMEOUT)
        except serial.SerialException as e:
            print(f"Serial open failed ({e}) — retrying in 3s...")
            await asyncio.sleep(3)
            continue

        print(f"Sensor ready — trigger < {TRIGGER_MM}mm  release > {RELEASE_MM}mm")
        last_heartbeat = asyncio.get_event_loop().time()

        while True:
            try:
                raw = await asyncio.to_thread(ser.readline)
            except serial.SerialException as e:
                print(f"Sensor disconnected ({e}) — reconnecting in 2s...")
                ser.close()
                await asyncio.sleep(2)
                break  # back to outer serial-reconnect loop

            if raw == b'':
                # serial timeout — nobody in range
                proximity, touched = TRIGGER_MM + 1, False
            else:
                line = raw.decode("utf-8", errors="replace").strip()
                if not line or "," not in line:
                    continue
                try:
                    proximity, touched = line.split(",")
                    proximity = int(proximity)
                    touched = bool(int(touched))
                except ValueError:
                    continue

            now = asyncio.get_event_loop().time()
            if now - last_heartbeat >= 5.0:
                idle = f"{now - last_trigger_at:.0f}s" if last_trigger_at else "-"
                print(f"  [{proximity}mm  active={active}  idle={idle}]")
                last_heartbeat = now

            if proximity < TRIGGER_MM or touched:
                idle_dimmed = False
                if not active:
                    dim_stop.set()
                    if tube:
                        await tube_trigger(tube, proximity)
                    await hue_trigger(proximity)
                    last_proximity = proximity
                    last_trigger_at = now
                    print(f"Triggered  proximity={proximity}mm  speed={proximity_to_speed(proximity)}")
                    active = True
                elif last_proximity is None or abs(proximity - last_proximity) >= UPDATE_MM:
                    if tube:
                        await tube_trigger(tube, proximity)
                    await hue_trigger(proximity)
                    last_proximity = proximity

            elif active and proximity > RELEASE_MM:
                if tube:
                    await tube_release(tube)
                    dim_stop = asyncio.Event()
                    asyncio.create_task(tube_dim(tube, dim_stop))
                await hue_release()
                last_proximity = None
                print(f"Released  proximity={proximity}mm")
                active = False

            if (not active and not idle_dimmed
                    and last_trigger_at is not None
                    and now - last_trigger_at >= IDLE_DIM_SECS):
                await _hue_set_all({"on": False})
                idle_dimmed = True
                print(f"Idle dim — no trigger for {IDLE_DIM_SECS:.0f}s")


async def main():
    while True:
        try:
            print("Scanning for TFH Bubble Column...")
            device = await BleakScanner.find_device_by_filter(
                lambda d, _: d.name and TFH_DEVICE_NAME in d.name,
                timeout=15.0,
            )
            if device is None:
                print("Tube not found — starting in Hue-only mode")
                await run(None)
            else:
                print(f"Found: {device.name}  ({device.address})")
                async with BleakClient(device) as client:
                    print("Connected")
                    await run(client)

        except Exception as e:
            print(f"Error ({e}) — restarting in 5s...")
            await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(main())
