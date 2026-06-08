# Bubbeltub – Närhetsstyrd Installation

En interaktiv museiinstallation där besökare som går förbi en bubbeltub triggar ljus- och bubbelanimationer baserat på avstånd.

## Hur det fungerar

En VL53L5CX avståndssensor (ToF) sitter monterad och mäter avstånd till besökare. En ESP32 läser sensorn och skickar mätvärden via seriell kommunikation till en Linux-dator. Python-skriptet `sensor.py` tolkar mätvärdena och styr:

- **TFH Bubble Column** – bubbeltub via Bluetooth LE (BLE)
- **Philips Hue** – omgivningsbelysning via Hue Bridge

## Hårdvara

| Komponent | Detalj |
|---|---|
| Avståndssensor | ST VL53L5CX (4×4 zoner, 20 Hz) |
| Mikrokontroller | ESP32 |
| Bubbeltub | TFH Bubble Column |
| Belysning | Philips Hue (bridge på 192.168.68.50) |
| Dator | Linux, `/dev/ttyUSB0` |

## Installation

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install bleak httpx pyserial
```

## Starta

```bash
source .venv/bin/activate
python3 sensor.py
```

Skriptet söker efter bubbeltubens BLE-enhet i 15 sekunder. Om den inte hittas (t.ex. vid testning hemma) körs det i Hue-only-läge.

## Inställningar

Justeras överst i `sensor.py`:

| Konstant | Standardvärde | Beskrivning |
|---|---|---|
| `TRIGGER_MM` | 1500 | Avstånd i mm som triggar aktivering |
| `RELEASE_MM` | 1600 | Avstånd i mm som återställer (ska vara under tomt-rum-läsning ~2200 mm) |
| `UPDATE_MM` | 50 | Minsta rörelse i mm för att uppdatera ljuset under aktivering |
| `IDLE_DIM_SECS` | 120 | Sekunder utan trigger innan lamporna släcks |

## Firmware

ESP32-firmware finns i `firmware/firmware.ino`. Använder VL53L5CX i 4×4-läge med medianfiltrering över 16 zoner. Skickar `avstånd_mm,tryckt` via seriell port (115200 baud).
