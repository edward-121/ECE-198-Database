from flask import Flask
from .extensions import db

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

    return app