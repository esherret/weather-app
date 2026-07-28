from datetime import datetime, timezone, timedelta
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


@st.cache_data(ttl=3600)
def fetch_tides():
  today_str = datetime.now().strftime("%Y%m%d")
  url = (
      f"https://api.tidesandcurrents.noaa.gov/api/prod/datagetter?"
      f"begin_date={today_str}&range=168&station=8721604&product=predictions"
      f"&datum=MLLW&units=english&time_zone=lst_ldt&format=json"
  )
  try:
    res = requests.get(url, timeout=5)
    if res.status_code == 200:
      data = res.json()
      predictions = data.get("predictions", [])
      tide_map = {}
      for p in predictions:
        # p['t'] format: "YYYY-MM-DD HH:MM"
        dt_obj = datetime.strptime(p["t"], "%Y-%m-%d %H:%M")
        tide_map[dt_obj] = float(p["v"])
      return tide_map
  except Exception:
    pass
  return {}


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


st.title("🌤️ Weather & Tide Windows (Port Canaveral Station ID: 8721604)")

periods = fetch_forecast()
tides_data = fetch_tides()

if not periods:
  st.error("Failed to retrieve data from the National Weather Service API.")
else:
  days_data = {}
  now = datetime.now(timezone.utc)

  for period in periods:
    start_time = datetime.fromisoformat(period["startTime"])
    day_name = start_time.strftime("%A, %b %d")
    hour = start_time.hour

    window_name = get_window_type(hour)
    if not window_name:
      continue

    if day_name not in days_data:
      days_data[day_name] = {
          "date_obj": start_time,
          "Morning (6AM-9AM)": [],
          "Midday (10AM-1PM)": [],
          "Afternoon (2PM-5PM)": [],
          "Evening (6PM-9PM)": [],
      }
    days_data[day_name][window_name].append((start_time, period))

  for day_name, windows in days_data.items():
    window_colors = {}
    for win_name in ["Morning (6AM-9AM)", "Midday (10AM-1PM)", "Afternoon (2PM-5PM)", "Evening (6PM-9PM)"]:
      win_periods = windows[win_name]
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

    moon_emoji, moon_desc = get_moon_phase_emoji(windows["date_obj"])

    header_html = f'<div style="display: flex; align-items: center; gap: 10px; margin-bottom: 8px;"><h3 style="margin: 0;"><span title="{moon_desc}" style="margin-right: 6px;">{moon_emoji}</span>{day_name}</h3><div style="display: flex; gap: 4px;">'
    for win_name in ["Morning (6AM-9AM)", "Midday (10AM-1PM)", "Afternoon (2PM-5PM)", "Evening (6PM-9PM)"]:
      color = window_colors.get(win_name)
      if color == "PAST":
        header_html += f'<div title="{win_name} (Past)" style="width: 14px; height: 14px;"></div>'
      elif color:
        header_html += f'<div title="{win_name}" style="width: 14px; height: 14px; background-color: {color}; border: 1px solid rgba(0,0,0,0.2); border-radius: 3px;"></div>'
      else:
        header_html += f'<div title="{win_name} (No Data)" style="width: 14px; height: 14px; background-color: #eee; border: 1px solid rgba(0,0,0,0.2); border-radius: 3px;"></div>'
    header_html += '</div></div>'
    st.markdown(header_html, unsafe_allow_html=True)

    for window_name in ["Morning (6AM-9AM)", "Midday (10AM-1PM)", "Afternoon (2PM-5PM)", "Evening (6PM-9PM)"]:
      window_periods = windows[window_name]
      if not window_periods:
        continue

      st.markdown(f"**{window_name}**")

      grid_html = '<div style="display: flex; gap: 6px; overflow-x: auto; padding-bottom: 6px;">'

      for i, (start_time, period) in enumerate(window_periods):
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

        local_dt = start_time.astimezone() # Local datetime for this forecast box hour
        
        tide_state = "N/A"
        if tides_data:
          # Find all actual high/low peaks/troughs across the full day or neighboring hours
          # We check a window from 30 minutes before this hour to 30 minutes after this hour
          hour_start_dt = local_dt.replace(minute=0, second=0, microsecond=0)
          hour_end_dt = hour_start_dt + timedelta(hours=1)

          matched_extreme = None
          
          # Scan NOAA predictions dictionary for any local peak or trough falling strictly inside [hour_start_dt, hour_end_dt)
          # A local peak/trough is where value is greater than or less than both adjacent entries (e.g., +/- 1 hour)
          sorted_tide_keys = sorted(tides_data.keys())
          
          extreme_found = None
          for dt_key in sorted_tide_keys:
            if hour_start_dt <= dt_key < hour_end_dt:
              # Check if it's a local max or min by inspecting neighbors
              val = tides_data[dt_key]
              prev_dt = dt_key - timedelta(hours=1)
              next_dt = dt_key + timedelta(hours=1)
              if prev_dt in tides_data and next_dt in tides_data:
                p_val = tides_data[prev_dt]
                n_val = tides_data[next_dt]
                if val >= p_val and val >= n_val:
                  extreme_found = ("High", dt_key)
                  break
                elif val <= p_val and val <= n_val:
                  extreme_found = ("Low", dt_key)
                  break

          if extreme_found:
            t_type, t_dt = extreme_found
            tide_state = f"{t_type} {t_dt.strftime('%H:%M')}"
          else:
            # If no exact peak/trough falls inside this specific hour slot, check general trend direction between start and end of hour
            val_start = tides_data.get(hour_start_dt, None)
            val_next = tides_data.get(hour_end_dt, None)
            if val_start is not None and val_next is not None:
              diff = val_next - val_start
              if abs(diff) < 0.02:
                tide_state = "Slack Tide"
              elif diff > 0:
                tide_state = "Rising Tide"
              else:
                tide_state = "Falling Tide"
            else:
              tide_state = "Rising Tide"

        grid_html += f"""
        <div style="flex: 1; min-width: 85px; background-color: {box_bg}; border: 2px solid {box_border}; border-radius: 6px; padding: 6px; text-align: center; font-size: 11px; color: black;">
          <div style="font-weight: bold; margin-bottom: 4px; border-bottom: 1px solid rgba(0,0,0,0.1);">{time_label}</div>
          <div style="margin-bottom: 4px; background-color: {wind_bg}; border-radius: 4px; padding: 2px;" title="Wind: {wind_val} mph {wind_dir}">
            <div>{int(wind_val)}mph</div>
            <div>{pointer_svg}<span style="font-size: 9px;">{wind_dir}</span></div>
          </div>
          <div style="margin-bottom: 2px; background-color: {rain_bg}; border-radius: 4px; padding: 2px;" title="Chance of Rain: {pop}%">💧{'I'*rain_level} <span style="font-size:9px;">{pop}%</span></div>
          <div style="margin-bottom: 4px; background-color: {thunder_bg}; border-radius: 4px; padding: 2px;" title="Chance of Thunder: {thunder_pct}%"><span style="text-shadow: 1px 1px 0 #000;">⚡</span>{'I'*thunder_level} <span style="font-size:9px;">{thunder_pct}%</span></div>
          <div style="font-size: 9px; color: #0369a1; font-weight: bold; background-color: #f0f9ff; border-radius: 3px; padding: 2px;" title="Tide State">{tide_state}</div>
        </div>
        """

      grid_html += '</div>'
      st.html(grid_html)

    st.divider()
