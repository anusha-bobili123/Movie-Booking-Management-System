from database.db import db
from datetime import datetime, timezone, timedelta
from werkzeug.security import generate_password_hash, check_password_hash

# ── IST helper (UTC+5:30) ──
_IST = timezone(timedelta(hours=5, minutes=30))

def _now_ist():
    """Return current time in IST (India Standard Time, UTC+5:30) as a naive datetime for DB storage."""
    return datetime.now(_IST).replace(tzinfo=None)


# ──────────────── ROLES ────────────────
class Role(db.Model):
    __tablename__ = "roles"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)  # admin, theatre_owner, user
    created_at = db.Column(db.DateTime, default=_now_ist)
    users = db.relationship("AppUser", back_populates="role", lazy="dynamic")


# ──────────────── APP USERS (Auth) ────────────────
class AppUser(db.Model):
    __tablename__ = "app_users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey("roles.id"), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    phone = db.Column(db.String(20))
    city = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=_now_ist)
    updated_at = db.Column(db.DateTime, default=_now_ist, onupdate=_now_ist)

    role = db.relationship("Role", back_populates="users")
    owned_theatres = db.relationship("TheatreOwnership", back_populates="owner", lazy="dynamic")
    bookings = db.relationship("UserBooking", back_populates="user", lazy="dynamic")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def role_name(self):
        return self.role.name if self.role else None


# ──────────────── THEATRE OWNERSHIP (linking theatre_owner to theatres) ────────────────
class TheatreOwnership(db.Model):
    __tablename__ = "theatre_ownership"
    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.Integer, db.ForeignKey("app_users.id"))
    theatre_db_id = db.Column(db.String(20))  # links to dataset theaters.theater_id
    assigned_at = db.Column(db.DateTime, default=_now_ist)

    owner = db.relationship("AppUser", back_populates="owned_theatres")


# ──────────────── USER BOOKINGS (portal bookings) ────────────────
class UserBooking(db.Model):
    __tablename__ = "user_bookings"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("app_users.id"))
    show_id = db.Column(db.String(120), nullable=True)          # dataset shows.show_id
    movie_title = db.Column(db.String(200))
    theatre_name = db.Column(db.String(200))
    theatre_city = db.Column(db.String(100))
    show_date = db.Column(db.Date)
    show_time = db.Column(db.String(20))
    num_tickets = db.Column(db.Integer)
    total_amount = db.Column(db.Float)
    payment_method = db.Column(db.String(50), default="Online")
    status = db.Column(db.String(30), default="Confirmed")  # Confirmed, Cancelled
    booking_ref = db.Column(db.String(20), unique=True)
    booked_at = db.Column(db.DateTime, default=_now_ist)
    seat_numbers = db.Column(db.String(200))
    cancel_reason = db.Column(db.String(500), nullable=True)

    user = db.relationship("AppUser", back_populates="bookings")


# ──────────────── CONTACT MESSAGES ────────────────
class ContactMessage(db.Model):
    __tablename__ = "contact_messages"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), nullable=False)
    message = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(30), default="New")  # New, Read, Responded
    created_at = db.Column(db.DateTime, default=_now_ist)
    updated_at = db.Column(db.DateTime, default=_now_ist, onupdate=_now_ist)
    # Cancellation-specific fields
    is_cancellation = db.Column(db.Boolean, default=False)
    booking_id = db.Column(db.Integer, db.ForeignKey("user_bookings.id"), nullable=True)
    refund_status = db.Column(db.String(30), default=None, nullable=True)  # None, Pending, Refunded
    admin_reply = db.Column(db.Text, nullable=True)
    replied_at = db.Column(db.DateTime, nullable=True)

    booking = db.relationship("UserBooking", foreign_keys=[booking_id], lazy="joined")
