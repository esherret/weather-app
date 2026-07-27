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

TARGET_START_HOUR = 5
TARGET_END_HOUR = 21
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


def get_wind_arrow(direction_str):
  arrows = {
      "N": "⬇️ N",
      "NNE": "↙️ NNE",
      "NE": "↙️ NE",
      "ENE": "⬅️ ENE",
      "E": "⬅️ E",
      "ESE": "↖️ ESE",
      "SE": "↖️ SE",
      "SSE": "⬆️ SSE",
      "S": "⬆️ S",
      "SSW": "↗️ SSW",
      "SW": "↗️ SW",
      "WSW": "➡️ WSW",
      "W": "➡️ W",
      "WNW": "↘️ WNW",
      "NW": "↘️ NW",
      "NNW": "⬇️ NNW",
  }
  return arrows.get(direction_str.upper(), direction_str)


st.title("🌤️ Local Weather Window Monitor")
st.write(
    f"Checking conditions between **5:00 AM** and **9:00 PM** (Max Wind:"
    f" {MAX_WIND_SPEED_MPH} mph)"
)

periods = fetch_forecast()

if not periods:
  st.error("Failed to retrieve data from the National Weather Service API.")
else:
  # Group periods by day of the week
  days_data = {}
  for period in periods:
    start_time = datetime.fromisoformat(period["startTime"])
    day_name = start_time.strftime("%A, %b %d, %Y")

    if day_name not in days_data:
      days_data[day_name] = []
    days_data[day_name].append((start_time, period))

  for day_name, day_periods in days_data.items():
    st.subheader(day_name)

    has_valid_hours = False
    for start_time, period in day_periods:
      hour = start_time.hour

      if TARGET_START_HOUR <= hour <= TARGET_END_HOUR:
        has_valid_hours = True
        time_str = start_time.strftime("%I:%M %p")

        wind_str = period["windSpeed"]
        wind_val = float(wind_str.split()[0])
        wind_dir = period.get("windDirection", "")
        wind_arrow_text = get_wind_arrow(wind_dir)

        short_forecast = period["shortForecast"].lower()
        detailed_forecast = period["detailedForecast"].lower()

        # Extract precise probability of precipitation if available, else fallback
        pop = period.get("probabilityOfPrecipitation", {}).get("value")
        if pop is None:
          pop = 80 if any(w in short_forecast for w in ["rain", "shower", "storm"]) else 0

        # Estimate thunderstorm probability based on text
        has_thunder = "thunder" in short_forecast or "thunder" in detailed_forecast
        storm_pop = pop if has_thunder and ("storm" in short_forecast or "thunder" in short_forecast) else (100 if has_thunder else 0)

        has_wind_issue = wind_val > MAX_WIND_SPEED_MPH
        has_precip = pop > 0 and not ALLOW_PRECIPITATION
        has_thunder_issue = storm_pop > 0 and not ALLOW_THUNDER

        is_good_window = not (has_wind_issue or has_precip or has_thunder_issue)
        reasons = []

        if has_wind_issue:
          reasons.append(f"High wind ({wind_str})")
        if has_precip:
          reasons.append(f"Precipitation ({pop}%)")
        if has_thunder_issue:
          reasons.append(f"Thunder risk ({storm_pop}%)")

        with st.container():
          col1, col2 = st.columns([1, 2])
          with col1:
            st.markdown(f"**{time_str}**")
            st.text(f"Wind: {wind_arrow_text} ({wind_str})")
          with col2:
            if is_good_window:
              st.success("🟢 GOOD WINDOW - Conditions clear")
            else:
              st.error(f"🔴 BAD WINDOW - {', '.join(reasons)}")

            # Custom styled bar graphs for Showers and Thunderstorms
            st.write(f"Showers: {pop}%")
            st.progress(min(max(pop, 0), 100))

            st.write(f"Thunderstorms: {storm_pop}%")
            # Red styled progress bar using markdown container simulation since default is blue
            st.markdown(
                f"""
                <div style="background-color: #ddd; border-radius: 4px; overflow: hidden; width: 100%; height: 10px;">
                  <div style="background-color: #ff4b4b; width: {storm_pop}%; height: 10px;"></div>
                </div>
                """,
                unsafe_allow_html=True,
            )
          st.divider()

    if not has_valid_hours:
      st.info(f"No tracking hours available for {day_name} within the selected window.")
