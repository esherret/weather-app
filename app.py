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


def get_wind_svg(direction_str):
  degrees = {
      "N": 180,
      "NNE": 202.5,
      "NE": 225,
      "ENE": 247.5,
      "E": 270,
      "ESE": 292.5,
      "SE": 315,
      "SSE": 337.5,
      "S": 0,
      "SSW": 22.5,
      "SW": 45,
      "WSW": 67.5,
      "W": 90,
      "WNW": 112.5,
      "NW": 135,
      "NNW": 157.5,
  }
  deg = degrees.get(direction_str.upper(), 0)
  return f'<span style="display: inline-block; transform: rotate({deg}deg); width: 14px; height: 14px; line-height: 14px; text-align: center; vertical-align: middle; margin-right: 4px;">⬆️</span>'


def get_window_type(hour):
  if 6 <= hour <= 9:
    return "Morning (6AM-9AM)"
  elif 10 <= hour <= 13:
    return "Midday (10AM-1PM)"
  elif 14 <= hour <= 17:
    return "Afternoon (2PM-5PM)"
  elif 18 <= hour <= 21:
    return "Evening (6PM-9PM)"
  return None


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


def get_rating_bg_color(val, is_wind=False):
  if is_wind:
    if val > 13.0:
      return "#ffdddd"
    elif val > 8.0:
      return "#fffacc"
    else:
      return "#e6f4ea"
  else:
    if val > 25:
      return "#ffdddd"
    elif val > 15:
      return "#fffacc"
    else:
      return "#e6f4ea"


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

    window_name = get_window_type(hour)
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
        pointer_svg = get_wind_svg(wind_dir)

        pop = period.get("probabilityOfPrecipitation", {}).get("value") or 0
        short_fc = period["shortForecast"].lower()
        detailed_fc = period["detailedForecast"].lower()
        text_blob = f"{short_fc} {detailed_fc}"

        has_thunder = "thunder" in text_blob or "storm" in text_blob
        thunder_pct = 80 if has_thunder and "slight chance" not in short_fc else (30 if has_thunder else 0)

        is_red = wind_val > 13.0 or pop > 25 or thunder_pct > 25
        is_yellow = not is_red and (wind_val > 8.0 or pop > 15 or thunder_pct > 15)

        if is_red:
          box_border = "#ff4b4b"
          box_bg = "#fff"
        elif is_yellow:
          box_border = "#ffeb3b"
          box_bg = "#fff"
        else:
          box_border = "#21c354"
          box_bg = "#fff"

        wind_bg = get_rating_bg_color(wind_val, is_wind=True)
        rain_bg = get_rating_bg_color(pop, is_wind=False)
        thunder_bg = get_rating_bg_color(thunder_pct, is_wind=False)

        rain_level = get_icon_level(pop)
        thunder_level = get_icon_level(thunder_pct)

        grid_html += f"""
        <div style="flex: 1; min-width: 85px; background-color: {box_bg}; border: 2px solid {box_border}; border-radius: 6px; padding: 6px; text-align: center; font-size: 11px; color: black;">
          <div style="font-weight: bold; margin-bottom: 4px; border-bottom: 1px solid rgba(0,0,0,0.1);">{time_label}</div>
          <div style="margin-bottom: 4px; background-color: {wind_bg}; border-radius: 4px; padding: 2px;" title="Wind: {wind_val} mph {wind_dir}">
            <div>{int(wind_val)}mph</div>
            <div>{pointer_svg}<span style="font-size: 9px;">{wind_dir}</span></div>
          </div>
          <div style="margin-bottom: 2px; background-color: {rain_bg}; border-radius: 4px; padding: 2px;" title="Chance of Rain: {pop}%">💧{'I'*rain_level} <span style="font-size:9px;">{pop}%</span></div>
          <div style="background-color: {thunder_bg}; border-radius: 4px; padding: 2px;" title="Chance of Thunder: {thunder_pct}%"><span style="text-shadow: 1px 1px 0 #000;">⚡</span>{'I'*thunder_level} <span style="font-size:9px;">{thunder_pct}%</span></div>
        </div>
        """

      grid_html += '</div>'
      st.html(grid_html)

    st.divider()
