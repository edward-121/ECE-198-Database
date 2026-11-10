from datetime import datetime, timedelta, timezone

from .extensions import db
from .models import Appointment, Patient, PrescribedExercise, SessionHistory


def seed_database():
    """Create four sample patients with linked exercise plans and histories."""
    if Patient.query.first():
        return

    now = datetime.now(timezone.utc)
    sample_data = [
        {
            "fob": "A1B2", "first": "Alice", "last": "Johnson", "age": 34,
            "gender": "Female",
            "assessment": "Baseline assessment: reduced knee range of motion; aerobic baseline established.",
            "health": "Mild hypertension. Follow the clinician-approved exercise plan.",
            "notes": "Prefers morning sessions.",
            "exercises": [
                ("Recumbent bike", "Cardio", 20, "Moderate; target heart-rate range per care team", 0, 0, "3 times per week", "Keep resistance comfortable."),
                ("Box squat", "Squat/Lunge", None, "Bodyweight", 2, 12, "2 times per week", "Use a stable support as needed."),
            ],
            "session": ("5 minutes easy walking", "18 minutes recumbent bike at moderate intensity", "5 minutes gentle stretching", "Completed planned cardio; no concerns reported."),
            "appointment": "Exercise plan review",
        },
        {
            "fob": "C3D4", "first": "Bob", "last": "Smith", "age": 52,
            "gender": "Male",
            "assessment": "Baseline assessment: reduced shoulder flexion; aerobic tolerance assessed.",
            "health": "Type 2 diabetes and hyperlipidemia. Follow clinician guidance during exercise.",
            "notes": "Check in with the care team about exercise-related symptoms.",
            "exercises": [
                ("Treadmill walk", "Cardio", 25, "Moderate; target heart-rate range per care team", 0, 0, "3 times per week", "Adjust pace to the prescribed intensity."),
                ("Resistance band row", "Pull", None, "Light resistance", 2, 10, "2 times per week", "Maintain a comfortable range of motion."),
            ],
            "session": ("3 minutes easy walking", "20 minutes treadmill walking at moderate intensity", "4 minutes gentle stretching", "Session completed as planned."),
            "appointment": "Exercise progress check",
        },
        {
            "fob": "E5F6", "first": "Carol", "last": "Danvers", "age": 28,
            "gender": "Female",
            "assessment": "Baseline assessment: strong aerobic baseline; conditioning plan established.",
            "health": "Exercise-induced asthma. Follow the individual's clinician-provided action plan.",
            "notes": "Use a gradual warm-up before cardio.",
            "exercises": [
                ("Stationary bike", "Cardio", 30, "Moderate; target heart-rate range per care team", 0, 0, "3 times per week", "Increase effort gradually after warming up."),
                ("Glute bridge", "Hinge", None, "Bodyweight", 2, 15, "2 times per week", "Stop if discomfort occurs."),
            ],
            "session": ("5 minutes easy cycling", "25 minutes stationary bike at moderate intensity", "5 minutes gentle mobility", "Completed with gradual warm-up."),
            "appointment": "Conditioning plan review",
        },
        {
            "fob": "789A", "first": "David", "last": "Miller", "age": 65,
            "gender": "Male",
            "assessment": "Baseline assessment: bilateral knee osteoarthritis; low-impact activity plan established.",
            "health": "Controlled hypertension and osteoarthritis. Follow the approved low-impact plan.",
            "notes": "Prioritize low-impact movements and comfortable ranges.",
            "exercises": [
                ("Elliptical", "Cardio", 15, "Low to moderate; target per care team", 0, 0, "3 times per week", "Use a comfortable pace and resistance."),
                ("Seated core rotation", "Core", None, "Light effort", 2, 10, "2 times per week", "Move within a comfortable range."),
            ],
            "session": ("5 minutes gentle mobility", "15 minutes elliptical at low to moderate intensity", "5 minutes gentle stretching", "Low-impact session completed."),
            "appointment": "Low-impact program review",
        },
    ]

    for index, data in enumerate(sample_data):
        patient = Patient(
            key_fob_id=data["fob"],
            first_name=data["first"],
            last_name=data["last"],
            age=data["age"],
            gender=data["gender"],
            initial_assessment=data["assessment"],
            health_details=data["health"],
            notes=data["notes"],
        )
        db.session.add(patient)
        db.session.flush()

        for exercise in data["exercises"]:
            name, category, duration, intensity, sets, reps, frequency, instructions = exercise
            db.session.add(PrescribedExercise(
                patient_id=patient.id,
                name=name,
                category=category,
                duration_minutes=duration,
                intensity=intensity,
                sets=sets,
                reps=reps,
                frequency=frequency,
                instructions=instructions,
            ))

        warmup, cardio, cooldown, notes = data["session"]
        db.session.add(SessionHistory(
            patient_id=patient.id,
            date=now - timedelta(days=7 + index),
            warmup=warmup,
            cardio=cardio,
            cooldown=cooldown,
            notes=notes,
        ))
        db.session.add(Appointment(
            patient_id=patient.id,
            appointment_date=now + timedelta(days=7 + index * 2),
            notes=data["appointment"],
        ))

    db.session.commit()
    print("Database seeded with 4 sample patient records.")
