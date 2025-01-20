import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime

from helpers import apology, login_required, lookup_location, search_weather, search_forecast, process_weather_data

# Configure application
app = Flask(__name__)

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"

Session(app)

# Define global constants
app.config["API_base_URL"] = "http://api.weatherapi.com/v1"
app.config["API_KEY"] = "f87bbf78616941c0bd2174335242912"
app.config["debug"] = True
app.config["MAX_LOCATIONS"] = 4

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///locations.db")

@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/", methods=["GET", "POST"])
@login_required
def index():
    if request.method == "POST":
        location_id = request.form.get("location_id")
                
        if app.config["debug"]:
            print(f"/nLocation ID: {location_id}\n")  # Debug print

        if not location_id:
            return apology("must provide location", 400)
                
        results = search_weather(location_id)
        
        if app.config["debug"]:
            print(f"\nResults: {results}\n")  # Debug print
        
        if results is None:
            return apology("invalid location", 400)
        
        if 'location' not in results:
            return apology("location key not found in results", 400)
        
        location = results['location']
        location["id"] = location_id

        if app.config["debug"]:
            print(f"\nLocation: {location}\n")  # Debug print

        if not db.execute("SELECT * FROM locations WHERE id = ?", location["id"]):
            db.execute(
                "INSERT INTO locations (id, name, country, lat, lon, last_used) VALUES (:id, :name, :country, :lat, :lon, :time)",
                id=location['id'], name=location['name'], country=location['country'], lat=location['lat'], lon=location['lon'], time=datetime.now()
            )
        else:
            db.execute(
                "UPDATE locations SET name = :name, country = :country, lat = :lat, lon = :lon, last_used = :time WHERE id = :id",
                name=location['name'], country=location['country'], lat=location['lat'], lon=location['lon'], id=location['id'], time=datetime.now()
            )

        # Check max location count and add into user_locations
        user_id = session.get("user_id")

        locations = db.execute("SELECT * FROM locations where id IN (SELECT location_id FROM user_locations WHERE user_id = ?)", user_id) or []

        if app.config["debug"]:
            print(f"\nThe following {len(locations)} locations were found in database:\n{locations}\n")  # Debug print

        if len(locations) > app.config["MAX_LOCATIONS"]:
            return apology("maximum location count reached", 400)
        
        else:
            existing_location = db.execute(
                "SELECT * FROM user_locations WHERE user_id = ? AND location_id = ?",
                user_id, location['id']
            )

            if not existing_location:
                db.execute(
                    "INSERT INTO user_locations (user_id, location_id) VALUES (?, ?)",
                    user_id, location['id']
                )
        
        return redirect("/")
    
    else:
        user_id = session.get("user_id")
        
        locations = db.execute("SELECT * FROM locations where id IN (SELECT location_id FROM user_locations WHERE user_id = ?)", user_id)

        weather = []

        for loc in locations:
            weather_data = search_weather(loc["id"])
            if weather_data is not None:
                weather.append(weather_data)
                weather[-1]["location"]["id"] = loc["id"]

        return render_template("weather.html", weather=weather)

@app.route("/delete", methods=["POST"])
@login_required
def delete():
    location_id = request.form.get("location_id")

    if not location_id:
        return apology("must provide location", 400)

    user_id = session.get("user_id")

    db.execute(
        "DELETE FROM user_locations WHERE user_id = ? AND location_id = ?",
        user_id, location_id
    )

    return redirect("/")

@app.route("/dashboard")
@login_required
def dashboard():
    user_id = session.get("user_id")

    locations = db.execute("SELECT * FROM locations where id IN (SELECT location_id FROM user_locations WHERE user_id = ?)", user_id)

    processed = []

    if len(locations) == 0:
        locations = []
        forecast = {}
    else:

        forecast = {}

        for location in locations:
            forecast = search_forecast(location["id"])
            processed.append(process_weather_data(forecast['forecast']['forecastday']))
    
    if app.config["debug"]:
        print(f"\nProcessed data:{processed}\n")

    return render_template("dashboard.html", locationCount=len(locations), locations=locations, processed=processed)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute(
            "SELECT * FROM users WHERE username = ?", request.form.get("username")
        )

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(
            rows[0]["hash"], request.form.get("password")
        ):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")

@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 400)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 400)

        elif not request.form.get("password") == request.form.get("confirmation"):
            return apology("password's don't match", 400)

        # Query database for username
        rows = db.execute(
            "SELECT * FROM users WHERE username = ?", request.form.get("username")
        )

        # Ensure username exists and password is correct
        if len(rows) != 0:
            return apology("user already taken", 400)

        db.execute(
            "INSERT INTO users (username, hash) VALUES (?, ?)",
            request.form.get("username"), generate_password_hash(request.form.get("password"))
        )

        rows = db.execute(
            "SELECT * FROM users WHERE username = ?", request.form.get("username")
        )

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html")
