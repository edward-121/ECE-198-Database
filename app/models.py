from datetime import datetime, timezone
from .extensions import db

class Patient(db.Model):
    __tablename__ = "patient_list"

    id = db.Column(db.Integer, primary_key=True)
    key_fob_id = db.Column(db.String(4), unique=True, nullable=False, index=True)
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

    def to_lcd_dict(self):
        """Format prescribed exercise and patient info for 16x2 and 20x4 LCD screens."""
        name_short = f"{self.first_name[0]}. {self.last_name}" if self.first_name and self.last_name else self.first_name
        full_name = f"{self.first_name} {self.last_name}"

        primary_ex = self.prescribed_exercises[0] if self.prescribed_exercises else None
        if primary_ex:
            if primary_ex.duration_minutes:
                dose = f"{primary_ex.duration_minutes} min"
            elif primary_ex.sets and primary_ex.reps:
                dose = f"{primary_ex.sets}x{primary_ex.reps}"
            else:
                dose = ""
            ex_str = f"{primary_ex.name} {dose}".strip()
            instr_str = primary_ex.intensity or primary_ex.frequency or "See plan"
        else:
            ex_str = "No active exercise"
            instr_str = "N/A"

        prog_cat = self.programs[0].functional_category if self.programs else (primary_ex.category if primary_ex else "General")

        line1_16 = f"FOB:{self.key_fob_id.upper()} {name_short}"[:16].ljust(16)
        line2_16 = f"{ex_str}"[:16].ljust(16)

        line1_20 = f"FOB:{self.key_fob_id.upper()} | {full_name}"[:20].ljust(20)
        line2_20 = f"Ex: {ex_str}"[:20].ljust(20)
        line3_20 = f"Inst: {instr_str}"[:20].ljust(20)
        line4_20 = f"Prog: {prog_cat}"[:20].ljust(20)

        return {
            "patient_id": self.id,
            "key_fob_id": self.key_fob_id.upper(),
            "patient_name": full_name,
            "exercises": [
                {
                    "name": e.name,
                    "category": e.category,
                    "duration_minutes": e.duration_minutes,
                    "intensity": e.intensity,
                    "sets": e.sets,
                    "reps": e.reps,
                    "frequency": e.frequency,
                    "instructions": e.instructions
                } for e in self.prescribed_exercises
            ],
            "lcd_16x2": [line1_16, line2_16],
            "lcd_20x4": [line1_20, line2_20, line3_20, line4_20]
        }


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
