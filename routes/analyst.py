from flask import Blueprint, render_template, session, request, jsonify
from routes.auth import login_required, role_required
from models.models import AppUser, Role, UserBooking, db
from sqlalchemy import text
from datetime import datetime, timedelta

analyst_bp = Blueprint("analyst", __name__, url_prefix="/analyst")

# ✅ helper added
def to_dict_list(result):
    return [dict(row._mapping) for row in result]


@analyst_bp.route("/")
@login_required
@role_required("analyst")
def dashboard():
    stats = {}
    try:
        stats["total_movies"] = db.session.execute(text("SELECT COUNT(*) FROM movies")).scalar() or 0
        stats["total_theatres"] = db.session.execute(text("SELECT COUNT(*) FROM theaters")).scalar() or 0
        stats["total_shows"] = db.session.execute(text("SELECT COUNT(*) FROM shows")).scalar() or 0
        stats["total_users"] = db.session.execute(text("SELECT COUNT(*) FROM users")).scalar() or 0
    except Exception:
        stats = {"total_movies": 0, "total_theatres": 0, "total_shows": 0, "total_users": 0}

    # 5.13 — Booking & revenue stats from user_bookings
    try:
        stats["total_bookings"] = db.session.execute(text("SELECT COUNT(*) FROM user_bookings WHERE status='Confirmed'")).scalar() or 0
        stats["total_revenue"] = db.session.execute(text("SELECT COALESCE(SUM(total_amount),0) FROM user_bookings WHERE status='Confirmed'")).scalar() or 0
        stats["total_tickets"] = db.session.execute(text("SELECT COALESCE(SUM(num_tickets),0) FROM user_bookings WHERE status='Confirmed'")).scalar() or 0
    except Exception:
        stats["total_bookings"] = 0
        stats["total_revenue"] = 0
        stats["total_tickets"] = 0

    # Bookings trend – last 30 days
    try:
        bookings_trend = to_dict_list(db.session.execute(text("""
            SELECT DATE(booked_at) as bdate, COUNT(*) as cnt, COALESCE(SUM(total_amount),0) as rev
            FROM user_bookings
            WHERE booked_at >= NOW() - INTERVAL '30 days'
            GROUP BY DATE(booked_at) ORDER BY bdate
        """)).fetchall())
    except Exception:
        bookings_trend = []

    # Revenue by payment method
    try:
        revenue_by_method = to_dict_list(db.session.execute(text("""
            SELECT payment_method, COUNT(*) as cnt, COALESCE(SUM(total_amount),0) as rev
            FROM user_bookings WHERE status='Confirmed' AND payment_method IS NOT NULL
            GROUP BY payment_method ORDER BY rev DESC
        """)).fetchall())
    except Exception:
        revenue_by_method = []

    # Top movies by bookings
    try:
        top_booked_movies = to_dict_list(db.session.execute(text("""
            SELECT movie_title, COUNT(*) as bookings, COALESCE(SUM(num_tickets),0) as tickets,
                   COALESCE(SUM(total_amount),0) as revenue
            FROM user_bookings WHERE status='Confirmed' AND movie_title IS NOT NULL
            GROUP BY movie_title ORDER BY bookings DESC LIMIT 8
        """)).fetchall())
    except Exception:
        top_booked_movies = []

    # Top cities by bookings
    try:
        top_cities_bookings = to_dict_list(db.session.execute(text("""
            SELECT theatre_city, COUNT(*) as bookings, COALESCE(SUM(total_amount),0) as revenue
            FROM user_bookings WHERE status='Confirmed' AND theatre_city IS NOT NULL
            GROUP BY theatre_city ORDER BY bookings DESC LIMIT 8
        """)).fetchall())
    except Exception:
        top_cities_bookings = []

    # User signup trend
    try:
        signup_trend = to_dict_list(db.session.execute(text("""
            SELECT DATE(created_at) as sdate, COUNT(*) as cnt
            FROM app_users
            WHERE created_at >= NOW() - INTERVAL '30 days'
            GROUP BY DATE(created_at) ORDER BY sdate
        """)).fetchall())
    except Exception:
        signup_trend = []

    # Cancellation rate
    try:
        cancelled = db.session.execute(text("SELECT COUNT(*) FROM user_bookings WHERE status='Cancelled'")).scalar() or 0
        total_b = (stats["total_bookings"] or 1) + cancelled
        stats["cancellation_rate"] = round((cancelled / total_b) * 100, 1)
    except Exception:
        stats["cancellation_rate"] = 0

    # Top movies by show count
    try:
        top_movies = to_dict_list(db.session.execute(text("""
            SELECT m.title, m.genre, m.rating, COUNT(s.show_id) as show_count
            FROM movies m JOIN shows s ON s.movie_id = m.movie_id
            GROUP BY m.title, m.genre, m.rating ORDER BY show_count DESC LIMIT 10
        """)).fetchall())
    except Exception:
        top_movies = []

    # Genre distribution
    try:
        genre_dist = to_dict_list(db.session.execute(text("""
            SELECT genre, COUNT(*) as cnt FROM movies
            WHERE genre IS NOT NULL GROUP BY genre ORDER BY cnt DESC LIMIT 10
        """)).fetchall())
    except Exception:
        genre_dist = []

    # Top cities
    try:
        top_cities = to_dict_list(db.session.execute(text("""
            SELECT city, COUNT(*) as cnt FROM theaters GROUP BY city ORDER BY cnt DESC LIMIT 8
        """)).fetchall())
    except Exception:
        top_cities = []

    # Language distribution
    try:
        lang_dist = to_dict_list(db.session.execute(text("""
            SELECT language, COUNT(*) as cnt FROM movies
            WHERE language IS NOT NULL GROUP BY language ORDER BY cnt DESC LIMIT 8
        """)).fetchall())
    except Exception:
        lang_dist = []

    # Rating by genre
    try:
        rating_by_genre = to_dict_list(db.session.execute(text("""
            SELECT genre, ROUND(AVG(rating)::numeric, 2) as avg_rating, COUNT(*) as cnt
            FROM movies WHERE genre IS NOT NULL AND rating IS NOT NULL
            GROUP BY genre ORDER BY avg_rating DESC LIMIT 8
        """)).fetchall())
    except Exception:
        rating_by_genre = []

    # Shows per city
    try:
        shows_per_city = to_dict_list(db.session.execute(text("""
            SELECT t.city, COUNT(s.show_id) as show_count
            FROM theaters t JOIN shows s ON s.theater_id = t.theater_id
            GROUP BY t.city ORDER BY show_count DESC LIMIT 8
        """)).fetchall())
    except Exception:
        shows_per_city = []

    # Top rated
    try:
        top_rated = to_dict_list(db.session.execute(text("""
            SELECT title, genre, language, rating, duration
            FROM movies WHERE rating IS NOT NULL
            ORDER BY rating DESC LIMIT 8
        """)).fetchall())
    except Exception:
        top_rated = []

    # Audit logs
    try:
        audit_logs = to_dict_list(db.session.execute(text("""
            SELECT u.name, u.email, r.name as role, u.created_at,
                   CASE WHEN u.is_active THEN 'Active' ELSE 'Inactive' END as status
            FROM app_users u JOIN roles r ON r.id = u.role_id
            ORDER BY u.created_at DESC LIMIT 20
        """)).fetchall())
    except Exception:
        audit_logs = []

    # Recent bookings
    try:
        recent_bookings_audit = to_dict_list(db.session.execute(text("""
            SELECT ub.booking_ref, au.name as user_name, ub.movie_title,
                   ub.theatre_name, ub.num_tickets, ub.total_amount,
                   ub.payment_method, ub.status, ub.booked_at
            FROM user_bookings ub
            JOIN app_users au ON au.id = ub.user_id
            ORDER BY ub.booked_at DESC LIMIT 20
        """)).fetchall())
    except Exception:
        recent_bookings_audit = []

    return render_template("analyst/dashboard.html",
        stats=stats,
        top_movies=top_movies,
        genre_dist=genre_dist,
        top_cities=top_cities,
        lang_dist=lang_dist,
        rating_by_genre=rating_by_genre,
        shows_per_city=shows_per_city,
        top_rated=top_rated,
        bookings_trend=bookings_trend,
        revenue_by_method=revenue_by_method,
        top_booked_movies=top_booked_movies,
        top_cities_bookings=top_cities_bookings,
        signup_trend=signup_trend,
        audit_logs=audit_logs,
        recent_bookings_audit=recent_bookings_audit,
    )
