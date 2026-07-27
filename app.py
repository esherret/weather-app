from datetime import datetime
import requests
import streamlit as st

# Configuration (Coordinates set for Kelly Park, Merritt Island, FL)
LATITUDE = 28.4021
LONGITUDE = -80.6629
HEADERS = {
    "User-Agent": "(myweatherapp.com, developer@myweatherapp.com)",
    "Accept": "application/geo+json",
}

st.set_page_config(
    page_title="Weather Window Monitor", page_icon="🌤️", layout="centered"
)


@st.cache_data(ttl=1800)
def fetch_forecast():
  points_url = f"https://api.weather.gov/points/{LATITUDE},{LONGITUDE}"
  response = requests.get(points_url, headers=HEADERS)
  if response.status_code != 200:
    return None

  point_data = response.json()
  forecast_hourly_url = point_data["properties"]["forecastHourly"]

  forecast_response = requests.get(forecast_hourly_url, headers=HEADERS)
  if forecast_response.status_code != 200:
    return None

  return forecast_response.json()["properties"]["periods"]


def get_wind_arrow(direction_str):
  arrows = {
      "N": "⬇️",
      "NNE": "↙️",
      "NE": "↙️",
      "ENE": "⬅️",
      "E": "⬅️",
      "ESE": "↖️",
      "SE": "↖️",
      "SSE": "⬆️",
      "S": "⬆️",
      "SSW": "↗️",
      "SW": "↗️",
      "WSW": "➡️",
      "W": "➡️",
      "WNW": "↘️",
      "NW": "↘️",
      "NNW": "⬇️",
  }
  return arrows.get(direction_str.upper(), "⬆️")


def get_window_type(hour):
  if 6 <= hour <= 9:
    return "Morning (6AM-9AM)", 6, 9
  elif 10 <= hour <= 13:
    return "Midday (10AM-1PM)", 10, 13
  elif 14 <= hour <= 17:
    return "Afternoon (2PM-5PM)", 14, 17
  elif 18 <= hour <= 21:
    return "Evening (6PM-9PM)", 18, 21
  return None, None, None


def get_icon_level(pct):
  if pct >= 75:
      return 5
  elif pct >= 55:
      return 4
  elif pct >= 25:
      return 3
  elif pct >= 15:
      return 2
  else:
      return 1


st.title("🌤️ Weather Windows")

periods = fetch_forecast()

if not periods:
  st.error("Failed to retrieve data from the National Weather Service API.")
else:
  days_data = {}
  for period in periods:
    start_time = datetime.fromisoformat(period["startTime"])
    day_name = start_time.strftime("%A, %b %d")
    hour = start_time.hour

    window_name, start_h, end_h = get_window_type(hour)
    if not window_name:
      continue

    if day_name not in days_data:
      days_data[day_name] = {
          "Morning (6AM-9AM)": [],
          "Midday (10AM-1PM)": [],
          "Afternoon (2PM-5PM)": [],
          "Evening (6PM-9PM)": [],
      }
    days_data[day_name][window_name].append((start_time, period))

  for day_name, windows in days_data.items():
    st.markdown(f"### {day_name}")

    for window_name in ["Morning (6AM-9AM)", "Midday (10AM-1PM)", "Afternoon (2PM-5PM)", "Evening (6PM-9PM)"]:
      window_periods = windows[window_name]
      if not window_periods:
        continue

      st.markdown(f"**{window_name}**")

      grid_html = '<div style="display: flex; gap: 6px; overflow-x: auto; padding-bottom: 6px;">'

      for start_time, period in window_periods:
        time_label = start_time.strftime("%l%p").strip()
        wind_str = period["windSpeed"]
        wind_val = float(wind_str.split()[0])
        wind_dir = period.get("windDirection", "N")
        arrow = get_wind_arrow(wind_dir)

        pop = period.get("probabilityOfPrecipitation", {}).get("value") or 0
        short_fc = period["shortForecast"].lower()
        detailed_fc = period["detailedForecast"].lower()
        text_blob = f"{short_fc} {detailed_fc}"

        has_thunder = "thunder" in text_blob or "storm" in text_blob
        thunder_pct = 80 if has_thunder and "slight chance" not in short_fc else (30 if has_thunder else 0)

        is_red = (
            wind_val > 13.0
            or pop > 25
            or thunder_pct > 25
        )
        is_yellow = (
            not is_red
            and (wind_val > 8.0 or pop > 15 or thunder_pct > 15)
        )

        if is_red:
          bg_color = "#ffdddd"
          border_color = "#ff4b4b"
          text_color = "#d93838"
        elif is_yellow:
          bg_color = "#fffacc"
          border_color = "#ccaa00"
          text_color = "#997a00"
        else:
          bg_color = "#e6f4ea"
          border_color = "#21c354"
          text_color = "#137333"

        rain_level = get_icon_level(pop)
        thunder_level = get_icon_level(thunder_pct)

        grid_html += f"""
        <div style="flex: 1; min-width: 85px; background-color: {bg_color}; border: 2px solid {border_color}; border-radius: 6px; padding: 6px; text-align: center; font-size: 11px;">
          <div style="font-weight: bold; margin-bottom: 4px; border-bottom: 1px solid rgba(0,0,0,0.1);">{time_label}</div>
          <div style="margin-bottom: 4px; color: {text_color}; font-weight: bold;" title="Wind: {wind_val} mph {wind_dir}">{arrow} {int(wind_val)}mph<br><span style="font-size: 9px;">{wind_dir}</span></div>
          <div style="margin-bottom: 2px; color: {text_color};" title="Chance of Rain: {pop}%">💧{'I'*rain_level} <span style="font-size:9px;">{pop}%</span></div>
          <div style="color: {text_color};" title="Chance of Thunder: {thunder_pct}%">⚡{'I'*thunder_level} <span style="font-size:9px;">{thunder_pct}%</span></div>
        </div>
        """

      grid_html += '</div>'
      st.html(grid_html)

    st.divider()
