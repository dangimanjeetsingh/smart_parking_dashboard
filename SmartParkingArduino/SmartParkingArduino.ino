#include <Servo.h>

/*
  Smart Parking System
  Arduino UNO + Python USB serial dashboard

  Entry IR sensor  -> pin 2
  Exit IR sensor   -> pin 3
  Entry servo      -> pin 4
  Exit servo       -> pin 5
  Buzzer           -> pin 6
  Slot 1 IR sensor -> pin 7
  Slot 2 IR sensor -> pin 8

  Serial output, every ~300ms:
  COUNT:<number> SLOT1:<0/1> SLOT2:<0/1>
*/

const byte ENTRY_SENSOR_PIN = 2;
const byte EXIT_SENSOR_PIN = 3;
const byte ENTRY_SERVO_PIN = 4;
const byte EXIT_SERVO_PIN = 5;
const byte BUZZER_PIN = 6;
const byte SLOT1_SENSOR_PIN = 7;
const byte SLOT2_SENSOR_PIN = 8;

int totalSlots = 2;
int carCount = 0;
int availableSlots = 2;

const int IR_ACTIVE_STATE = LOW;

const int ENTRY_GATE_OPEN_ANGLE = 0;
const int ENTRY_GATE_CLOSE_ANGLE = 100;

// Exit servo direction is reversed compared with entry servo.
const int EXIT_GATE_OPEN_ANGLE = 100;
const int EXIT_GATE_CLOSE_ANGLE = 0;

const unsigned long DEBOUNCE_TIME = 50;
const unsigned long SENSOR_COOLDOWN = 1500;
const unsigned long GATE_OPEN_TIME = 2000;
const unsigned long SERIAL_SEND_INTERVAL = 300;
const unsigned long BEEP_TIME = 200;
const unsigned long BEEP_GAP = 120;

struct DebouncedSensor {
  byte pin;
  bool stableActive;
  bool lastRawActive;
  unsigned long lastChangeTime;
};

Servo entryServo;
Servo exitServo;

DebouncedSensor entrySensor;
DebouncedSensor exitSensor;
DebouncedSensor slot1Sensor;
DebouncedSensor slot2Sensor;

bool lastEntryState = false;
bool lastExitState = false;

unsigned long lastEntryTriggerTime = 0;
unsigned long lastExitTriggerTime = 0;
unsigned long lastSerialSendTime = 0;

bool entryGateOpen = false;
bool exitGateOpen = false;

unsigned long entryGateOpenedTime = 0;
unsigned long exitGateOpenedTime = 0;

void setupSensor(DebouncedSensor &sensor, byte pin) {
  sensor.pin = pin;
  sensor.stableActive = digitalRead(pin) == IR_ACTIVE_STATE;
  sensor.lastRawActive = sensor.stableActive;
  sensor.lastChangeTime = millis();
}

void updateSensor(DebouncedSensor &sensor) {
  bool rawActive = digitalRead(sensor.pin) == IR_ACTIVE_STATE;

  if (rawActive != sensor.lastRawActive) {
    sensor.lastRawActive = rawActive;
    sensor.lastChangeTime = millis();
  }

  if (millis() - sensor.lastChangeTime >= DEBOUNCE_TIME) {
    sensor.stableActive = rawActive;
  }
}

void updateAllSensors() {
  updateSensor(entrySensor);
  updateSensor(exitSensor);
  updateSensor(slot1Sensor);
  updateSensor(slot2Sensor);
}

void updateAvailableSlots() {
  availableSlots = totalSlots - carCount;
}

int sensorToOccupancy(DebouncedSensor &sensor) {
  return sensor.stableActive ? 1 : 0;
}

void sendParkingState() {
  Serial.print("COUNT:");
  Serial.print(carCount);
  Serial.print(" SLOT1:");
  Serial.print(sensorToOccupancy(slot1Sensor));
  Serial.print(" SLOT2:");
  Serial.println(sensorToOccupancy(slot2Sensor));
}

void openEntryGate() {
  entryServo.write(ENTRY_GATE_OPEN_ANGLE);
  entryGateOpen = true;
  entryGateOpenedTime = millis();
}

void openExitGate() {
  exitServo.write(EXIT_GATE_OPEN_ANGLE);
  exitGateOpen = true;
  exitGateOpenedTime = millis();
}

void closeGatesIfNeeded() {
  unsigned long currentTime = millis();

  if (entryGateOpen && currentTime - entryGateOpenedTime >= GATE_OPEN_TIME) {
    entryServo.write(ENTRY_GATE_CLOSE_ANGLE);
    entryGateOpen = false;
  }

  if (exitGateOpen && currentTime - exitGateOpenedTime >= GATE_OPEN_TIME) {
    exitServo.write(EXIT_GATE_CLOSE_ANGLE);
    exitGateOpen = false;
  }
}

void beepOnce() {
  digitalWrite(BUZZER_PIN, HIGH);
  delay(BEEP_TIME);
  digitalWrite(BUZZER_PIN, LOW);
}

void beepTwice() {
  beepOnce();
  delay(BEEP_GAP);
  beepOnce();
}

void handleEntry() {
  if (carCount < totalSlots) {
    openEntryGate();
    carCount++;
    updateAvailableSlots();
    sendParkingState();
    beepOnce();
  }
}

void handleExit() {
  if (carCount > 0) {
    openExitGate();
    carCount--;
    updateAvailableSlots();
    sendParkingState();
    beepTwice();
  }
}

void setup() {
  pinMode(ENTRY_SENSOR_PIN, INPUT_PULLUP);
  pinMode(EXIT_SENSOR_PIN, INPUT_PULLUP);
  pinMode(SLOT1_SENSOR_PIN, INPUT_PULLUP);
  pinMode(SLOT2_SENSOR_PIN, INPUT_PULLUP);
  pinMode(BUZZER_PIN, OUTPUT);

  digitalWrite(BUZZER_PIN, LOW);

  entryServo.attach(ENTRY_SERVO_PIN);
  exitServo.attach(EXIT_SERVO_PIN);

  entryServo.write(ENTRY_GATE_CLOSE_ANGLE);
  exitServo.write(EXIT_GATE_CLOSE_ANGLE);

  Serial.begin(9600);
  delay(2000);

  setupSensor(entrySensor, ENTRY_SENSOR_PIN);
  setupSensor(exitSensor, EXIT_SENSOR_PIN);
  setupSensor(slot1Sensor, SLOT1_SENSOR_PIN);
  setupSensor(slot2Sensor, SLOT2_SENSOR_PIN);

  updateAvailableSlots();
  sendParkingState();
}

void loop() {
  unsigned long currentTime = millis();

  updateAllSensors();

  bool entryState = entrySensor.stableActive;
  bool exitState = exitSensor.stableActive;

  if (entryState && !lastEntryState && currentTime - lastEntryTriggerTime >= SENSOR_COOLDOWN) {
    lastEntryTriggerTime = currentTime;
    handleEntry();
  }

  if (exitState && !lastExitState && currentTime - lastExitTriggerTime >= SENSOR_COOLDOWN) {
    lastExitTriggerTime = currentTime;
    handleExit();
  }

  lastEntryState = entryState;
  lastExitState = exitState;

  closeGatesIfNeeded();

  if (currentTime - lastSerialSendTime >= SERIAL_SEND_INTERVAL) {
    lastSerialSendTime = currentTime;
    sendParkingState();
  }
}
