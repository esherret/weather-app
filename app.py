from datetime import datetime, timezone
import requests
import streamlit as st

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
def fetch_grid_forecast():
  points_url = f"https://api.weather.gov/points/{LATITUDE},{LONGITUDE}"
  res = requests.get(points_url, headers=HEADERS)
  if res.status_code != 200:
    return None

  point_data = res.json()
  grid_url = point_data["properties"]["forecastGridData"]
  hourly_url = point_data["properties"]["forecastHourly"]

  grid_res = requests.get(grid_url, headers=HEADERS)
  hourly_res = requests.get(hourly_url, headers=HEADERS)

  if grid_res.status_code != 200 or hourly_res.status_code != 200:
    return None

  return {
      "grid": grid_res.json()["properties"],
      "hourly": hourly_res.json()["properties"]["periods"],
  }


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
  if 5 <= hour <= 11:
    return "Morning", 5, 11
  elif 12 <= hour <= 16:
    return "Midday", 12, 16
  elif 17 <= hour <= 21:
    return "Evening", 17, 21
  return None, None, None


def get_val_at_time(values_list, target_dt):
  for entry in values_list:
    valid_str = entry["validTime"]
    parts = valid_str.split("/")
    start_dt = datetime.fromisoformat(parts[0])
    duration_str = parts[1]
    hours_to_add = int(duration_str.replace("PT", "").replace("H", ""))
    from datetime import timedelta

    end_dt = start_dt + timedelta(hours=hours_to_add)

    if start_dt <= target_dt < end_dt:
      return entry["value"]
  return 0


st.title("🌤️ Weather Windows")

data = fetch_grid_forecast()

if not data:
  st.error("Failed to retrieve grid data from the National Weather Service API.")
else:
  grid = data["grid"]
  periods = data["hourly"]

  pop_values = grid.get("probabilityOfPrecipitation", {}).get("values", [])
  wind_spd_values = grid.get("windSpeed", {}).get("values", [])

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
          "Morning": [],
          "Midday": [],
          "Evening": [],
      }
    days_data[day_name][window_name].append((start_time, period))

  for day_name, windows in days_data.items():
    st.markdown(f"### {day_name}")

    for window_name in ["Morning", "Midday", "Evening"]:
      window_periods = windows[window_name]
      if not window_periods:
        continue

      max_wind = 0.0
      worst_precip_status = "GOOD"
      worst_thunder_status = "GOOD"
      reasons = []

      for start_time, period in window_periods:
        utc_time = start_time.astimezone(timezone.utc)
        pop_val = get_val_at_time(pop_values, utc_time) or 0
        w_spd = get_val_at_time(wind_spd_values, utc_time) or 0
        w_spd_mph = w_spd * 0.621371

        if w_spd_mph > max_wind:
          max_wind = w_spd_mph

        short_fc = period["shortForecast"].lower()
        detailed_fc = period["detailedForecast"].lower()
        text_blob = f"{short_fc} {detailed_fc}"

        if pop_val >= 50:
          worst_precip_status = "BAD"
        elif pop_val > 0 and worst_precip_status != "BAD":
          worst_precip_status = "CHECK"

        if "thunder" in text_blob or "storm" in text_blob:
          if "slight chance" in text_blob:
            if worst_thunder_status == "GOOD":
              worst_thunder_status = "CHECK"
          else:
            worst_thunder_status = "BAD"

      if (
          max_wind > 15.0
          or worst_precip_status == "BAD"
          or worst_thunder_status == "BAD"
      ):
        badge = "🔴 BAD"
        if max_wind > 15.0:
          reasons.append(f"Wind {int(max_wind)}mph")
        if worst_precip_status == "BAD":
          reasons.append("Precip")
        if worst_thunder_status == "BAD":
          reasons.append("Thunder")
      elif (
          worst_precip_status == "CHECK" or worst_thunder_status == "CHECK"
      ):
        badge = "🟡 CHECK"
        if worst_precip_status == "CHECK":
          reasons.append("Slight precip")
        if worst_thunder_status == "CHECK":
          reasons.append("Slight thunder")
      else:
        badge = "🟢 GOOD"

      reason_text = f" ({', '.join(reasons)})" if reasons else ""

      col_w, col_b = st.columns([2, 3])
      with col_w:
        st.markdown(f"**{window_name}**")
      with col_b:
        st.markdown(f"{badge}{reason_text}")

      html_output = """
            <div style="display: flex; flex-direction: column; gap: 5px; margin-bottom: 8px; background: rgba(0,0,0,0.03); padding: 4px; border-radius: 4px;">
              <!-- Wind Arrows Row -->
              <div style="display: flex; gap: 4px; align-items: center;">
            """
      for start_time, period in window_periods:
        wind_dir = period.get("windDirection", "N")
        arrow = get_wind_arrow(wind_dir)
        html_output += f"""
                <div style="flex: 1; display: flex; justify-content: center; align-items: center; font-size: 26px; line-height: 1;">
                  {arrow}
                </div>
                """
      html_output += """
              </div>

              <!-- Wind Direction Text Row -->
              <div style="display: flex; gap: 4px;">
            """
      for start_time, period in window_periods:
        wind_dir = period.get("windDirection", "N")
        html_output += f"""
                <div style="flex: 1; text-align: center; font-size: 9px; font-weight: bold; color: #444;">
                  {wind_dir}
                </div>
                """
      html_output += """
              </div>
              
              <!-- Rain Bar Graph Row -->
              <div style="display: flex; gap: 4px; align-items: flex-end; height: 22px;">
            """
      for start_time, period in window_periods:
        utc_time = start_time.astimezone(timezone.utc)
        pop = get_val_at_time(pop_values, utc_time) or 0
        # Only show height if pop > 0, completely zero out if 0% to match NWS charts
        height_pct = pop if pop > 0 else 0
        html_output += f"""
                <div style="flex: 1; display: flex; flex-direction: column; justify-content: flex-end; height: 100%;">
                  <div title="Rain: {pop}%" style="width: 100%; background-color: #21c354; height: {height_pct}%; border-radius: 2px;"></div>
                </div>
                """
      html_output += """
              </div>

              <!-- Thunder Bar Graph Row -->
              <div style="display: flex; gap: 4px; align-items: flex-end; height: 22px;">
            """
      for start_time, period in window_periods:
        short_fc = period["shortForecast"].lower()
        detailed_fc = period["detailedForecast"].lower()
        has_thunder = (
            "thunder" in short_fc
            or "thunder" in detailed_fc
            or "storm" in short_fc
        )
        thunder_pct = 100 if has_thunder and "slight chance" not in short_fc else (40 if has_thunder else 0)
        height_pct = thunder_pct if thunder_pct > 0 else 0
        bg_col = "#ff4b4b" if thunder_pct > 0 else "transparent"
        html_output += f"""
                <div style="flex: 1; display: flex; flex-direction: column; justify-content: flex-end; height: 100%;">
                  <div title="Thunder Risk" style="width: 100%; background-color: {bg_col}; height: {height_pct}%; border-radius: 2px;"></div>
                </div>
                """
      html_output += """
              </div>

              <!-- AM/PM Time Labels Row -->
              <div style="display: flex; gap: 4px; border-top: 1px solid rgba(0,0,0,0.1); padding-top: 2px;">
            """
      for start_time, period in window_periods:
        time_label = start_time.strftime("%l%p").strip()
        html_output += f"""
                <div style="flex: 1; text-align: center; font-size: 8px; color: #555; white-space: nowrap;">
                  {time_label}
                </div>
                """
      html_output += """
              </div>
            </div>
            """

      st.html(html_output)

    st.divider()
