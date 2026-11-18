from datetime import datetime, timezone
import re
from flask import Blueprint, render_template, redirect, url_for, jsonify, request, flash
from .extensions import db
from .models import Appointment, Patient, PrescribedExercise, SessionHistory, WorkoutLog
from .forms import (
    AppointmentForm, DeletePatientForm, FobAssignmentForm, FobScanForm,
    PatientForm, PrescribedExerciseForm, SessionHistoryForm,
)

pages = Blueprint("pages", __name__)
_PATIENT_TOKEN_PATTERN = re.compile(r"^[A-Za-z0-9_-]{43}$")


def _valid_patient_token(token):
    return isinstance(token, str) and _PATIENT_TOKEN_PATTERN.fullmatch(token) is not None


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
        delete_form=DeletePatientForm(),
    )

@pages.route("/patient/<int:patient_id>")
def patient_detail(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    return render_template(
        "pages/patient_detail.html",
        patient=patient,
        delete_form=DeletePatientForm(),
        workout_url=url_for("pages.workout_log_page", token=patient.token, _external=True),
    )


@pages.route("/patient/<int:patient_id>/edit", methods=["GET", "POST"])
def edit_patient(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    form = PatientForm(obj=patient)
    if form.validate_on_submit():
        fob_code = form.key_fob_id.data.strip().upper()
        existing = Patient.query.filter(
            db.func.upper(Patient.key_fob_id) == fob_code,
            Patient.id != patient.id,
        ).first()
        if existing:
            form.key_fob_id.errors.append("Key Fob ID already exists!")
        else:
            patient.key_fob_id = fob_code
            patient.first_name = form.first_name.data.strip()
            patient.last_name = form.last_name.data.strip()
            patient.age = form.age.data
            patient.gender = form.gender.data
            patient.initial_assessment = form.initial_assessment.data
            patient.health_details = form.health_details.data
            patient.notes = form.notes.data
            db.session.commit()
            flash(f"Patient {patient.first_name} updated.", "success")
            return redirect(url_for("pages.patient_detail", patient_id=patient.id))
    return render_template("pages/edit_patient.html", form=form, patient=patient)


@pages.route("/patient/<int:patient_id>/delete", methods=["POST"])
def delete_patient(patient_id):
    form = DeletePatientForm()
    if not form.validate_on_submit():
        flash("Could not verify the delete request. Please try again.", "error")
        return redirect(url_for("pages.patient_detail", patient_id=patient_id))

    patient = Patient.query.get_or_404(patient_id)
    patient_name = f"{patient.first_name} {patient.last_name}"
    db.session.delete(patient)
    db.session.commit()
    flash(f"Patient {patient_name} and their linked records were deleted.", "success")
    return redirect(url_for("pages.patients"))

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
    if request.method == "GET":
        fob_code = _normalize_fob_id(request.args.get("key_fob_id", ""))
        if fob_code:
            form.key_fob_id.data = fob_code
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
    fob_input = _normalize_fob_id(request.args.get("fob", ""))

    if fob_input:
        form.key_fob_id.data = fob_input
        scanned_patient = Patient.query.filter(
            db.func.upper(Patient.key_fob_id) == fob_input
        ).first()

    if form.validate_on_submit():
        fob_code = form.key_fob_id.data.strip().upper()
        return redirect(url_for("pages.scan", fob=fob_code))

    return render_template("pages/scan.html", form=form, scanned_patient=scanned_patient)

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
    return jsonify({
        "patient_name": f"{patient.first_name} {patient.last_name}",
        "exercises": [
            {"name": exercise.name}
            for exercise in patient.prescribed_exercises
        ],
    }), 200


@pages.route("/log")
def workout_log_page():
    return render_template("pages/workout_log.html")


@pages.route("/api/patient-lookup")
def api_patient_lookup():
    token = request.args.get("token", "")
    if not _valid_patient_token(token):
        return jsonify({"error": "A valid patient token is required."}), 400
    patient = Patient.query.filter_by(token=token).first()
    if patient is None:
        return jsonify({"error": "Patient token not found."}), 404

    return jsonify({
        "participant_id": patient.id,
        "name": f"{patient.first_name} {patient.last_name}",
        "exercises": [
            {
                "id": exercise.id,
                "name": exercise.name,
                "category": exercise.category,
                "sets": exercise.sets,
                "reps": exercise.reps,
                "frequency": exercise.frequency,
                "instructions": exercise.instructions,
                "duration_minutes": exercise.duration_minutes,
            }
            for exercise in patient.prescribed_exercises
        ],
    })


@pages.route("/api/workout-logs", methods=["POST"])
def api_create_workout_log():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"error": "A JSON request body is required."}), 400

    token = payload.get("token")
    exercise_id = payload.get("exercise_id")
    reps_completed = payload.get("reps_completed")
    tracking_mode = payload.get("tracking_mode")
    if not _valid_patient_token(token):
        return jsonify({"error": "A valid patient token is required."}), 400
    if isinstance(exercise_id, bool) or not isinstance(exercise_id, int) or exercise_id < 1:
        return jsonify({"error": "A valid prescribed exercise is required."}), 400
    if isinstance(reps_completed, bool) or not isinstance(reps_completed, int) or not 0 <= reps_completed <= 10000:
        return jsonify({"error": "Repetitions must be an integer from 0 to 10000."}), 400
    if not isinstance(tracking_mode, str) or tracking_mode not in {"camera_auto", "manual"}:
        return jsonify({"error": "Tracking mode must be camera_auto or manual."}), 400

    patient = Patient.query.filter_by(token=token).first()
    if patient is None:
        return jsonify({"error": "Patient token not found."}), 404
    exercise = PrescribedExercise.query.filter_by(
        id=exercise_id,
        patient_id=patient.id,
    ).first()
    if exercise is None:
        return jsonify({"error": "That exercise is not assigned to this patient."}), 400
    if tracking_mode == "camera_auto" and not _supports_auto_count(exercise.name):
        return jsonify({"error": "Camera counting is not supported for that exercise."}), 400

    logged_at = datetime.now(timezone.utc)
    log_entry = WorkoutLog(
        participant_id=patient.id,
        exercise_id=exercise.id,
        exercise_name=exercise.name,
        reps_completed=reps_completed,
        tracking_mode=tracking_mode,
        timestamp=logged_at,
    )
    db.session.add(log_entry)
    db.session.commit()
    return jsonify({
        "id": log_entry.id,
        "participant_id": log_entry.participant_id,
        "exercise_name": log_entry.exercise_name,
        "reps_completed": log_entry.reps_completed,
        "tracking_mode": log_entry.tracking_mode,
        "timestamp": logged_at.isoformat(),
    }), 201


def _supports_auto_count(exercise_name):
    return "squat" in exercise_name.casefold() or (
        "bicep" in exercise_name.casefold() and "curl" in exercise_name.casefold()
    )
