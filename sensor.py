import asyncio
import httpx
import serial_asyncio
from bleak import BleakClient, BleakScanner

SERIAL_PORT = "/dev/cu.usbserial-0163A9A7"
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

TRIGGER_MM    = 1500  # mm — body within 1.5m triggers
RELEASE_MM    = 1800  # mm — hysteresis to avoid flicker
READ_TIMEOUT  = 2.0   # seconds of sensor silence = out of range

DIM_DELAY      = 3.0
DIM_DURATION   = 4.0
DIM_STEPS      = 20
WAKE_BRIGHTNESS = 200
DIM_BRIGHTNESS  = 15

# Philips Hue — fill in once bridge is ready
HUE_BRIDGE_IP = None
HUE_API_KEY   = None


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

async def hue_trigger(proximity: int):
    if not HUE_BRIDGE_IP or not HUE_API_KEY:
        return
    pass


async def hue_release():
    if not HUE_BRIDGE_IP or not HUE_API_KEY:
        return
    pass


# --- main loop ---------------------------------------------------------------

async def run(client: BleakClient):
    opts = await client.read_gatt_char(UUID_MODE_OPTIONS)
    print(f"Modes available: {opts.decode('utf-8', errors='replace')}")

    await tube_wake(client)
    print(f"Bubble tube ready  (trigger < {TRIGGER_MM}mm, release > {RELEASE_MM}mm)")

    reader, _ = await serial_asyncio.open_serial_connection(
        url=SERIAL_PORT, baudrate=SERIAL_BAUD
    )

    # discard stale buffered readings from before we connected
    for _ in range(10):
        try:
            await asyncio.wait_for(reader.readline(), timeout=0.5)
        except asyncio.TimeoutError:
            break

    print("Sensor ready — waiting for proximity")

    active = False
    last_speed = None
    dim_stop = asyncio.Event()
    dim_stop.set()
    last_log_prox = None
    last_heartbeat = asyncio.get_event_loop().time()

    while True:
        try:
            raw = await asyncio.wait_for(reader.readline(), timeout=READ_TIMEOUT)
            line = raw.decode("utf-8", errors="replace").strip()
        except asyncio.TimeoutError:
            proximity, touched = RELEASE_MM + 1, False
        else:
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
            print(f"  [{proximity}mm  active={active}]")
            last_heartbeat = now

        if proximity < TRIGGER_MM or touched:
            speed = proximity_to_speed(proximity)
            if not active:
                dim_stop.set()
                await tube_trigger(client, proximity)
                await hue_trigger(proximity)
                last_speed = speed
                print(f"Triggered  proximity={proximity}mm  speed={speed}")
                active = True
            elif speed != last_speed:
                await tube_trigger(client, proximity)
                await hue_trigger(proximity)
                last_speed = speed

        elif active and proximity > RELEASE_MM:
            await tube_release(client)
            await hue_release()
            dim_stop = asyncio.Event()
            asyncio.create_task(tube_dim(client, dim_stop))
            last_speed = None
            print("Released")
            active = False


async def main():
    while True:
        try:
            print("Scanning for TFH Bubble Column...")
            device = await BleakScanner.find_device_by_filter(
                lambda d, _: d.name and TFH_DEVICE_NAME in d.name,
                timeout=15.0,
            )
            if device is None:
                print("Not found — retrying in 5s...")
                await asyncio.sleep(5)
                continue

            print(f"Found: {device.name}  ({device.address})")
            async with BleakClient(device) as client:
                print("Connected")
                await run(client)

        except Exception as e:
            print(f"Disconnected ({e}) — reconnecting in 5s...")
            await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(main())
