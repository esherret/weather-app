import streamlit as st
import requests
import datetime

# Page Configuration
st.set_page_config(page_title="Weather Dashboard - Merritt Island (32952)", layout="wide")

# NWS API endpoints for Merritt Island (32952 area / KMLB grid)
LAT = 28.375
LON = -80.677

@st.cache_data(ttl=1800)
def fetch_nws_data():
    headers = {"User-Agent": "(weather-app-user, contact@example.com)"}
    points_url = f"https://api.weather.gov/points/{LAT},{LON}"
    res = requests.get(points_url, headers=headers)
    if res.status_code != 200:
        return None, None
    
    data = res.json()
    forecast_hourly_url = data['properties']['forecastHourly']
    forecast_grid_url = data['properties']['forecastGridData']
    
    hourly_res = requests.get(forecast_hourly_url, headers=headers).json()
    grid_res = requests.get(forecast_grid_url, headers=headers).json()
    
    return hourly_res, grid_res

def parse_forecast(hourly_data, grid_data):
    if not hourly_data or not grid_data:
        return []
    
    periods = hourly_data['properties']['periods'][:24]
    
    # Extract CAPE values from grid data if available, otherwise estimate/default
    cape_values = []
    cape_prop = grid_data['properties'].get('convectiveAvailablePotentialEnergy', {})
    cape_values = cape_prop.get('values', [])
    
    parsed = []
    for p in periods:
        start_time = p['startTime']
        # Format hour label e.g., "12PM", "7PM"
        dt = datetime.datetime.fromisoformat(start_time.replace('Z', '+00:00'))
        hour_label = dt.strftime('%I%p').lstrip('0')
        
        # Approximate CAPE mapping from NWS grid or default to typical seasonal values
        cape = 1500 # Default moderate baseline
        for cv in cape_values:
            valid_time = cv['validTime'].split('/')[0]
            if start_time[:13] in valid_time:
                cape = cv['value']
                break
                
        parsed.append({
            "hour": hour_label,
            "temperature": p['temperature'],
            "temperatureUnit": p['temperatureUnit'],
            "windSpeed": p['windSpeed'],
            "windDirection": p['windDirection'],
            "shortForecast": p['shortForecast'],
            "probabilityOfPrecipitation": p['probabilityOfPrecipitation']['value'] or 0,
            "cape": cape if cape is not None else 1200
        })
    return parsed

def get_instability_rating(cape):
    if cape <= 1000:
        return "!"
    elif cape <= 2000:
        return "!!"
    else:
        return "!!!"

# Main App Layout & Integration
st.title("Merritt Island Weather Dashboard (32952)")
st.markdown("### Next 24-Hour Forecast Grid")

hourly_data, grid_data = fetch_nws_data()
forecast_items = parse_forecast(hourly_data, grid_data)

if forecast_items:
    cols = st.columns(6)
    for i, item in enumerate(forecast_items):
        col_idx = i % 6
        with cols[col_idx]:
            rating = get_instability_rating(item["cape"])
            display_label = f"{item['hour']} {rating}"
            
            st.markdown(f"""
            <div style="border: 1px solid #ccc; padding: 10px; border-radius: 5px; text-align: center; margin-bottom: 10px;">
                <strong>{display_label}</strong><br>
                {item['windSpeed']} {item['windDirection']}<br>
                💧 {item['probabilityOfPrecipitation']}%<br>
                🌡️ {item['temperature']}°{item['temperatureUnit']}<br>
                <small>{item['shortForecast']}</small>
            </div>
            """, unsafe_allow_html=True)
else:
    st.warning("Unable to retrieve live NWS data at the moment. Please check your connection.")

st.markdown("---")

# Key at the bottom of the page
st.markdown("""
### Key
**Instability:**
* `!` = 0 – 1,000 J/kg (Weakly Unstable)
* `!!` = 1,001 – 2,000 J/kg (Moderately Unstable)
* `!!!` = 2,001+ J/kg (Very Unstable)
""")
