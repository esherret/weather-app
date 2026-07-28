from datetime import datetime, timezone, timedelta
import requests
import streamlit as st

st.set_page_config(
    page_title="Weather Window Monitor", page_icon="🌤️", layout="wide"
)

# Custom CSS for spacing between wind icon and text on desktop/tablet, bolding, sizing, and header shading.
st.markdown("""
<style>
    .weather-card * {
        font-weight: bold !important;
    }

    @media (min-width: 768px) {
        .block-container {
            max-width: 95rem;
            padding-top: 2rem;
            padding-right: 2rem;
            padding-left: 2rem;
            padding-bottom: 2rem;
        }
        
        html, body, [class*="css"] {
            font-size: 18px !important;
        }
        
        h3 {
            font-size: 1.8rem !important;
        }

        .box-time {
            font-size: 1.5rem !important;
        }
        .box-text {
            font-size: 1.15rem !important;
        }
        
        .wind-dir-space {
            display: inline-block;
            width: 14px;
        }
    }

    @media (max-width: 767px) {
        .box-time {
            font-size: 0.95rem !important;
        }
        .box-text {
            font-size: 0.65rem !important;
        }
        .weather-card {
            min-width: 0 !important;
            padding: 4px !important;
        }
        .wind-dir-space {
            display: inline;
            width: auto;
        }
    }
</style>
""", unsafe_allow_html=True)

HEADERS = {
    "User-Agent": "(myweatherapp.com, developer@myweatherapp.com)",
    "Accept": "application/geo+json",
}


@st.cache_data(ttl=3600)
def get_location_from_ip():
  try:
    res = requests.get("https://ipapi.co/json", timeout=3)
    if res.status_code == 200:
      data = res.json()
      postal = data.get("postal")
      if postal:
        return postal
  except Exception:
    pass
  return "32953"


@st.cache_data(ttl=3600)
def get_lat_lon_from_query(query, user_lat=28.3, user_lon=-80.6):
  url = f"https://nominatim.openstreetmap.org/search?q={requests.utils.quote(query)}&country=United States&format=json&limit=1"
  try:
    res = requests.get(url, headers={"User-Agent": "WeatherWindowApp/1.0"}, timeout=5)
    if res.status_code == 200 and res.json():
      data = res.json()[0]
      return float(data["lat"]), float(data["lon"]), data.get("display_name", query)
  except Exception:
    pass
  
  url_fallback = f"https://nominatim.openstreetmap.org/search?q={requests.utils.quote(query + ', Merritt Island, FL')} &format=json&limit=1"
  try:
    res = requests.get(url_fallback, headers={"User-Agent": "WeatherWindowApp/1.0"}, timeout=5)
    if res.status_code == 200 and res.json():
      data = res.json()[0]
      return float(data["lat"]), float(data["lon"]), data.get("display_name", query)
  except Exception:
    pass

  return 28.4021, -80.6629, "Merritt Island, FL (Default)"


@st.cache_data(ttl=1800)
def fetch_forecast(lat, lon):
  points_url = f"https://api.weather.gov/points/{lat},{lon}"
  response = requests.get(points_url, headers=HEADERS)
  if response.status_code != 200:
    return None

  point_data = response.json()
  forecast_hourly_url = point_data["properties"]["forecastHourly"]

  forecast_response = requests.get(forecast_hourly_url, headers=HEADERS)
  if forecast_response.status_code != 200:
    return None

  return forecast_response.json()["properties"]["periods"]


@st.cache_data(ttl=3600)
def fetch_nearest_tide_station(lat, lon):
  url = f"https://api.tidesandcurrents.noaa.gov/mdapi/prod/webapi/stations.json?type=tidepredictions&units=english"
  try:
    res = requests.get(url, timeout=5)
    if res.status_code == 200:
      stations = res.json().get("stations", [])
      closest_station = None
      min_dist = float("inf")
      for s in stations:
        try:
          s_lat = float(s["lat"])
          s_lon = float(s["lng"])
          dist = (s_lat - lat) ** 2 + (s_lon - lon) ** 2
          if dist < min_dist:
            min_dist = dist
            closest_station = s["id"]
        except (KeyError, ValueError):
          continue
      return closest_station or "8721604"
  except Exception:
    pass
  return "8721604"


@st.cache_data(ttl=3600)
def fetch_tides(station_id):
  today_str = datetime.now().strftime("%Y%m%d")
  url = (
      f"https://api.tidesandcurrents.noaa.gov/api/prod/datagetter?"
      f"begin_date={today_str}&range=168&station={station_id}&product=predictions"
      f"&datum=MLLW&units=english&time_zone=lst_ldt&format=json"
  )
  try:
    res = requests.get(url, timeout=5)
    if res.status_code == 200:
      data = res.json()
      predictions = data.get("predictions", [])
      tide_map = {}
      for p in predictions:
        dt_obj = datetime.strptime(p["t"], "%Y-%m-%d %H:%M")
        tide_map[dt_obj] = float(p["v"])
      return tide_map
  except Exception:
    pass
  return {}


@st.cache_data(ttl=3600)
def get_sun_times(lat, lon, date_str):
  url = f"https://api.sunrise-sunset.org/json?lat={lat}&lng={lon}&date={date_str}&formatted=0"
  try:
    res = requests.get(url, timeout=3)
    if res.status_code == 200:
      data = res.json()
      if data.get("status") == "OK":
        results = data["results"]
        dawn_utc = datetime.fromisoformat(results["civil_twilight_begin"])
        dusk_utc = datetime.fromisoformat(results["civil_twilight_end"])
        rise_utc = datetime.fromisoformat(results["sunrise"])
        set_utc = datetime.fromisoformat(results["sunset"])
        
        local_tz = timezone(timedelta(hours=-5))
        
        dawn_local = dawn_utc.astimezone(local_tz)
        dusk_local = dusk_utc.astimezone(local_tz)
        rise_local = rise_utc.astimezone(local_tz)
        set_local = set_utc.astimezone(local_tz)
        
        return (
            dawn_local.strftime("%I:%M %p").lstrip("0"),
            rise_local.strftime("%I:%M %p").lstrip("0"),
            set_local.strftime("%I:%M %p").lstrip("0"),
            dusk_local.strftime("%I:%M %p").lstrip("0"),
        )
  except Exception:
    pass
  return "6:10 AM", "6:42 AM", "8:16 PM", "8:48 PM"


def get_moon_phase_emoji(dt):
  known_new_moon = datetime(2024, 1, 11, tzinfo=timezone.utc)
  lunar_cycle = 29.5305877057
  delta = (dt.astimezone(timezone.utc) - known_new_moon).total_seconds() / 86400.0
  phase = (delta % lunar_cycle) / lunar_cycle

  if phase < 0.03 or phase > 0.97:
    return "🌑", "New Moon"
  elif phase < 0.22:
    return "🌒", "Waxing Crescent"
  elif phase < 0.28:
    return "🌓", "First Quarter"
  elif phase < 0.47:
    return "🌔", "Waxing Gibbous"
  elif phase < 0.53:
    return "🌕", "Full Moon"
  elif phase < 0.72:
    return "🌖", "Waning Gibbous"
  elif phase < 0.78:
    return "🌗", "Last Quarter"
  else:
    return "🌘", "Waning Crescent"


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


def get_icon_level(pct):
  if pct >= 50:
      return 3
  elif pct >= 25:
      return 2
  elif pct > 0:
      return 1
  else:
      return 0


def get_cloud_icon(short_fc):
  text = short_fc.lower()
  if "sunny" in text or "clear" in text:
    return "☀️"
  elif "partly cloudy" in text or "mostly sunny" in text:
    return "⛅"
  elif "cloud" in text or "overcast" in text:
    return "☁️"
  elif "rain" in text or "shower" in text or "storm" in text:
    return "🌧️"
  else:
    return "☁️"


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


# Initialize session state for location query dynamically from current location (IP)
if "location_query" not in st.session_state:
  st.session_state["location_query"] = get_location_from_ip()

# Sidebar configuration using a form for submit-to-close behavior
st.sidebar.header("Location Settings")
with st.sidebar.form(key="location_form"):
  entered_query = st.text_input("Enter ZIP, Address, or Landmark", value=st.session_state["location_query"])
  submit_button = st.form_submit_button(label="Update Location")

  if submit_button:
    st.session_state["location_query"] = entered_query

LATITUDE, LONGITUDE, location_name = get_lat_lon_from_query(st.session_state["location_query"])

display_title_location = location_name.split(",")[0] if location_name else "Weather"

st.title(f"{display_title_location} Weather")
st.caption(f"Current Location Context: {location_name}")

st.markdown(
    f"📊 [View official National Weather Service forecast for this area]"
    f"(https://forecast.weather.gov/MapClick.php?lat={LATITUDE}&lon={LONGITUDE})"
)

station_id = fetch_nearest_tide_station(LATITUDE, LONGITUDE)
periods = fetch_forecast(LATITUDE, LONGITUDE)
tides_data = fetch_tides(station_id)

if not periods:
  st.error("Failed to retrieve data from the National Weather Service API.")
else:
  forecast_map = {}
  for period in periods:
    start_time = datetime.fromisoformat(period["startTime"])
    day_name = start_time.strftime("%A, %b %d")
    hour = start_time.hour
    if day_name not in forecast_map:
      forecast_map[day_name] = {}
    forecast_map[day_name][hour] = (start_time, period)

  windows_def = {
      "Morning (6AM-9AM)": [6, 7, 8, 9],
      "Midday (10AM-1PM)": [10, 11, 12, 13],
      "Afternoon (2PM-5PM)": [14, 15, 16, 17],
      "Evening (6PM-9PM)": [18, 19, 20, 21],
  }

  available_days = list(forecast_map.keys())
  now = datetime.now(timezone.utc)

  for day_name in available_days:
    day_hours = forecast_map[day_name]
    sample_dt = list(day_hours.values())[0][0] if day_hours else datetime.now(timezone.utc)

    valid_windows = {}
    for win_name, hours in windows_def.items():
      if any(h in day_hours for h in hours):
        valid_windows[win_name] = hours

    if not valid_windows:
      continue

    window_colors = {}
    for win_name, hours in windows_def.items():
      win_periods = [day_hours[h] for h in hours if h in day_hours]
      if not win_periods:
        window_colors[win_name] = None
        continue
      
      window_end = win_periods[-1][0].replace(minute=59, second=59)
      if window_end < now:
          window_colors[win_name] = "PAST"
          continue

      has_red = False
      has_yellow = False
      for _, period in win_periods:
        wind_val = float(period["windSpeed"].split()[0])
        pop = period.get("probabilityOfPrecipitation", {}).get("value") or 0
        short_fc = period["shortForecast"].lower()
        detailed_fc = period["detailedForecast"].lower()
        text_blob = f"{short_fc} {detailed_fc}"
        has_thunder = "thunder" in text_blob or "storm" in text_blob
        thunder_pct = 80 if has_thunder and "slight chance" not in short_fc else (30 if has_thunder else 0)

        is_red = wind_val > 13.0 or pop > 25 or thunder_pct > 25
        is_yellow = not is_red and (wind_val > 8.0 or pop >
