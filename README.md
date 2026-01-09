# Presto Weather

A simple weather application for the Pimoroni Presto that displays current weather conditions and temperature.

## Features
- Fetches real-time weather data from [Open-Meteo](https://open-meteo.com/).
- Displays weather icon, temperature, description, and last update time.
- Automatic location geocoding.
- Updates every 10 minutes.

## Hardware Required
- [Pimoroni Presto](https://shop.pimoroni.com/products/presto)

## Setup

1.  **Wi-Fi Configuration**:
    Create a `secrets.py` file on your Presto with your Wi-Fi credentials:
    ```python
    WIFI_SSID = "your-ssid-here"
    WIFI_PASSWORD = "your-password-here"
    ```

2.  **Installation**:
    Copy `weather.py` to your device (e.g., as `main.py` if you want it to run on boot, or keep as `weather.py` and import/run it).

## Configuration

By default, the app shows weather for London, GB. You can change this by editing the `PLACE_NAME` and `COUNTRY` variables at the top of `weather.py`:

```python
PLACE_NAME = "London"
COUNTRY = "GB"
```

## Credits
Weather data provided by [Open-Meteo](https://open-meteo.com/) (CC BY 4.0).