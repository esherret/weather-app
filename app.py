from datetime import datetime, timezone, timedelta
import requests
import streamlit as st

st.set_page_config(
    page_title="Weather Window Monitor", page_icon="🌤️", layout="wide"
)

# Custom CSS targeting computer/tablet viewports to increase font sizes by ~50% for specific elements
# and remove bolding from windspeed on both platforms.
st.markdown("""
<style>
    /* Remove bolding from wind speed across all platforms */
    .wind-speed-val {
        font-weight: normal !important;
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

        /* Increase size by ~50% for specified elements on computer/tablet */
        .desktop-time {
            font-size: 1.25rem !important;
        }
        .desktop-wind {
            font-size: 1.15rem !important;
        }
        .desktop-metric {
            font-size: 1.15rem !important;
        }
        .desktop-tide {
            font-size: 1.2rem !important;
        }
        .desktop-temp {
            font-size: 1.3rem !important;
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
def get_lat_lon_from_zip(zip_code):
  url = f"https://nominatim.openstreetmap.org/search?postalcode={zip_code}&country=United States&format=json"
  try:
    res = requests.get(url, headers={"User-Agent": "WeatherWindowApp/1.0"}, timeout=5)
    if res.status_code == 200 and res.json():
      data = res.json()[0]
      return float(data["lat"]), float(data["lon"]), data.get("display_name", zip_code)
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
  return f'<span style="display: inline-block; transform: rotate({deg}deg); width: 16px; height: 16px; line-height: 16px; text-align: center; vertical-align: middle; margin-right: 4px;">⬆️</span>'


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


# Initialize session state for zip code dynamically from current location (IP)
if "zip_code" not in st.session_state:
  st.session_state["zip_code"] = get_location_from_ip()

# Sidebar configuration using a form for submit-to-close behavior
st.sidebar.header("Location Settings")
with st.sidebar.form(key="zip_form"):
  entered_zip = st.text_input("Enter ZIP Code", value=st.session_state["zip_code"])
  submit_button = st.form_submit_button(label="Update Location")

  if submit_button:
    st.session_state["zip_code"] = entered_zip

LATITUDE, LONGITUDE, location_name = get_lat_lon_from_zip(st.session_state["zip_code"])

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
        is_yellow = not is_red and (wind_val > 8.0 or pop > 15 or thunder_pct > 15)

        if is_red:
          has_red = True
        elif is_yellow:
          has_yellow = True

      if has_red:
        window_colors[win_name] = "#ff4b4b"
      elif has_yellow:
        window_colors[win_name] = "#ffeb3b"
      else:
        window_colors[win_name] = "#21c354"

    moon_emoji, moon_desc = get_moon_phase_emoji(sample_dt)
    date_str_api = sample_dt.strftime("%Y-%m-%d")
    dawn_str, sunrise_str, sunset_str, dusk_str = get_sun_times(LATITUDE, LONGITUDE, date_str_api)

    header_html = f'''
    <div style="margin-bottom: 12px;">
      <div style="display: flex; align-items: center; gap: 12px;">
        <h3 style="margin: 0;"><span title="{moon_desc}" style="margin-right: 6px;">{moon_emoji}</span>{day_name}</h3>
        <div style="display: flex; gap: 6px;">
    '''
    for win_name in windows_def.keys():
      color = window_colors.get(win_name)
      if color == "PAST":
        header_html += f'<div title="{win_name} (Past)" style="width: 16px; height: 16px;"></div>'
      elif color:
        header_html += f'<div title="{win_name}" style="width: 16px; height: 16px; background-color: {color}; border: 1px solid rgba(0,0,0,0.2); border-radius: 4px;"></div>'
      else:
        header_html += f'<div title="{win_name} (No Data)" style="width: 16px; height: 16px; background-color: #eee; border: 1px solid rgba(0,0,0,0.2); border-radius: 4px;"></div>'
    header_html += f'''
        </div>
      </div>
      <div style="font-size: 13px; color: #555; margin-top: 4px; margin-left: 36px; font-weight: 500;">
        First Light: {dawn_str} &nbsp;|&nbsp; Sunrise: {sunrise_str} &nbsp;|&nbsp; Sunset: {sunset_str} &nbsp;|&nbsp; Last Light: {dusk_str}
      </div>
    </div>
    '''
    st.markdown(header_html, unsafe_allow_html=True)

    for window_name, hours in valid_windows.items():
      st.markdown(f"**{window_name}**")

      grid_html = '<div style="display: flex; gap: 8px; overflow-x: auto; padding-bottom: 8px;">'

      for h in hours:
        dummy_dt = sample_dt.replace(hour=h, minute=0, second=0, microsecond=0)
        time_label = dummy_dt.strftime("%l%p").strip()

        if h in day_hours:
          _, period = day_hours[h]
          wind_str = period["windSpeed"]
          wind_val = float(wind_str.split()[0])
          wind_dir = period.get("windDirection", "N")
          pointer_svg = get_wind_svg(wind_dir)

          pop = period.get("probabilityOfPrecipitation", {}).get("value") or 0
          short_fc = period["shortForecast"]
          detailed_fc = period["detailedForecast"].lower()
          text_blob = f"{short_fc.lower()} {detailed_fc}"

          temp_val = period.get("temperature", "--")
          temp_unit = period.get("temperatureUnit", "F")
          cloud_icon = get_cloud_icon(short_fc)

          has_thunder = "thunder" in text_blob or "storm" in text_blob
          thunder_pct = 80 if has_thunder and "slight chance" not in short_fc.lower() else (30 if has_thunder else 0)

          is_red = wind_val > 13.0 or pop > 25 or thunder_pct > 25
          is_yellow = not is_red and (wind_val > 8.0 or pop > 15 or thunder_pct > 15)

          if is_red:
            box_border = "#ff4b4b"
          elif is_yellow:
            box_border = "#ffeb3b"
          else:
            box_border = "#21c354"
          box_bg = "#fff"

          wind_bg = get_rating_bg_color(wind_val, is_wind=True)
          rain_bg = get_rating_bg_color(pop, is_wind=False)
          thunder_bg = get_rating_bg_color(thunder_pct, is_wind=False)

          rain_level = get_icon_level(pop)
          thunder_level = get_icon_level(thunder_pct)

          rain_icons = "💧" * rain_level if rain_level > 0 else ""
          thunder_icons = "⚡" * thunder_level if thunder_level > 0 else ""

          # Tide state determination
          local_dt = dummy_dt.replace(tzinfo=None)
          tide_state = "Rising"
          if tides_data:
            hour_preds = [(dt, val) for dt, val in tides_data.items() if dt.date() == local_dt.date() and dt.hour == local_dt.hour]
            found_extreme = None
            if hour_preds:
              for dt_p, val_p in hour_preds:
                prev_v = tides_data.get(dt_p - timedelta(minutes=6), val_p)
                next_v = tides_data.get(dt_p + timedelta(minutes=6), val_p)
                if val_p >= prev_v and val_p >= next_v:
                  found_extreme = "High"
                  break
                elif val_p <= prev_v and val_p <= next_v:
                  found_extreme = "Low"
                  break

            if found_extreme:
              tide_state = found_extreme
            else:
              next_hr_dt = local_dt + timedelta(hours=1)
              v_curr = tides_data.get(local_dt)
              v_next = tides_data.get(next_hr_dt)
              if v_curr is not None and v_next is not None:
                if v_next < v_curr:
                  tide_state = "Falling"
                else:
                  tide_state = "Rising"
              else:
                prev_hr_dt = local_dt - timedelta(hours=1)
                v_prev = tides_data.get(prev_hr_dt, v_curr)
                if v_curr is not None and v_prev is not None:
                  if v_curr < v_prev:
                    tide_state = "Falling"
                  else:
                    tide_state = "Rising"

          if tide_state == "High":
            tide_display = '<span style="display: inline-block; width: 24px; height: 24px; line-height: 24px; text-align: center; background-color: white; color: red; font-weight: bold; font-size: 14px; border-radius: 50%; box-shadow: 0 0 2px rgba(0,0,0,0.3);">H</span> High'
          elif tide_state == "Low":
            tide_display = '<span style="display: inline-block; width: 24px; height: 24px; line-height: 24px; text-align: center; background-color: white; color: green; font-weight: bold; font-size: 14px; border-radius: 50%; box-shadow: 0 0 2px rgba(0,0,0,0.3);">L</span> Low'
          elif tide_state == "Rising":
            tide_display = '<span style="font-weight: bold; font-size: 20px;">↗</span>&nbsp;&nbsp;<span style="font-size: 11px; font-weight: normal;">Rising</span>'
          else:
            tide_display = '<span style="font-weight: bold; font-size: 20px;">↘</span>&nbsp;&nbsp;<span style="font-size: 11px; font-weight: normal;">Falling</span>'

          grid_html += f"""
          <div style="flex: 1; min-width: 100px; background-color: {box_bg}; border: 2px solid {box_border}; border-radius: 8px; padding: 8px; text-align: center; font-size: 13px; color: black;">
            <div class="desktop-time" style="font-weight: bold; font-size: 14px; margin-bottom: 6px; border-bottom: 1px solid rgba(0,0,0,0.1);">{time_label}</div>
            <div style="margin-bottom: 6px; background-color: {wind_bg}; border-radius: 5px; padding: 4px;" title="Wind: {wind_val} mph {wind_dir}">
              <div class="desktop-wind wind-speed-val" style="font-size: 13px;">{int(wind_val)}mph</div>
              <div class="desktop-wind">{pointer_svg}<span style="font-size: 11px;">{wind_dir}</span></div>
            </div>
            <div class="desktop-metric" style="margin-bottom: 4px; background-color: {rain_bg}; border-radius: 5px; padding: 4px;" title="Chance of Rain: {pop}%">{rain_icons} <span style="font-size:11px; font-weight: 500;">{pop}%</span></div>
            <div class="desktop-metric" style="margin-bottom: 6px; background-color: {thunder_bg}; border-radius: 5px; padding: 4px;" title="Chance of Thunder: {thunder_pct}%"><span style="text-shadow: -1px -1px 0 #000, 1px -1px 0 #000, -1px 1px 0 #000, 1px 1px 0 #000; color: #ffeb3b;">{thunder_icons}</span> <span style="font-size:11px; font-weight: 500;">{thunder_pct}%</span></div>
            <div class="desktop-tide" style="margin-bottom: 4px; font-size: 12px; background-color: #f0f9ff; border-radius: 4px; padding: 4px;" title="Tide">{tide_display}</div>
            <div class="desktop-temp" style="font-size: 12px; font-weight: bold; background-color: #f8fafc; border-radius: 4px; padding: 4px;" title="Temperature & Sky"><span style="font-size: 24px; vertical-align: middle;">{cloud_icon}</span> {temp_val}°{temp_unit}</div>
          </div>
          """
        else:
          current_utc = datetime.now(timezone.utc)
          dummy_utc = dummy_dt.astimezone(timezone.utc)
          
          if dummy_utc < current_utc:
            msg = "Data no longer available"
          else:
            msg = "Data not yet available"

          grid_html += f"""
          <div style="flex: 1; min-width: 100px; background-color: #f8f9fa; border: 2px solid #d1d5db; border-radius: 8px; padding: 8px; text-align: center; font-size: 13px; color: #9ca3af;">
            <div class="desktop-time" style="font-weight: bold; font-size: 14px; margin-bottom: 6px; border-bottom: 1px solid rgba(0,0,0,0.1);">{time_label}</div>
            <div style="margin-top: 25px; font-size: 11px; font-style: italic; line-height: 1.3;">{msg}</div>
          </div>
          """

      grid_html += '</div>'
      st.html(grid_html)

    st.divider()
