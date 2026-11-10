#include <SPI.h>
#include <Adafruit_PN532.h>
#include <Wire.h>
#include "rgb_lcd.h"

#define PN532_SS   10
#define POT_PIN    A0
#define BUTTON_PIN 2

Adafruit_PN532 nfc(PN532_SS);   // hardware SPI
rgb_lcd lcd;

const uint8_t EX_COUNT = 3;     // exercises per user

char patientName[25];
char exercises[EX_COUNT][33];

void showReady() {
  lcd.clear();
  lcd.setRGB(0, 0, 255);        // blue = waiting
  lcd.print("Scan your card...");
}

// Prints the UID bytes as hex with leading zeros (lcd.print can't do uint64_t)
void printUid(const uint8_t* bytes, uint8_t len) {
  for (uint8_t i = 0; i < len; i++) {
    if (bytes[i] < 0x10) lcd.print("0");
    lcd.print(bytes[i], HEX);
  }
}

// Draws one exercise: name + position on top, exercise on the bottom
void showExercise(uint8_t idx) {
  char header[17];
  snprintf(header, sizeof(header), "%.12s %u/%u", patientName, idx + 1, EX_COUNT);
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print(header);
  lcd.setCursor(0, 1);
  uint8_t length = 0;
  while (length < 16 && exercises[idx][length]) {
    lcd.print(exercises[idx][length]);
    length++;
  }
  for (uint8_t i = length; i < 16; i++) {
    lcd.print(" ");
  }
}

// Pot picks the exercise, button exits
void browseExercises() {
  lcd.setRGB(0, 255, 0);

  int raw = analogRead(POT_PIN);
  uint8_t idx = constrain((long)raw * EX_COUNT / 1024, 0, EX_COUNT - 1);
  showExercise(idx);

  while (true) {
    // Button pressed (wired to GND, so LOW = pressed)
    if (digitalRead(BUTTON_PIN) == LOW) {
      delay(30);                                   // debounce
      if (digitalRead(BUTTON_PIN) == LOW) {
        while (digitalRead(BUTTON_PIN) == LOW);    // wait for release
        delay(30);
        return;
      }
    }

    raw = analogRead(POT_PIN);
    uint8_t newIdx = constrain((long)raw * EX_COUNT / 1024, 0, EX_COUNT - 1);

    // Only switch if the pot has moved a little past the boundary (stops flicker)
    if (newIdx != idx) {
      long zoneStart = (long)newIdx * 1024 / EX_COUNT;
      long zoneEnd   = (long)(newIdx + 1) * 1024 / EX_COUNT;
      if (raw > zoneStart + 15 && raw < zoneEnd - 15) {
        idx = newIdx;
        showExercise(idx);
      }
    }
    delay(20);
  }
}

bool receivePatientData(const uint8_t* uidBytes, uint8_t uidLength) {
  lcd.clear();
  lcd.setRGB(255, 165, 0);
  lcd.print("Looking up fob...");

  uint32_t started = millis();
  while (millis() - started < 15000) {
    if (!Serial.available()) continue;

    String response = Serial.readStringUntil('\n');
    response.trim();
    if (response.startsWith("E|")) {
      lcd.clear();
      lcd.setRGB(255, 0, 0);
      if (response == "E|Unknown fob") {
        lcd.print("Unknown fob");
        lcd.setCursor(0, 1);
        printUid(uidBytes, uidLength);
      } else {
        lcd.print(response.substring(2));
      }
      delay(2500);
      return false;
    }
    if (!response.startsWith("P|")) continue;

    String fields[5];
    int start = 0;
    bool complete = true;
    for (uint8_t i = 0; i < 5; i++) {
      int separator = response.indexOf('|', start);
      if (i == 4) separator = response.length();
      if (separator < 0) {
        complete = false;
        break;
      }
      fields[i] = response.substring(start, separator);
      start = separator + 1;
    }
    if (!complete) continue;

    fields[1].toCharArray(patientName, sizeof(patientName));
    for (uint8_t i = 0; i < EX_COUNT; i++) {
      fields[i + 2].toCharArray(exercises[i], sizeof(exercises[i]));
    }
    return true;
  }

  lcd.clear();
  lcd.setRGB(255, 0, 0);
  lcd.print("No database reply");
  delay(2500);
  return false;
}

void setup() {
  pinMode(BUTTON_PIN, INPUT_PULLUP);

  Serial.begin(115200);
  Serial.setTimeout(15000);
  lcd.begin(16, 2);
  nfc.begin();

  lcd.setRGB(255, 165, 0);      // orange = connecting
  lcd.print("Looking for");
  lcd.setCursor(0, 1);
  lcd.print("PN532...");

  // Keep checking until the reader responds
  uint32_t version = 0;
  while (!version) {
    version = nfc.getFirmwareVersion();
    if (!version) delay(1000);
  }

  nfc.SAMConfig();              // configure to read cards
  showReady();
}

void loop() {
  uint8_t uidBytes[7] = {0};
  uint8_t uidLength = 0;

  // Waits up to 500 ms for a card
  bool found = nfc.readPassiveTargetID(PN532_MIFARE_ISO14443A, uidBytes, &uidLength, 500);
  if (!found) return;

  // Only 7-byte cards are supported
  if (uidLength != 7) {
    lcd.clear();
    lcd.setRGB(255, 0, 0);
    lcd.print("Unsupported card");
    lcd.setCursor(0, 1);
    printUid(uidBytes, uidLength);
    delay(3000);
    showReady();
    return;
  }

  // Send the complete UID to the scan page, which looks it up in SQLite.
  for (uint8_t i = 0; i < 7; i++) {
    if (uidBytes[i] < 0x10) Serial.print("0");
    Serial.print(uidBytes[i], HEX);
  }
  Serial.println();

  if (receivePatientData(uidBytes, uidLength)) {
    lcd.clear();
    lcd.setRGB(0, 255, 0);
    lcd.print("Hi ");
    for (uint8_t i = 0; i < 13 && patientName[i]; i++) {
      lcd.print(patientName[i]);
    }
    delay(1500);
    browseExercises();
  }
  showReady();
}