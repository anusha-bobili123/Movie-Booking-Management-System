from flask import Blueprint, render_template, request, jsonify, session
from routes.auth import login_required, role_required
from models.models import AppUser, TheatreOwnership, db
from sqlalchemy import text

theatre_owner_bp = Blueprint("theatre_owner", __name__, url_prefix="/theatre-owner")


def get_owner_theatre_ids():
    user_id = session.get("user_id")
    ownerships = TheatreOwnership.query.filter_by(owner_id=user_id).all()
    return [o.theatre_db_id for o in ownerships]


@theatre_owner_bp.route("/")
@login_required
@role_required("theatre_owner")
def dashboard():
    theatre_ids = get_owner_theatre_ids()
    stats = {"total_theatres": len(theatre_ids), "total_shows": 0, "total_bookings": 0, "total_revenue": 0, "total_screens": 0}
    theatres = []
    top_shows = []
    screens_summary = []
    movies_summary = []

    if theatre_ids:
        placeholder = ",".join([f"'{tid}'" for tid in theatre_ids])

        try:
            stats["total_shows"] = db.session.execute(text(f"""
                SELECT COUNT(*) FROM shows WHERE theater_id IN ({placeholder})
            """)).scalar() or 0

            stats["total_screens"] = db.session.execute(text(f"""
                SELECT COUNT(*) FROM screens WHERE theater_id IN ({placeholder})
            """)).scalar() or 0

            from models.models import UserBooking
            theatre_names = db.session.execute(text(f"""
                SELECT name FROM theaters WHERE theater_id IN ({placeholder})
            """)).fetchall()
            tnames = [r.name for r in theatre_names]
            if tnames:
                all_bookings = UserBooking.query.filter(UserBooking.theatre_name.in_(tnames)).all()
                stats["total_bookings"] = len(all_bookings)
                stats["total_revenue"]  = int(sum(b.total_amount for b in all_bookings if b.total_amount))

            theatres = db.session.execute(text(f"""
                SELECT t.*, COUNT(DISTINCT s.show_id) as show_count,
                       COUNT(DISTINCT sc.screen_id) as screen_count
                FROM theaters t
                LEFT JOIN shows s ON s.theater_id = t.theater_id
                LEFT JOIN screens sc ON sc.theater_id = t.theater_id
                WHERE t.theater_id IN ({placeholder})
                GROUP BY t.theater_id, t.name, t.location, t.city, t.state
            """)).fetchall()

            top_shows = db.session.execute(text(f"""
                SELECT s.show_id, s.show_date, s.start_time, s.available_seats,
                       s.price_per_ticket, m.title as movie_title,
                       t.name as theatre_name, sc.screen_number
                FROM shows s
                JOIN movies m ON m.movie_id = s.movie_id
                JOIN theaters t ON t.theater_id = s.theater_id
                JOIN screens sc ON sc.screen_id = s.screen_id
                WHERE s.theater_id IN ({placeholder})
                ORDER BY s.show_date DESC LIMIT 10
            """)).fetchall()

            screens_summary = db.session.execute(text(f"""
                SELECT sc.screen_id, sc.screen_number, sc.total_seats,
                       t.name as theatre_name,
                       COUNT(DISTINCT s.show_id) as show_count
                FROM screens sc
                JOIN theaters t ON t.theater_id = sc.theater_id
                LEFT JOIN shows s ON s.screen_id = sc.screen_id
                WHERE sc.theater_id IN ({placeholder})
                GROUP BY sc.screen_id, sc.screen_number, sc.total_seats, t.name
                ORDER BY t.name, sc.screen_number
            """)).fetchall()

            movies_summary = db.session.execute(text(f"""
                SELECT m.movie_id, m.title, m.genre, m.language, m.rating,
                       COUNT(DISTINCT s.show_id) as show_count
                FROM movies m
                JOIN shows s ON s.movie_id = m.movie_id
                WHERE s.theater_id IN ({placeholder})
                GROUP BY m.movie_id, m.title, m.genre, m.language, m.rating
                ORDER BY show_count DESC
            """)).fetchall()

        except Exception as e:
            print(f"Error loading theatre owner data: {e}")
            screens_summary = []
            movies_summary = []
    else:
        screens_summary = []
        movies_summary = []

    return render_template("theatre_owner/dashboard.html",
        stats=stats, theatres=theatres, top_shows=top_shows,
        screens_summary=screens_summary, movies_summary=movies_summary)


@theatre_owner_bp.route("/theatres")
@login_required
@role_required("theatre_owner")
def my_theatres():
    theatre_ids = get_owner_theatre_ids()
    theatres = []
    if theatre_ids:
        placeholder = ",".join([f"'{tid}'" for tid in theatre_ids])
        try:
            theatres = db.session.execute(text(f"""
                SELECT t.*, COUNT(DISTINCT sc.screen_id) as screen_count
                FROM theaters t
                LEFT JOIN screens sc ON sc.theater_id = t.theater_id
                WHERE t.theater_id IN ({placeholder})
                GROUP BY t.theater_id, t.name, t.location, t.city, t.state
            """)).fetchall()
        except Exception as e:
            print(f"Error: {e}")

    return render_template("theatre_owner/theatres.html", theatres=theatres)


@theatre_owner_bp.route("/theatres/<theatre_id>")
@login_required
@role_required("theatre_owner")
def theatre_detail(theatre_id):
    theatre_ids = get_owner_theatre_ids()
    if theatre_id not in theatre_ids:
        return jsonify({"error": "Unauthorized"}), 403

    try:
        theatre = db.session.execute(text("SELECT * FROM theaters WHERE theater_id = :tid"), {"tid": theatre_id}).fetchone()
        screens = db.session.execute(text("""
            SELECT sc.*, COUNT(s.show_id) as show_count
            FROM screens sc LEFT JOIN shows s ON s.screen_id = sc.screen_id
            WHERE sc.theater_id = :tid GROUP BY sc.screen_id, sc.theater_id, sc.screen_number, sc.total_seats
        """), {"tid": theatre_id}).fetchall()
        shows = db.session.execute(text("""
            SELECT s.show_id, s.show_date, s.start_time, s.price_per_ticket, s.available_seats,
                   m.title as movie_title, sc.screen_number
            FROM shows s JOIN movies m ON m.movie_id = s.movie_id
            JOIN screens sc ON sc.screen_id = s.screen_id
            WHERE s.theater_id = :tid ORDER BY s.show_date DESC, s.start_time LIMIT 20
        """), {"tid": theatre_id}).fetchall()
    except Exception as e:
        print(f"Error: {e}")
        theatre, screens, shows = None, [], []

    return render_template("theatre_owner/theatre_detail.html",
        theatre=theatre, screens=screens, shows=shows)


@theatre_owner_bp.route("/shows")
@login_required
@role_required("theatre_owner")
def my_shows():
    theatre_ids = get_owner_theatre_ids()
    shows = []
    theatres = []
    if theatre_ids:
        placeholder = ",".join([f"'{tid}'" for tid in theatre_ids])
        try:
            shows = db.session.execute(text(f"""
                SELECT s.show_id, s.show_date, s.start_time, s.price_per_ticket, s.available_seats,
                       m.title as movie_title, t.name as theatre_name, t.city, sc.screen_number
                FROM shows s
                JOIN movies m ON m.movie_id = s.movie_id
                JOIN theaters t ON t.theater_id = s.theater_id
                JOIN screens sc ON sc.screen_id = s.screen_id
                WHERE s.theater_id IN ({placeholder})
                ORDER BY s.show_date DESC, s.start_time
            """)).fetchall()
            theatres = db.session.execute(text(f"""
                SELECT theater_id, name, city FROM theaters
                WHERE theater_id IN ({placeholder}) ORDER BY name
            """)).fetchall()
        except Exception as e:
            print(f"Error: {e}")

    return render_template("theatre_owner/shows.html", shows=shows, theatres=theatres)


@theatre_owner_bp.route("/api/movies-list")
@login_required
@role_required("theatre_owner")
def api_movies():
    movies = db.session.execute(text("SELECT movie_id, title FROM movies ORDER BY title")).fetchall()
    return jsonify([{"id": m.movie_id, "title": m.title} for m in movies])


@theatre_owner_bp.route("/api/screens/<theatre_id>")
@login_required
@role_required("theatre_owner")
def api_screens(theatre_id):
    screens = db.session.execute(text("""
        SELECT screen_id, screen_number, total_seats FROM screens WHERE theater_id = :tid
    """), {"tid": theatre_id}).fetchall()
    return jsonify([{"id": s.screen_id, "number": s.screen_number, "seats": s.total_seats} for s in screens])


# ── Add Show ─────────────────────────────────────────────────
@theatre_owner_bp.route("/shows/add", methods=["POST"])
@login_required
@role_required("theatre_owner")
def add_show():
    theatre_ids = get_owner_theatre_ids()
    data = request.get_json()
    theatre_id  = data.get("theatre_id", "").strip()
    movie_id    = data.get("movie_id", "").strip()
    screen_id   = data.get("screen_id", "").strip()
    show_date   = data.get("show_date", "").strip()
    start_time  = data.get("start_time", "").strip()
    price       = data.get("price_per_ticket", "")
    avail_seats = data.get("available_seats", "")

    if theatre_id not in theatre_ids:
        return jsonify({"success": False, "message": "Unauthorized theatre."}), 403

    if not all([theatre_id, movie_id, screen_id, show_date, start_time, price]):
        return jsonify({"success": False, "message": "All fields are required."}), 400

    try:
        # Get total seats from screen if not provided
        if not avail_seats:
            screen = db.session.execute(
                text("SELECT total_seats FROM screens WHERE screen_id = :sid"),
                {"sid": screen_id}
            ).fetchone()
            avail_seats = screen.total_seats if screen else 100

        import uuid
        show_id = "SH" + uuid.uuid4().hex[:8].upper()
        db.session.execute(text("""
            INSERT INTO shows (show_id, movie_id, theater_id, screen_id, show_date, start_time,
                               price_per_ticket, available_seats)
            VALUES (:show_id, :movie_id, :theater_id, :screen_id, :show_date, :start_time,
                    :price, :avail_seats)
        """), {
            "show_id": show_id, "movie_id": movie_id, "theater_id": theatre_id,
            "screen_id": screen_id, "show_date": show_date, "start_time": start_time,
            "price": float(price), "avail_seats": int(avail_seats)
        })
        db.session.commit()
        return jsonify({"success": True, "message": "Show added successfully!"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": f"Error: {str(e)}"}), 500


# ── Edit Show ────────────────────────────────────────────────
@theatre_owner_bp.route("/shows/<show_id>/edit", methods=["POST"])
@login_required
@role_required("theatre_owner")
def edit_show(show_id):
    theatre_ids = get_owner_theatre_ids()
    # Verify this show belongs to one of owner's theatres
    show = db.session.execute(
        text("SELECT * FROM shows WHERE show_id = :sid"), {"sid": show_id}
    ).fetchone()
    if not show or show.theater_id not in theatre_ids:
        return jsonify({"success": False, "message": "Unauthorized."}), 403

    data = request.get_json()
    show_date  = data.get("show_date", "").strip()
    start_time = data.get("start_time", "").strip()
    price      = data.get("price_per_ticket", "")
    avail      = data.get("available_seats", "")

    try:
        db.session.execute(text("""
            UPDATE shows SET show_date=:show_date, start_time=:start_time,
                price_per_ticket=:price, available_seats=:avail
            WHERE show_id=:sid
        """), {
            "show_date": show_date, "start_time": start_time,
            "price": float(price), "avail": int(avail), "sid": show_id
        })
        db.session.commit()
        return jsonify({"success": True, "message": "Show updated successfully!"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": f"Error: {str(e)}"}), 500


# ── Delete Show ──────────────────────────────────────────────
@theatre_owner_bp.route("/shows/<show_id>/delete", methods=["POST"])
@login_required
@role_required("theatre_owner")
def delete_show(show_id):
    theatre_ids = get_owner_theatre_ids()
    show = db.session.execute(
        text("SELECT * FROM shows WHERE show_id = :sid"), {"sid": show_id}
    ).fetchone()
    if not show or show.theater_id not in theatre_ids:
        return jsonify({"success": False, "message": "Unauthorized."}), 403
    try:
        db.session.execute(text("DELETE FROM shows WHERE show_id = :sid"), {"sid": show_id})
        db.session.commit()
        return jsonify({"success": True, "message": "Show deleted."})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": f"Error: {str(e)}"}), 500


# ── Profile / Change Password ────────────────────────────────
@theatre_owner_bp.route("/profile")
@login_required
@role_required("theatre_owner")
def profile():
    user = AppUser.query.get(session["user_id"])
    return render_template("theatre_owner/profile.html", user=user)


@theatre_owner_bp.route("/profile/update", methods=["POST"])
@login_required
@role_required("theatre_owner")
def update_profile():
    user = AppUser.query.get(session["user_id"])
    data = request.get_json()
    action = data.get("action")

    if action == "update_info":
        name  = data.get("name", "").strip()
        phone = data.get("phone", "").strip()
        city  = data.get("city", "").strip()
        if not name:
            return jsonify({"success": False, "message": "Name is required."})
        user.name  = name
        user.phone = phone
        user.city  = city
        db.session.commit()
        session["user_name"] = name
        return jsonify({"success": True, "message": "Profile updated!"})

    elif action == "change_password":
        current_pw  = data.get("current_password", "")
        new_pw      = data.get("new_password", "")
        confirm_pw  = data.get("confirm_password", "")
        if not user.check_password(current_pw):
            return jsonify({"success": False, "message": "Current password is incorrect."})
        if len(new_pw) < 6:
            return jsonify({"success": False, "message": "New password must be at least 6 characters."})
        if new_pw != confirm_pw:
            return jsonify({"success": False, "message": "Passwords do not match."})
        user.set_password(new_pw)
        db.session.commit()
        return jsonify({"success": True, "message": "Password changed successfully!"})

    return jsonify({"success": False, "message": "Invalid action."})


# ── Register New Theatre ──────────────────────────────────────
@theatre_owner_bp.route("/theatres/register", methods=["POST"])
@login_required
@role_required("theatre_owner")
def register_theatre():
    data = request.get_json()
    name     = data.get("name", "").strip()
    city     = data.get("city", "").strip()
    state    = data.get("state", "").strip()
    location = data.get("location", "").strip()
    screens  = int(data.get("screens", 1))

    if not all([name, city, state, location]):
        return jsonify({"success": False, "message": "All fields are required."}), 400

    try:
        import uuid
        theater_id = "TH" + uuid.uuid4().hex[:8].upper()
        db.session.execute(text("""
            INSERT INTO theaters (theater_id, name, city, state, location)
            VALUES (:tid, :name, :city, :state, :location)
        """), {"tid": theater_id, "name": name, "city": city, "state": state, "location": location})

        # Add screens
        for i in range(1, screens + 1):
            screen_id = "SC" + uuid.uuid4().hex[:8].upper()
            db.session.execute(text("""
                INSERT INTO screens (screen_id, theater_id, screen_number, total_seats)
                VALUES (:sid, :tid, :num, :seats)
            """), {"sid": screen_id, "tid": theater_id, "num": i, "seats": 120})

        # Link to owner via TheatreOwnership
        user_id = session.get("user_id")
        from models.models import TheatreOwnership
        new_ownership = TheatreOwnership(owner_id=user_id, theatre_db_id=theater_id)
        db.session.add(new_ownership)
        db.session.commit()
        return jsonify({"success": True, "message": f"Theatre '{name}' registered successfully with {screens} screen(s)!", "theater_id": theater_id})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": f"Error: {str(e)}"}), 500


# ── New Panel Routes ──────────────────────────────────────────────────

@theatre_owner_bp.route("/add-movie")
@login_required
@role_required("theatre_owner")
def add_movie():
    theatre_ids = get_owner_theatre_ids()
    theatres = []
    if theatre_ids:
        placeholder = ",".join([f"'{tid}'" for tid in theatre_ids])
        try:
            theatres = db.session.execute(text(f"SELECT theater_id, name, city FROM theaters WHERE theater_id IN ({placeholder})")).fetchall()
        except Exception as e:
            print(f"Error: {e}")
    return render_template("theatre_owner/add_movie.html", theatres=theatres)


@theatre_owner_bp.route("/manage-shows")
@login_required
@role_required("theatre_owner")
def manage_shows():
    theatre_ids = get_owner_theatre_ids()
    shows = []
    if theatre_ids:
        placeholder = ",".join([f"'{tid}'" for tid in theatre_ids])
        try:
            shows = db.session.execute(text(f"""
                SELECT s.show_id, s.show_date, s.start_time, s.price_per_ticket,
                       s.available_seats, m.title as movie_title,
                       t.name as theatre_name, sc.screen_number
                FROM shows s
                JOIN movies m ON m.movie_id = s.movie_id
                JOIN theaters t ON t.theater_id = s.theater_id
                JOIN screens sc ON sc.screen_id = s.screen_id
                WHERE s.theater_id IN ({placeholder})
                ORDER BY s.show_date DESC
            """)).fetchall()
        except Exception as e:
            print(f"Error: {e}")
    return render_template("theatre_owner/manage_shows.html", shows=shows)


@theatre_owner_bp.route("/view-bookings")
@login_required
@role_required("theatre_owner")
def view_bookings():
    theatre_ids = get_owner_theatre_ids()
    bookings = []
    total_revenue = 0
    if theatre_ids:
        placeholder = ",".join([f"'{tid}'" for tid in theatre_ids])
        try:
            bookings = db.session.execute(text(f"""
                SELECT ub.booking_ref, ub.movie_title, ub.theatre_name,
                       ub.show_date, ub.show_time, ub.num_tickets,
                       ub.seat_numbers, ub.total_amount, ub.status, ub.booked_at
                FROM user_bookings ub
                WHERE ub.theatre_name IN (
                    SELECT name FROM theaters WHERE theater_id IN ({placeholder})
                )
                ORDER BY ub.booked_at DESC
            """)).fetchall()
            total_revenue = sum(b.total_amount for b in bookings if b.total_amount)
        except Exception as e:
            print(f"Error: {e}")
    return render_template("theatre_owner/view_bookings.html", bookings=bookings, total_revenue=total_revenue)


@theatre_owner_bp.route("/screen-management")
@login_required
@role_required("theatre_owner")
def screen_management():
    theatre_ids = get_owner_theatre_ids()
    screens = []
    theatres = []
    if theatre_ids:
        placeholder = ",".join([f"'{tid}'" for tid in theatre_ids])
        try:
            screens = db.session.execute(text(f"""
                SELECT sc.screen_id, sc.screen_number, sc.total_seats,
                       t.name as theatre_name, t.theater_id,
                       COUNT(s.show_id) as show_count
                FROM screens sc
                JOIN theaters t ON t.theater_id = sc.theater_id
                LEFT JOIN shows s ON s.screen_id = sc.screen_id
                WHERE sc.theater_id IN ({placeholder})
                GROUP BY sc.screen_id, sc.screen_number, sc.total_seats, t.name, t.theater_id
                ORDER BY t.name, sc.screen_number
            """)).fetchall()
            theatres = db.session.execute(text(f"SELECT theater_id, name FROM theaters WHERE theater_id IN ({placeholder})")).fetchall()
        except Exception as e:
            print(f"Error: {e}")
    return render_template("theatre_owner/screen_management.html", screens=screens, theatres=theatres)


@theatre_owner_bp.route("/analytics")
@login_required
@role_required("theatre_owner")
def analytics():
    """Dedicated analytics page for theatre owner."""
    theatre_ids = get_owner_theatre_ids()
    stats = {"total_theatres": len(theatre_ids), "total_shows": 0,
             "total_bookings": 0, "total_revenue": 0, "total_screens": 0}
    if theatre_ids:
        placeholder = ",".join([f"'{tid}'" for tid in theatre_ids])
        try:
            stats["total_shows"] = db.session.execute(text(
                f"SELECT COUNT(*) FROM shows WHERE theater_id IN ({placeholder})"
            )).scalar() or 0
            stats["total_screens"] = db.session.execute(text(
                f"SELECT COUNT(*) FROM screens WHERE theater_id IN ({placeholder})"
            )).scalar() or 0
            from models.models import UserBooking
            tnames = [r.name for r in db.session.execute(text(
                f"SELECT name FROM theaters WHERE theater_id IN ({placeholder})"
            )).fetchall()]
            if tnames:
                all_bookings = UserBooking.query.filter(UserBooking.theatre_name.in_(tnames)).all()
                stats["total_bookings"] = len(all_bookings)
                stats["total_revenue"] = int(sum(b.total_amount for b in all_bookings if b.total_amount))
        except Exception as e:
            print(f"Analytics stats error: {e}")
    return render_template("theatre_owner/analytics.html", stats=stats)


@theatre_owner_bp.route("/analytics-data")
@login_required
@role_required("theatre_owner")
def analytics_data():
    """Return JSON analytics data for theatre owner charts."""
    theatre_ids = get_owner_theatre_ids()
    if not theatre_ids:
        return jsonify({
            "revenue_by_theatre": [],
            "bookings_by_movie": [],
            "shows_by_day": [],
            "seat_utilisation": [],
            "revenue_trend": []
        })

    placeholder = ",".join([f"'{tid}'" for tid in theatre_ids])

    def q(sql, **kw):
        try:
            rows = db.session.execute(text(sql), kw).fetchall()
            return [dict(r._mapping) for r in rows]
        except Exception as e:
            print(f"Analytics query error: {e}")
            return []

    # 1. Revenue by theatre (bar: x=theatre name, y=revenue Rs)
    revenue_by_theatre = q(f"""
        SELECT t.name as theatre, COALESCE(SUM(ub.total_amount),0) as revenue
        FROM theaters t
        LEFT JOIN user_bookings ub ON ub.theatre_name = t.name
        WHERE t.theater_id IN ({placeholder})
        GROUP BY t.name ORDER BY revenue DESC
    """)

    # 2. Top movies by bookings (bar: x=movie title, y=booking count)
    bookings_by_movie = q(f"""
        SELECT ub.movie_title as movie, COUNT(*) as bookings
        FROM user_bookings ub
        WHERE ub.theatre_name IN (SELECT name FROM theaters WHERE theater_id IN ({placeholder}))
        GROUP BY ub.movie_title ORDER BY bookings DESC LIMIT 8
    """)

    # 3. Shows scheduled per weekday (bar: x=day, y=show count)
    shows_by_day = q(f"""
        SELECT CASE CAST(strftime('%w', show_date) AS INTEGER)
            WHEN 0 THEN 'Sun' WHEN 1 THEN 'Mon' WHEN 2 THEN 'Tue'
            WHEN 3 THEN 'Wed' WHEN 4 THEN 'Thu' WHEN 5 THEN 'Fri'
            WHEN 6 THEN 'Sat' END as day_name,
            CAST(strftime('%w', show_date) AS INTEGER) as day_num,
            COUNT(*) as show_count
        FROM shows WHERE theater_id IN ({placeholder})
        GROUP BY day_num, day_name ORDER BY day_num
    """)

    # 4. Seat utilisation by screen (bar: x=screen label, y=% filled)
    seat_utilisation = q(f"""
        SELECT t.name || ' - Scr ' || sc.screen_number as screen_label,
               sc.total_seats,
               COALESCE(SUM(s.available_seats), sc.total_seats) as remaining,
               COUNT(s.show_id) as shows
        FROM screens sc
        JOIN theaters t ON t.theater_id = sc.theater_id
        LEFT JOIN shows s ON s.screen_id = sc.screen_id
        WHERE sc.theater_id IN ({placeholder})
        GROUP BY sc.screen_id, sc.screen_number, sc.total_seats, t.name
        ORDER BY t.name, sc.screen_number
    """)
    for row in seat_utilisation:
        total = row["total_seats"] * max(row["shows"], 1)
        remaining = row["remaining"]
        row["utilisation"] = round(max(0, min(100, (1 - remaining / total) * 100)), 1) if total > 0 else 0

    # 5. Monthly revenue trend (line: x=month, y=revenue)
    revenue_trend = q(f"""
        SELECT strftime('%Y-%m', ub.booked_at) as month,
               COALESCE(SUM(ub.total_amount), 0) as revenue,
               COUNT(*) as bookings
        FROM user_bookings ub
        WHERE ub.theatre_name IN (SELECT name FROM theaters WHERE theater_id IN ({placeholder}))
          AND ub.booked_at IS NOT NULL
        GROUP BY month ORDER BY month DESC LIMIT 12
    """)
    revenue_trend = list(reversed(revenue_trend))

    return jsonify({
        "revenue_by_theatre": revenue_by_theatre,
        "bookings_by_movie": bookings_by_movie,
        "shows_by_day": shows_by_day,
        "seat_utilisation": seat_utilisation,
        "revenue_trend": revenue_trend
    })


@theatre_owner_bp.route("/api/states")
@login_required
@role_required("theatre_owner")
def api_states():
    """Return Indian states list"""
    from flask import jsonify
    states = [
        "Andhra Pradesh","Arunachal Pradesh","Assam","Bihar","Chhattisgarh",
        "Goa","Gujarat","Haryana","Himachal Pradesh","Jharkhand","Karnataka",
        "Kerala","Madhya Pradesh","Maharashtra","Manipur","Meghalaya","Mizoram",
        "Nagaland","Odisha","Punjab","Rajasthan","Sikkim","Tamil Nadu",
        "Telangana","Tripura","Uttar Pradesh","Uttarakhand","West Bengal",
        "Andaman and Nicobar Islands","Chandigarh","Dadra and Nagar Haveli",
        "Daman and Diu","Delhi","Jammu and Kashmir","Ladakh","Lakshadweep","Puducherry"
    ]
    return jsonify({"states": sorted(states)})


@theatre_owner_bp.route("/api/cities/<state_name>")
@login_required
@role_required("theatre_owner")
def api_cities(state_name):
    """Return cities for a given Indian state"""
    from flask import jsonify
    cities_map = {
        "Andhra Pradesh": ["Visakhapatnam","Vijayawada","Guntur","Nellore","Kurnool","Tirupati","Rajahmundry","Kakinada"],
        "Assam": ["Guwahati","Silchar","Dibrugarh","Jorhat","Nagaon","Tinsukia"],
        "Bihar": ["Patna","Gaya","Bhagalpur","Muzaffarpur","Purnia","Darbhanga"],
        "Chhattisgarh": ["Raipur","Bhilai","Bilaspur","Korba","Durg","Rajnandgaon"],
        "Delhi": ["New Delhi","Central Delhi","North Delhi","South Delhi","East Delhi","West Delhi","Dwarka","Rohini","Noida Extension"],
        "Goa": ["Panaji","Margao","Vasco da Gama","Mapusa","Ponda"],
        "Gujarat": ["Ahmedabad","Surat","Vadodara","Rajkot","Gandhinagar","Bhavnagar","Jamnagar","Junagadh"],
        "Haryana": ["Faridabad","Gurgaon","Panipat","Ambala","Yamunanagar","Rohtak","Hisar","Karnal"],
        "Himachal Pradesh": ["Shimla","Dharamshala","Solan","Mandi","Baddi","Kullu","Manali"],
        "Jharkhand": ["Ranchi","Jamshedpur","Dhanbad","Bokaro","Deoghar","Phusro"],
        "Karnataka": ["Bengaluru","Mysuru","Hubli","Mangaluru","Belgaum","Davangere","Ballari","Shimoga"],
        "Kerala": ["Thiruvananthapuram","Kochi","Kozhikode","Thrissur","Kollam","Palakkad","Alappuzha","Kannur"],
        "Madhya Pradesh": ["Bhopal","Indore","Gwalior","Jabalpur","Ujjain","Sagar","Satna","Rewa"],
        "Maharashtra": ["Mumbai","Pune","Nagpur","Nashik","Aurangabad","Solapur","Thane","Navi Mumbai","Kolhapur"],
        "Manipur": ["Imphal","Thoubal","Bishnupur","Churachandpur"],
        "Meghalaya": ["Shillong","Tura","Jowai"],
        "Odisha": ["Bhubaneswar","Cuttack","Rourkela","Brahmapur","Sambalpur","Puri"],
        "Punjab": ["Ludhiana","Amritsar","Jalandhar","Patiala","Bathinda","Mohali","Hoshiarpur"],
        "Rajasthan": ["Jaipur","Jodhpur","Kota","Bikaner","Ajmer","Udaipur","Sikar","Alwar"],
        "Tamil Nadu": ["Chennai","Coimbatore","Madurai","Tiruchirappalli","Salem","Tirunelveli","Vellore","Erode","Tiruppur"],
        "Telangana": ["Hyderabad","Warangal","Nizamabad","Khammam","Karimnagar","Ramagundam","Secunderabad"],
        "Uttar Pradesh": ["Lucknow","Kanpur","Agra","Varanasi","Prayagraj","Meerut","Noida","Ghaziabad","Bareilly"],
        "Uttarakhand": ["Dehradun","Haridwar","Rishikesh","Roorkee","Haldwani","Kashipur","Rudrapur"],
        "West Bengal": ["Kolkata","Asansol","Siliguri","Durgapur","Bardhaman","Malda","Berhampore"],
        "Jammu and Kashmir": ["Srinagar","Jammu","Anantnag","Baramulla","Sopore","Kathua"],
        "Ladakh": ["Leh","Kargil"],
        "Arunachal Pradesh": ["Itanagar","Naharlagun","Pasighat","Tawang"],
        "Nagaland": ["Kohima","Dimapur","Mokokchung","Tuensang"],
        "Mizoram": ["Aizawl","Lunglei","Saiha"],
        "Tripura": ["Agartala","Dharmanagar","Udaipur"],
        "Sikkim": ["Gangtok","Namchi","Rangpo"],
        "Chandigarh": ["Chandigarh"],
        "Puducherry": ["Puducherry","Karaikal","Yanam","Mahe"],
        "Andaman and Nicobar Islands": ["Port Blair"],
        "Dadra and Nagar Haveli": ["Silvassa"],
        "Daman and Diu": ["Daman","Diu"],
        "Lakshadweep": ["Kavaratti"],
    }
    cities = cities_map.get(state_name, [])
    return jsonify({"cities": sorted(cities)})


# ── Add Movie Submit ──────────────────────────────────────────────────
@theatre_owner_bp.route("/add-movie-submit", methods=["POST"])
@login_required
@role_required("theatre_owner")
def add_movie_submit():
    """Handle Add Movie form submission — creates the movie and a first show."""
    from flask import flash, redirect, url_for
    import uuid

    theatre_ids = get_owner_theatre_ids()

    title        = request.form.get("title", "").strip()
    genre        = request.form.get("genre", "").strip()
    language     = request.form.get("language", "").strip()
    duration     = request.form.get("duration", "").strip()
    release_date = request.form.get("release_date", "").strip()
    description  = request.form.get("description", "").strip()
    theatre_id   = request.form.get("theatre_id", "").strip()
    price        = request.form.get("price", "").strip()
    show_date    = request.form.get("show_date", "").strip()
    show_time    = request.form.get("show_time", "").strip()

    # Validate required fields
    if not all([title, genre, language, duration, release_date, theatre_id, price, show_date, show_time]):
        flash("Please fill in all required fields.", "danger")
        return redirect(url_for("theatre_owner.add_movie"))

    # Validate theatre ownership
    if theatre_id not in theatre_ids:
        flash("You do not own that theatre.", "danger")
        return redirect(url_for("theatre_owner.add_movie"))

    try:
        # Check if movie with same title already exists
        existing = db.session.execute(
            text("SELECT movie_id FROM movies WHERE title = :title"),
            {"title": title}
        ).fetchone()

        if existing:
            movie_id = existing.movie_id
        else:
            # Create new movie record
            movie_id = "MV" + uuid.uuid4().hex[:8].upper()
            db.session.execute(text("""
                INSERT INTO movies (movie_id, title, genre, language, duration, release_date, description, rating)
                VALUES (:mid, :title, :genre, :lang, :dur, :rdate, :desc, :rating)
            """), {
                "mid": movie_id,
                "title": title,
                "genre": genre,
                "lang": language,
                "dur": int(duration),
                "rdate": release_date,
                "desc": description[:250] if description else "",
                "rating": 0.0
            })

        # Pick first available screen for the theatre
        screen = db.session.execute(
            text("SELECT screen_id, total_seats FROM screens WHERE theater_id = :tid ORDER BY screen_number LIMIT 1"),
            {"tid": theatre_id}
        ).fetchone()

        if not screen:
            flash("No screens found for the selected theatre. Please add screens first.", "danger")
            db.session.rollback()
            return redirect(url_for("theatre_owner.add_movie"))

        # Create the show
        show_id = "SH" + uuid.uuid4().hex[:8].upper()
        db.session.execute(text("""
            INSERT INTO shows (show_id, movie_id, theater_id, screen_id, show_date, start_time,
                               price_per_ticket, available_seats)
            VALUES (:sid, :mid, :tid, :scid, :sdate, :stime, :price, :seats)
        """), {
            "sid": show_id,
            "mid": movie_id,
            "tid": theatre_id,
            "scid": screen.screen_id,
            "sdate": show_date,
            "stime": show_time,
            "price": float(price),
            "seats": screen.total_seats
        })

        db.session.commit()
        flash(f"Movie '{title}' added successfully and show scheduled!", "success")
        return redirect(url_for("theatre_owner.add_movie"))

    except Exception as e:
        db.session.rollback()
        print(f"Error adding movie: {e}")
        flash("An error occurred while adding the movie. Please try again.", "danger")
        return redirect(url_for("theatre_owner.add_movie"))
