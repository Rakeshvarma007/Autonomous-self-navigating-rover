import cv2
import time
import threading
import serial
import numpy as np
from flask import Flask, Response, render_template, request, redirect, url_for

try:
    SERIAL_PORT = '/dev/ttyACM0'
    BAUD_RATE = 9600
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
    ser.flush()
    print(f"Connected to Arduino on {SERIAL_PORT}")
except Exception as e:
    print(f"[WARN] Arduino not found: {e}")
    ser = None

try:
    from picamera2 import Picamera2
    USING_PICAM = True
except ImportError:
    USING_PICAM = False

STOP_DISTANCE_CM = 25
OBSTACLE_THRESH = 0.30

current_state = "IDLE"
distance_reading = 100.0
video_frame = None
lock = threading.Lock()

manual_kill = False
manual_mode = False
manual_command = "stop"

def read_from_arduino():
    global distance_reading
    while True:
        if ser and ser.in_waiting > 0:
            try:
                line = ser.readline().decode('utf-8', errors='ignore').strip()
                if line.startswith("D:"):
                    dist_str = line.split(":")[1]
                    distance_reading = int(dist_str)
            except:
                pass
        time.sleep(0.01)

if ser:
    serial_thread = threading.Thread(target=read_from_arduino)
    serial_thread.daemon = True
    serial_thread.start()
    
class RoverHardware:
    def __init__(self):
        self.last_command = None 

    def send_command(self, cmd_char):
        if cmd_char == self.last_command:
            return
       
        if ser:
            try:
                ser.write(cmd_char.encode())
                self.last_command = cmd_char 
            except:
                print("Serial Write Error")

    def move_forward(self): self.send_command('F')
    def move_backward(self): self.send_command('B')
    def turn_left(self): self.send_command('L')
    def turn_right(self): self.send_command('R')
    def stop(self): self.send_command('S')
   
    def get_distance(self):
        return distance_reading

rover = RoverHardware()

class YOLO:
    def __init__(self, model_path, conf_thres=0.5):
        try:
            self.net = cv2.dnn.readNetFromONNX(model_path)
            self.net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
            self.net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
        except Exception as e:
            print(f"Error loading YOLO: {e}")
            self.net = None

        self.conf_thres = conf_thres
        self.input_size = (320, 320)
        self.classes = ['person', 'bicycle', 'car', 'motorcycle', 'airplane', 'bus', 'train', 'truck', 'boat', 'traffic light', 'fire hydrant', 'stop sign']

    def detect(self, image):
        if self.net is None: return False, False, None, image
       
        blob = cv2.dnn.blobFromImage(image, 1/255.0, self.input_size, [0,0,0], swapRB=True, crop=False)
        self.net.setInput(blob)
        outputs = self.net.forward()
        outputs = np.array([cv2.transpose(outputs[0])])
        rows = outputs.shape[1]

        boxes, scores, class_ids = [], [], []

        for i in range(rows):
            classes_scores = outputs[0][i][4:]
            _, maxScore, _, (_, maxClassIndex) = cv2.minMaxLoc(classes_scores)
            if maxScore >= self.conf_thres:
                # Filter: Only detect classes we care about
                if maxClassIndex > 12: continue
               
                box = outputs[0][i][0:4]
                image_h, image_w = image.shape[:2]
                x_scale, y_scale = image_w / self.input_size[0], image_h / self.input_size[1]
                left = int((box[0] - 0.5 * box[2]) * x_scale)
                top = int((box[1] - 0.5 * box[3]) * y_scale)
                width, height = int(box[2] * x_scale), int(box[3] * y_scale)
                boxes.append([left, top, width, height])
                scores.append(float(maxScore))
                class_ids.append(maxClassIndex)

        indices = cv2.dnn.NMSBoxes(boxes, scores, self.conf_thres, 0.5)
       
        is_blocked = False
        saw_stop_sign = False
        target_x = None

        if len(indices) > 0:
            for i in indices.flatten():
                left, top, width, height = boxes[i]
               
                # Draw Box
                cv2.rectangle(image, (left, top), (left + width, top + height), (0, 255, 0), 2)
               
                # Check for Stop Sign (Class ID 11 is usually Stop Sign in COCO)
                if class_ids[i] == 11:
                    saw_stop_sign = True
                    cv2.putText(image, "STOP SIGN", (left, top - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
               
                # Check Obstacle Size
                area_ratio = (width * height) / (image.shape[0] * image.shape[1])
                if area_ratio > OBSTACLE_THRESH:
                    is_blocked = True
                    target_x = left + (width / 2)

        return is_blocked, saw_stop_sign, target_x, image

app = Flask(__name__)

@app.route('/')
def index(): return render_template('index.html')

@app.route('/video_feed')
def video_feed(): return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/telemetry')
def telemetry():
    global current_state, distance_reading
    return {"state": current_state, "distance": distance_reading}

@app.route('/kill_switch', methods=['POST'])
def kill_switch():
    global manual_kill, current_state
    manual_kill = True
    current_state = "KILL SWITCH ACTIVATED"
    rover.stop()
    return {"status": "STOPPED"}

@app.route('/reset_rover', methods=['POST'])
def reset_rover():
    global manual_kill
    manual_kill = False
    return {"status": "RESUMED"}

@app.route('/manual_control', methods=['POST'])
def manual_control():
    global manual_mode, manual_command, current_state
    manual_mode = True
    cmd = request.form.get('command')
    if cmd:
        manual_command = cmd
        current_state = f"MANUAL: {cmd.upper()}"
    return redirect(url_for('index'))

@app.route('/resume_auto', methods=['POST'])
def resume_auto():
    global manual_mode
    manual_mode = False
    return redirect(url_for('index'))

def gen_frames():
    global video_frame
    while True:
        with lock:
            if video_frame is None: time.sleep(0.1); continue
            try:
                ret, buffer = cv2.imencode('.jpg', video_frame)
                if not ret: continue
                yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
            except: pass

def autonomous_loop():
    global current_state, video_frame, USING_PICAM # <--- FIXED HERE
   
    print("Loading YOLO...")
    vision = YOLO("yolov8n.onnx")
   
    if USING_PICAM:
        print("Starting Picamera2...")
        try:
            picam2 = Picamera2()
            config = picam2.create_video_configuration(main={"size": (320, 240), "format": "BGR888"})
            picam2.configure(config)
            picam2.start()
        except:
            print("Picamera2 failed, falling back to OpenCV")
            USING_PICAM = False

    if not USING_PICAM:
        print("Using OpenCV VideoCapture...")
        cap = cv2.VideoCapture(0)

    print("Autonomous System Ready.")

    while True:
        if manual_kill:
            rover.stop()
            current_state = "HALTED"
            time.sleep(0.5); continue
           
        if manual_mode:
            if manual_command == 'forward': rover.move_forward()
            elif manual_command == 'left': rover.turn_left()
            elif manual_command == 'right': rover.turn_right()
            elif manual_command == 'backward': rover.move_backward()
            elif manual_command == 'stop': rover.stop()
           
            # Keep video running in manual
            if USING_PICAM: frame = picam2.capture_array()
            else: _, frame = cap.read()
            with lock: video_frame = frame
            time.sleep(0.1); continue

        try:
            if USING_PICAM: frame = picam2.capture_array()
            else: _, frame = cap.read()
        except:
            continue
       
        if frame is None: continue

        dist = rover.get_distance()
       
        is_blocked, saw_stop_sign, obj_x, processed_frame = vision.detect(frame)
        with lock: video_frame = processed_frame
       
        FRAME_WIDTH = 320

        if saw_stop_sign:
            current_state = "STOP SIGN DETECTED"
            rover.stop()
            time.sleep(3.0) 
            current_state = "CLEARING SIGN"
            rover.move_forward()
            time.sleep(1.0)
            continue

        if dist < STOP_DISTANCE_CM and dist > 0:
            current_state = "TOO CLOSE: Reversing"
            rover.stop()
            time.sleep(0.2)
            rover.move_backward()
            time.sleep(0.5)
            rover.turn_left()
            time.sleep(0.4)
            continue

        elif is_blocked and obj_x is not None:
            left_lim, right_lim = FRAME_WIDTH / 3, 2 * FRAME_WIDTH / 3
           
            if obj_x < left_lim:
                current_state = "SWERVING RIGHT"
                rover.turn_right()
            elif obj_x > right_lim:
                current_state = "SWERVING LEFT"
                rover.turn_left()
            else:
                current_state = "BLOCKED CENTER: Turning"
                rover.turn_left()
        else:
            current_state = "FORWARD"
            rover.move_forward()

        time.sleep(0.05)

if __name__ == '__main__':
    try:
        logic_thread = threading.Thread(target=autonomous_loop)
        logic_thread.daemon = True
        logic_thread.start()
        app.run(host='0.0.0.0', port=5000, debug=False)
    finally:
        if rover: rover.stop()