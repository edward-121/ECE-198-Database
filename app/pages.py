from flask import Blueprint, render_template, redirect, url_for
from .extensions import db
from .models import Patient
from .forms import PatientForm

pages = Blueprint("pages", __name__)

@pages.route("/")
def home():
    return render_template("pages/home.html")

@pages.route("/patients")
def patients():
    all_patients = Patient.query.all()
    return render_template("pages/patients.html", patients=all_patients)

@pages.route("/patients/add", methods=["GET", "POST"])
def add_patient():
    form = PatientForm()
    if form.validate_on_submit():
        db.session.add(Patient(first_name=form.first_name.data,
                               last_name=form.last_name.data))
        db.session.commit()
        return redirect(url_for("pages.patients"))
    return render_template("pages/add_patient.html", form=form)