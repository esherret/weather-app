from datetime import datetime, timezone, timedelta
import requests
import streamlit as st

st.set_page_config(
    page_title="Weather Window Monitor", page_icon="🌤️", layout="wide"
)

# Custom CSS for spacing, top margin to clear Streamlit's toolbar, bolding, sizing, and header shading.
st.markdown("""
<style>
    .weather-card * {
        font-weight: bold !important;
    }

    .main .block-container {
        padding-top: 3.5rem !important;
    }

    @media (min-width: 768px) {
        .block-container {
            max-width: 95rem;
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


# Initialize session state for location query.
if "location_query" not in st.session_state:
  st.session_state["location_query"] = get_location_from_ip()

# Sidebar configuration
st.sidebar.header("Location Settings")
with st.sidebar.form(key="location_form"):
  entered_query = st.text_input("Enter ZIP, Address, or Landmark", value=st.session_state["location_query"])
  submit_button = st.form_submit_button(label="Update Location")

# Check if form was submitted to update session state and rerun app
if submit_button and entered_query != st.session_state["location_query"]:
    st.session_state["location_query"] = entered_query
    st.rerun()

LATITUDE, LONGITUDE, location_name = get_lat_lon_from_query(st.session_state["location_query"])

display_title_location = location_name.split(",")[0] if location_name else "Weather"

# Top layout containing title/caption on the left and comprehensive legends on the right
top_col1, top_col2 = st.columns([2, 3])
with top_col1:
  st.title(f"{display_title_location} Weather")
  st.caption(f"Current Location Context: {location_name}")

with top_col2:
  st.markdown("""
    <div style="display: flex; justify-content: flex-end; align-items: flex-start; height: 100%; padding-top: 5px;">
      <div style="display: flex; flex-direction: column; gap: 4px; font-size: 11px; font-weight: bold; background: #f8fafc; padding: 6px 10px; border: 1px solid #d1d5db; border-radius: 6px; box-shadow: 0 1px 2px rgba(0,0,0,0.05);">
        <div style="display: flex; align-items: center; gap: 8px;">
          <span style="color: #4b5563;">Wind Ranges:</span>
          <div style="display: flex; align-items: center; gap: 3px;">
            <span style="display: inline-block; width: 10px; height: 10px; background-color: #e6f4ea; border: 1px solid #21c354; border-radius: 2px;"></span>
            <span>≤8</span>
          </div>
          <div style="display: flex; align-items: center; gap: 3px;">
            <span style="display: inline-block; width: 10px; height: 10px; background-color: #fffacc; border: 1px solid #ffeb3b; border-radius: 2px;"></span>
            <span>8.1–13</span>
          </div>
          <div style="display: flex; align-items: center; gap: 3px;">
            <span style="display: inline-block; width: 10px; height: 10px; background-color: #ffdddd; border: 1px solid #ff4b4b; border-radius: 2px;"></span>
            <span>>13 mph</span>
          </div>
        </div>
        <div style="display: flex; align-items: center; gap: 8px;">
          <span style="color: #4b5563;">Rain (%):</span>
          <span>💧: 1–24%</span>
          <span>💧💧: 25–49%</span>
          <span>💧💧💧: ≥50%</span>
        </div>
        <div style="display: flex; align-items: center; gap: 8px;">
          <span style="color: #4b5563;">Thunder (%):</span>
          <span>⚡: 1–24%</span>
          <span>⚡⚡: 25–49%</span>
          <span>⚡⚡⚡: ≥50%</span>
        </div>
      </div>
    </div>
  """, unsafe_allow_html=True)

st.markdown(
    f"📊 [View official National Weather Service forecast for this area]"
    f"(https://forecast.weather.gov/MapClick.php?lat={LATITUDE}&lon={LONGITUDE})"
)

station_id = fetch_nearest_tide_station(LATITUDE, LONGITUDE)
periods = fetch_forecast(LATITUDE,
