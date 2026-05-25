from flask import Blueprint, render_template, request, jsonify, session
from sqlalchemy import text
from database.db import db

public_bp = Blueprint("public", __name__)

DISPLAY_LIMIT = 300   # Hard cap — show exactly 300 movies max, no infinite scroll

# Total seats in theatre layout (rows A-I: 12+21*7+14 = 173)
_TOTAL_LAYOUT_SEATS = 173

def _calc_available(show_id: str) -> int:
    """Return available seats = total layout seats minus deterministically pre-sold seats."""
    import hashlib, random as _rnd
    all_seats = (
        [f"A{c}" for c in range(1, 13)] +
        [f"{r}{c}" for r in ["B","C","D","E","F","G","H"] for c in range(1, 22)] +
        [f"I{c}" for c in range(1, 15)]
    )
    h = int(hashlib.md5(show_id.encode()).hexdigest(), 16)
    fill_pct = 0.50 + (h % 20) / 100.0
    num_sold = int(len(all_seats) * fill_pct)
    return max(1, len(all_seats) - num_sold)


def _get_movies(genre=None, language=None, city=None, search=None):
    """
    Return up to 300 movies that have ALL of:
    - a show scheduled
    - a theater with non-null location
    - a screen assigned
    Ordered by rating DESC so best movies appear first.
    """
    params = {"limit": DISPLAY_LIMIT}

    base_q = """
        SELECT DISTINCT m.movie_id, m.title, m.genre, m.language, m.duration,
               m.rating, m.release_date, m.description,
               t.city as show_city, t.name as theatre_name, t.location as theatre_location,
               sc.screen_number
        FROM movies m
        INNER JOIN shows s    ON s.movie_id   = m.movie_id
        INNER JOIN theaters t ON t.theater_id = s.theater_id
        INNER JOIN screens sc ON sc.screen_id = s.screen_id
        WHERE t.location IS NOT NULL
          AND t.location <> ''
          AND sc.screen_number IS NOT NULL
    """

    filters = []
    if genre:
        filters.append("AND m.genre ILIKE :genre")
        params["genre"] = f"%{genre}%"
    if language:
        filters.append("AND m.language ILIKE :language")
        params["language"] = f"%{language}%"
    if city:
        filters.append("AND t.city ILIKE :city")
        params["city"] = f"%{city}%"
    if search:
        filters.append("AND (m.title ILIKE :search OR m.genre ILIKE :search)")
        params["search"] = f"%{search}%"

    where = " ".join(filters)
    rows = db.session.execute(
        text(base_q + where + " ORDER BY m.rating DESC NULLS LAST, m.title LIMIT :limit"),
        params
    ).fetchall()

    # Total is capped at 300 — never show inflated counts
    total = min(len(rows), DISPLAY_LIMIT)
    return rows, total


@public_bp.route("/")
def home():
    genre    = request.args.get("genre", "")
    language = request.args.get("language", "")
    city     = request.args.get("city", "")
    search   = request.args.get("search", "")

    movies, total = _get_movies(
        genre    or None,
        language or None,
        city     or None,
        search   or None
    )

    # No infinite scroll — all movies loaded at once, capped at 300
    has_more = False

    # Filter dropdowns — only genres/languages present in qualifying movies
    genres = [r[0] for r in db.session.execute(text("""
        SELECT DISTINCT m.genre FROM movies m
        INNER JOIN shows s    ON s.movie_id   = m.movie_id
        INNER JOIN theaters t ON t.theater_id = s.theater_id
        INNER JOIN screens sc ON sc.screen_id = s.screen_id
        WHERE m.genre IS NOT NULL
          AND t.location IS NOT NULL AND t.location <> ''
          AND sc.screen_number IS NOT NULL
        ORDER BY m.genre
    """)).fetchall()]

    languages = [r[0] for r in db.session.execute(text("""
        SELECT DISTINCT m.language FROM movies m
        INNER JOIN shows s    ON s.movie_id   = m.movie_id
        INNER JOIN theaters t ON t.theater_id = s.theater_id
        INNER JOIN screens sc ON sc.screen_id = s.screen_id
        WHERE m.language IS NOT NULL
          AND t.location IS NOT NULL AND t.location <> ''
          AND sc.screen_number IS NOT NULL
        ORDER BY m.language
    """)).fetchall()]

    cities = [r[0] for r in db.session.execute(text(
        "SELECT DISTINCT city FROM theaters WHERE city IS NOT NULL ORDER BY city"
    )).fetchall()]

    return render_template("public/home.html",
        movies=movies, total=total, has_more=False,
        total_pages=1, per_page=DISPLAY_LIMIT,
        genres=genres, languages=languages, cities=cities,
        selected_genre=genre, selected_language=language,
        selected_city=city, search=search
    )


@public_bp.route("/movie/<movie_id>")
def movie_detail(movie_id):
    import types as _types
    movie = db.session.execute(
        text("SELECT * FROM movies WHERE movie_id = :mid"), {"mid": movie_id}
    ).fetchone()

    if not movie:
        return render_template("public/404.html"), 404

    shows_raw = db.session.execute(text("""
        SELECT s.show_id, s.show_date, s.start_time, s.price_per_ticket, s.available_seats,
               t.name as theatre_name, t.city, t.location, sc.screen_number
        FROM shows s
        JOIN theaters t ON t.theater_id = s.theater_id
        JOIN screens sc ON sc.screen_id = s.screen_id
        WHERE s.movie_id = :mid AND s.available_seats > 0
        ORDER BY t.city, t.name, s.show_date, s.start_time
    """), {"mid": movie_id}).fetchall()

    # Recalculate available_seats consistently with the seat_selection page layout
    # Layout: A(12) + B-H(21x7=147) + I(14) = 173 total seats
    shows = []
    for s in shows_raw:
        avail = _calc_available(s.show_id)  # returns consistent available count
        ns = _types.SimpleNamespace(
            show_id=s.show_id,
            show_date=s.show_date,
            start_time=s.start_time,
            price_per_ticket=s.price_per_ticket,
            available_seats=avail,
            theatre_name=s.theatre_name,
            city=s.city,
            location=s.location,
            screen_number=s.screen_number,
        )
        shows.append(ns)

    reviews = db.session.execute(text("""
        SELECT r.rating, r.review_text, r.review_date, u.name as user_name
        FROM reviews r
        JOIN users u ON u.user_id = r.user_id
        WHERE r.movie_id = :mid
        ORDER BY r.review_date DESC
        LIMIT 10
    """), {"mid": movie_id}).fetchall()

    return render_template("public/movie_detail.html", movie=movie, shows=shows, reviews=reviews)



@public_bp.route("/movie/<movie_id>/book")
def movie_booking(movie_id):
    from datetime import date, timedelta
    import types
    from collections import defaultdict

    movie = db.session.execute(
        text("SELECT * FROM movies WHERE movie_id = :mid"), {"mid": movie_id}
    ).fetchone()
    if not movie:
        return render_template("public/404.html"), 404

    today = date.today()
    # Always exactly 7 days: today, today+1 ... today+6
    seven_days = [str(today + timedelta(days=i)) for i in range(7)]

    # Fetch all DB shows for this movie (any date, seats > 0)
    shows_raw = db.session.execute(text("""
        SELECT s.show_id, s.show_date, s.start_time, s.price_per_ticket, s.available_seats,
               t.name as theatre_name, t.city, t.location, sc.screen_number, t.theater_id
        FROM shows s
        JOIN theaters t ON t.theater_id = s.theater_id
        JOIN screens sc ON sc.screen_id = s.screen_id
        WHERE s.movie_id = :mid AND s.available_seats > 0
        ORDER BY s.show_date, t.name, s.start_time
    """), {"mid": movie_id}).fetchall()

    # Collect unique theatres from DB (or use demo theatres)
    db_theatres = {}
    for s in shows_raw:
        if s.theatre_name not in db_theatres:
            db_theatres[s.theatre_name] = s

    if not db_theatres:
        # No real theatres — use demo theatres
        demo_list = [
            {"name": "PVR Cinemas", "city": "Mumbai", "location": "Phoenix Mall, Lower Parel", "theater_id": "DEMO-T0", "price": 220},
            {"name": "INOX Multiplex", "city": "Mumbai", "location": "R-City Mall, Ghatkopar", "theater_id": "DEMO-T1", "price": 180},
            {"name": "Cinepolis", "city": "Delhi", "location": "DLF Mall of India, Noida", "theater_id": "DEMO-T2", "price": 260},
        ]
    else:
        demo_list = None

    # Fixed time slots for each theatre index
    timing_sets = [
        ["09:15 AM", "12:00 PM", "03:00 PM", "06:15 PM", "09:00 PM", "11:30 PM"],
        ["10:00 AM", "01:00 PM", "04:00 PM", "07:00 PM", "10:00 PM", "11:45 PM"],
        ["09:45 AM", "12:45 PM", "03:45 PM", "06:45 PM", "09:45 PM", "11:15 PM"],
    ]

    dates_map = defaultdict(lambda: defaultdict(list))

    for day_str in seven_days:
        day_date = date.fromisoformat(day_str)

        if demo_list:
            theatres_iter = enumerate(demo_list)
        else:
            theatres_iter = enumerate([
                {"name": t.theatre_name, "city": t.city, "location": t.location,
                 "theater_id": t.theater_id, "price": t.price_per_ticket}
                for t in db_theatres.values()
            ])

        for idx, th in theatres_iter:
            slots = timing_sets[idx % len(timing_sets)]
            shows_for_day = []
            for k, timing in enumerate(slots):
                show = types.SimpleNamespace(
                    show_id=f"GEN-{movie_id}-{day_str}-{idx}-{k}",
                    show_date=day_date,
                    start_time=timing,
                    price_per_ticket=th["price"] if demo_list else th["price"],
                    available_seats=_calc_available(f"GEN-{movie_id}-{day_str}-{idx}-{k}"),
                    theatre_name=th["name"],
                    city=th["city"],
                    location=th["location"],
                    screen_number=f"Screen {k+1}",
                    theater_id=th["theater_id"]
                )
                shows_for_day.append(show)
            dates_map[day_str][th["name"]] = shows_for_day

    # Overlay real DB shows on top (replace generated slots for matching date+theatre)
    # Use _calc_available so seat counts stay consistent across all pages
    for s in shows_raw:
        day_str = str(s.show_date)
        if day_str in seven_days:
            tname = s.theatre_name
            db_shows_for_slot = [s for s in shows_raw
                                  if str(s.show_date) == day_str and s.theatre_name == tname]
            # Wrap DB shows in SimpleNamespace so available_seats uses consistent calculation
            wrapped = []
            for ds in db_shows_for_slot:
                wrapped.append(types.SimpleNamespace(
                    show_id=ds.show_id,
                    show_date=ds.show_date,
                    start_time=ds.start_time,
                    price_per_ticket=ds.price_per_ticket,
                    available_seats=_calc_available(ds.show_id),
                    theatre_name=ds.theatre_name,
                    city=ds.city,
                    location=ds.location,
                    screen_number=ds.screen_number,
                    theater_id=ds.theater_id if hasattr(ds, 'theater_id') else None,
                ))
            dates_map[day_str][tname] = wrapped

    sorted_dates = seven_days  # always exactly today → today+6 in order

    return render_template("public/movie_booking.html",
        movie=movie, dates_map=dict(dates_map), sorted_dates=sorted_dates)


@public_bp.route("/contact", methods=["GET", "POST"])
def contact():
    from models.models import ContactMessage
    
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        message = request.form.get("message", "").strip()
        
        if name and email and message:
            contact_msg = ContactMessage(name=name, email=email, message=message)
            db.session.add(contact_msg)
            db.session.commit()
            return render_template("public/contact.html", success=True)
        else:
            return render_template("public/contact.html", error="All fields are required")
    
    return render_template("public/contact.html")


@public_bp.route("/api/movies")
def api_movies():
    genre    = request.args.get("genre") or None
    language = request.args.get("language") or None
    city     = request.args.get("city") or None
    search   = request.args.get("search") or None

    movies, total = _get_movies(genre, language, city, search)

    data = []
    for m in movies:
        data.append({
            "movie_id":        m.movie_id,
            "title":           m.title,
            "genre":           m.genre,
            "language":        m.language,
            "duration":        m.duration,
            "rating":          float(m.rating) if m.rating else None,
            "release_date":    str(m.release_date) if m.release_date else None,
            "description":     m.description,
            "city":            m.show_city,
            "theatre_name":    m.theatre_name,
            "theatre_location":m.theatre_location,
            "screen_number":   m.screen_number,
        })

    return jsonify({
        "movies":      data,
        "total":       total,
        "page":        1,
        "total_pages": 1,
        "has_more":    False,
        "per_page":    DISPLAY_LIMIT
    })


@public_bp.route("/search-suggestions")
def search_suggestions():
    q = request.args.get("q", "").strip()
    if len(q) < 2:
        return jsonify({"movies": [], "genres": []})

    # Only suggest movies that actually have shows
    movies = db.session.execute(
        text("""SELECT DISTINCT m.title, m.genre
                FROM movies m
                INNER JOIN shows s ON s.movie_id = m.movie_id
                WHERE m.title ILIKE :q LIMIT 6"""),
        {"q": f"%{q}%"}
    ).fetchall()

    # Only suggest genres from movies that have shows
    genres = db.session.execute(
        text("""SELECT DISTINCT m.genre
                FROM movies m
                INNER JOIN shows s ON s.movie_id = m.movie_id
                WHERE m.genre ILIKE :q AND m.genre IS NOT NULL LIMIT 4"""),
        {"q": f"%{q}%"}
    ).fetchall()

    return jsonify({
        "movies": [{"title": m[0], "genre": m[1]} for m in movies],
        "genres": [g[0] for g in genres]
    })
