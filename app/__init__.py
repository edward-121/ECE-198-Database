from flask import Flask
from flask_admin import Admin               
from flask_admin.contrib.sqla import ModelView
from .extensions import db

admin = Admin(name="Database Dashboard")

def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "apples-and-bananas"        
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///app.db"

    db.init_app(app)
    admin.init_app(app)

    from .pages import pages
    app.register_blueprint(pages)

    from . import models  
    with app.app_context():
        db.create_all()

    admin.add_view(ModelView(models.Patient, db.session))

    return app