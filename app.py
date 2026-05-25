from flask import Flask, render_template
from database.db import db
from flask_migrate import Migrate
from config import config_map
import os

migrate = Migrate()


def create_app(env=None):
    app = Flask(__name__)
    env = env or os.environ.get("FLASK_ENV", "development")
    app.config.from_object(config_map[env])

    db.init_app(app)
    migrate.init_app(app, db)
    app.jinja_env.globals.update(enumerate=enumerate)

    # Custom filter: stable poster index based on movie_id hash
    import hashlib
    def stable_poster_idx(movie_id, total=30):
        h = int(hashlib.md5(str(movie_id).encode()).hexdigest(), 16)
        return h % total
    app.jinja_env.filters['stable_poster_idx'] = stable_poster_idx

    with app.app_context():
        from models.models import Role, AppUser, TheatreOwnership, UserBooking

        # Register blueprints
        from routes.auth import auth_bp
        from routes.public import public_bp
        from routes.admin import admin_bp
        from routes.theatre_owner import theatre_owner_bp
        from routes.user import user_bp
        from routes.analyst import analyst_bp

        app.register_blueprint(auth_bp)
        app.register_blueprint(public_bp)
        app.register_blueprint(admin_bp)
        app.register_blueprint(theatre_owner_bp)
        app.register_blueprint(user_bp)
        app.register_blueprint(analyst_bp)

        # Create tables and seed roles + admin
        db.create_all()
        _add_missing_columns(db)
        _seed_initial_data(app)

    @app.errorhandler(404)
    def not_found(e):
        return render_template("public/404.html"), 404

    @app.errorhandler(500)
    def server_error(e):
        return render_template("public/500.html"), 500

    return app


def _add_missing_columns(db):
    """Safely add any new columns to existing tables without requiring a full migration."""
    from sqlalchemy import text
    with db.engine.connect() as conn:
        try:
            with conn.begin_nested():
                conn.execute(text("ALTER TABLE user_bookings ADD COLUMN cancel_reason VARCHAR(500)"))
            conn.commit()
            print("\u2705 Added cancel_reason column to user_bookings")
        except Exception:
            pass
        # Each ALTER must run in its own savepoint/transaction for PostgreSQL compatibility
        new_cols = [
            ("contact_messages", "is_cancellation", "BOOLEAN DEFAULT FALSE"),
            ("contact_messages", "booking_id", "INTEGER"),
            ("contact_messages", "refund_status", "VARCHAR(30)"),
            ("contact_messages", "admin_reply", "TEXT"),
            ("contact_messages", "replied_at", "TIMESTAMP"),
        ]
        for table, col, col_type in new_cols:
            try:
                # Use a nested transaction (SAVEPOINT) so a failure on one column
                # doesn't abort the whole connection (critical for PostgreSQL)
                with conn.begin_nested():
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {col_type}"))
                conn.commit()
                print(f"\u2705 Added {col} column to {table}")
            except Exception:
                pass

def _seed_initial_data(app):
    from models.models import Role, AppUser
    roles_needed = ["admin", "theatre_owner", "user", "analyst"]
    for rname in roles_needed:
        if not Role.query.filter_by(name=rname).first():
            db.session.add(Role(name=rname))
    db.session.commit()

    # Create default admin
    admin_role = Role.query.filter_by(name="admin").first()
    if not AppUser.query.filter_by(email="admin@bookmyshow.com").first():
        admin = AppUser(
            name="Super Admin",
            email="admin@bookmyshow.com",
            role_id=admin_role.id,
            phone="9999999999",
            city="Mumbai",
            is_active=True
        )
        admin.set_password("Admin@123")
        db.session.add(admin)
        db.session.commit()
        print("✅ Default admin created: admin@bookmyshow.com / Admin@123")

    # Create default analyst
    analyst_role = Role.query.filter_by(name="analyst").first()
    if not AppUser.query.filter_by(email="analyst@bookmyshow.com").first():
        analyst = AppUser(
            name="Data Analyst",
            email="analyst@bookmyshow.com",
            role_id=analyst_role.id,
            phone="8888888888",
            city="Mumbai",
            is_active=True
        )
        analyst.set_password("Analyst@123")
        db.session.add(analyst)
        db.session.commit()
        print("✅ Default analyst created: analyst@bookmyshow.com / Analyst@123")


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, host="0.0.0.0", port=5000)
