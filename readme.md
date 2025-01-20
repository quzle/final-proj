# SNOWIFY
#### Video Demo:  https://youtu.be/Yth9zsAnP8E
#### Description:

My final project for CS50x is a simple webapp build using Flask.
A simple database stores user accounts.
Users are able to register and/or login.

Once logged in, users can add up to 4 favourite locations.
For these locations, the webapp uses the Weatherapi API (https://www.weatherapi.com/docs/) to retrieve the current weather conditions.

In the 'Dashboard' screen, the webapp uses the same API to retrieve the weather conditions for tomorrow. Via a python function, the data is analysed to score each location for skiability, from 1 to 10, and display this score to the user.\

A score of 10 indicates perfect skiability: daytime temperature near 0 degrees, wind not excessive, good visibility and no rain are all factors that contribute to the perfect score of 10.
The score does not account for the geography of the location.
I wanted to include snow cover in the calculation, but unfortunately I could not find a free API with this information.