# ESP32 Departure Board - MVP Plan

A small physical device that shows real-time Stockholm transit departures on a screen,
powered by an ESP32 running MicroPython.

---

## Hardware Shopping List

| Item | Recommendation | Why |
|------|---------------|-----|
| **MCU** | ESP32-S3-DevKitC-1 (or any ESP32-WROOM-32 dev board) | Built-in WiFi, USB-C, good MicroPython support |
| **Display** | SSD1306 OLED 1.3" 128x64 (I2C) | Simple wiring (4 wires), great MicroPython library support, readable text |
| **Wires** | 4x female-to-female jumper wires | Connect display to ESP32 |
| **USB cable** | USB-C (or Micro-USB depending on board) | Power + flashing |

**Estimated cost:** ~100-150 SEK total from Electrokit, Amazon.se, or AliExpress.

### Wiring (SSD1306 I2C to ESP32)

```
SSD1306    ESP32
───────    ─────
VCC    →   3.3V
GND    →   GND
SCL    →   GPIO 22
SDA    →   GPIO 21
```

---

## Software Architecture

```
┌──────────────┐     HTTPS      ┌──────────────────┐
│   ESP32      │ ──────────────→│  SL Transport    │
│  MicroPython │                │  API (public)    │
│              │ ←──────────────│  transport.      │
│  ┌────────┐  │   JSON response│  integration.sl.se│
│  │ SSD1306│  │                └──────────────────┘
│  │ Display│  │
│  └────────┘  │
└──────────────┘
```

The ESP32 calls the SL API directly (no backend needed - the API is public and
requires no API key). It fetches departures, parses the JSON, and renders text
on the OLED screen.

---

## MVP Scope (What We Build)

1. **Connect to WiFi** on boot
2. **Fetch departures** for ONE hardcoded stop from the SL API
3. **Display departures** on the OLED (line number, destination, time)
4. **Auto-refresh** every 30 seconds
5. **Error handling** - show WiFi/API errors on screen

### Explicitly NOT in MVP

- Stop search / selection UI
- Multiple stops
- Button input
- OTA updates
- Battery power / deep sleep
- Web configuration portal

---

## File Structure

```
esp32/
├── MVP_PLAN.md          ← this file
├── main.py              ← entry point, runs after boot
├── boot.py              ← WiFi connection on startup
├── config.py            ← WiFi credentials + stop ID
├── sl_api.py            ← fetch & parse SL departures
├── display.py           ← render departures on SSD1306
└── lib/
    └── ssd1306.py       ← display driver (standard MicroPython lib)
```

---

## Implementation Steps

### Step 1: Flash MicroPython onto ESP32

- Download MicroPython firmware from micropython.org
- Flash using `esptool.py`:
  ```
  esptool.py --chip esp32 erase_flash
  esptool.py --chip esp32 write_flash -z 0x1000 firmware.bin
  ```
- Verify with a REPL over serial (e.g. using `mpremote` or Thonny IDE)

### Step 2: `config.py` - Configuration

```python
WIFI_SSID = "your-wifi-name"
WIFI_PASSWORD = "your-wifi-password"

# Hardcoded stop - find your stop ID at:
# https://transport.integration.sl.se/v1/sites?q=YOUR_STOP_NAME
SITE_ID = 1002  # Example: T-Centralen
```

### Step 3: `boot.py` - WiFi Connection

- Connect to WiFi using `network.WLAN`
- Retry up to 10 times
- Print IP address on success

### Step 4: `lib/ssd1306.py` - Display Driver

- Use the standard MicroPython SSD1306 driver
- Available from the micropython-lib repository

### Step 5: `display.py` - Screen Rendering

- Initialize I2C and SSD1306
- Function to clear screen and draw departure rows
- Each row: `"{line} {destination} {time}"`
- Show ~5 departures (limited by 64px height at 8px per line)
- Header row with stop name

### Step 6: `sl_api.py` - API Client

- Use `urequests` to GET from:
  `https://transport.integration.sl.se/v1/sites/{SITE_ID}/departures`
- Parse JSON response
- Extract: line, destination, display time, transport mode
- Return list of departure dicts

### Step 7: `main.py` - Main Loop

```
loop forever:
    departures = fetch_departures()
    render_to_screen(departures)
    sleep 30 seconds
```

### Step 8: Upload & Test

- Upload all files using `mpremote` or Thonny
- Power cycle the ESP32
- Verify departures appear on screen

---

## Tools You Need on Your Computer

| Tool | Purpose |
|------|---------|
| `esptool` | Flash MicroPython firmware (`pip install esptool`) |
| `mpremote` | Upload files + REPL (`pip install mpremote`) |
| **OR** Thonny IDE | Beginner-friendly IDE with built-in ESP32 support |

---

## API Reference

**Search stops:**
```
GET https://transport.integration.sl.se/v1/sites?q=centralen
```

**Get departures:**
```
GET https://transport.integration.sl.se/v1/sites/{siteId}/departures
```

Response includes departures with: `line`, `destination`, `display`, `direction`,
`transport_mode`, and deviation messages.

No API key required.
