from flask_wtf import FlaskForm
from wtforms import StringField
from wtforms.validators import DataRequired

class PatientForm(FlaskForm):
    first_name = StringField("First Name", validators=[DataRequired()])
    last_name = StringField("Last Name", validators=[DataRequired()])