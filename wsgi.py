from app import create_app
from database.db import db
from flask_migrate import upgrade

app = create_app()