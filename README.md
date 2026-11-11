# ECE-198 CCCare Records

A Flask and SQLite prototype for keeping each participant's profile, individualized exercise prescriptions, exercise-session history, and appointments in one patient record. A hexadecimal key fob is linked to each participant and can be used by the scanner page or `/api/scan/<fob_id>`.

Shared UI color and typography tokens are defined in `app/static/css/design-tokens.css`.

## Run locally

```powershell
pip install -r requirements.txt
flask --app app run --port 8000 --debug
```

Exercise prescriptions support either a duration (for example, minutes of cardio) or sets and repetitions, plus category, intensity/target, frequency, and instructions. Session history records warm-up, cardio, cool-down, and notes.

## Data model

- A patient has many exercise prescriptions, session-history entries, and appointments.
- Each prescription, session, and appointment stores the patient's database ID as a foreign key.
- Each patient has a unique fob ID. The scanner endpoint returns a compact prescription summary for an LCD display.
