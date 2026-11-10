from datetime import datetime

from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, TextAreaField, SelectField, SubmitField
from wtforms.fields import DateTimeLocalField
from wtforms.validators import DataRequired, Length, Regexp, Optional

FOB_ID_VALIDATORS = [
    DataRequired(),
    Length(min=4, max=14, message="Key Fob ID must be 4 or 14 hexadecimal characters."),
    Regexp(
        r'^(?:[0-9a-fA-F]{4}|[0-9a-fA-F]{14})$',
        message="Enter a 4-character legacy ID or a 14-character RFID UID.",
    ),
]


class PatientForm(FlaskForm):
    key_fob_id = StringField("Key Fob Hex ID (4 or 14 digits)", validators=FOB_ID_VALIDATORS)
    first_name = StringField("First Name", validators=[DataRequired()])
    last_name = StringField("Last Name", validators=[DataRequired()])
    age = IntegerField("Age", validators=[Optional()])
    gender = SelectField("Gender", choices=[("", "Select..."), ("Male", "Male"), ("Female", "Female"), ("Other", "Other")], validators=[Optional()])
    initial_assessment = TextAreaField("Initial Assessment", validators=[Optional()])
    health_details = TextAreaField("Health Details / Conditions", validators=[Optional()])
    notes = TextAreaField("General Notes", validators=[Optional()])
    submit = SubmitField("Save Patient")


class PrescribedExerciseForm(FlaskForm):
    name = StringField("Exercise Name", validators=[DataRequired()])
    category = SelectField("Functional Category", choices=[
        ("Cardio", "Cardio"), ("Mobility", "Mobility"), ("Squat/Lunge", "Squat/Lunge"),
        ("Push", "Push"), ("Hinge", "Hinge"), ("Pull", "Pull"),
        ("Carry", "Carry"), ("Core", "Core"), ("Stretching", "Stretching"),
        ("Other", "Other")
    ], validators=[DataRequired()])
    duration_minutes = IntegerField("Duration (minutes, if applicable)", validators=[Optional()])
    intensity = StringField("Intensity / target", validators=[Optional()])
    sets = IntegerField("Sets (if applicable)", validators=[Optional()])
    reps = IntegerField("Reps (if applicable)", validators=[Optional()])
    frequency = StringField("Frequency (e.g. Daily, 3x/week)", validators=[DataRequired()])
    instructions = TextAreaField("Instructions", validators=[Optional()])
    submit = SubmitField("Add Prescribed Exercise")

    def validate(self, extra_validators=None):
        valid = super().validate(extra_validators=extra_validators)
        if self.duration_minutes.data is None and not (self.sets.data and self.reps.data):
            self.duration_minutes.errors.append("Enter a duration or both sets and reps.")
            valid = False
        if self.duration_minutes.data is not None and self.duration_minutes.data <= 0:
            self.duration_minutes.errors.append("Duration must be greater than zero.")
            valid = False
        if self.sets.data is not None and self.sets.data <= 0:
            self.sets.errors.append("Sets must be greater than zero.")
            valid = False
        if self.reps.data is not None and self.reps.data <= 0:
            self.reps.errors.append("Reps must be greater than zero.")
            valid = False
        if (self.sets.data is None) != (self.reps.data is None):
            if self.sets.data is None:
                self.sets.errors.append("Enter sets together with reps.")
            if self.reps.data is None:
                self.reps.errors.append("Enter reps together with sets.")
            valid = False
        return valid


class SessionHistoryForm(FlaskForm):
    date = DateTimeLocalField(
        "Session date and time",
        format="%Y-%m-%dT%H:%M",
        validators=[DataRequired()],
        default=lambda: datetime.now().replace(second=0, microsecond=0),
    )
    warmup = TextAreaField("Warm-up", validators=[Optional()])
    cardio = TextAreaField("Cardio", validators=[Optional()])
    cooldown = TextAreaField("Cool-down", validators=[Optional()])
    notes = TextAreaField("Session notes", validators=[Optional()])
    submit = SubmitField("Save Session")


class AppointmentForm(FlaskForm):
    appointment_date = DateTimeLocalField("Appointment date and time", format="%Y-%m-%dT%H:%M", validators=[DataRequired()])
    notes = TextAreaField("Reason / notes", validators=[DataRequired()])
    submit = SubmitField("Save Appointment")


class FobScanForm(FlaskForm):
    key_fob_id = StringField("Key Fob ID (4 or 14 hex characters)", validators=FOB_ID_VALIDATORS)
    submit = SubmitField("Scan Fob")


class FobAssignmentForm(FlaskForm):
    key_fob_id = StringField("Key Fob Hex ID (4 or 14 digits)", validators=FOB_ID_VALIDATORS)
    submit = SubmitField("Save Fob ID")


class DeletePatientForm(FlaskForm):
    pass
