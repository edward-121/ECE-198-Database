from datetime import datetime, timezone
import secrets
from .extensions import db

class Patient(db.Model):
    __tablename__ = "patient_list"

    id = db.Column(db.Integer, primary_key=True)
    key_fob_id = db.Column(db.String(14), unique=True, nullable=False, index=True)
    token = db.Column(db.String(64), unique=True, nullable=False, index=True, default=lambda: secrets.token_urlsafe(32))
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    age = db.Column(db.Integer, nullable=True)
    gender = db.Column(db.String(50), nullable=True)
    initial_assessment = db.Column(db.Text, nullable=True)
    health_details = db.Column(db.Text, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    prescribed_exercises = db.relationship("PrescribedExercise", backref="patient", lazy=True, cascade="all, delete-orphan", order_by="PrescribedExercise.id")
    programs = db.relationship("Program", backref="patient", lazy=True, cascade="all, delete-orphan")
    sessions = db.relationship("SessionHistory", backref="patient", lazy=True, cascade="all, delete-orphan", order_by="SessionHistory.date.desc()")
    appointments = db.relationship("Appointment", backref="patient", lazy=True, cascade="all, delete-orphan", order_by="Appointment.appointment_date.desc()")

    def __repr__(self):
        return f"<Patient {self.id}: {self.first_name} {self.last_name} (Fob: {self.key_fob_id})>"

class SeedMarker(db.Model):
    __tablename__ = "seed_marker"

    key = db.Column(db.String(100), primary_key=True)


class PrescribedExercise(db.Model):
    __tablename__ = "prescribed_exercise"
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patient_list.id"), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(100), nullable=True)
    duration_minutes = db.Column(db.Integer, nullable=True)
    intensity = db.Column(db.String(100), nullable=True)
    sets = db.Column(db.Integer, nullable=False, default=0)
    reps = db.Column(db.Integer, nullable=False, default=0)
    frequency = db.Column(db.String(100), nullable=False)
    instructions = db.Column(db.Text, nullable=True)


class Program(db.Model):
    __tablename__ = "program"
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patient_list.id"), nullable=False)
    functional_category = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    exercises = db.relationship("Exercise", backref="program", lazy=True, cascade="all, delete-orphan")


class Exercise(db.Model):
    __tablename__ = "exercise"
    id = db.Column(db.Integer, primary_key=True)
    program_id = db.Column(db.Integer, db.ForeignKey("program.id"), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    functional_category = db.Column(db.String(100), nullable=True)
    description = db.Column(db.Text, nullable=True)
    sets = db.Column(db.Integer, nullable=True)
    reps = db.Column(db.Integer, nullable=True)
    cooldown = db.Column(db.String(100), nullable=True)


class SessionHistory(db.Model):
    __tablename__ = "session_history"
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patient_list.id"), nullable=False)
    date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    warmup = db.Column(db.Text, nullable=True)
    cardio = db.Column(db.Text, nullable=True)
    cooldown = db.Column(db.Text, nullable=True)
    notes = db.Column(db.Text, nullable=True)


class Appointment(db.Model):
    __tablename__ = "appointment"
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patient_list.id"), nullable=False)
    appointment_date = db.Column(db.DateTime, nullable=False)
    notes = db.Column(db.Text, nullable=True)


class WorkoutLog(db.Model):
    __tablename__ = "workout_log"

    id = db.Column(db.Integer, primary_key=True)
    participant_id = db.Column(db.Integer, db.ForeignKey("patient_list.id"), nullable=False, index=True)
    exercise_id = db.Column(db.Integer, db.ForeignKey("prescribed_exercise.id"), nullable=False)
    exercise_name = db.Column(db.String(100), nullable=False)
    reps_completed = db.Column(db.Integer, nullable=False)
    tracking_mode = db.Column(db.String(20), nullable=False)
    timestamp = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    participant = db.relationship("Patient", backref=db.backref(
        "workout_logs",
        lazy=True,
        cascade="all, delete-orphan",
        order_by="WorkoutLog.timestamp.desc()",
    ))
    exercise = db.relationship("PrescribedExercise")
