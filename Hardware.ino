#include <SPI.h>
#include <Adafruit_PN532.h>
#include <Wire.h>
#include "rgb_lcd.h"

#define PN532_SS   10
#define POT_PIN    A0
#define BUTTON_PIN 2

Adafruit_PN532 nfc(PN532_SS);   // hardware SPI
rgb_lcd lcd;

char patientName[25];
uint16_t exerciseCount = 0;

void showReady() {
  lcd.clear();
  lcd.setRGB(0, 0, 255);
  lcd.print("Scan your card...");
}

void printUid(const uint8_t* bytes, uint8_t len) {
  for (uint8_t i = 0; i < len; i++) {
    if (bytes[i] < 0x10) lcd.print("0");
    lcd.print(bytes[i], HEX);
  }
}

bool requestExercise(uint16_t index, char* exercise, size_t exerciseSize) {
  Serial.print("GET|");
  Serial.println(index);

  uint32_t started = millis();
  while (millis() - started < 6000) {
    if (!Serial.available()) continue;

    String response = Serial.readStringUntil('\n');
    response.trim();
    if (response.startsWith("X|")) {
      response.substring(2).toCharArray(exercise, exerciseSize);
      return true;
    }
    if (response.startsWith("E|")) {
      return false;
    }
  }
  return false;
}

void showExercise(uint16_t index) {
  char header[17];
  char exercise[33];

  snprintf(
    header,
    sizeof(header),
    "%.8s %u/%u",
    patientName,
    (unsigned int)(index + 1),
    (unsigned int)exerciseCount
  );
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print(header);
  lcd.setCursor(0, 1);
  lcd.print("Loading...");

  if (!requestExercise(index, exercise, sizeof(exercise))) {
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("Exercise lookup");
    lcd.setCursor(0, 1);
    lcd.print("failed");
    return;
  }

  lcd.setCursor(0, 1);
  uint8_t length = 0;
  while (length < 16 && exercise[length]) {
    lcd.print(exercise[length]);
    length++;
  }
  while (length++ < 16) {
    lcd.print(" ");
  }
}

void browseExercises() {
  if (exerciseCount == 0) {
    lcd.clear();
    lcd.setRGB(0, 255, 0);
    lcd.print("No exercises");
    delay(2000);
    return;
  }

  lcd.setRGB(0, 255, 0);
  int raw = analogRead(POT_PIN);
  uint16_t index = ((uint32_t)raw * exerciseCount) / 1024UL;
  if (index >= exerciseCount) index = exerciseCount - 1;
  showExercise(index);

  while (true) {
    if (digitalRead(BUTTON_PIN) == LOW) {
      delay(30);
      if (digitalRead(BUTTON_PIN) == LOW) {
        while (digitalRead(BUTTON_PIN) == LOW);
        delay(30);
        return;
      }
    }

    raw = analogRead(POT_PIN);
    uint16_t newIndex = ((uint32_t)raw * exerciseCount) / 1024UL;
    if (newIndex >= exerciseCount) newIndex = exerciseCount - 1;

    if (newIndex != index) {
      long zoneStart = (long)newIndex * 1024L / exerciseCount;
      long zoneEnd = (long)(newIndex + 1) * 1024L / exerciseCount;
      long margin = 15;
      long zoneWidth = zoneEnd - zoneStart;
      if (zoneWidth / 3 < margin) margin = zoneWidth / 3;
      if (raw >= zoneStart + margin && raw < zoneEnd - margin) {
        index = newIndex;
        showExercise(index);
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

    int nameEnd = response.indexOf('|', 2);
    if (nameEnd < 0) continue;

    String countText = response.substring(nameEnd + 1);
    if (countText.length() == 0) continue;
    bool validCount = true;
    for (uint8_t i = 0; i < countText.length(); i++) {
      if (!isDigit(countText[i])) {
        validCount = false;
        break;
      }
    }
    if (!validCount) continue;

    unsigned long count = countText.toInt();
    if (count > 65535UL) continue;
    response.substring(2, nameEnd).toCharArray(patientName, sizeof(patientName));
    exerciseCount = (uint16_t)count;
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
  Serial.setTimeout(1000);
  lcd.begin(16, 2);
  nfc.begin();

  lcd.setRGB(255, 165, 0);
  lcd.print("Looking for");
  lcd.setCursor(0, 1);
  lcd.print("PN532...");

  uint32_t version = 0;
  while (!version) {
    version = nfc.getFirmwareVersion();
    if (!version) delay(1000);
  }

  nfc.SAMConfig();
  showReady();
}

void loop() {
  uint8_t uidBytes[7] = {0};
  uint8_t uidLength = 0;

  bool found = nfc.readPassiveTargetID(PN532_MIFARE_ISO14443A, uidBytes, &uidLength, 500);
  if (!found) return;

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
