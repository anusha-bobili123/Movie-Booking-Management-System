from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, flash, current_app
from routes.auth import login_required, role_required
from models.models import AppUser, Role, TheatreOwnership, db
from sqlalchemy import text
import random, string, secrets, smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


def gen_password(length=10):
    chars = string.ascii_letters + string.digits + "!@#$"
    return ''.join(secrets.choice(chars) for _ in range(length))


def send_credentials_email(to_email, owner_name, login_email, password):
    try:
        mail_user = current_app.config.get("MAIL_USERNAME")
        mail_pass = current_app.config.get("MAIL_PASSWORD")
        mail_server = current_app.config.get("MAIL_SERVER", "smtp.gmail.com")
        mail_port = current_app.config.get("MAIL_PORT", 587)
        login_url = "https://bookmyshow.com/login"
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "Your BookMyShow Theatre Owner Account Credentials"
        msg["From"] = mail_user
        msg["To"] = to_email
        html_body = f"""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Theatre Owner Account Credentials</title>
</head>
<body style="margin:0;padding:0;background-color:#1a1a2e;font-family:'Segoe UI',Arial,sans-serif;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0"
         style="background-color:#1a1a2e;min-height:100vh;padding:40px 0;">
    <tr>
      <td align="center">
        <table role="presentation" width="520" cellspacing="0" cellpadding="0"
               style="background-color:#12121f;border-radius:16px;overflow:hidden;
                      box-shadow:0 8px 32px rgba(0,0,0,0.5);">

          <!-- HEADER BANNER -->
          <tr>
            <td style="background:linear-gradient(135deg,#e63946 0%,#c1121f 100%);
                        padding:32px 36px;text-align:center;">
              <div style="font-size:28px;margin-bottom:6px;">🎬</div>
              <div style="font-family:'Bebas Neue',Arial,sans-serif;
                          font-size:32px;font-weight:700;color:#ffffff;
                          letter-spacing:2px;line-height:1;">BookMyShow</div>
              <div style="color:rgba(255,255,255,0.85);font-size:13px;
                          margin-top:6px;letter-spacing:1px;">Theatre Owner Account Created</div>
            </td>
          </tr>

          <!-- BODY -->
          <tr>
            <td style="padding:36px 36px 28px;">
              <p style="margin:0 0 8px;color:#cccccc;font-size:15px;">Hello <strong style="color:#ffffff;">{owner_name}</strong>,</p>
              <p style="margin:0 0 28px;color:#aaaaaa;font-size:14px;line-height:1.6;">
                Your Theatre Owner account has been created. Use the credentials below to login:
              </p>

              <!-- CREDENTIALS BOX -->
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0"
                     style="background-color:#1e1e35;border-radius:12px;
                            border-left:4px solid #e63946;overflow:hidden;">
                <tr>
                  <td style="padding:20px 24px;">
                    <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
                      <tr>
                        <td style="padding:6px 0;">
                          <span style="color:#888888;font-size:12px;font-weight:600;
                                       text-transform:uppercase;letter-spacing:1px;">Login URL</span><br>
                          <a href="{login_url}"
                             style="color:#e63946;font-size:14px;text-decoration:none;
                                    font-weight:600;">{login_url}</a>
                        </td>
                      </tr>
                      <tr>
                        <td style="padding:6px 0;border-top:1px solid #2a2a45;">
                          <span style="color:#888888;font-size:12px;font-weight:600;
                                       text-transform:uppercase;letter-spacing:1px;">Email</span><br>
                          <span style="color:#4da6ff;font-size:14px;font-weight:600;">{login_email}</span>
                        </td>
                      </tr>
                      <tr>
                        <td style="padding:6px 0;border-top:1px solid #2a2a45;">
                          <span style="color:#888888;font-size:12px;font-weight:600;
                                       text-transform:uppercase;letter-spacing:1px;">Password</span><br>
                          <span style="background:#2a2a45;color:#ffffff;font-size:15px;
                                       font-family:'Courier New',monospace;font-weight:700;
                                       padding:4px 12px;border-radius:6px;
                                       display:inline-block;margin-top:4px;
                                       letter-spacing:1px;">{password}</span>
                        </td>
                      </tr>
                    </table>
                  </td>
                </tr>
              </table>

              <!-- SECURITY NOTE -->
              <p style="margin:24px 0 0;color:#888888;font-size:13px;line-height:1.6;">
                🔒 Please change your password after first login for security.
              </p>
              <p style="margin:8px 0 0;color:#888888;font-size:13px;line-height:1.6;">
                If you have questions, contact your administrator.
              </p>
            </td>
          </tr>

          <!-- FOOTER -->
          <tr>
            <td style="background-color:#0d0d1a;padding:20px 36px;text-align:center;
                        border-top:1px solid #2a2a45;">
              <p style="margin:0;color:#555566;font-size:12px;">
                © 2025 BookMyShow · This is an automated message, please do not reply.
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>
        """
        msg.attach(MIMEText(html_body, "html"))
        with smtplib.SMTP(mail_server, mail_port) as server:
            server.starttls()
            server.login(mail_user, mail_pass)
            server.sendmail(mail_user, to_email, msg.as_string())
        return True
    except Exception as e:
        current_app.logger.error(f"Email send failed: {e}")
        return False


# ── Dashboard ────────────────────────────────────────────────
@admin_bp.route("/")
@login_required
@role_required("admin")
def dashboard():
    from models.models import UserBooking
    stats = {}
    try:
        stats["total_movies"]   = db.session.execute(text("SELECT COUNT(*) FROM movies")).scalar() or 0
        stats["total_theatres"] = db.session.execute(text("SELECT COUNT(*) FROM theaters")).scalar() or 0
        stats["total_shows"]    = db.session.execute(text("SELECT COUNT(*) FROM shows")).scalar() or 0
        stats["total_users"]    = db.session.execute(text("SELECT COUNT(*) FROM users")).scalar() or 0
        stats["total_screens"]  = db.session.execute(text("SELECT COUNT(*) FROM screens")).scalar() or 0
    except:
        stats = {"total_movies": 0, "total_theatres": 0, "total_shows": 0, "total_users": 0, "total_screens": 0}
    stats["app_users"]            = AppUser.query.count()
    stats["total_bookings"]       = UserBooking.query.count()
    stats["total_revenue"]        = int(db.session.query(db.func.sum(UserBooking.total_amount)).scalar() or 0)
    stats["theatre_owners_count"] = AppUser.query.join(Role).filter(Role.name == "theatre_owner").count()

    # Top movies by show count
    try:
        top_movies = db.session.execute(text("""
            SELECT m.title, COUNT(s.show_id) as show_count
            FROM movies m JOIN shows s ON s.movie_id = m.movie_id
            GROUP BY m.title ORDER BY show_count DESC LIMIT 5
        """)).fetchall()
    except:
        top_movies = []

    # Top cities by theatre count
    try:
        top_cities = db.session.execute(text("""
            SELECT city, COUNT(*) as cnt FROM theaters GROUP BY city ORDER BY cnt DESC LIMIT 5
        """)).fetchall()
    except:
        top_cities = []

    # Genre distribution
    try:
        genre_dist = db.session.execute(text("""
            SELECT genre, COUNT(*) as cnt FROM movies WHERE genre IS NOT NULL GROUP BY genre ORDER BY cnt DESC LIMIT 8
        """)).fetchall()
    except:
        genre_dist = []

    theatre_owners = AppUser.query.join(Role).filter(Role.name == "theatre_owner").all()

    try:
        top_theatres_screens = db.session.execute(text("""
            SELECT t.theater_id, t.name, t.city, COUNT(sc.screen_id) as screen_count
            FROM theaters t LEFT JOIN screens sc ON sc.theater_id = t.theater_id
            GROUP BY t.theater_id, t.name, t.city ORDER BY screen_count DESC LIMIT 6
        """)).fetchall()
    except:
        top_theatres_screens = []

    return render_template("admin/dashboard.html",
        stats=stats, top_movies=top_movies, top_cities=top_cities,
        genre_dist=genre_dist, theatre_owners=theatre_owners,
        top_theatres_screens=top_theatres_screens
    )


# ── Movies Management ────────────────────────────────────────
@admin_bp.route("/movies")
@login_required
@role_required("admin")
def movies():
    page = request.args.get("page", 1, type=int)
    search = request.args.get("search", "")
    per_page = 15
    offset = (page - 1) * per_page

    params = {"limit": per_page, "offset": offset}
    where = "WHERE 1=1"
    if search:
        where += " AND title ILIKE :search"
        params["search"] = f"%{search}%"

    total = db.session.execute(text(f"SELECT COUNT(*) FROM movies {where}"), params).scalar() or 0
    movie_list = db.session.execute(
        text(f"SELECT * FROM movies {where} ORDER BY title LIMIT :limit OFFSET :offset"), params
    ).fetchall()
    total_pages = max(1, (total + per_page - 1) // per_page)

    return render_template("admin/movies.html", movies=movie_list, total=total,
        page=page, total_pages=total_pages, search=search)


# ── Theatres Management ──────────────────────────────────────
@admin_bp.route("/theatres")
@login_required
@role_required("admin")
def theatres():
    page = request.args.get("page", 1, type=int)
    city_filter = request.args.get("city", "")
    per_page = 15
    offset = (page - 1) * per_page

    params = {"limit": per_page, "offset": offset}
    where = "WHERE 1=1"
    if city_filter:
        where += " AND t.city ILIKE :city"
        params["city"] = f"%{city_filter}%"

    total = db.session.execute(text(f"SELECT COUNT(*) FROM theaters t {where}"), params).scalar() or 0
    theatre_list = db.session.execute(text(f"""
        SELECT t.*, COUNT(DISTINCT s.screen_id) as screen_count,
               COUNT(DISTINCT sh.show_id) as show_count
        FROM theaters t
        LEFT JOIN screens s ON s.theater_id = t.theater_id
        LEFT JOIN shows sh ON sh.theater_id = t.theater_id
        {where}
        GROUP BY t.theater_id, t.name, t.location, t.city, t.state
        ORDER BY t.name LIMIT :limit OFFSET :offset
    """), params).fetchall()
    total_pages = max(1, (total + per_page - 1) // per_page)

    cities = [r[0] for r in db.session.execute(text("SELECT DISTINCT city FROM theaters ORDER BY city")).fetchall()]
    theatre_owners = AppUser.query.join(Role).filter(Role.name == "theatre_owner").all()

    return render_template("admin/theatres.html", theatres=theatre_list, total=total,
        page=page, total_pages=total_pages, cities=cities, city_filter=city_filter,
        theatre_owners=theatre_owners)


# ── Theatre Owners ───────────────────────────────────────────
@admin_bp.route("/theatre-owners")
@login_required
@role_required("admin")
def theatre_owners():
    owners = AppUser.query.join(Role).filter(Role.name == "theatre_owner").all()
    return render_template("admin/theatre_owners.html", owners=owners)


@admin_bp.route("/theatre-owners/create", methods=["POST"])
@login_required
@role_required("admin")
def create_theatre_owner():
    data = request.get_json()
    name = data.get("name", "").strip()
    email = data.get("email", "").strip().lower()
    phone = data.get("phone", "")
    city = data.get("city", "")

    if AppUser.query.filter_by(email=email).first():
        return jsonify({"success": False, "message": "Email already exists."}), 400

    owner_role = Role.query.filter_by(name="theatre_owner").first()
    if not owner_role:
        owner_role = Role(name="theatre_owner")
        db.session.add(owner_role)
        db.session.commit()

    password = gen_password()
    user = AppUser(name=name, email=email, role_id=owner_role.id, phone=phone, city=city)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    email_sent = send_credentials_email(email, name, email, password)

    return jsonify({
        "success": True,
        "message": "Theatre owner created successfully. Login credentials have been sent to the owner's email address.",
        "email_sent": email_sent
    })


@admin_bp.route("/theatre-owners/<int:owner_id>/assign-theatre", methods=["POST"])
@login_required
@role_required("admin")
def assign_theatre(owner_id):
    data = request.get_json()
    theatre_id = data.get("theatre_id")       # single theatre id OR "chain:PVR"
    theatre_ids = data.get("theatre_ids", [])  # list of ids for chain assignment

    # Chain assignment: assign ALL theatres in the chain at once
    if theatre_ids:
        assigned_count = 0
        skipped_count = 0
        for tid in theatre_ids:
            existing = TheatreOwnership.query.filter_by(owner_id=owner_id, theatre_db_id=tid).first()
            if not existing:
                db.session.add(TheatreOwnership(owner_id=owner_id, theatre_db_id=tid))
                assigned_count += 1
            else:
                skipped_count += 1
        db.session.commit()
        msg = f"{assigned_count} theatre(s) assigned successfully."
        if skipped_count:
            msg += f" ({skipped_count} already assigned, skipped.)"
        return jsonify({"success": True, "message": msg, "assigned_count": assigned_count})

    # Single theatre assignment
    existing = TheatreOwnership.query.filter_by(owner_id=owner_id, theatre_db_id=theatre_id).first()
    if existing:
        return jsonify({"success": False, "message": "Theatre already assigned to this owner."})

    ownership = TheatreOwnership(owner_id=owner_id, theatre_db_id=theatre_id)
    db.session.add(ownership)
    db.session.commit()
    return jsonify({"success": True, "message": "Theatre assigned successfully."})


@admin_bp.route("/theatre-owners/<int:owner_id>/theatres", methods=["GET"])
@login_required
@role_required("admin")
def get_owner_theatres(owner_id):
    ownerships = TheatreOwnership.query.filter_by(owner_id=owner_id).all()
    assigned_ids = [o.theatre_db_id for o in ownerships]
    if not assigned_ids:
        return jsonify({"assigned": []})
    placeholder = ",".join([f"'{tid}'" for tid in assigned_ids])
    theatres = db.session.execute(text(f"""
        SELECT theater_id, name, city, state, location
        FROM theaters WHERE theater_id IN ({placeholder}) ORDER BY name
    """)).fetchall()
    return jsonify({"assigned": [
        {"id": t.theater_id, "name": t.name, "city": t.city, "state": t.state, "location": t.location}
        for t in theatres
    ]})


@admin_bp.route("/theatre-owners/<int:owner_id>/unassign-theatre", methods=["POST"])
@login_required
@role_required("admin")
def unassign_theatre(owner_id):
    data = request.get_json()
    theatre_id = data.get("theatre_id")
    ownership = TheatreOwnership.query.filter_by(owner_id=owner_id, theatre_db_id=theatre_id).first()
    if not ownership:
        return jsonify({"success": False, "message": "Assignment not found."})
    db.session.delete(ownership)
    db.session.commit()
    return jsonify({"success": True, "message": "Theatre unassigned successfully."})


@admin_bp.route("/theatre-owners/<int:owner_id>/deactivate", methods=["POST"])
@login_required
@role_required("admin")
def deactivate_owner(owner_id):
    user = AppUser.query.get_or_404(owner_id)
    user.is_active = not user.is_active
    db.session.commit()
    status = "activated" if user.is_active else "deactivated"
    return jsonify({"success": True, "message": f"Owner {status}.", "is_active": user.is_active})


# ── Shows Management ─────────────────────────────────────────
@admin_bp.route("/shows")
@login_required
@role_required("admin")
def shows():
    page = request.args.get("page", 1, type=int)
    per_page = 15
    offset = (page - 1) * per_page

    total = db.session.execute(text("SELECT COUNT(*) FROM shows")).scalar() or 0
    show_list = db.session.execute(text("""
        SELECT s.show_id, s.show_date, s.start_time, s.price_per_ticket, s.available_seats,
               m.title as movie_title, t.name as theatre_name, t.city,
               sc.screen_number
        FROM shows s
        JOIN movies m ON m.movie_id = s.movie_id
        JOIN theaters t ON t.theater_id = s.theater_id
        JOIN screens sc ON sc.screen_id = s.screen_id
        ORDER BY s.show_date DESC, s.start_time
        LIMIT :limit OFFSET :offset
    """), {"limit": per_page, "offset": offset}).fetchall()
    total_pages = max(1, (total + per_page - 1) // per_page)

    return render_template("admin/shows.html", shows=show_list, total=total,
        page=page, total_pages=total_pages)


# ── Users ────────────────────────────────────────────────────
@admin_bp.route("/users")
@login_required
@role_required("admin")
def users():
    app_users = AppUser.query.order_by(AppUser.created_at.desc()).all()
    return render_template("admin/users.html", users=app_users)


# ── API: Theatre list for dropdown ──────────────────────────
@admin_bp.route("/api/theatres-list")
@login_required
@role_required("admin")
def api_theatres_list():
    # Return chain-grouped theatres: each entry represents a chain (e.g. "PVR") with all its theatres
    theatres = db.session.execute(text(
        "SELECT theater_id, name, city, state, location FROM theaters ORDER BY name"
    )).fetchall()

    # Detect chain by common prefixes in the name
    CHAINS = ["PVR", "INOX", "Cinepolis", "Carnival", "Miraj", "Movietime", "Wave", "SPI", "Fun Cinemas", "Cinemax", "Big Cinemas", "DT Cinemas", "Mövenpick", "Mövie"]

    def get_chain(name):
        name_upper = name.upper()
        for chain in CHAINS:
            if name_upper.startswith(chain.upper()):
                return chain
        return None

    # Group theatres by chain, standalone theatres kept individually
    from collections import defaultdict
    chain_groups = defaultdict(list)
    standalone = []

    for t in theatres:
        chain = get_chain(t.name)
        if chain:
            chain_groups[chain].append({
                "id": t.theater_id, "name": t.name,
                "city": t.city, "state": t.state, "location": t.location
            })
        else:
            standalone.append({
                "id": t.theater_id, "name": t.name,
                "city": t.city, "state": t.state, "location": t.location,
                "is_chain": False, "chain_name": None, "theatre_ids": [t.theater_id]
            })

    result = []
    # Add chain groups as single selectable items
    for chain_name, chain_theatres in sorted(chain_groups.items()):
        cities = sorted(set(t["city"] for t in chain_theatres if t["city"]))
        result.append({
            "id": f"chain:{chain_name}",
            "name": chain_name,
            "city": f"{len(chain_theatres)} locations · " + ", ".join(cities[:3]) + ("…" if len(cities) > 3 else ""),
            "is_chain": True,
            "chain_name": chain_name,
            "theatre_ids": [t["id"] for t in chain_theatres],
            "theatre_count": len(chain_theatres)
        })
    # Add standalone theatres
    result.extend(standalone)
    return jsonify(result)


@admin_bp.route("/api/theatres-by-chain/<chain_name>")
@login_required
@role_required("admin")
def api_theatres_by_chain(chain_name):
    """Return all theatre IDs for a given chain name."""
    theatres = db.session.execute(text(
        "SELECT theater_id, name, city FROM theaters WHERE UPPER(name) LIKE :prefix ORDER BY name"
    ), {"prefix": chain_name.upper() + "%"}).fetchall()
    return jsonify([{"id": t.theater_id, "name": t.name, "city": t.city} for t in theatres])


# ── DELETE: Movie ────────────────────────────────────────────
@admin_bp.route("/movies/<movie_id>/delete", methods=["POST"])
@login_required
@role_required("admin")
def delete_movie(movie_id):
    try:
        db.session.execute(text("DELETE FROM shows WHERE movie_id = :id"), {"id": movie_id})
        db.session.execute(text("DELETE FROM movies WHERE movie_id = :id"), {"id": movie_id})
        db.session.commit()
        return jsonify({"success": True, "message": "Movie deleted successfully."})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


# ── DELETE: Show ─────────────────────────────────────────────
@admin_bp.route("/shows/<show_id>/delete", methods=["POST"])
@login_required
@role_required("admin")
def delete_show(show_id):
    try:
        db.session.execute(text("DELETE FROM shows WHERE show_id = :id"), {"id": show_id})
        db.session.commit()
        return jsonify({"success": True, "message": "Show deleted successfully."})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


# ── DELETE: Theatre ──────────────────────────────────────────
@admin_bp.route("/theatres/<theatre_id>/delete", methods=["POST"])
@login_required
@role_required("admin")
def delete_theatre(theatre_id):
    try:
        db.session.execute(text("DELETE FROM shows WHERE theater_id = :id"), {"id": theatre_id})
        db.session.execute(text("DELETE FROM screens WHERE theater_id = :id"), {"id": theatre_id})
        db.session.execute(text("DELETE FROM theaters WHERE theater_id = :id"), {"id": theatre_id})
        db.session.commit()
        return jsonify({"success": True, "message": "Theatre deleted successfully."})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


# ── DELETE: Theatre Owner ────────────────────────────────────
@admin_bp.route("/theatre-owners/<int:owner_id>/delete", methods=["POST"])
@login_required
@role_required("admin")
def delete_owner(owner_id):
    try:
        user = AppUser.query.get_or_404(owner_id)
        TheatreOwnership.query.filter_by(owner_id=owner_id).delete()
        db.session.delete(user)
        db.session.commit()
        return jsonify({"success": True, "message": "Theatre owner deleted successfully."})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


# ── ADD: Movie ───────────────────────────────────────────────
@admin_bp.route("/movies/add", methods=["POST"])
@login_required
@role_required("admin")
def add_movie():
    data = request.get_json()
    try:
        movie_id = "M" + ''.join(secrets.choice(string.digits) for _ in range(8))
        db.session.execute(text("""
            INSERT INTO movies (movie_id, title, genre, language, duration, rating, release_date, description)
            VALUES (:movie_id, :title, :genre, :language, :duration, :rating, :release_date, :description)
        """), {
            "movie_id": movie_id,
            "title": data.get("title", "").strip(),
            "genre": data.get("genre", "").strip() or None,
            "language": data.get("language", "").strip() or None,
            "duration": int(data.get("duration", 0)) if data.get("duration") else None,
            "rating": float(data.get("rating", 0)) if data.get("rating") else None,
            "release_date": data.get("release_date") or None,
            "description": data.get("description", "").strip() or None,
        })
        db.session.commit()
        return jsonify({"success": True, "message": "Movie added successfully."})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


# ── ADD: Show ────────────────────────────────────────────────
@admin_bp.route("/shows/add", methods=["POST"])
@login_required
@role_required("admin")
def add_show():
    data = request.get_json()
    try:
        show_id = "SH" + ''.join(secrets.choice(string.digits) for _ in range(8))
        db.session.execute(text("""
            INSERT INTO shows (show_id, movie_id, theater_id, screen_id, show_date, start_time, price_per_ticket, available_seats)
            VALUES (:show_id, :movie_id, :theater_id, :screen_id, :show_date, :start_time, :price, :seats)
        """), {
            "show_id": show_id,
            "movie_id": data.get("movie_id"),
            "theater_id": data.get("theater_id"),
            "screen_id": data.get("screen_id"),
            "show_date": data.get("show_date"),
            "start_time": data.get("start_time"),
            "price": float(data.get("price", 0)),
            "seats": int(data.get("seats", 0)),
        })
        db.session.commit()
        return jsonify({"success": True, "message": "Show added successfully."})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


# ── ADD: Theatre ─────────────────────────────────────────────
@admin_bp.route("/theatres/add", methods=["POST"])
@login_required
@role_required("admin")
def add_theatre():
    data = request.get_json()
    try:
        theater_id = "T" + ''.join(secrets.choice(string.digits) for _ in range(8))
        db.session.execute(text("""
            INSERT INTO theaters (theater_id, name, location, city, state)
            VALUES (:theater_id, :name, :location, :city, :state)
        """), {
            "theater_id": theater_id,
            "name": data.get("name", "").strip(),
            "location": data.get("location", "").strip() or None,
            "city": data.get("city", "").strip() or None,
            "state": data.get("state", "").strip() or None,
        })
        db.session.commit()
        return jsonify({"success": True, "message": "Theatre added successfully."})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


# ── API: Movies list for dropdown ────────────────────────────
@admin_bp.route("/api/movies-list")
@login_required
@role_required("admin")
def api_movies_list():
    movies = db.session.execute(text("SELECT movie_id, title FROM movies ORDER BY title")).fetchall()
    return jsonify([{"id": m.movie_id, "title": m.title} for m in movies])


# ── API: Screens list for dropdown ───────────────────────────
@admin_bp.route("/api/screens-list")
@login_required
@role_required("admin")
def api_screens_list():
    theater_id = request.args.get("theater_id")
    if not theater_id:
        return jsonify([])
    screens = db.session.execute(
        text("SELECT screen_id, screen_number FROM screens WHERE theater_id = :tid ORDER BY screen_number"),
        {"tid": theater_id}
    ).fetchall()
    return jsonify([{"id": s.screen_id, "number": s.screen_number} for s in screens])


# ── Screens Management Page ─────────────────────────────────
@admin_bp.route("/screens")
@login_required
@role_required("admin")
def screens():
    theater_id = request.args.get("theater_id", "")
    theatres = db.session.execute(text("SELECT theater_id, name, city FROM theaters ORDER BY name")).fetchall()

    screens_list = []
    if theater_id:
        screens_list = db.session.execute(text("""
            SELECT sc.screen_id, sc.screen_number, sc.total_seats,
                   t.name as theatre_name, t.city,
                   COUNT(s.show_id) as show_count
            FROM screens sc
            JOIN theaters t ON t.theater_id = sc.theater_id
            LEFT JOIN shows s ON s.screen_id = sc.screen_id
            WHERE sc.theater_id = :tid
            GROUP BY sc.screen_id, sc.screen_number, sc.total_seats, t.name, t.city
            ORDER BY sc.screen_number
        """), {"tid": theater_id}).fetchall()
    else:
        screens_list = db.session.execute(text("""
            SELECT sc.screen_id, sc.screen_number, sc.total_seats,
                   t.name as theatre_name, t.city,
                   COUNT(s.show_id) as show_count
            FROM screens sc
            JOIN theaters t ON t.theater_id = sc.theater_id
            LEFT JOIN shows s ON s.screen_id = sc.screen_id
            GROUP BY sc.screen_id, sc.screen_number, sc.total_seats, t.name, t.city
            ORDER BY t.name, sc.screen_number
            LIMIT 50
        """)).fetchall()

    return render_template("admin/screens.html",
        screens=screens_list, theatres=theatres, selected_theatre=theater_id)


@admin_bp.route("/screens/add", methods=["POST"])
@login_required
@role_required("admin")
def add_screen():
    data = request.get_json()
    try:
        import uuid
        screen_id = "SC" + uuid.uuid4().hex[:8].upper()
        db.session.execute(text("""
            INSERT INTO screens (screen_id, theater_id, screen_number, total_seats)
            VALUES (:screen_id, :theater_id, :screen_number, :total_seats)
        """), {
            "screen_id": screen_id,
            "theater_id": data.get("theater_id"),
            "screen_number": data.get("screen_number", "Screen 1"),
            "total_seats": int(data.get("total_seats", 150)),
        })
        db.session.commit()
        return jsonify({"success": True, "message": "Screen added successfully.", "screen_id": screen_id})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


@admin_bp.route("/screens/<screen_id>/delete", methods=["POST"])
@login_required
@role_required("admin")
def delete_screen(screen_id):
    try:
        db.session.execute(text("DELETE FROM screens WHERE screen_id = :id"), {"id": screen_id})
        db.session.commit()
        return jsonify({"success": True, "message": "Screen deleted."})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


@admin_bp.route("/contact-messages")
@login_required
@role_required("admin")
def contact_messages():
    from models.models import ContactMessage
    page = request.args.get("page", 1, type=int)
    per_page = 10

    messages = ContactMessage.query.order_by(ContactMessage.created_at.desc()).paginate(page=page, per_page=per_page)

    return render_template("admin/contact_messages.html", messages=messages)


@admin_bp.route("/contact-messages/<int:msg_id>/mark-read", methods=["POST"])
@login_required
@role_required("admin")
def mark_message_read(msg_id):
    from models.models import ContactMessage
    try:
        message = ContactMessage.query.get_or_404(msg_id)
        message.status = "Read"
        db.session.commit()
        return jsonify({"success": True, "message": "Message marked as read."})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


@admin_bp.route("/contact-messages/<int:msg_id>/delete", methods=["POST"])
@login_required
@role_required("admin")
def delete_contact_message(msg_id):
    from models.models import ContactMessage
    try:
        message = ContactMessage.query.get_or_404(msg_id)
        db.session.delete(message)
        db.session.commit()
        return jsonify({"success": True, "message": "Message deleted."})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


@admin_bp.route("/contact-messages/<int:msg_id>/reply", methods=["POST"])
@login_required
@role_required("admin")
def reply_contact_message(msg_id):
    from models.models import ContactMessage
    from datetime import datetime
    try:
        message = ContactMessage.query.get_or_404(msg_id)
        data = request.get_json() or {}
        reply_text = data.get("reply", "").strip()
        if not reply_text:
            return jsonify({"success": False, "message": "Reply cannot be empty."}), 400

        message.admin_reply = reply_text
        message.replied_at = datetime.utcnow()
        message.status = "Responded"

        # Send email reply to the user
        mail_user = current_app.config.get("MAIL_USERNAME")
        mail_pass = current_app.config.get("MAIL_PASSWORD")
        mail_server = current_app.config.get("MAIL_SERVER", "smtp.gmail.com")
        mail_port = current_app.config.get("MAIL_PORT", 587)

        if mail_user and mail_pass:
            try:
                msg_email = MIMEMultipart("alternative")
                msg_email["Subject"] = "Response to Your CineVerse Query"
                msg_email["From"] = mail_user
                msg_email["To"] = message.email

                subject_line = "Response Regarding Your Cancellation Request" if message.is_cancellation else "Response to Your Inquiry"
                msg_email["Subject"] = subject_line

                html_body = f"""
                <html><body style="font-family:Arial,sans-serif;background:#f5f5f5;padding:20px;">
                <div style="max-width:600px;margin:auto;background:#fff;border-radius:10px;overflow:hidden;box-shadow:0 2px 10px rgba(0,0,0,0.1)">
                  <div style="background:#0F1419;padding:25px;text-align:center">
                    <h1 style="color:#FF6B35;margin:0;font-size:28px">CINEVERSE</h1>
                    <p style="color:#aaa;margin:5px 0 0">Support Team</p>
                  </div>
                  <div style="padding:30px">
                    <p style="color:#333">Dear <strong>{message.name}</strong>,</p>
                    <p style="color:#555">Thank you for reaching out. Here is our response to your message:</p>
                    <div style="background:#f9f9f9;border-left:4px solid #FF6B35;padding:15px 20px;border-radius:4px;margin:20px 0">
                      <p style="color:#333;margin:0;white-space:pre-wrap">{reply_text}</p>
                    </div>
                    <hr style="border:none;border-top:1px solid #eee;margin:20px 0">
                    <p style="color:#888;font-size:13px">Your original message:</p>
                    <div style="background:#f0f0f0;padding:12px 16px;border-radius:4px">
                      <p style="color:#666;font-size:13px;margin:0;white-space:pre-wrap">{message.message}</p>
                    </div>
                    <p style="color:#555;margin-top:25px">Best regards,<br><strong>CineVerse Support Team</strong></p>
                  </div>
                  <div style="background:#0F1419;padding:15px;text-align:center">
                    <p style="color:#666;font-size:12px;margin:0">&copy; 2025 CineVerse · This is an automated reply, please do not reply to this email.</p>
                  </div>
                </div>
                </body></html>
                """
                msg_email.attach(MIMEText(html_body, "html"))
                with smtplib.SMTP(mail_server, mail_port) as smtp:
                    smtp.ehlo()
                    smtp.starttls()
                    smtp.login(mail_user, mail_pass)
                    smtp.sendmail(mail_user, message.email, msg_email.as_string())
            except Exception as mail_err:
                current_app.logger.warning(f"Reply email failed: {mail_err}")

        db.session.commit()
        return jsonify({"success": True, "message": "Reply sent successfully."})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


@admin_bp.route("/contact-messages/<int:msg_id>/process-refund", methods=["POST"])
@login_required
@role_required("admin")
def process_refund(msg_id):
    from models.models import ContactMessage, UserBooking
    from datetime import datetime
    try:
        message = ContactMessage.query.get_or_404(msg_id)
        if not message.is_cancellation or not message.booking_id:
            return jsonify({"success": False, "message": "This is not a cancellation request."}), 400
        if message.refund_status == "Refunded":
            return jsonify({"success": False, "message": "Refund already processed."}), 400

        booking = UserBooking.query.get(message.booking_id)
        if not booking:
            return jsonify({"success": False, "message": "Booking not found."}), 404

        message.refund_status = "Refunded"
        message.status = "Responded"

        # ── Unlock the cancelled seats so they become bookable again ──
        # Only unlock seats when admin approves cancellation (this function)
        try:
            from routes.user import _seat_locks
            if booking.show_id and booking.seat_numbers:
                seat_part = booking.seat_numbers.split(" | Snacks:")[0].split(" | Cancel")[0]
                cancelled_seats = [s.strip() for s in seat_part.split(",") if s.strip()]
                show_id = booking.show_id
                if show_id in _seat_locks:
                    for seat in cancelled_seats:
                        _seat_locks[show_id].pop(seat, None)
            # Update available_seats in DB if it's a real show_id
            if booking.show_id and not booking.show_id.startswith(("GEN-", "DEMO-", "FILL-", "EXT-")):
                from sqlalchemy import text as _text
                seat_part = booking.seat_numbers.split(" | Snacks:")[0].split(" | Cancel")[0] if booking.seat_numbers else ""
                num_freed = len([s for s in seat_part.split(",") if s.strip()])
                if num_freed > 0:
                    db.session.execute(_text(
                        "UPDATE shows SET available_seats = available_seats + :n WHERE show_id = :sid"
                    ), {"n": num_freed, "sid": booking.show_id})
        except Exception as unlock_err:
            current_app.logger.warning(f"Seat unlock after cancel approval failed: {unlock_err}")

        # Send refund confirmation email to user
        mail_user = current_app.config.get("MAIL_USERNAME")
        mail_pass = current_app.config.get("MAIL_PASSWORD")
        mail_server = current_app.config.get("MAIL_SERVER", "smtp.gmail.com")
        mail_port = current_app.config.get("MAIL_PORT", 587)

        if mail_user and mail_pass:
            try:
                msg_email = MIMEMultipart("alternative")
                msg_email["Subject"] = "Refund Processed - CineVerse"
                msg_email["From"] = mail_user
                msg_email["To"] = message.email

                html_body = f"""
                <html><body style="font-family:Arial,sans-serif;background:#f5f5f5;padding:20px;">
                <div style="max-width:600px;margin:auto;background:#fff;border-radius:10px;overflow:hidden;box-shadow:0 2px 10px rgba(0,0,0,0.1)">
                  <div style="background:#0F1419;padding:25px;text-align:center">
                    <h1 style="color:#FF6B35;margin:0;font-size:28px">CINEVERSE</h1>
                  </div>
                  <div style="padding:30px">
                    <div style="text-align:center;margin-bottom:25px">
                      <div style="font-size:50px">✅</div>
                      <h2 style="color:#22c55e">Refund Approved!</h2>
                    </div>
                    <p style="color:#333">Dear <strong>{message.name}</strong>,</p>
                    <p style="color:#555">We are pleased to inform you that your refund has been processed successfully.</p>
                    <div style="background:#f0fff4;border:1px solid #22c55e;border-radius:8px;padding:20px;margin:20px 0">
                      <table style="width:100%;font-size:14px;color:#333">
                        <tr><td><strong>Booking Ref:</strong></td><td>{booking.booking_ref}</td></tr>
                        <tr><td><strong>Movie:</strong></td><td>{booking.movie_title}</td></tr>
                        <tr><td><strong>Refund Amount:</strong></td><td style="color:#22c55e;font-weight:bold;font-size:18px">&#8377;{booking.total_amount:.2f}</td></tr>
                        <tr><td><strong>Status:</strong></td><td><span style="color:#22c55e;font-weight:bold">APPROVED</span></td></tr>
                      </table>
                    </div>
                    <p style="color:#555">The refund of <strong>&#8377;{booking.total_amount:.2f}</strong> will be credited to your original payment method within <strong>5-7 business days</strong>.</p>
                    <p style="color:#555">We apologize for any inconvenience caused and hope to see you again at CineVerse!</p>
                    <p style="color:#555">Best regards,<br><strong>CineVerse Support Team</strong></p>
                  </div>
                  <div style="background:#0F1419;padding:15px;text-align:center">
                    <p style="color:#666;font-size:12px;margin:0">&copy; 2025 CineVerse · This is an automated message, please do not reply.</p>
                  </div>
                </div>
                </body></html>
                """
                msg_email.attach(MIMEText(html_body, "html"))
                with smtplib.SMTP(mail_server, mail_port) as smtp:
                    smtp.ehlo()
                    smtp.starttls()
                    smtp.login(mail_user, mail_pass)
                    smtp.sendmail(mail_user, message.email, msg_email.as_string())
            except Exception as mail_err:
                current_app.logger.warning(f"Refund email failed: {mail_err}")

        db.session.commit()
        return jsonify({
            "success": True,
            "message": f"Refund of ₹{booking.total_amount:.2f} processed successfully.",
            "refund_amount": booking.total_amount
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


@admin_bp.route("/analytics")
@login_required
@role_required("admin")
def analytics():
    from models.models import UserBooking
    from datetime import datetime, timedelta
    import json

    total_bookings = UserBooking.query.count()
    total_revenue = db.session.query(db.func.sum(UserBooking.total_amount)).scalar() or 0
    total_seats_booked = UserBooking.query.with_entities(db.func.sum(UserBooking.num_tickets)).scalar() or 0

    # 1. Bookings per day (last 30 days)
    last_30 = datetime.now() - timedelta(days=30)
    bookings_per_day = db.session.execute(text("""
        SELECT DATE(booked_at) as date, COUNT(*) as count
        FROM user_bookings WHERE booked_at >= :s GROUP BY DATE(booked_at) ORDER BY date
    """), {"s": last_30}).fetchall()

    # 2. Bookings by city
    city_bookings = db.session.execute(text("""
        SELECT theatre_city, COUNT(*) as count FROM user_bookings
        GROUP BY theatre_city ORDER BY count DESC LIMIT 10
    """)).fetchall()

    # 3. Peak booking hours
    peak_hours = db.session.execute(text("""
        SELECT LPAD(EXTRACT(HOUR FROM booked_at)::INTEGER::TEXT, 2, '0') as hour,
               COUNT(*) as count
        FROM user_bookings GROUP BY hour ORDER BY hour
    """)).fetchall()

    # 4. Bookings by time slot
    time_slots = db.session.execute(text("""
        SELECT CASE
            WHEN EXTRACT(HOUR FROM booked_at) < 12 THEN 'Morning'
            WHEN EXTRACT(HOUR FROM booked_at) < 17 THEN 'Afternoon'
            WHEN EXTRACT(HOUR FROM booked_at) < 20 THEN 'Evening'
            ELSE 'Night' END as slot, COUNT(*) as count
        FROM user_bookings GROUP BY slot ORDER BY MIN(EXTRACT(HOUR FROM booked_at))
    """)).fetchall()

    # 5. Top 10 movies by bookings
    top_movies = db.session.execute(text("""
        SELECT movie_title, COUNT(*) as count FROM user_bookings
        GROUP BY movie_title ORDER BY count DESC LIMIT 10
    """)).fetchall()

    # 6. Genre performance (proxy via movie title grouping — real genre from movies table if joined)
    genre_data = db.session.execute(text("""
        SELECT m.genre, COUNT(ub.id) as count
        FROM user_bookings ub
        LEFT JOIN movies m ON m.title = ub.movie_title
        WHERE m.genre IS NOT NULL
        GROUP BY m.genre ORDER BY count DESC LIMIT 8
    """)).fetchall()

    # 7. Movie trends over time (top 3 movies last 30 days)
    movie_trends = db.session.execute(text("""
        SELECT movie_title, DATE(booked_at) as date, COUNT(*) as count
        FROM user_bookings WHERE booked_at >= :s
        GROUP BY movie_title, DATE(booked_at) ORDER BY date
    """), {"s": last_30}).fetchall()

    # 9. Top theatres
    top_theatres = db.session.execute(text("""
        SELECT theatre_name, COUNT(*) as count FROM user_bookings
        GROUP BY theatre_name ORDER BY count DESC LIMIT 10
    """)).fetchall()

    # 10. Theatre bookings by city (grouped)
    theatre_city = db.session.execute(text("""
        SELECT theatre_name, theatre_city, COUNT(*) as count FROM user_bookings
        GROUP BY theatre_name, theatre_city ORDER BY count DESC LIMIT 12
    """)).fetchall()

    # 13. Revenue by movie
    revenue_movie = db.session.execute(text("""
        SELECT movie_title, SUM(total_amount) as revenue FROM user_bookings
        GROUP BY movie_title ORDER BY revenue DESC LIMIT 10
    """)).fetchall()

    # 14. Avg ticket price by city
    price_city = db.session.execute(text("""
        SELECT theatre_city, AVG(total_amount/num_tickets) as avg_price, COUNT(*) as cnt
        FROM user_bookings WHERE num_tickets > 0
        GROUP BY theatre_city ORDER BY avg_price DESC LIMIT 10
    """)).fetchall()

    # 15. Ticket price distribution
    price_dist = db.session.execute(text("""
        SELECT ROUND((total_amount/num_tickets/50)::numeric)*50 as bucket, COUNT(*) as cnt
        FROM user_bookings WHERE num_tickets > 0
        GROUP BY bucket ORDER BY bucket
    """)).fetchall()

    # 18. Payment methods (mock if column missing)
    try:
        payment_methods = db.session.execute(text("""
            SELECT payment_method, COUNT(*) as count FROM user_bookings
            WHERE payment_method IS NOT NULL GROUP BY payment_method
        """)).fetchall()
    except Exception:
        payment_methods = []

    # 20. Avg booking value distribution
    avg_booking = db.session.execute(text("""
        SELECT ROUND((total_amount/50)::numeric)*50 as bucket, COUNT(*) as cnt
        FROM user_bookings GROUP BY bucket ORDER BY bucket
    """)).fetchall()

    # ── Serialize rows to JSON for charts ──────────────────────────────────────
    # Handles date, datetime, Decimal and other non-serializable types automatically
    def serialize_value(v):
        if hasattr(v, 'isoformat'):      # date / datetime → "2026-05-04"
            return v.isoformat()
        if hasattr(v, '__float__'):      # Decimal → float
            return float(v)
        return v

    def rows_to_json(rows, *keys):
        return json.dumps([
            {k: serialize_value(getattr(r, k) if hasattr(r, k) else r[i])
             for i, k in enumerate(keys)}
            for r in rows
        ])
    # ───────────────────────────────────────────────────────────────────────────

    return render_template("admin/analytics.html",
        total_bookings=total_bookings,
        total_revenue=total_revenue,
        total_seats_booked=total_seats_booked,
        # JSON for charts
        j_bookings_per_day=rows_to_json(bookings_per_day, "date", "count"),
        j_city_bookings=rows_to_json(city_bookings, "theatre_city", "count"),
        j_peak_hours=rows_to_json(peak_hours, "hour", "count"),
        j_time_slots=rows_to_json(time_slots, "slot", "count"),
        j_top_movies=rows_to_json(top_movies, "movie_title", "count"),
        j_genre_data=rows_to_json(genre_data, "genre", "count"),
        j_top_theatres=rows_to_json(top_theatres, "theatre_name", "count"),
        j_theatre_city=rows_to_json(theatre_city, "theatre_name", "theatre_city", "count"),
        j_revenue_movie=rows_to_json(revenue_movie, "movie_title", "revenue"),
        j_price_city=rows_to_json(price_city, "theatre_city", "avg_price", "cnt"),
        j_price_dist=rows_to_json(price_dist, "bucket", "cnt"),
        j_payment_methods=rows_to_json(payment_methods, "payment_method", "count") if payment_methods else "[]",
        j_avg_booking=rows_to_json(avg_booking, "bucket", "cnt"),
    )