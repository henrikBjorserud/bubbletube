# Bubbeltub & taktil vägg – Museiinstallation

Två interaktiva museiinstallationer som körs från samma Mac Mini:

- **Bubbeltub** – besökare som går förbi triggar ljus- och bubbelanimationer baserat på avstånd.
- **Taktil vägg** – 8 piezosensorer i olika material (trä, borste, harpa, metall) som ger ljud i SuperCollider när man rör dem.

Allt startas och stoppas av `launcher.py`, som körs automatiskt vid inloggning.

## Hur det fungerar

### Bubbeltub (`sensor.py`)

En VL53L5CX avståndssensor (ToF) mäter avstånd till besökare. En ESP32 läser sensorn och skickar mätvärden via seriell port till Macen. `sensor.py` tolkar mätvärdena och styr:

- **TFH Bubble Column** – bubbeltub via Bluetooth LE (BLE)
- **Philips Hue** – omgivningsbelysning via Hue Bridge

### Taktil vägg (`sc/`)

8 piezos → Focusrite OctoPre → ADAT → Scarlett 18i8 USB → SuperCollider → Scarlett line out 1–2 → förstärkare.

`sc/07_material_inputs_8ch.scd` är huvudskriptet. Piezo 1–8 kommer in på SuperColliders ingångar 12–19 (`SoundIn.ar(i + 12)`), eftersom Scarletts drivrutin lägger analog 0–7, S/PDIF 8–9 och loopback 10–11 före ADAT.

| Piezo | Material |
|---|---|
| 1 | Trä A – låg tjock planka |
| 2 | Borste A – mjuk varm vind |
| 3 | Harpa A – lägre register |
| 4 | Harpa B – högre register |
| 5 | Borste B – låg varm borste |
| 6 | Trä B – filthammare, kalimba-likt |
| 7 | Metall – kort oharmonisk klang |
| 8 | Trä C – högre klubba med eko |

Förstärkning (`gains`) och tröskelvärden (`thresh`) per piezo justeras i `07_material_inputs_8ch.scd`. Test- och diagnosskript ligger i `sc/tests/`.

### Launcher (`launcher.py`)

Vid start:

1. Slår på Hue-pluggarna **Audio** (OctoPre + Scarlett) och **Bubbletube**
2. Startar Focusrite Control 2 och väntar på att Scarlett dyker upp (minst 60 s, så att ADAT-routingen hinner läggas på)
3. Startar `sclang` med `sc/07_material_inputs_8ch.scd`
4. Startar `sensor.py`

Vid stopp sker allt i omvänd ordning, och Focusrite Control 2 avslutas så att routingen läggs på igen nästa gång.

**Styrning:**

| Kontroll | Funktion |
|---|---|
| Ctrl+F12 | Starta / stoppa hela installationen |
| Hue-dimmer, knapp **På** | Slå på bubbeltuben (startar om `sensor.py`) |
| Hue-dimmer, knapp **Av** | Stäng av bubbeltuben |
| Hue-dimmer, **Av** långtryck | Stäng av allt och stäng av datorn |

## Hårdvara

| Komponent | Detalj |
|---|---|
| Dator | Mac Mini (macOS) |
| Avståndssensor | ST VL53L5CX (4×4 zoner, 20 Hz) |
| Mikrokontroller | ESP32, `/dev/cu.usbserial-0163A9A7` |
| Bubbeltub | TFH Bubble Column |
| Belysning | Philips Hue (bridge `0017887feafe.local`) |
| Smarta pluggar | Hue-pluggar "Bubbletube" och "Audio" |
| Fjärrkontroll | Hue dimmer switch |
| Förförstärkare | Focusrite OctoPre (intern klocka, 48 kHz) |
| Ljudkort | Focusrite Scarlett 18i8 USB |

## Installation

```bash
pip3 install -r requirements.txt
```

**Focusrite Control 2:** klockkälla = ADAT, S/PDIF-källa = RCA (frigör optisk ingång för ADAT), 48 kHz. Monitormixen ska bara innehålla Software Playback 1–2, inga ADAT-ingångar.

**Autostart:** `~/Library/LaunchAgents/com.tactile.launcher.plist` kör `python3 /Users/tactile/bubble/launcher.py` vid inloggning.

**Avstängning via fjärrkontroll** kräver en sudoers-regel:

```
tactile ALL=(root) NOPASSWD: /sbin/shutdown
```

macOS måste också ge Terminal/Python behörighet för Hjälpmedel (för Ctrl+F12).

## Starta manuellt

```bash
python3 launcher.py
```

Bara bubbeltuben:

```bash
python3 sensor.py
```

Skriptet söker efter bubbeltubens BLE-enhet i 15 sekunder. Om den inte hittas (t.ex. vid testning hemma) körs det i Hue-only-läge.

Bara ljudet:

```bash
pkill -9 scsynth; pkill -9 sclang; sleep 2
/Applications/SuperCollider.app/Contents/MacOS/sclang sc/07_material_inputs_8ch.scd
```

Felsök ljudet i ordningen `sc/tests/00_boot_and_tone.scd` (ton ut), `sc/tests/01_passthrough_test.scd` (piezos in) och sedan `07`.

## Loggar

| Fil | Innehåll |
|---|---|
| `/tmp/launcher.log` | Start/stopp, pluggar, fjärrkontroll |
| `/tmp/sensor.log` | `sensor.py` |
| `/tmp/sc.log` | SuperCollider |

## Inställningar

Justeras överst i `sensor.py`:

| Konstant | Standardvärde | Beskrivning |
|---|---|---|
| `TRIGGER_MM` | 1500 | Avstånd i mm som triggar aktivering |
| `RELEASE_MM` | 1600 | Avstånd i mm som återställer (ska vara under tomt-rum-läsning ~2200 mm) |
| `UPDATE_MM` | 50 | Minsta rörelse i mm för att uppdatera ljuset under aktivering |
| `IDLE_DIM_SECS` | 120 | Sekunder utan trigger innan lamporna släcks |

Hue-bridgens adress och API-nyckel finns i både `sensor.py` och `launcher.py` – håll dem i synk.

## Firmware

ESP32-firmware finns i `firmware/firmware.ino`. Använder VL53L5CX i 4×4-läge med medianfiltrering över 16 zoner. Skickar `avstånd_mm,tryckt` via seriell port (115200 baud).
