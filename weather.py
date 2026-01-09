# ICON schedule
# NAME Weather
# DESC Web weather.

import gc
import time
import math

from presto import Presto

try:
    import urequests as requests
except ImportError:
    import requests


# ----------------------------
# Configuration
# ----------------------------

PLACE_NAME = "London"
COUNTRY = "GB"
REFRESH_SECONDS = 10 * 60


# ----------------------------
# Networking helpers
# ----------------------------

def http_get_json(url: str):
    r = requests.get(url)
    try:
        if r.status_code != 200:
            raise RuntimeError("HTTP {}: {}".format(r.status_code, r.text))
        return r.json()
    finally:
        r.close()
        gc.collect()


def geocode_place(name: str, country_code: str = "GB"):
    url = (
        "https://geocoding-api.open-meteo.com/v1/search"
        "?name={}&count=1&language=en&format=json&country={}"
    ).format(name.replace(" ", "%20"), country_code)

    data = http_get_json(url)
    results = data.get("results", [])
    if not results:
        raise RuntimeError("No geocoding results for: {}".format(name))

    top = results[0]
    return (
        float(top["latitude"]),
        float(top["longitude"]),
        top.get("name", name),
        top.get("admin1", ""),
    )


def fetch_current_weather(lat: float, lon: float):
    url = (
        "https://api.open-meteo.com/v1/forecast"
        "?latitude={}&longitude={}"
        "&current=temperature_2m,weather_code"
        "&timezone=auto"
    ).format(lat, lon)

    data = http_get_json(url)
    current = data.get("current", {})
    temp_c = current.get("temperature_2m", None)
    code = current.get("weather_code", None)
    ts = current.get("time", "")
    return temp_c, code, ts


# ----------------------------
# Weather interpretation
# ----------------------------

def weather_code_to_text(code):
    mapping = {
        0:  "Clear",
        1:  "Mainly clear",
        2:  "Partly cloudy",
        3:  "Overcast",
        45: "Fog",
        48: "Rime fog",
        51: "Light drizzle",
        53: "Drizzle",
        55: "Heavy drizzle",
        61: "Light rain",
        63: "Rain",
        65: "Heavy rain",
        71: "Light snow",
        73: "Snow",
        75: "Heavy snow",
        80: "Rain showers",
        81: "Rain showers",
        82: "Violent showers",
        95: "Thunderstorm",
    }
    return mapping.get(code, "Code {}".format(code))


def weather_code_to_icon(code):
    if code in (0, 1):
        return "sun"
    if code in (2, 3):
        return "cloud"
    if code in (45, 48):
        return "fog"
    if code in (51, 53, 55, 61, 63, 65, 80, 81, 82):
        return "rain"
    if code in (71, 73, 75):
        return "snow"
    if code in (95,):
        return "storm"
    return "unknown"


# ----------------------------
# Icon drawing (Option A)
# ----------------------------

def draw_sun(display, x, y, r):
    YELLOW = display.create_pen(255, 220, 0)
    display.set_pen(YELLOW)
    display.circle(x, y, r)

    # rays
    for deg in range(0, 360, 30):
        a = math.radians(deg)
        x1 = x + int(math.cos(a) * (r + 6))
        y1 = y + int(math.sin(a) * (r + 6))
        x2 = x + int(math.cos(a) * (r + 18))
        y2 = y + int(math.sin(a) * (r + 18))
        display.line(x1, y1, x2, y2)


def draw_cloud(display, x, y):
    GREY = display.create_pen(210, 210, 210)
    display.set_pen(GREY)
    display.circle(x - 22, y + 2, 16)
    display.circle(x, y - 10, 22)
    display.circle(x + 24, y + 2, 15)
    display.rectangle(x - 45, y + 2, 90, 28)


def draw_rain(display, x, y):
    draw_cloud(display, x, y)
    BLUE = display.create_pen(80, 160, 255)
    display.set_pen(BLUE)
    for i in (-22, -2, 18, 38):
        display.line(x + i, y + 34, x + i - 6, y + 54)


def draw_snow(display, x, y):
    draw_cloud(display, x, y)
    WHITE = display.create_pen(255, 255, 255)
    display.set_pen(WHITE)
    for i in (-18, 2, 22, 40):
        display.circle(x + i, y + 46, 4)


def draw_storm(display, x, y):
    draw_cloud(display, x, y)
    YELLOW = display.create_pen(255, 220, 0)
    display.set_pen(YELLOW)
    # lightning bolt
    display.line(x + 5, y + 30, x - 8, y + 52)
    display.line(x - 8, y + 52, x + 10, y + 52)
    display.line(x + 10, y + 52, x - 2, y + 70)


def draw_fog(display, x, y):
    draw_cloud(display, x, y)
    FOG = display.create_pen(180, 180, 180)
    display.set_pen(FOG)
    # fog lines
    display.line(x - 45, y + 40, x + 45, y + 40)
    display.line(x - 35, y + 52, x + 35, y + 52)
    display.line(x - 25, y + 64, x + 25, y + 64)


def draw_unknown(display, x, y):
    WHITE = display.create_pen(255, 255, 255)
    display.set_pen(WHITE)
    display.set_font("bitmap8")
    display.text("?", x - 6, y - 10, scale=5)


def draw_icon(display, icon, x, y):
    if icon == "sun":
        draw_sun(display, x, y, 22)
    elif icon == "cloud":
        draw_cloud(display, x, y)
    elif icon == "rain":
        draw_rain(display, x, y)
    elif icon == "snow":
        draw_snow(display, x, y)
    elif icon == "storm":
        draw_storm(display, x, y)
    elif icon == "fog":
        draw_fog(display, x, y)
    else:
        draw_unknown(display, x, y)


# ----------------------------
# UI
# ----------------------------

def draw_screen(presto, title, temp_c, desc, updated, icon):
    display = presto.display

    BLACK = display.create_pen(0, 0, 0)
    WHITE = display.create_pen(255, 255, 255)
    CYAN = display.create_pen(0, 255, 255)

    display.set_pen(BLACK)
    display.clear()

    # Header
    display.set_pen(CYAN)
    display.set_font("bitmap8")
    display.text(title, 10, 10, scale=2)

    # Icon (top-right-ish)
    draw_icon(display, icon, 250, 90)

    # Temperature
    display.set_pen(WHITE)
    display.set_font("bitmap8")
    if temp_c is None:
        display.text("No data", 10, 70, scale=3)
    else:
        display.text("{:.1f}C".format(temp_c), 10, 70, scale=5)

    # Description + time
    display.set_font("bitmap8")
    display.text(desc, 10, 150, scale=2)
    if updated:
        display.text("Updated: {}".format(updated), 10, 200, scale=1)

    presto.update()


# ----------------------------
# Main app
# ----------------------------

def main():
    presto = Presto()

    # Connect Wi-Fi using secrets.py
    presto.connect()

    lat, lon, name, region = geocode_place(PLACE_NAME, COUNTRY)
    title = name if not region else "{} ({})".format(name, region)

    while True:
        try:
            temp_c, code, updated = fetch_current_weather(lat, lon)
            desc = weather_code_to_text(code)
            icon = weather_code_to_icon(code)
            draw_screen(presto, title, temp_c, desc, updated, icon)
        except Exception as e:
            draw_screen(presto, title, None, "Error: {}".format(e), "", "unknown")

        time.sleep(REFRESH_SECONDS)


main()
