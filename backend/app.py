import json
from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit
from flask_swagger_ui import get_swaggerui_blueprint
from flask_cors import CORS
import os
from datetime import datetime
from time import time
from utils.logger import get_shared_logger  # Importing the shared logger utility

logger = get_shared_logger()

app = Flask(__name__)  # Configure Flask app
CORS(app)  # Enabling CORS for all routes
socketio = SocketIO(app, cors_allowed_origins="*")  # Initialize Flask-SocketIO

# Storing temperature from frontend
current_temperature = {"temperature": None}  # Global dictionary to store latest temperature from GUI

# Storing the test count for each battery ID to generate testId
battery_test_history = {}  # Keeps track of how many times each battery has been tested

# Global flag to block multiple test initiations:
is_test_running = False

#Global variable to calculate the time it takes for a test to complete
test_start_time = None


# Swagger UI setup
SWAGGER_URL = '/docs'
API_URL = '/swagger.json'
swaggerui_blueprint = get_swaggerui_blueprint(SWAGGER_URL, API_URL, config={'app_name': "FlaskQtStream Test API"})
app.register_blueprint(swaggerui_blueprint, url_prefix=SWAGGER_URL)

# Serving the Swagger JSON file, allowing it to load in Swagger UI
@app.route("/swagger.json")
def swagger_spec():
    with open(os.path.join(os.path.dirname(__file__), 'swagger.json'), 'r') as f:
        return jsonify(json.load(f))

# REST API endpoint to get the most recent temp received from frontend
@app.route("/api/temp")
def get_temp():
    temp = current_temperature.get("temperature")
    if temp is None:
        return jsonify({"error": "No temperature received yet"}), 404
    return jsonify({"temperature": temp, "unit": "Celsius"}), 200

# REST API endpoint to initiate test on battery and send parameters to GUI
@app.route("/test", methods=["PUT"])
def initiate_test():
    global is_test_running  # Use of the global flag to control test initiation



    if is_test_running:
        return jsonify({"error": "A test is already running. Please wait until it completes."}), 429

    is_test_running = True  # Set the flag to indicate a test is running

    #start timing:
    api_start_time = time()

    # Extract query parameters
    battery_id = request.args.get("batteryId")
    battery_ref_date = request.args.get("batteryRefDate")

    # Extract JSON body
    data = request.get_json()
    test_done_callback = data.get("testDoneCallbackURL")
    analysis_done_callback = data.get("analysisDoneCallbackURL")

    # Handle missing required fields
    if not battery_id or not battery_ref_date:
        return jsonify({"error": "Missing batteryId or batteryRefDate in query parameters"}), 400

    if not test_done_callback or not analysis_done_callback:
        return jsonify({"error": "Missing callback URLs in request body"}), 400

    # Increment testId for the battery
    if battery_id not in battery_test_history:
        battery_test_history[battery_id] = 1
    else:
        battery_test_history[battery_id] += 1

    test_id = battery_test_history[battery_id]


    # Generate current test date and time
    now = datetime.now()
    test_date = now.strftime("%Y-%m-%d")
    test_time = now.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]  # Millisecond precision

    #record the time right before emitting the event to the front-end GUI:
    socketio_emit_time = time()
    # Emit event to front-end GUI with all test parameters
    socketio.emit("start_test_signal", {
        "start": True,
        "batteryId": battery_id,
        "batteryRefDate": battery_ref_date,
        "testDoneCallbackURL": test_done_callback,
        "analysisDoneCallbackURL": analysis_done_callback,
        "testId": test_id,
        "testDate": test_date,
        "testTime": test_time,
        "backendEmitTime": socketio_emit_time,  # Time when the backend emitted the event
    })

    # total api duration:
    # Measures only the server-side duration of handling the PUT /test request—from the moment the request reaches the Flask route to just before the response is returned; does NOT include GUI processing, event delivery time, or callback durations.
    total_api_duration = round((time() - api_start_time) * 1000, 5)  # in milliseconds
    print(f"REST API duration (PUT /test): {total_api_duration} ms")

    # Log to file
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logger.info(f"[{timestamp}] Start Test (PUT) REST API duration (PUT /test): {total_api_duration} ms\n")

    # Respond to client with acknowledgment of test initiation
    return jsonify({
        "batteryId": battery_id,
        "batteryRefDate": battery_ref_date,
        "testId": test_id,
        "testDate": test_date,
        "testTime": test_time
    }), 200

@app.route("/callback/test_done", methods=["GET", "POST"])
def test_done_callback():
    if request.method == "POST":
        data = request.get_json()
        print("Test Done Callback Received:", data)
    return "Test done", 200


@app.route("/callback/analysis_done", methods=["GET", "POST"])
def analysis_done_callback():
    global is_test_running
    if request.method == "POST":
        data = request.get_json()
        print("Analysis Done Callback Received:", data)
        is_test_running = False
    return "Analysis done", 200



# Socket.IO event handler which runs when a client connects to the server
@socketio.on('connect')
def handle_connect():
    print("Client connected")
    emit('connected', {'message': 'Front-end connected to Flask-SocketIO server'})  # Confirmation message sent to front-end

# Socket.IO event handler for receiving temperature updates from front-end
@socketio.on('temperature_update')
def receive_temperature(data):
    temp = data.get("temperature")
    front_end_emit_time = data.get("frontendEmitTime")
    if temp is not None:
        current_temperature["temperature"] = temp  # Update stored temperature

        if front_end_emit_time:
            backend_receive_time = time()
            delay_ms = round((backend_receive_time - front_end_emit_time) * 1000, 2)  # Calculate delay in milliseconds
            logger.info(f"Socket.IO delay (front-end -> back-end): {delay_ms} ms\n")


# Start the Flask-SocketIO server
if __name__ == "__main__":
    socketio.run(app, debug=True)
