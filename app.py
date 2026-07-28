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


def get_icon_level(pct):
  if pct >= 75:
      return 4
  elif pct >= 50:
      return 3
  elif pct >= 25:
      return 2
  elif pct > 0:
      return 1
  else:
      return 0


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

    header_html = f'<div style="display: flex; align-items: center; gap: 10px; margin-bottom: 8px;"><h3 style="margin: 0;"><span title="{moon_desc}" style="margin-right: 6px;">{moon_emoji}</span>{day_name}</h3><div style="display: flex; gap: 4px;">'
    for win_name in windows_def.keys():
      color = window_colors.get(win_name)
      if color == "PAST":
        header_html += f'<div title="{win_name} (Past)" style="width: 14px; height: 14px;"></div>'
      elif color:
        header_html += f'<div title="{win_name}" style="width: 14px; height: 14px; background-color: {color}; border: 1px solid rgba(0,0,0,0.2); border-radius: 3px;"></div>'
      else:
        header_html += f'<div title="{win_name} (No Data)" style="width: 14px; height: 14px; background-color: #eee; border: 1px solid rgba(0,0,0,0.2); border-radius: 3px;"></div>'
    header_html += '</div></div>'
    st.markdown(header_html, unsafe_allow_html=True)

    for window_name, hours in valid_windows.items():
      st.markdown(f"**{window_name}**")

      grid_html = '<div style="display: flex; gap: 6px; overflow-x: auto; padding-bottom: 6px;">'

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
          short_fc = period["shortForecast"].lower()
          detailed_fc = period["detailedForecast"].lower()
          text_blob = f"{short_fc} {detailed_fc}"

          has_thunder = "thunder" in text_blob or "storm" in text_blob
          thunder_pct = 80 if has_thunder and "slight chance" not in short_fc else (30 if has_thunder else 0)

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

          rain_icons = "💧" * rain_level if rain_level > 0 else "—"
          thunder_icons = "⚡" * thunder_level if thunder_level > 0 else "—"

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

          # Formatting for High (red H in white circle), Low (green L in white circle), Rising (arrow), Falling (arrow)
          if tide_state == "High":
            tide_display = '<span style="display: inline-block; width: 22px; height: 22px; line-height: 22px; text-align: center; background-color: white; color: red; font-weight: bold; font-size: 14px; border-radius: 50%; box-shadow: 0 0 2px rgba(0,0,0,0.3);">H</span>'
          elif tide_state == "Low":
            tide_display = '<span style="display: inline-block; width: 22px; height: 22px; line-height: 22px; text-align: center; background-color: white; color: green; font-weight: bold; font-size: 14px; border-radius: 50%; box-shadow: 0 0 2px rgba(0,0,0,0.3);">L</span>'
          elif tide_state == "Rising":
            tide_display = '<span style="color: black; font-weight: bold; font-size: 14px;">↗ Rising</span>'
          else:
            tide_display = '<span style="color: black; font-weight: bold; font-size: 14px;">↘ Falling</span>'

          grid_html += f"""
          <div style="flex: 1; min-width: 85px; background-color: {box_bg}; border: 2px solid {box_border}; border-radius: 6px; padding: 6px; text-align: center; font-size: 11px; color: black;">
            <div style="font-weight: bold; margin-bottom: 4px; border-bottom: 1px solid rgba(0,0,0,0.1);">{time_label}</div>
            <div style="margin-bottom: 4px; background-color: {wind_bg}; border-radius: 4px; padding: 2px;" title="Wind: {wind_val} mph {wind_dir}">
              <div>{int(wind_val)}mph</div>
              <div>{pointer_svg}<span style="font-size: 9px;">{wind_dir}</span></div>
            </div>
            <div style="margin-bottom: 2px; background-color: {rain_bg}; border-radius: 4px; padding: 2px;" title="Chance of Rain: {pop}%">{rain_icons} <span style="font-size:9px;">{pop}%</span></div>
            <div style="margin-bottom: 4px; background-color: {thunder_bg}; border-radius: 4px; padding: 2px;" title="Chance of Thunder: {thunder_pct}%"><span style="text-shadow: -1px -1px 0 #000, 1px -1px 0 #000, -1px 1px 0 #000, 1px 1px 0 #000; color: #ffeb3b;">{thunder_icons}</span> <span style="font-size:9px;">{thunder_pct}%</span></div>
            <div style="font-size: 10px; font-weight: bold; background-color: #f0f9ff; border-radius: 3px; padding: 3px;" title="Tide">{tide_display}</div>
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
          <div style="flex: 1; min-width: 85px; background-color: #f8f9fa; border: 2px solid #d1d5db; border-radius: 6px; padding: 6px; text-align: center; font-size: 11px; color: #9ca3af;">
            <div style="font-weight: bold; margin-bottom: 4px; border-bottom: 1px solid rgba(0,0,0,0.1);">{time_label}</div>
            <div style="margin-top: 15px; font-size: 9px; font-style: italic; line-height: 1.2;">{msg}</div>
          </div>
          """

      grid_html += '</div>'
      st.html(grid_html)

    st.divider()
