# ECE-198 Exercise Care Records

A Flask and SQLite prototype for keeping each participant's profile, individualized exercise prescriptions, exercise-session history, and appointments in one patient record. A four-character hexadecimal key fob is linked to each participant and can be used by the scanner page or `/api/scan/<fob_id>`.

## Run locally

```powershell
pip install -r requirements.txt
flask --app app run --port 8000 --debug
```

On first run, the app creates the SQLite database and adds four fictional sample participants, with exercise plans, session logs, and appointments. Seed data is added only when the patient table is empty.

Open `/patients` to select a participant. Their detail page connects assessment and health notes with the prescribed exercises, complete session entries, and appointment history. Use the actions on that page to add a prescription, log a session, or add an appointment.

Exercise prescriptions support either a duration (for example, minutes of cardio) or sets and repetitions, plus category, intensity/target, frequency, and instructions. Session history records warm-up, cardio, cool-down, and notes.

## Data model

- A patient has many exercise prescriptions, session-history entries, and appointments.
- Each prescription, session, and appointment stores the patient's database ID as a foreign key.
- Each patient has a unique four-character fob ID. The scanner endpoint returns a compact prescription summary for an LCD prototype.

## Before using real participant data

This is a classroom prototype, not a production health-record system. It currently has no user authentication or authorization, and the Flask secret key is a development placeholder. Do not expose it to a network or enter real health information until access control, secret management, encrypted transport and storage, audit logging, backups, retention rules, and applicable privacy requirements are addressed.

For a more complete clinical workflow, consider recording who authorized each prescription, effective dates and status (active/paused/completed), the basis and units for intensity targets, who entered each session, and appointment outcomes or follow-up actions. Use a stable participant identifier rather than age as an identity field; collect additional personal details only if they are needed and appropriately protected.
