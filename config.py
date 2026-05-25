import os

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "bookmyshow-secret-key-2024")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False
    MAIL_SERVER = 'smtp.gmail.com'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME", "anushabobili414@gmail.com")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD", "nfyqeztiebqfxqyq")
    MAIL_DEFAULT_SENDER = os.environ.get("MAIL_USERNAME", "anushabobili414@gmail.com")

class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "postgresql://postgres:anuchinni329@localhost:5432/movie_booking_db"
    )
    SQLALCHEMY_ECHO = False

class ProductionConfig(Config):
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "postgresql://postgres:anuchinni329@localhost:5432/movie_booking_db"
    )
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"

class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"

config_map = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig,
}
