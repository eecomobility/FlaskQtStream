import sys
import random
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel
from PyQt6.QtGui import QFont
from PyQt6.QtCore import QTimer, Qt
import socketio
import threading


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
            self.sio.emit("temperature_update", {"temperature": temp}) #socket IO client sends (via emit) the temperature data to the backend Flask server
            print(f"Sent temperature: {temp}")
        except Exception as e:
            print("Emit error:", e)

    def on_start_test(self,data):
        try:
            self.start_test_label.setText("Start Test\n1")
            print("Start test signal received from backend")
        except Exception as e:
            print("UI update error")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TestApp()
    window.show()
    sys.exit(app.exec())
