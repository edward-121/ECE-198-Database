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
        db.session.commit()
        seed_database()

    return app
