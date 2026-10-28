from .extensions import db

class Patient(db.Model):
    __tablename__ = "patient_list"
    patient_id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String)
    last_name = db.Column(db.String)