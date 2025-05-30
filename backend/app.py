import json
import random
from flask import Flask, request, jsonify, send_file
from flask_socketio import SocketIO, emit
from flask_swagger_ui import get_swaggerui_blueprint
from flask_cors import CORS
import os


app = Flask(__name__) # Configure Flask app
CORS(app) #enabling CORS for all routes
socketio = SocketIO(app, cors_allowed_origins="*") #initialize Flask-SocketIO

#Storing temperature from frontend
current_temperature = {"temperature": None} #global dictionary/variable to store the most recent temperature

#Swagger UI setup
SWAGGER_URL = '/docs'
API_URL = '/swagger.json'
swaggerui_blueprint = get_swaggerui_blueprint(SWAGGER_URL, API_URL, config={'app_name': "FlaskQtStream Test API"})
app.register_blueprint(swaggerui_blueprint, url_prefix=SWAGGER_URL)

#Serving the Swagger JSON file, allowing to load it in Swagger UI
@app.route("/swagger.json")
def swagger_spec():
    with open(os.path.join(os.path.dirname(__file__), 'swagger.json'), 'r') as f:
        return jsonify(json.load(f))

#REST API endpoint to get the most recent temp received from frontend
@app.route("/api/temp")
def get_temp():
    temp = current_temperature.get("temperature")
    if temp is None:
        return jsonify({"error": "No temperature received yet"}), 404
    return jsonify({"temperature": temp, "unit": "Celsius"}), 200

# REST API endpoint to trigger GUI changes:
@app.route("/api/start_test", methods=["GET"])
def start_test_trigger():
    # sends a real-time trigger to the front-end which listens for the "start_test_signal" event and when received, updates the UI accordingly:
    socketio.emit("start_test_signal", {"start": True}) # Flask-SocketIO broadcasts event "start_test_signal" to all connected clients (front-end)
    return jsonify({"status": "Start test signal sent", "start":1})


# Socket.IO event handler which runs the function whenever a client connects to the server:
@socketio.on('connect')
# No arguments are needed here, optionally get session ID for individual clients' tracking
def handle_connect(): # gets called automatically when a frontend client connects via SocketIO
    print("Client connected")
    emit('connected', {'message': 'Front-end connected to Flask-SocketIO server'}) #confirmation message sent to the newly connected front-end


# event handler specifically for "temperature_update" event
@socketio.on('temperature_update')
#  function that will handle incoming 'temperature_update' events
def receive_temperature(data): #the data argument contains the temperature in the form of JSON sent by the front-end
    temp = data.get("temperature") #extract the temperature from the received data
    if temp is not None:
        current_temperature["temperature"] = temp # updates the global variable current_temperature with the latest temperature value sent from the frontend
        print(f"Received temperature from front-end: {temp}")
if __name__ == "__main__":
    # Start the Flask-SocketIO server
    socketio.run(app, debug=True) #Start the Flask-SocketIO server with debug mode enabled