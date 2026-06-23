import os
import requests
from dotenv import load_dotenv

def get_weather_context(location="Patparganj, Delhi, IN"):
    
    load_dotenv()
    api_key = os.getenv("OPENWEATHER_API_KEY")
    if not os.getenv("OPENWEATHER_API_KEY"):
        print("⚠️ No OPENWEATHER_API_KEY found, returning mock weather data.")
        return f"Weather Context for {location}: 38°C, clear sky, 45% humidity. (Mocked Data due to missing API key)"

    try:
        # STEP 1: Use Geocoding API to convert location name to Lat/Lon
        geo_url = f"http://api.openweathermap.org/geo/1.0/direct?q={location}&limit=1&appid={api_key}"
        geo_response = requests.get(geo_url, timeout=5)
        geo_response.raise_for_status()
        geo_data = geo_response.json()
        
        if not geo_data:
            return f"Weather Context for {location}: Could not resolve location coordinates."
            
        lat = geo_data[0]["lat"]
        lon = geo_data[0]["lon"]
        
        # STEP 2: Use Lat/Lon to get precise weather data
        weather_url = f"http://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={api_key}&units=metric"
        weather_response = requests.get(weather_url, timeout=5)
        weather_response.raise_for_status()
        weather_data = weather_response.json()
        
        temp = weather_data["main"]["temp"]
        humidity = weather_data["main"]["humidity"]
        description = weather_data["weather"][0]["description"]
        
        return f"Weather Context for {location} (Lat: {lat:.2f}, Lon: {lon:.2f}): {temp}°C, {description}, {humidity}% humidity."
        
    except Exception as e:
        print(f"❌ Error fetching weather from OpenWeatherMap: {e}")
        return f"Weather Context for {location}: Data unavailable due to API error."

if __name__ == "__main__":
    print(get_weather_context())
