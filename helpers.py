import requests

from flask import redirect, render_template, session, current_app
from functools import wraps
from datetime import datetime
import json

def apology(message, code=400):
    """Render message as an apology to user."""

    def escape(s):
        """
        Escape special characters.

        https://github.com/jacebrowning/memegen#special-characters
        """
        for old, new in [
            ("-", "--"),
            (" ", "-"),
            ("_", "__"),
            ("?", "~q"),
            ("%", "~p"),
            ("#", "~h"),
            ("/", "~s"),
            ('"', "''"),
        ]:
            s = s.replace(old, new)
        return s

    return render_template("apology.html", top=code, bottom=escape(message)), code


def login_required(f):
    """
    Decorate routes to require login.

    https://flask.palletsprojects.com/en/latest/patterns/viewdecorators/
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)

    return decorated_function


def lookup_location(location):
    """Look up location."""
    api_url = current_app.config["API_base_URL"]
    api_key = current_app.config["API_KEY"]

    url = f"{api_url}/search.json?key={api_key}&q={location}"

    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an error for HTTP error responses
        
        response_data = response.json()

        print("Location response data:")
        print(response_data)

        return {
            "id": response_data[0]["id"],
            "lat": response_data[0]["lat"],
            "lon": response_data[0]["lon"],
            "name": response_data[0]["name"],
            "country": response_data[0]["country"],
        }
    except requests.RequestException as e:
        print(f"Error fetching location data: {e}")
        return None


def search_weather(id):
    """Look up weather for location id."""
    api_url = current_app.config["API_base_URL"]
    api_key = current_app.config["API_KEY"]

    url = f"{api_url}/current.json?key={api_key}&q=id:{id}"

    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an error for HTTP error responses
        
        response_data = response.json()

        if current_app.config["debug"]:
            print("Retrieved today's weather")

        return response_data
    
    except requests.RequestException as e:
        print(f"Request error: {e}")
    except (KeyError, ValueError) as e:
        print(f"Data parsing error: {e}")
    return None

def search_forecast(id):
    """Look up 3 day forecast for location id."""
    api_url = current_app.config["API_base_URL"]
    api_key = current_app.config["API_KEY"]

    url = f"{api_url}/forecast.json?key={api_key}&q=id:{id}&days=3"

    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an error for HTTP error responses
        
        response_data = response.json()

        if current_app.config["debug"]:
            print("Retrieved weather forecast")

        return response_data
    
    except requests.RequestException as e:
        print(f"Request error: {e}")
    except (KeyError, ValueError) as e:
        print(f"Data parsing error: {e}")
    return None

def process_weather_data(forecast_days):
    processed_data = []
    today = datetime.now()

    for day in forecast_days:
        date = day['date']
        day_date = datetime.strptime(date, "%Y-%m-%d")
        days_from_now = (day_date - today).days
        icon = day['day']['condition']['icon']

        best_precip_time = None
        highest_precip_chance = 0
        precip_type = "none"
        rain_chance = 0

        # Filter hours between 8 AM and 5 PM
        daytime_hours = [hour for hour in day['hour'] if 8 <= int(hour['time'].split()[1].split(':')[0]) <= 17]

        if not daytime_hours:
            continue  # Skip if no valid hours are found

        # Analyze hourly data for precipitation
        for hour in daytime_hours:
            if hour['chance_of_rain'] > highest_precip_chance:
                highest_precip_chance = hour['chance_of_rain']
                best_precip_time = hour['time']
                precip_type = "rain"
                rain_chance = hour['chance_of_rain']
            if hour['chance_of_snow'] > highest_precip_chance:
                highest_precip_chance = hour['chance_of_snow']
                best_precip_time = hour['time']
                precip_type = "snow"

        # Categorize wind and calculate kph and direction
        avg_wind_mph = sum(hour['wind_mph'] for hour in daytime_hours) / len(daytime_hours)
        avg_wind_kph = avg_wind_mph * 1.60934  # Convert mph to kph
        avg_wind_dir = sum(hour['wind_degree'] for hour in daytime_hours) / len(daytime_hours)

        if avg_wind_mph <= 5:
            wind_category = "absent"
        elif avg_wind_mph <= 15:
            wind_category = "mild"
        elif avg_wind_mph <= 25:
            wind_category = "strong"
        else:
            wind_category = "very strong"

        # Calculate ski score
        avg_temp_c = sum(hour['temp_c'] for hour in daytime_hours) / len(daytime_hours)
        min_temp_c = min(hour['temp_c'] for hour in daytime_hours)
        max_temp_c = max(hour['temp_c'] for hour in daytime_hours)
        snowfall_cm = day['day'].get('totalsnow_cm', 0)
        avg_vis_km = sum(hour['vis_km'] for hour in daytime_hours) / len(daytime_hours)
        ski_score = 10

        # Incremental temperature adjustment
        if avg_temp_c > 5:
            ski_score -= 0.5 * (avg_temp_c - 5)
        elif avg_temp_c < -10:
            ski_score -= 0.5 * abs(avg_temp_c + 10)

        # Incremental rain penalty
        ski_score -= 0.02 * rain_chance

        # Visibility penalty
        if avg_vis_km < 5:
            ski_score -= (5 - avg_vis_km) * 0.4

        # High snowfall penalty (not penalizing low snowfall)
        if snowfall_cm > 50:
            ski_score -= 3

        # Wind penalty
        if wind_category in ["strong", "very strong"]:
            ski_score -= 2

        # Ensure score is between 1 and 10
        ski_score = max(1, min(10, ski_score))

        # Determine if the day is primarily sunny or cloudy
        condition_text = day['day']['condition']['text'].lower()
        if "sunny" in condition_text or "clear" in condition_text:
            daytime_sun_or_cloudy = "sunny"
        else:
            daytime_sun_or_cloudy = "cloudy"

        # Add processed data for the day
        processed_data.append({
            "date": date,
            "days_from_now": days_from_now,
            "icon_url": icon,
            "precipitation": {
                "time": best_precip_time,
                "type": precip_type,
                "chance": highest_precip_chance,
                "icon_url": day['day']['condition']['icon']
            },
            "wind": {
                "category": wind_category,
                "speed_kph": avg_wind_kph,
                "direction": avg_wind_dir
            },
            "temperature": {
                "min": min_temp_c,
                "max": max_temp_c
            },
            "visibility": avg_vis_km,
            "daytime_sun_or_cloudy": daytime_sun_or_cloudy,
            "ski_score": ski_score
        })

    return processed_data