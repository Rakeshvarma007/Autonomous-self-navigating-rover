🤖 AI-Powered Autonomous Rover

This project is a fully functional autonomous rover that uses a Raspberry Pi 4 for high-level computer vision and a Arduino for low-level hardware control. The system processes real-time video to detect objects using YOLOv8 and avoids obstacles using ultrasonic data.

🌟 Features

Dual-Controller Architecture: Offloads heavy AI processing to the Raspberry Pi 4 while using the Arduino for real-time motor and sensor timing.

Computer Vision: Utilizes YOLOv8 (ONNX) to identify objects such as people, cars, and stop signs.

Autonomous Navigation: \* Stop Sign Detection: Automatically halts for 3 seconds when a stop sign is detected.

Proximity Logic: Reverses and turns if an obstacle is closer than 25cm.

Dynamic Swerving: Swerves left or right if a large obstacle (occupying >30% of the frame) is detected in its path.

Web-Based Control Center: A Flask-hosted dashboard featuring a live video feed, real-time telemetry, manual override controls, and a safety "Kill Switch".

🛠️ Hardware Setup

Arduino Pin Mapping

The Arduino manages the physical movement and the ultrasonic sensor.

Component,Pin,Function

Ultrasonic Trigger,3,Sends out sonic pulse

Ultrasonic Echo,5,Receives reflected pulse

Left Motor (P1/P2),"11, 12",Controls left side wheels

Right Motor (P1/P2),"10, 9",Controls right side wheels

Connectivity

Communication: The Raspberry Pi connects to the Arduino via USB Serial at 9600 baud (typically on /dev/ttyACM0).

Camera: Supports both the Raspberry Pi Camera Module (via Picamera2) and standard USB webcams.

🚀 Installation & Usage

1. Arduino Preparation

Open the aurd.cpp file in the Arduino IDE.

Upload the code to your Arduino Uno or Nano.

1. Raspberry Pi Preparation

Clone the Repository:

git clone https://github.com/Rakeshvarma007/Autonomous-self-navigating-rover

cd your-repo-name

Install Dependencies:

pip install flask opencv-python numpy pyserial

Model File: Ensure yolov8n.onnx is located in the root directory.

Run the System:

python un.py

📂 Project Structure

un.py: The main Python script handling YOLO detection, navigation logic, and the Flask web server.

aurd.cpp: The Arduino firmware for motor control and ultrasonic distance measurements.

templates/index.html: The web dashboard for remote monitoring and manual control.

requirements.txt: List of necessary Python libraries.

🕹️ Logic Overview

Manual Mode: Allows the user to take control via the web interface using the arrow buttons.

Autonomous Mode: \* If the distance is < 25cm, the rover enters "TOO CLOSE" mode: it stops, reverses, and turns left.

If a Stop Sign is detected, it pauses for 3 seconds before clearing the sign.

If an obstacle is detected in the center of the camera frame, it swerves to an open path.

