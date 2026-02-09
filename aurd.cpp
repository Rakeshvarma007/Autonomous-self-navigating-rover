// PIN DEFINITIONS
const int TR = 3;  // Trigger
const int EC = 5;  // Echo
const int LP1 = 11; // Left Motor Pin 1
const int LP2 = 12; // Left Motor Pin 2
const int RP1 = 10; // Right Motor Pin 1
const int RP2 = 9;  // Right Motor Pin 2

long duration;
int distance;
char command = 'S';

void setup() {
  Serial.begin(9600);

  // Pin Modes
  pinMode(TR, OUTPUT);
  pinMode(EC, INPUT);
  
  pinMode(LP1, OUTPUT);
  pinMode(LP2, OUTPUT);
  pinMode(RP1, OUTPUT);
  pinMode(RP2, OUTPUT);
  
  stopMotors();
}

void loop() {
  if (Serial.available() > 0) {
    command = Serial.read();
    executeCommand(command);
  }

  digitalWrite(TR, LOW);
  delayMicroseconds(2);
  digitalWrite(TR, HIGH);
  delayMicroseconds(10);
  digitalWrite(TR, LOW);
  
  duration = pulseIn(EC, HIGH, 30000);
  
  if (duration == 0) {
    distance = 100;
  } else {
    distance = duration * 0.034 / 2;
  }

  Serial.print("D:");
  Serial.println(distance);

  delay(50);
}

void executeCommand(char cmd) {
  switch (cmd) {
    case 'F': moveForward(); break;
    case 'B': moveBackward(); break;
    case 'L': turnLeft(); break;
    case 'R': turnRight(); break;
    case 'S': stopMotors(); break;
  }
}

void moveForward() {
  digitalWrite(LP1, HIGH); digitalWrite(LP2, LOW);
  digitalWrite(RP1, HIGH); digitalWrite(RP2, LOW);
}

void moveBackward() {
  digitalWrite(LP1, LOW); digitalWrite(LP2, HIGH);
  digitalWrite(RP1, LOW); digitalWrite(RP2, HIGH);
}

void turnLeft() {
  digitalWrite(LP1, LOW); digitalWrite(LP2, HIGH);
  digitalWrite(RP1, HIGH); digitalWrite(RP2, LOW);
}

void turnRight() {
  digitalWrite(LP1, HIGH); digitalWrite(LP2, LOW);
  digitalWrite(RP1, LOW); digitalWrite(RP2, HIGH);
}

void stopMotors() {
  digitalWrite(LP1, LOW); digitalWrite(LP2, LOW);
  digitalWrite(RP1, LOW); digitalWrite(RP2, LOW);
}