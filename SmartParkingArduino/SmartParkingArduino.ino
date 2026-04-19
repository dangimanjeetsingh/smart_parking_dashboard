#include <Servo.h>

const byte ENTRY_SENSOR_PIN = 2;
const byte EXIT_SENSOR_PIN = 3;
const byte SERVO_PIN = 4;

int totalSlots = 4;
int availableSlots = 4;

const int IR_ACTIVE_STATE = LOW;

const int GATE_OPEN_ANGLE = 0;
const int GATE_CLOSE_ANGLE = 100;

const unsigned long GATE_OPEN_TIME = 1000;
const unsigned long DEBOUNCE_TIME = 60;
const unsigned long SENSOR_COOLDOWN = 1500;
const unsigned long SLOT_SEND_INTERVAL = 500;

Servo gateServo;

bool lastEntryState = false;
bool lastExitState = false;

unsigned long lastEntryTriggerTime = 0;
unsigned long lastExitTriggerTime = 0;
unsigned long lastSlotSendTime = 0;

bool gateIsOpen = false;
unsigned long gateOpenedTime = 0;

bool isSensorTriggered(byte pin) {
  if (digitalRead(pin) != IR_ACTIVE_STATE) {
    return false;
  }

  unsigned long startTime = millis();

  while (millis() - startTime < DEBOUNCE_TIME) {
    if (digitalRead(pin) != IR_ACTIVE_STATE) {
      return false;
    }
  }

  return true;
}

void sendSlots() {
  Serial.print("SLOTS:");
  Serial.println(availableSlots);
}

void openGate() {
  gateServo.write(GATE_OPEN_ANGLE);
  gateIsOpen = true;
  gateOpenedTime = millis();
}

void closeGateIfNeeded() {
  if (gateIsOpen && millis() - gateOpenedTime >= GATE_OPEN_TIME) {
    gateServo.write(GATE_CLOSE_ANGLE);
    gateIsOpen = false;
  }
}

void handleEntry() {
  if (availableSlots > 0) {
    openGate();
    availableSlots--;
    Serial.println("ENTRY");
    sendSlots();
  } else {
    Serial.println("FULL");
    sendSlots();
  }
}

void handleExit() {
  if (availableSlots < totalSlots) {
    availableSlots++;
  }

  openGate();
  Serial.println("EXIT");
  sendSlots();
}

void setup() {
  pinMode(ENTRY_SENSOR_PIN, INPUT_PULLUP);
  pinMode(EXIT_SENSOR_PIN, INPUT_PULLUP);

  gateServo.attach(SERVO_PIN);
  gateServo.write(GATE_CLOSE_ANGLE);

  Serial.begin(9600);
  sendSlots();
}

void loop() {
  unsigned long currentTime = millis();

  bool entryState = isSensorTriggered(ENTRY_SENSOR_PIN);
  bool exitState = isSensorTriggered(EXIT_SENSOR_PIN);

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

  closeGateIfNeeded();

  if (currentTime - lastSlotSendTime >= SLOT_SEND_INTERVAL) {
    lastSlotSendTime = currentTime;
    sendSlots();
  }
}
