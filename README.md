# ECE-198 CCCare Records

A Flask and SQLite prototype for keeping each participant's profile, individualized exercise prescriptions, exercise-session history, and appointments in one patient record. A fob ID is linked to each participant and can be used by the scanner page or `/api/scan/<fob_id>`. Legacy four-character IDs and 14-character UIDs from 7-byte PN532 cards are supported.

Shared UI color and typography tokens are defined in `app/static/css/design-tokens.css`.

## Run locally

```powershell
pip install -r requirements.txt
flask --app app run --port 8000 --debug
```

Exercise prescriptions support either a duration (for example, minutes of cardio) or sets and repetitions, plus category, intensity/target, frequency, and instructions. Session history records warm-up, cardio, cool-down, and notes.

## Arduino RFID reader

1. Open a patient record, choose **Change fob**, and enter that patient's 14-character RFID UID (the UID is printed by `Hardware.ino` in the Arduino serial monitor if needed).
2. Upload `Hardware.ino` and connect the Arduino to the computer over USB.
3. Run the Flask app over `localhost` and open its Scan page in a Web Serial-capable Chromium browser.
4. Choose **Connect Arduino reader**, select the Arduino's serial port, and scan a fob. The browser looks up the UID in SQLite, shows the patient, then sends the patient's first three prescribed exercises back to the Arduino LCD.

The browser must remain connected to the Scan page while scanning. Close the Arduino serial monitor before connecting the browser to the same port. The Arduino uses 115200 baud and waits up to 15 seconds for the database response.

## Data model

- A patient has many exercise prescriptions, session-history entries, and appointments.
- Each prescription, session, and appointment stores the patient's database ID as a foreign key.
- Each patient has a unique fob ID. The scanner endpoint returns a compact prescription summary for an LCD display.
