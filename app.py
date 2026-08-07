import streamlit as st
import requests
import pandas as pd

# Configuration for Merritt Island (32952) - Latitude/Longitude
LAT = 28.375
LON = -80.677

def get_instability_rating(cape):
    """Returns exclamation marks based on CAPE value."""
    if cape is None: return ""
    if cape <= 1000: return "!"
    elif cape <= 2000: return "!!"
    else: return "!!!"

def fetch_nws_data():
    # 1. Get grid endpoint
    points_url = f"https://api.weather.gov/points/{LAT},{LON}"
    response = requests.get(points_url).json()
    forecast_url = response['properties']['forecastHourly']
    
    # 2. Get hourly forecast
    hourly_response = requests.get(forecast_url).json()
    periods = hourly_response['properties']['periods'][:24]
    
    # Note: NWS does not provide CAPE in this JSON. 
    # Placeholder logic for demonstration.
    data = []
    for p in periods:
        data.append({
            "hour": p['startTime'][11:13], # Simplified hour
            "temp": p['temperature'],
            "wind": p['windSpeed'],
            "rain": p['probabilityOfPrecipitation']['value'] or 0,
            "cape": 1500 # Placeholder: In a production app, fetch from GRIB2/NOMADS
        })
    return data

st.set_page_config(page_title="Weather Dashboard - 32952", layout="wide")
st.title("Merritt Island Weather Dashboard (32952)")

try:
    forecast_data = fetch_nws_data()
    
    cols = st.columns(6)
    for i, item in enumerate(forecast_data):
        col_idx = i % 6
        with cols[col_idx]:
            rating = get_instability_rating(item["cape"])
            # Format: Hour (Space) Exclamation Points
            display_label = f"{item['hour']} {rating}"
            
            st.markdown(f"""
            <div style="border: 1px solid #ccc; padding: 10px; border-radius: 5px; text-align: center; margin-bottom: 10px;">
                <strong>{display_label}</strong><br>
                {item['wind']}<br>
                💧 {item['rain']}%<br>
                🌡️ {item['temp']}°F
            </div>
            """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("""
    ### Instability Key
    * `!` = 0 – 1,000 J/kg (Weakly Unstable)
    * `!!` = 1,001 – 2,000 J/kg (Moderately Unstable)
    * `!!!` = 2,001+ J/kg (Very Unstable)
    """)

except Exception as e:
    st.error(f"Error fetching data: {e}")
