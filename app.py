import streamlit as st
import pandas as pd

# Page Configuration
st.set_page_config(page_title="Weather Dashboard - Merritt Island (32952)", layout="wide")

# Helper function to generate instability exclamation rating
def get_instability_rating(cape):
    if cape <= 1000:
        return "!"
    elif cape <= 2000:
        return "!!"
    else:
        return "!!!"

# Sample data structure representing 24-hour forecast data
def load_forecast_data():
    data = [
        {"hour": "8AM", "temp": 81, "wind": 8, "dir": "NE", "rain": 25, "thunder": 0, "cape": 820},
        {"hour": "9AM", "temp": 82, "wind": 9, "dir": "NE", "rain": 30, "thunder": 10, "cape": 1150},
        {"hour": "10AM", "temp": 83, "wind": 10, "dir": "E", "rain": 35, "thunder": 20, "cape": 1550},
        {"hour": "11AM", "temp": 83, "wind": 11, "dir": "E", "rain": 40, "thunder": 25, "cape": 1980},
        {"hour": "12PM", "temp": 84, "wind": 9, "dir": "E", "rain": 45, "thunder": 30, "cape": 2350},
        {"hour": "1PM", "temp": 84, "wind": 10, "dir": "E", "rain": 35, "thunder": 30, "cape": 2520},
        {"hour": "2PM", "temp": 84, "wind": 11, "dir": "E", "rain": 50, "thunder": 60, "cape": 2410},
        {"hour": "3PM", "temp": 83, "wind": 10, "dir": "E", "rain": 75, "thunder": 80, "cape": 2100},
        {"hour": "4PM", "temp": 83, "wind": 9, "dir": "E", "rain": 60, "thunder": 50, "cape": 1750},
        {"hour": "5PM", "temp": 83, "wind": 15, "dir": "E", "rain": 75, "thunder": 80, "cape": 1300},
        {"hour": "6PM", "temp": 83, "wind": 10, "dir": "E", "rain": 85, "thunder": 80, "cape": 900},
        {"hour": "7PM", "temp": 82, "wind": 8, "dir": "NE", "rain": 50, "thunder": 30, "cape": 600},
        {"hour": "8PM", "temp": 82, "wind": 7, "dir": "NE", "rain": 30, "thunder": 0, "cape": 400},
        {"hour": "9PM", "temp": 81, "wind": 6, "dir": "NE", "rain": 20, "thunder": 0, "cape": 300},
        {"hour": "10PM", "temp": 80, "wind": 6, "dir": "NE", "rain": 15, "thunder": 0, "cape": 250},
        {"hour": "11PM", "temp": 80, "wind": 5, "dir": "NE", "rain": 15, "thunder": 0, "cape": 200},
        {"hour": "12AM", "temp": 79, "wind": 5, "dir": "N", "rain": 10, "thunder": 0, "cape": 200},
        {"hour": "1AM", "temp": 79, "wind": 5, "dir": "N", "rain": 10, "thunder": 0, "cape": 250},
        {"hour": "2AM", "temp": 78, "wind": 4, "dir": "N", "rain": 10, "thunder": 0, "cape": 300},
        {"hour": "3AM", "temp": 78, "wind": 4, "dir": "N", "rain": 15, "thunder": 0, "cape": 350},
        {"hour": "4AM", "temp": 78, "wind": 5, "dir": "NE", "rain": 15, "thunder": 0, "cape": 400},
        {"hour": "5AM", "temp": 78, "wind": 5, "dir": "NE", "rain": 20, "thunder": 0, "cape": 450},
        {"hour": "6AM", "temp": 79, "wind": 6, "dir": "NE", "rain": 20, "thunder": 0, "cape": 550},
        {"hour": "7AM", "temp": 80, "wind": 7, "dir": "NE", "rain": 25, "thunder": 0, "cape": 700}
    ]
    return data

st.title("Merritt Island Weather Dashboard (32952)")
st.markdown("### Next 24-Hour Forecast Grid")

forecast_data = load_forecast_data()

# Render Hourly Grid Layout
cols = st.columns(6)
for i, item in enumerate(forecast_data):
    col_idx = i % 6
    with cols[col_idx]:
        rating = get_instability_rating(item["cape"])
        display_label = f"{item['hour']} {rating}"
        
        st.markdown(f"""
        <div style="border: 1px solid #ccc; padding: 10px; border-radius: 5px; text-align: center; margin-bottom: 10px;">
            <strong>{display_label}</strong><br>
            {item['wind']} mph<br>
            {item['dir']}<br>
            💧 {item['rain']}%<br>
            ⚡ {item['thunder']}%<br>
            🌡️ {item['temp']}°F
        </div>
        """, unsafe_allow_html=True)

st.markdown("---")

# Key at the bottom of the page
st.markdown("""
### Key
**Instability:**
* `!` = 0 – 1,000 J/kg (Weakly Unstable)
* `!!` = 1,001 – 2,000 J/kg (Moderately Unstable)
* `!!!` = 2,001+ J/kg (Very Unstable)
""")

[How to Build Your Own Weather App using Python & Streamlit](https://www.youtube.com/watch?v=UzzrraJpwT4)

This video provides a complete tutorial on setting up real-time weather dashboards using Python and Streamlit.
http://googleusercontent.com/youtube_content/1
