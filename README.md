# ECE-198 CCCare Records

A Flask and SQLite prototype for keeping each participant's profile, individualized exercise prescriptions, exercise-session history, and appointments in one patient record. A hexadecimal key fob is linked to each participant and can be used by the scanner page or `/api/scan/<fob_id>`.

Shared UI color and typography tokens are defined in `app/static/css/design-tokens.css`.

## Run locally

```powershell
pip install -r requirements.txt
flask --app app run --host 0.0.0.0 --port 8000 --debug
```

Open `http://localhost:8000` on the computer. To test from a phone on the same Wi-Fi or hotspot, open `http://<computer-ip>:8000` on the phone, where `<computer-ip>` is the computer's IPv4 address from `ipconfig`. Keep the Flask process running.

Exercise prescriptions support either a duration (for example, minutes of cardio) or sets and repetitions, plus category, intensity/target, frequency, and instructions. Session history records warm-up, cardio, cool-down, and notes.

## Arduino RFID reader

1. Open a patient record, choose **Change fob**, and enter that patient's 14-character RFID UID (the UID is printed by `Hardware.ino` in the Arduino serial monitor if needed).
2. Upload `Hardware.ino` and connect the Arduino to the computer over USB.
3. Run the Flask app and open its Scan page in a Web Serial-capable Chromium browser.
4. Choose **Connect Arduino reader**, select the Arduino's serial port, and scan a fob. The browser looks up the UID in SQLite and displays `Scanned: <name>` followed by numbered exercises as normal text. If the fob is unknown, the browser offers to open the patient registration form with its UID filled in. The Arduino requests each exercise by index as the potentiometer browses the plan, so it can cycle through the complete prescription without keeping a fixed three-exercise array in memory.

The browser must remain connected to the Scan page while scanning and browsing exercises. Close the Arduino serial monitor before connecting the browser to the same port. The Arduino uses 115200 baud and waits up to 15 seconds for the initial database lookup; each exercise lookup has a six-second timeout.

## Patient workout logging

Each patient has a random, unique workout token. Open the patient record and use **Patient workout link** to get their `/log?token=...` URL. The app creates tokens for existing patients automatically when it starts. Arduino RFID fobs are identified by their UID and do not contain a URL for a phone to open.

To print a URL for a seeded patient who has a Squat or Bicep Curl exercise:

```powershell
flask --app app workout-test-url
```

Start the app with `flask --app app run --host 0.0.0.0 --port 8000`, then open the printed URL on the computer. For phone access on the same Wi-Fi or hotspot, use `http://<computer-ip>:8000/log?token=...` with the computer's IPv4 address. The patient can log repetitions manually or enable the camera counter for Squats and Bicep Curls. Camera counting requires HTTPS or localhost and explicit camera permission. MediaPipe's model/runtime assets are loaded by the browser from their public CDNs when camera counting is enabled; pose estimation and video frames remain in the browser and are never sent to this server. Turning the camera off or leaving the page stops the media tracks.

For squat counting, keep the full body in view with good lighting; a side view helps the hip, knee, and ankle landmarks track. Squats switch to the down stage below a 120° knee angle and count a rep when the knee straightens above 140°. For curls, select the front or rear camera and face sideways to it so the shoulder, elbow, and wrist are visible. Curl angles use MediaPipe's 3D world landmarks when available and count the bend below 75° and extension above 135°. Clothing that hides the joints or hangs loosely can reduce pose visibility.

Workout sets are stored in `workout_log`, linked to the patient's prescribed exercise, and include the rep count, tracking mode, and UTC timestamp.

## Data model

- A patient has many exercise prescriptions, session-history entries, and appointments.
- Each patient also has a unique random workout token and can have many exercise workout logs.
- Each prescription, session, and appointment stores the patient's database ID as a foreign key.
- Each patient has a unique fob ID. The scanner endpoint returns the patient's name and prescribed exercises.
