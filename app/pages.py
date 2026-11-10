from flask import Blueprint, render_template, redirect, url_for, jsonify, request, flash
from .extensions import db
from .models import Appointment, Patient, PrescribedExercise, SessionHistory
from .forms import (
    AppointmentForm, FobScanForm, PatientForm, PrescribedExerciseForm,
    SessionHistoryForm,
)

pages = Blueprint("pages", __name__)

@pages.route("/")
def home():
    patients = Patient.query.all()
    return render_template("pages/home.html", patients=patients)

@pages.route("/patients")
def patients():
    all_patients = Patient.query.order_by(Patient.last_name, Patient.first_name).all()
    return render_template("pages/patients.html", patients=all_patients)

@pages.route("/patient/<int:patient_id>")
def patient_detail(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    return render_template("pages/patient_detail.html", patient=patient)

@pages.route("/patients/add", methods=["GET", "POST"])
def add_patient():
    form = PatientForm()
    if form.validate_on_submit():
        fob_code = form.key_fob_id.data.strip().upper()
        existing = Patient.query.filter(Patient.key_fob_id.ilike(fob_code)).first()
        if existing:
            form.key_fob_id.errors.append("Key Fob ID already exists!")
            return render_template("pages/add_patient.html", form=form)

        new_patient = Patient(
            key_fob_id=fob_code,
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            age=form.age.data,
            gender=form.gender.data,
            initial_assessment=form.initial_assessment.data,
            health_details=form.health_details.data,
            notes=form.notes.data
        )
        db.session.add(new_patient)
        db.session.commit()
        flash(f"Patient {new_patient.first_name} added!", "success")
        return redirect(url_for("pages.patient_detail", patient_id=new_patient.id))
    return render_template("pages/add_patient.html", form=form)

@pages.route("/patient/<int:patient_id>/add_exercise", methods=["GET", "POST"])
def add_exercise(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    form = PrescribedExerciseForm()
    if form.validate_on_submit():
        ex = PrescribedExercise(
            patient_id=patient.id,
            name=form.name.data,
            category=form.category.data,
            duration_minutes=form.duration_minutes.data,
            intensity=form.intensity.data,
            sets=form.sets.data or 0,
            reps=form.reps.data or 0,
            frequency=form.frequency.data,
            instructions=form.instructions.data
        )
        db.session.add(ex)
        db.session.commit()
        flash("Prescribed exercise added!", "success")
        return redirect(url_for("pages.patient_detail", patient_id=patient.id))
    return render_template("pages/add_exercise.html", form=form, patient=patient)


@pages.route("/patient/<int:patient_id>/sessions/add", methods=["GET", "POST"])
def add_session(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    form = SessionHistoryForm()
    if form.validate_on_submit():
        session = SessionHistory(
            patient_id=patient.id,
            date=form.date.data,
            warmup=form.warmup.data,
            cardio=form.cardio.data,
            cooldown=form.cooldown.data,
            notes=form.notes.data,
        )
        db.session.add(session)
        db.session.commit()
        flash("Exercise session added to patient history.", "success")
        return redirect(url_for("pages.patient_detail", patient_id=patient.id))
    return render_template("pages/add_session.html", form=form, patient=patient)


@pages.route("/patient/<int:patient_id>/appointments/add", methods=["GET", "POST"])
def add_appointment(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    form = AppointmentForm()
    if form.validate_on_submit():
        appointment = Appointment(
            patient_id=patient.id,
            appointment_date=form.appointment_date.data,
            notes=form.notes.data,
        )
        db.session.add(appointment)
        db.session.commit()
        flash("Appointment added to patient history.", "success")
        return redirect(url_for("pages.patient_detail", patient_id=patient.id))
    return render_template("pages/add_appointment.html", form=form, patient=patient)

@pages.route("/scan", methods=["GET", "POST"])
def scan():
    form = FobScanForm()
    scanned_patient = None
    lcd_data = None
    fob_input = request.args.get("fob", "").strip().upper()

    if fob_input:
        form.key_fob_id.data = fob_input
        scanned_patient = Patient.query.filter(Patient.key_fob_id.ilike(fob_input)).first()
        if scanned_patient:
            lcd_data = scanned_patient.to_lcd_dict()

    if form.validate_on_submit():
        fob_code = form.key_fob_id.data.strip().upper()
        return redirect(url_for("pages.scan", fob=fob_code))

    return render_template("pages/scan.html", form=form, scanned_patient=scanned_patient, lcd_data=lcd_data)

@pages.route("/api/scan/<fob_id>", methods=["GET"])
def api_scan_fob(fob_id):
    clean_fob = fob_id.strip().upper()
    patient = Patient.query.filter(Patient.key_fob_id.ilike(clean_fob)).first()
    if not patient:
        return jsonify({"status": "error", "message": "Not found"}), 404
    res = patient.to_lcd_dict()
    res["status"] = "success"
    return jsonify(res), 200
