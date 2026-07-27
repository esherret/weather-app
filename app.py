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

TARGET_START_HOUR = 8
TARGET_END_HOUR = 20
MAX_WIND_SPEED_MPH = 15.0
ALLOW_PRECIPITATION = False
ALLOW_THUNDER = False

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


st.title("🌤️ Local Weather Window Monitor")
st.write(
    f"Checking conditions between **{TARGET_START_HOUR}:00** and"
    f" **{TARGET_END_HOUR}:00** (Max Wind: {MAX_WIND_SPEED_MPH} mph)"
)

periods = fetch_forecast()

if not periods:
  st.error("Failed to retrieve data from the National Weather Service API.")
else:
  for period in periods:
    start_time = datetime.fromisoformat(period["startTime"])
    hour = start_time.hour

    if TARGET_START_HOUR <= hour <= TARGET_END_HOUR:
      wind_str = period["windSpeed"]
      wind_val = float(wind_str.split()[0])

      short_forecast = period["shortForecast"].lower()
      detailed_forecast = period["detailedForecast"].lower()

      has_wind_issue = wind_val > MAX_WIND_SPEED_MPH
      has_precip = any(
          w in short_forecast or w in detailed_forecast
          for w in ["rain", "shower", "storm", "snow", "drizzle"]
      )
      has_thunder = "thunder" in short_forecast or "thunder" in detailed_forecast

      is_good_window = True
      reasons = []

      if has_wind_issue:
        is_good_window = False
        reasons.append(f"High wind ({wind_str})")
      if not ALLOW_PRECIPITATION and has_precip:
        is_good_window = False
        reasons.append(f"Precipitation ({period['shortForecast']})")
      if not ALLOW_THUNDER and has_thunder:
        is_good_window = False
        reasons.append("Thunder risk")

      with st.container():
        col1, col2 = st.columns([1, 3])
        with col1:
          st.text(start_time.strftime("%b %d, %H:%M"))
        with col2:
          if is_good_window:
            st.success("🟢 GOOD WINDOW - Conditions clear")
          else:
            st.error(f"🔴 BAD WINDOW - {', '.join(reasons)}")
        st.divider()
