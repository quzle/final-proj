import requests

from flask import redirect, render_template, session, current_app
from functools import wraps


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
    """Look up quote for symbol."""
    api_url = current_app.config["API_URL"]
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
        print(f"Request error: {e}")
    except (KeyError, ValueError) as e:
        print(f"Data parsing error: {e}")
    return None

def search_weather(id):
    """Look up weather for id returned by search."""
    api_url = current_app.config["API_URL"]
    api_key = current_app.config["API_KEY"]

    url = f"{api_url}/current.json?key={api_key}&q=id:{id}"

    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an error for HTTP error responses
        
        response_data = response.json()

        print("Weather response data:")
        print(response_data)

        return {
            "temp_c": response_data["current"]["temp_c"],
            "wind_kph": response_data["current"]["wind_kph"],
            "cloud": response_data["current"]["cloud"],

        }
    
    except requests.RequestException as e:
        print(f"Request error: {e}")
    except (KeyError, ValueError) as e:
        print(f"Data parsing error: {e}")
    return None

def usd(value):
    """Format value as USD."""
    return f"${value:,.2f}"
