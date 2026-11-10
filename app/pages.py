from flask import Blueprint, render_template, redirect, url_for, jsonify, request, flash
from .extensions import db
from .models import Appointment, Patient, PrescribedExercise, SessionHistory
from .forms import (
    AppointmentForm, FobAssignmentForm, FobScanForm, PatientForm,
    PrescribedExerciseForm, SessionHistoryForm,
)

pages = Blueprint("pages", __name__)


def _normalize_fob_id(fob_id):
    clean_fob = fob_id.strip().upper()
    if len(clean_fob) not in {4, 14} or any(
        character not in "0123456789ABCDEF" for character in clean_fob
    ):
        return None
    return clean_fob


@pages.route("/")
def home():
    patients = Patient.query.all()
    return render_template("pages/home.html", patients=patients)

@pages.route("/patients")
def patients():
    search = request.args.get("q", "").strip()
    sort_by = request.args.get("sort", "last_name")
    if sort_by not in {"first_name", "last_name"}:
        sort_by = "last_name"

    query = Patient.query
    if search:
        escaped_search = search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        pattern = f"%{escaped_search}%"
        query = query.filter(
            db.or_(
                Patient.first_name.ilike(pattern, escape="\\"),
                Patient.last_name.ilike(pattern, escape="\\"),
                (Patient.first_name + " " + Patient.last_name).ilike(pattern, escape="\\"),
                Patient.key_fob_id.ilike(pattern, escape="\\"),
            )
        )

    sort_column = getattr(Patient, sort_by)
    secondary_column = Patient.last_name if sort_by == "first_name" else Patient.first_name
    all_patients = query.order_by(sort_column, secondary_column).all()
    return render_template(
        "pages/patients.html",
        patients=all_patients,
        search=search,
        sort_by=sort_by,
    )

@pages.route("/patient/<int:patient_id>")
def patient_detail(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    return render_template("pages/patient_detail.html", patient=patient)


@pages.route("/patient/<int:patient_id>/fob", methods=["GET", "POST"])
def assign_fob(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    form = FobAssignmentForm()
    if form.validate_on_submit():
        fob_code = form.key_fob_id.data.strip().upper()
        existing = Patient.query.filter(
            db.func.upper(Patient.key_fob_id) == fob_code,
            Patient.id != patient.id,
        ).first()
        if existing:
            form.key_fob_id.errors.append("Key Fob ID is already assigned to another patient.")
        else:
            patient.key_fob_id = fob_code
            db.session.commit()
            flash("Key fob assigned to patient.", "success")
            return redirect(url_for("pages.patient_detail", patient_id=patient.id))
    elif request.method == "GET":
        form.key_fob_id.data = patient.key_fob_id
    return render_template("pages/assign_fob.html", form=form, patient=patient)


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
    fob_input = _normalize_fob_id(request.args.get("fob", ""))

    if fob_input:
        form.key_fob_id.data = fob_input
        scanned_patient = Patient.query.filter(
            db.func.upper(Patient.key_fob_id) == fob_input
        ).first()
        if scanned_patient:
            lcd_data = scanned_patient.to_lcd_dict()

    if form.validate_on_submit():
        fob_code = form.key_fob_id.data.strip().upper()
        return redirect(url_for("pages.scan", fob=fob_code))

    return render_template("pages/scan.html", form=form, scanned_patient=scanned_patient, lcd_data=lcd_data)

@pages.route("/api/scan/<fob_id>", methods=["GET"])
def api_scan_fob(fob_id):
    clean_fob = _normalize_fob_id(fob_id)
    if clean_fob is None:
        return jsonify({"status": "error", "message": "Invalid fob ID"}), 400
    patient = Patient.query.filter(
        db.func.upper(Patient.key_fob_id) == clean_fob
    ).first()
    if not patient:
        return jsonify({"status": "error", "message": "Not found"}), 404
    res = patient.to_lcd_dict()
    res["status"] = "success"
    return jsonify(res), 200
