import secrets
import click
from flask import Flask
from sqlalchemy import inspect, text
from .extensions import db
from .seed import seed_database

def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "apples-and-bananas"        
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///app.db"

    db.init_app(app)

    from .pages import pages
    app.register_blueprint(pages)

    from . import models  
    with app.app_context():
        db.create_all()
        # Lightweight migration: create_all() won't add columns to existing tables,
        # so add any columns introduced after an older app.db was created.
        exercise_columns = {
            column["name"]
            for column in inspect(db.engine).get_columns("prescribed_exercise")
        }
        for column_name, column_type in (
            ("category", "VARCHAR(100)"),
            ("duration_minutes", "INTEGER"),
            ("intensity", "VARCHAR(100)"),
        ):
            if column_name not in exercise_columns:
                db.session.execute(text(
                    f"ALTER TABLE prescribed_exercise ADD COLUMN {column_name} {column_type}"
                ))
        patient_columns = {
            column["name"]
            for column in inspect(db.engine).get_columns("patient_list")
        }
        # Every patient needs a private token for their workout-log link.
        # Add the column if missing, then backfill tokens for older rows.
        if "token" not in patient_columns:
            db.session.execute(text("ALTER TABLE patient_list ADD COLUMN token VARCHAR(64)"))
        for patient_id, token in db.session.execute(
            text("SELECT id, token FROM patient_list WHERE token IS NULL OR token = ''")
        ):
            db.session.execute(
                text("UPDATE patient_list SET token = :token WHERE id = :patient_id"),
                {"token": secrets.token_urlsafe(32), "patient_id": patient_id},
            )
        db.session.execute(text(
            "CREATE UNIQUE INDEX IF NOT EXISTS ix_patient_list_token ON patient_list (token)"
        ))
        db.session.commit()
        # Insert demo/test patients (only does anything on a fresh DB).
        seed_database()

    # Run with `flask workout-test-url` to get a ready-to-open workout log link.
    @app.cli.command("workout-test-url")
    def workout_test_url():
        """Print the log URL for a seeded test patient with a countable exercise."""
        from .models import Patient, PrescribedExercise

        patient = (
            Patient.query.filter_by(key_fob_id="044CB8499E6180")
            .join(PrescribedExercise)
            .filter(
                db.or_(
                    PrescribedExercise.name.ilike("%squat%"),
                    db.and_(
                        PrescribedExercise.name.ilike("%bicep%"),
                        PrescribedExercise.name.ilike("%curl%"),
                    ),
                )
            )
            .first()
        )
        if patient is None:
            raise click.ClickException("No patient with a Squat or Bicep Curl exercise was found.")
        click.echo(f"http://localhost:8000/log?token={patient.token}")

    return app
