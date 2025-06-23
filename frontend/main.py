import sys
import random
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel
from PyQt6.QtGui import QFont
from PyQt6.QtCore import QTimer, Qt
import socketio
import threading
import requests
import time
from utils.logger import get_shared_logger  # Importing the shared logger utility

logger = get_shared_logger()  # Initialize the shared logger


class TestApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Battery Test Panel")
        self.setGeometry(100, 100, 300, 400)

        layout = QVBoxLayout()
        layout.setSpacing(40)

        # Temperature Box
        self.temp_label = QLabel()
        self.temp_label.setFont(QFont("Arial", 12, weight=QFont.Weight.Bold))
        self.temp_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.temp_label.setStyleSheet("border: 2px solid black; padding: 15px;")
        layout.addWidget(self.temp_label)

        # Start Test Box
        self.start_test_label = QLabel("Start Test\n0/1")
        self.start_test_label.setFont(QFont("Arial", 12, weight=QFont.Weight.Bold))
        self.start_test_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.start_test_label.setStyleSheet("border: 2px solid black; padding: 15px;")
        layout.addWidget(self.start_test_label)

        self.setLayout(layout)

        # Initialize SocketIO client
        self.sio = socketio.Client()
        self.sio_thread = threading.Thread(target=self.connect_socket) # the socket IO connection is started in a separate thread so GUI remains responsive
        self.sio_thread.start()

        # Start temperature simulation and sending every 5 seconds
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.send_temperature)
        self.update_timer.start(5000)


        # Listens for the start_test_signal event from the Flask backend.
        # When received, it calls self.on_start_test(data)
        self.sio.on("start_test_signal", self.on_start_test)

    def connect_socket(self):
        try:
            self.sio.connect("http://localhost:5000") #establishes a connection to the socket.io server running on localhost at port 5000
            print("Connected to Flask backend.")
        except Exception as e:
            print("Socket connection error:", e)

    def send_temperature(self):
        try:
            # Simulate temperature
            temp = random.randint(15, 35)
            self.temp_label.setText(f"Temperature\n{temp} degrees")
            # Send to backend
            self.sio.emit("temperature_update", {
                "temperature": temp,
                "frontendEmitTime": time.time()
            }) #socket IO client sends (via emit) the temperature data to the backend Flask server

        except Exception as e:
            print("Emit error:", e)

    def on_start_test(self, data):
        try:
            # Extract test parameters sent from the backend
            battery_id = data.get("batteryId", "N/A")
            battery_ref_date = data.get("batteryRefDate", "N/A")
            test_id = data.get("testId", "N/A")
            test_date = data.get("testDate", "N/A")
            test_time = data.get("testTime", "N/A")
            test_done_url = data.get("testDoneCallbackURL")
            analysis_done_url = data.get("analysisDoneCallbackURL")
            backend_time = data.get("backendEmitTime")

            # Calculate and log socket delay if available
            if backend_time:
                frontend_time = time.time()

                # socket_delay measures the time difference between when the backend emitted the event and when the frontend received it and enter the `on_start_test` method
                socket_delay = round((frontend_time - backend_time) * 1000, 2)  # in milliseconds
                logger.info(f"Socket.IO delay (back-end -> front-end): {socket_delay} ms\n")
                print(f"Socket.IO delay (back-end -> front-end): {socket_delay} ms")
            else:
                print("Backend emit time not provided; skipping delay calculation.")

            # Update GUI to reflect test started
            self.start_test_label.setText(f"Test Started\nBattery: {battery_id}\nTest ID: {test_id}")



            # Simulate test completion callback
            if test_done_url:
                try:
                    response = requests.post(test_done_url, json={"message": "Test complete"})
                    print(f"Sent test completion to {test_done_url}, Status: {response.status_code}")
                except Exception as e:
                    print(f"Failed to send test complete callback: {e}")

            # Wait 3 seconds before sending analysis callback
            time.sleep(3)

            # Simulate analysis completion callback
            if analysis_done_url:
                try:
                    response = requests.post(analysis_done_url, json={"message": "Analysis complete"})
                    print(f"Sent analysis completion to {analysis_done_url}, Status: {response.status_code}")
                except Exception as e:
                    print(f"Failed to send analysis complete callback: {e}")

        except Exception as e:
            print("UI update or processing error:", e)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TestApp()
    window.show()
    sys.exit(app.exec())
