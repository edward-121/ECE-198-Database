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

struct User {
  uint64_t tag;                 // 7-byte UID fits in 64 bits
  char* name;
  char* exercises[3];
};

// Replace these placeholder tags with your real 7-byte card UIDs.
// Unknown cards show their hex UID on the LCD so you can copy it from there.
// Write them as 14 hex digits with the ULL suffix.

User users[] = {
  {0x040EE5429E6180, "Daniel",   {"Jumping Jacks", "Squats", "One mile"}},
  {0x045c88459E6181, "Ethan",    {"Bicep Curls", "Hopscotch", "1 hour walk"}},
  {0x045FF518CD2A81, "Mohammed", {"2 minute sprint", "Jumps", "Leg curls"}},
  {0x04919D20CA2A81, "Edward",   {"Bench press", "Push ups", "Pullups"}},
  {0x044CB8499E6180, "Jonah",    {"Dips", "Tricep extensions", "Diamond pushups"}},
};
const uint8_t USER_COUNT = sizeof(users) / sizeof(users[0]);

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
void showExercise(const User* u, uint8_t idx) {
  lcd.clear();
  lcd.print(u->name);
  lcd.setCursor(12, 0);
  lcd.print(idx + 1);
  lcd.print("/");
  lcd.print(EX_COUNT);
  lcd.setCursor(0, 1);
  lcd.print(u->exercises[idx]);
}

// Pot picks the exercise, button exits
void browseExercises(const User* u) {
  lcd.setRGB(0, 255, 0);

  int raw = analogRead(POT_PIN);
  uint8_t idx = constrain((long)raw * EX_COUNT / 1024, 0, EX_COUNT - 1);
  showExercise(u, idx);

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
        showExercise(u, idx);
      }
    }
    delay(20);
  }
}

void setup() {
  pinMode(BUTTON_PIN, INPUT_PULLUP);

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

  // Pack the 7 bytes into one 64-bit number
  uint64_t uid = 0;
  for (uint8_t i = 0; i < 7; i++) {
    uid = (uid << 8) | uidBytes[i];
  }

  // Look up the user
  User* match = nullptr;
  for (uint8_t i = 0; i < USER_COUNT; i++) {
    if (users[i].tag == uid) {
      match = &users[i];
      break;
    }
  }

  if (match) {
    // Greeting
    lcd.clear();
    lcd.setRGB(0, 255, 0);      // green = known user
    lcd.print("Hi ");
    lcd.print(match->name);
    delay(1500);

    // Scroll with the pot until the button is pressed
    browseExercises(match);
  } else {
    lcd.clear();
    lcd.setRGB(255, 0, 0);      // red = unknown card
    lcd.print("Unknown card");
    lcd.setCursor(0, 1);
    printUid(uidBytes, uidLength);
    delay(3000);
  }

  showReady();
}