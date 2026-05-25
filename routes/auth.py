from flask import Blueprint, render_template, redirect, url_for, session, request, flash, jsonify
from models.models import AppUser, Role, db
from functools import wraps
import random, string, smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import current_app

auth_bp = Blueprint("auth", __name__)

# In-memory OTP store: {email: otp_string}
_otp_store = {}

def _send_otp_email(to_email, otp):
    """Send OTP to user email via SMTP."""
    try:
        username = current_app.config.get("MAIL_USERNAME")
        password = current_app.config.get("MAIL_PASSWORD")
        server_host = current_app.config.get("MAIL_SERVER", "smtp.gmail.com")
        server_port = current_app.config.get("MAIL_PORT", 587)

        msg = MIMEMultipart("alternative")
        msg["Subject"] = "🎬 CineVerse – Your Password Reset OTP"
        msg["From"] = username
        msg["To"] = to_email

        html = f"""
        <div style="font-family:Arial,sans-serif;max-width:480px;margin:0 auto;background:#0d0d1a;color:#fff;border-radius:16px;overflow:hidden;">
          <div style="background:linear-gradient(135deg,#e50914,#b00000);padding:28px;text-align:center;">
            <h1 style="margin:0;font-size:26px;letter-spacing:3px;">🎬 CineVerse</h1>
            <p style="margin:6px 0 0;font-size:13px;opacity:.85;">Password Reset OTP</p>
          </div>
          <div style="padding:32px 28px;">
            <p style="color:rgba(255,255,255,0.7);font-size:14px;">Use the OTP below to reset your password. It expires in <strong>10 minutes</strong>.</p>
            <div style="background:rgba(229,9,20,0.12);border:2px dashed #e50914;border-radius:12px;padding:20px;text-align:center;margin:20px 0;">
              <div style="font-size:36px;font-weight:900;letter-spacing:8px;color:#e50914;">{otp}</div>
            </div>
            <p style="color:rgba(255,255,255,0.4);font-size:12px;">If you did not request this, please ignore this email.</p>
          </div>
          <div style="background:rgba(255,255,255,0.04);padding:14px;text-align:center;font-size:11px;color:rgba(255,255,255,0.3);">
            CineVerse &bull; support@cineverse.com
          </div>
        </div>
        """

        msg.attach(MIMEText(html, "html"))
        with smtplib.SMTP(server_host, server_port) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.login(username, password)
            smtp.sendmail(username, to_email, msg.as_string())
        return True
    except Exception as e:
        current_app.logger.error(f"OTP email error: {e}")
        return False

def _send_welcome_email(to_email, name, password):
    """Send welcome email with login credentials after signup."""
    try:
        username = current_app.config.get("MAIL_USERNAME")
        mail_password = current_app.config.get("MAIL_PASSWORD")
        server_host = current_app.config.get("MAIL_SERVER", "smtp.gmail.com")
        server_port = int(current_app.config.get("MAIL_PORT", 587))

        if not username or not mail_password:
            return False

        msg = MIMEMultipart("alternative")
        msg["Subject"] = "🎬 Welcome to CineVerse – Your Account Credentials"
        msg["From"] = f"CineVerse <{username}>"
        msg["To"] = to_email

        html = f"""
        <div style="font-family:Arial,sans-serif;max-width:520px;margin:0 auto;background:#0d0d1a;color:#fff;border-radius:16px;overflow:hidden;">
          <div style="background:linear-gradient(135deg,#e50914,#b00000);padding:30px;text-align:center;">
            <h1 style="margin:0;font-size:28px;letter-spacing:3px;">🎬 CineVerse</h1>
            <p style="margin:8px 0 0;font-size:13px;opacity:.85;">Welcome! Your account is ready.</p>
          </div>
          <div style="padding:32px 28px;">
            <p style="font-size:16px;margin-bottom:6px;">Hi <strong>{name}</strong> 👋</p>
            <p style="color:rgba(255,255,255,0.65);font-size:14px;line-height:1.6;">
              Your CineVerse account has been created successfully. Here are your login credentials:
            </p>
            <div style="background:rgba(229,9,20,0.10);border:1.5px solid rgba(229,9,20,0.35);border-radius:12px;padding:22px 24px;margin:22px 0;">
              <table style="width:100%;font-size:14px;border-collapse:collapse;">
                <tr>
                  <td style="color:rgba(255,255,255,0.45);padding:8px 0;width:40%;">Email</td>
                  <td style="color:#fff;font-weight:700;padding:8px 0;">{to_email}</td>
                </tr>
                <tr>
                  <td style="color:rgba(255,255,255,0.45);padding:8px 0;border-top:1px solid rgba(255,255,255,0.06);">Password</td>
                  <td style="color:#FF6B35;font-weight:700;letter-spacing:1px;padding:8px 0;border-top:1px solid rgba(255,255,255,0.06);font-family:monospace;font-size:15px;">{password}</td>
                </tr>
              </table>
            </div>
            <p style="color:rgba(255,255,255,0.5);font-size:12px;line-height:1.7;">
              🔒 Please keep your credentials safe. You can change your password anytime from your profile settings.<br>
              Do not share your password with anyone.
            </p>
            <div style="text-align:center;margin-top:24px;">
              <a href="#" style="background:linear-gradient(135deg,#e50914,#b00000);color:#fff;text-decoration:none;padding:12px 32px;border-radius:8px;font-weight:700;font-size:14px;">Book Your First Movie 🍿</a>
            </div>
          </div>
          <div style="background:rgba(255,255,255,0.04);padding:14px;text-align:center;font-size:11px;color:rgba(255,255,255,0.3);">
            CineVerse &bull; Book movies, create memories
          </div>
        </div>
        """

        msg.attach(MIMEText(html, "html"))
        import ssl as _ssl
        ctx = _ssl.create_default_context()
        with smtplib.SMTP(server_host, server_port) as smtp:
            smtp.ehlo()
            smtp.starttls(context=ctx)
            smtp.login(username, mail_password)
            smtp.sendmail(username, to_email, msg.as_string())
        return True
    except Exception as e:
        current_app.logger.warning(f"Welcome email failed: {e}")
        return False


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            flash("Please login to continue.", "warning")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated

def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if "user_id" not in session:
                return redirect(url_for("auth.login"))
            if session.get("role") not in roles:
                flash("Access denied.", "danger")
                return redirect(url_for("public.home"))
            return f(*args, **kwargs)
        return decorated
    return decorator

# ── Routes ──────────────────────────────────────────────────
@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return _redirect_by_role(session.get("role"))

    if request.method == "POST":
        data = request.get_json() if request.is_json else request.form
        email = data.get("email", "").strip().lower()
        password = data.get("password", "")

        user = AppUser.query.filter_by(email=email, is_active=True).first()
        if user and user.check_password(password):
            session["user_id"] = user.id
            session["user_name"] = user.name
            session["role"] = user.role_name
            session["user_email"] = user.email

            if request.is_json:
                return jsonify({"success": True, "role": user.role_name, "redirect": _get_redirect_url(user.role_name)})
            return _redirect_by_role(user.role_name)

        if request.is_json:
            return jsonify({"success": False, "message": "Invalid email or password."}), 401
        flash("Invalid email or password.", "danger")

    return render_template("auth/login.html")


@auth_bp.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        data = request.get_json() if request.is_json else request.form
        name = data.get("name", "").strip()
        email = data.get("email", "").strip().lower()
        password = data.get("password", "")
        phone = data.get("phone", "")
        city = data.get("city", "")

        if AppUser.query.filter_by(email=email).first():
            msg = "Email already registered."
            if request.is_json:
                return jsonify({"success": False, "message": msg}), 400
            flash(msg, "danger")
            return render_template("auth/signup.html")

        user_role = Role.query.filter_by(name="user").first()
        if not user_role:
            user_role = Role(name="user")
            db.session.add(user_role)
            db.session.commit()

        user = AppUser(name=name, email=email, role_id=user_role.id, phone=phone, city=city)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        # Send welcome email with credentials
        try:
            _send_welcome_email(email, name, password)
        except Exception:
            pass  # Don't break signup if email fails

        session["user_id"] = user.id
        session["user_name"] = user.name
        session["role"] = "user"
        session["user_email"] = user.email

        if request.is_json:
            return jsonify({
                "success": True,
                "redirect": url_for("public.home"),
                "message": "Account created! Please check your email for your login credentials."
            })
        flash("🎉 Account created successfully! Please check your email for your login credentials.", "success")
        return redirect(url_for("public.home"))

    return render_template("auth/signup.html")


@auth_bp.route("/auth/send-otp", methods=["POST"])
def send_otp():
    data = request.get_json()
    email = (data.get("email") or "").strip().lower()
    if not email:
        return jsonify({"success": False, "message": "Email is required."}), 400
    user = AppUser.query.filter_by(email=email, is_active=True).first()
    if not user:
        return jsonify({"success": False, "message": "Email not found."}), 404

    otp = str(random.randint(100000, 999999))
    _otp_store[email] = otp

    sent = _send_otp_email(email, otp)
    if sent:
        return jsonify({"success": True, "message": f"OTP sent to {email}."})
    else:
        # Fallback: log it so dev can test without real SMTP
        current_app.logger.warning(f"[DEV OTP] {email} → {otp}")
        return jsonify({"success": True, "message": f"OTP sent to {email}. (Check server logs if email fails)"})


@auth_bp.route("/auth/verify-otp", methods=["POST"])
def verify_otp():
    data = request.get_json()
    email = (data.get("email") or "").strip().lower()
    entered = (data.get("otp") or "").strip()
    stored = _otp_store.get(email)
    if stored and stored == entered:
        del _otp_store[email]
        return jsonify({"success": True})
    return jsonify({"success": False, "message": "Invalid or expired OTP."}), 400


@auth_bp.route("/reset-password-otp", methods=["POST"])
@auth_bp.route("/auth/reset-password-otp", methods=["POST"])
def reset_password_otp():
    data = request.get_json()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password", "")
    if not email or not password or len(password) < 6:
        return jsonify({"success": False, "message": "Invalid request."}), 400
    user = AppUser.query.filter_by(email=email, is_active=True).first()
    if not user:
        return jsonify({"success": False, "message": "Email not found."}), 404
    user.set_password(password)
    db.session.commit()
    return jsonify({"success": True, "message": "Password reset successfully."})


@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully.", "success")
    return redirect(url_for("public.home"))


def _get_redirect_url(role):
    if role == "admin":
        return url_for("admin.dashboard")
    elif role == "theatre_owner":
        return url_for("theatre_owner.dashboard")
    elif role == "analyst":
        return url_for("analyst.dashboard")
    return url_for("public.home")

def _redirect_by_role(role):
    return redirect(_get_redirect_url(role))
