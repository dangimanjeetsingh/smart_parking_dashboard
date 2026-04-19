#include <Servo.h>

const byte ENTRY_SENSOR_PIN = 2;
const byte EXIT_SENSOR_PIN = 3;
const byte ENTRY_SERVO_PIN = 4;
const byte EXIT_SERVO_PIN = 5;
const byte BUZZER_PIN = 6;

int totalSlots = 4;
int availableSlots = 4;

const int IR_ACTIVE_STATE = LOW;

const int ENTRY_GATE_OPEN_ANGLE = 0;
const int ENTRY_GATE_CLOSE_ANGLE = 100;

// Exit servo direction is reversed compared with entry servo.
const int EXIT_GATE_OPEN_ANGLE = 100;
const int EXIT_GATE_CLOSE_ANGLE = 0;

const unsigned long DEBOUNCE_TIME = 60;
const unsigned long SENSOR_COOLDOWN = 1500;
const unsigned long GATE_OPEN_TIME = 2000;
const unsigned long BEEP_TIME = 200;
const unsigned long BEEP_GAP = 120;

Servo entryServo;
Servo exitServo;

bool lastEntryState = false;
bool lastExitState = false;

unsigned long lastEntryTriggerTime = 0;
unsigned long lastExitTriggerTime = 0;

bool entryGateOpen = false;
bool exitGateOpen = false;

unsigned long entryGateOpenedTime = 0;
unsigned long exitGateOpenedTime = 0;

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
  if (availableSlots > 0) {
    openEntryGate();
    availableSlots--;

    Serial.println("ENTRY");
    sendSlots();

    beepOnce();
  } else {
    Serial.println("FULL");
    sendSlots();
  }
}

void handleExit() {
  if (availableSlots < totalSlots) {
    availableSlots++;

    openExitGate();

    Serial.println("EXIT");
    sendSlots();

    beepTwice();
  } else {
    // Parking is already empty, so ignore false exit triggers.
    sendSlots();
  }
}

void setup() {
  pinMode(ENTRY_SENSOR_PIN, INPUT_PULLUP);
  pinMode(EXIT_SENSOR_PIN, INPUT_PULLUP);
  pinMode(BUZZER_PIN, OUTPUT);

  digitalWrite(BUZZER_PIN, LOW);

  entryServo.attach(ENTRY_SERVO_PIN);
  exitServo.attach(EXIT_SERVO_PIN);

  entryServo.write(ENTRY_GATE_CLOSE_ANGLE);
  exitServo.write(EXIT_GATE_CLOSE_ANGLE);

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

  closeGatesIfNeeded();
}
