# ICON monitoring
# NAME Weather
# DESC Current weather conditions.

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
TEMPERATURE_UNIT = "celsius" # Set to "celsius" or "fahrenheit"
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
        "&daily=precipitation_probability_max"
        "&timezone=auto"
        "&temperature_unit={}"
    ).format(lat, lon, TEMPERATURE_UNIT)

    data = http_get_json(url)
    current = data.get("current", {})
    daily = data.get("daily", {})
    temperature = current.get("temperature_2m", None)
    code = current.get("weather_code", None)
    ts = current.get("time", "")
    
    rain_prob = None
    if daily and "precipitation_probability_max" in daily:
        probs = daily["precipitation_probability_max"]
        if probs:
            rain_prob = probs[0]
            
    return temperature, code, ts, rain_prob


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
# Icon drawing
# ----------------------------

def draw_sun(display, x, y, r):
    YELLOW = display.create_pen(255, 220, 0)
    display.set_pen(YELLOW)
    display.circle(x, y, r)

    # rays
    for deg in range(0, 360, 45):
        a = math.radians(deg)
        x1 = x + int(math.cos(a) * (r + 8))
        y1 = y + int(math.sin(a) * (r + 8))
        x2 = x + int(math.cos(a) * (r + 20))
        y2 = y + int(math.sin(a) * (r + 20))
        display.line(x1, y1, x2, y2)


def draw_cloud(display, x, y):
    GREY = display.create_pen(220, 220, 230)
    display.set_pen(GREY)
    # Fluffier cloud
    display.circle(x - 20, y + 5, 18)
    display.circle(x, y - 8, 24)
    display.circle(x + 20, y + 5, 18)
    display.rectangle(x - 20, y + 5, 40, 20)


def draw_rain(display, x, y):
    draw_cloud(display, x, y)
    BLUE = display.create_pen(100, 180, 255)
    display.set_pen(BLUE)
    # nice angled rain
    for i in range(-15, 25, 10):
        display.line(x + i, y + 25, x + i - 8, y + 45)


def draw_snow(display, x, y):
    draw_cloud(display, x, y)
    WHITE = display.create_pen(255, 255, 255)
    display.set_pen(WHITE)
    for i in (-15, 0, 15):
        display.circle(x + i, y + 35, 3)


def draw_storm(display, x, y):
    draw_cloud(display, x, y)
    YELLOW = display.create_pen(255, 220, 0)
    display.set_pen(YELLOW)
    # lightning bolt
    display.line(x + 5, y + 20, x - 5, y + 40)
    display.line(x - 5, y + 40, x + 8, y + 40)
    display.line(x + 8, y + 40, x, y + 60)


def draw_fog(display, x, y):
    draw_cloud(display, x, y)
    FOG = display.create_pen(180, 180, 200)
    display.set_pen(FOG)
    # longer fog lines
    for i in range(25, 55, 10):
        display.line(x - 30, y + i, x + 30, y + i)


def draw_unknown(display, x, y):
    WHITE = display.create_pen(255, 255, 255)
    display.set_pen(WHITE)
    display.set_font("sans")
    display.text("?", x - 10, y - 20, scale=1.5)


def draw_icon(display, icon, x, y):
    if icon == "sun":
        draw_sun(display, x, y, 24)
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

def measure_text_spaced(display, text, scale, spacing):
    width = 0
    for char in text:
        w = display.measure_text(char, scale=scale)
        width += w + spacing
    return width - spacing if width > 0 else 0

def draw_text_spaced(display, text, x, y, scale, spacing):
    offset = 0
    for char in text:
        display.text(char, x + offset, y, scale=scale)
        w = display.measure_text(char, scale=scale)
        offset += w + spacing

def draw_screen(presto, title, temperature, desc, updated, icon, rain_prob):
    display = presto.display
    width, height = display.get_bounds()

    # Palette
    BG = display.create_pen(10, 10, 20)  # Very dark blue/black
    PRIMARY = display.create_pen(240, 240, 245)  # Off-white
    ACCENT = display.create_pen(100, 200, 255)  # Sky blue
    DIM = display.create_pen(100, 100, 120)  # Dim grey

    display.set_pen(BG)
    display.clear()

    # Location
    display.set_pen(ACCENT)
    display.set_font("sans")
    
    display.text(title, 10, 25, scale=0.8)

    # Main Content (Split view)
    # Left: Icon, Right: Temp
    draw_icon(display, icon, 70, 110)

    display.set_pen(PRIMARY)
    if temperature is None:
        display.text("--", 120, 80, scale=3.0)
    else:
        # Large, thin temp
        t_str = "{:.0f}".format(temperature)
        spacing = -8
        
        # Right align to x=220 (margin of 20)
        # Measure temp and degree symbol
        w_temp = measure_text_spaced(display, t_str, scale=3.0, spacing=spacing)
        w_deg = display.measure_text("°", scale=1.5)
        
        total_w = w_temp + w_deg
        start_x = 220 - total_w

        # Draw shadow
        display.set_pen(DIM)
        display.set_thickness(5)
        draw_text_spaced(display, t_str, start_x+2, 80+2, scale=3.0, spacing=spacing)

        # Draw temperature
        display.set_pen(PRIMARY)
        draw_text_spaced(display, t_str, start_x, 80, scale=3.0, spacing=spacing)
        
        # Small superscript degree symbol
        display.set_thickness(2)
        display.text("°", start_x + w_temp, 60, scale=1.5)

        display.set_thickness(1)

    # Description
    display.set_pen(PRIMARY)
    display.text(desc, 10, 180, scale=1.0)
    
    if rain_prob is not None:
        display.set_pen(ACCENT)
        display.set_font("bitmap8")
        display.text("Chance of rain: {}%".format(rain_prob), 20, 205, scale=1)

    # Footer
    if updated:
        display.set_pen(DIM)
        display.text("Updated " + updated[-5:], 170, 225, scale=1)

    presto.update()


# ----------------------------
# Main app
# ----------------------------

def main():
    presto = Presto()

    # Connect Wi-Fi using secrets.py
    presto.connect()

    lat, lon, name, region = geocode_place(PLACE_NAME, COUNTRY)
    title = name 

    while True:
        try:
            temp_c, code, updated, rain_prob = fetch_current_weather(lat, lon)
            desc = weather_code_to_text(code)
            icon = weather_code_to_icon(code)
            draw_screen(presto, title, temp_c, desc, updated, icon, rain_prob)
        except Exception as e:
            draw_screen(presto, title, None, "Error: {}".format(e), "", "unknown", None)

        time.sleep(REFRESH_SECONDS)


main()
