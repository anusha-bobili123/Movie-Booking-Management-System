from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, flash, current_app
from routes.auth import login_required, role_required
from models.models import AppUser, UserBooking, db
from sqlalchemy import text
import random, string, smtplib, ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from io import BytesIO
from datetime import date, datetime, timedelta, timezone

user_bp = Blueprint("user", __name__, url_prefix="/user")

# ── IST timezone helper (UTC+5:30) ──
_IST = timezone(timedelta(hours=5, minutes=30))

def _now_ist():
    """Return current IST datetime as naive datetime (for DB and display consistency)."""
    return datetime.now(_IST).replace(tzinfo=None)

# In-memory seat lock store — keyed by show_id
# Structure: {show_id: {seat_id: {"user_id": X, "expires": datetime, "permanent": bool}}}
_seat_locks = {}


def _parse_show_datetime(show_date, show_time_str):
    """
    Parse show date + time string into a datetime.
    show_time_str examples: '09:15 AM', '10:00 PM'
    Returns a naive datetime (local/system time).
    Returns None on parse failure.
    """
    try:
        if isinstance(show_date, str):
            from datetime import date as _d
            show_date = _d.fromisoformat(show_date)
        dt_str = f"{show_date} {show_time_str}"
        return datetime.strptime(dt_str, "%Y-%m-%d %I:%M %p")
    except Exception:
        return None


def _show_unlock_datetime(show_date, show_time_str):
    """
    Returns the IST datetime when a show's seats should be unlocked:
    show start time + 3 hours.
    """
    show_dt = _parse_show_datetime(show_date, show_time_str)
    if show_dt:
        return show_dt + timedelta(hours=3)
    return None


def gen_booking_ref():
    return "BMS" + "".join(random.choices(string.digits, k=8))


def _generate_ticket_pdf_bytes(booking):
    """Generate PDF ticket bytes for the given booking (reusable for email + download)."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    from reportlab.pdfgen import canvas as pdfcanvas
    import datetime as dt

    buf = BytesIO()
    W, H = A4
    c = pdfcanvas.Canvas(buf, pagesize=A4)

    # Header background
    c.setFillColor(colors.HexColor("#0F1419"))
    c.rect(0, H - 110*mm, W, 110*mm, fill=1, stroke=0)
    c.setFillColor(colors.HexColor("#FF6B35"))
    c.rect(0, H - 114*mm, W, 4*mm, fill=1, stroke=0)

    c.setFillColor(colors.HexColor("#FFFFFF"))
    c.setFont("Helvetica-Bold", 36)
    c.drawCentredString(W/2, H - 25*mm, "CINEVERSE")
    c.setFillColor(colors.HexColor("#FF6B35"))
    c.setFont("Helvetica", 10)
    c.drawCentredString(W/2, H - 33*mm, "MOVIE TICKET CONFIRMATION")

    movie_title = booking.movie_title[:35] if len(booking.movie_title) > 35 else booking.movie_title
    c.setFillColor(colors.HexColor("#FFFFFF"))
    c.setFont("Helvetica-Bold", 20)
    c.drawCentredString(W/2, H - 48*mm, movie_title)

    theatre_info = f"{booking.theatre_name} • {getattr(booking, 'theatre_city', '')}"
    c.setFillColor(colors.HexColor("#B0B8C1"))
    c.setFont("Helvetica", 9)
    c.drawCentredString(W/2, H - 56*mm, theatre_info)

    # Pills
    pills = [("DATE", str(booking.show_date)), ("TIME", str(booking.show_time)), ("TICKETS", str(booking.num_tickets))]
    pill_w, pill_h = 50*mm, 22*mm
    total_w = len(pills) * (pill_w + 5*mm)
    sx = (W - total_w) / 2
    pill_top = H - 65*mm
    for i, (lbl, val) in enumerate(pills):
        px = sx + i * (pill_w + 5*mm)
        py = pill_top - pill_h
        c.setFillColor(colors.HexColor("#F5F7FA"))
        c.roundRect(px, py, pill_w, pill_h, 6, fill=1, stroke=0)
        c.setStrokeColor(colors.HexColor("#E1E8ED"))
        c.setLineWidth(1)
        c.roundRect(px, py, pill_w, pill_h, 6, fill=0, stroke=1)
        c.setFillColor(colors.HexColor("#7A8490"))
        c.setFont("Helvetica", 7)
        c.drawCentredString(px + pill_w/2, py + 15*mm, lbl)
        c.setFillColor(colors.HexColor("#0F1419"))
        c.setFont("Helvetica-Bold", 11)
        c.drawCentredString(px + pill_w/2, py + 5*mm, val)

    # Dashed separator
    sep_y = H - 110*mm - 25*mm
    c.setStrokeColor(colors.HexColor("#D8DCE0"))
    c.setLineWidth(1)
    c.setDash(3, 2)
    c.line(20*mm, sep_y, W - 20*mm, sep_y)
    c.setDash()
    c.setFillColor(colors.HexColor("#FFFFFF"))
    c.setStrokeColor(colors.HexColor("#D8DCE0"))
    c.setLineWidth(2)
    c.circle(15*mm, sep_y, 5*mm, fill=1, stroke=1)
    c.circle(W - 15*mm, sep_y, 5*mm, fill=1, stroke=1)

    # Details grid
    detail_y = sep_y - 20*mm
    booked_date = booking.booked_at.date() if hasattr(booking, 'booked_at') and booking.booked_at else "N/A"
    details = [
        ("BOOKING REFERENCE", booking.booking_ref),
        ("SEAT NUMBER(S)", booking.seat_numbers or "N/A"),
        ("TOTAL AMOUNT", f"Rs. {booking.total_amount:.2f}"),
        ("BOOKING DATE", str(booked_date)),
    ]
    col_w = (W - 40*mm) / 2
    for idx, (lbl, val) in enumerate(details):
        row = idx // 2
        col = idx % 2
        xp = 20*mm + col * (col_w + 20*mm)
        yp = detail_y - row * 30*mm
        c.setFillColor(colors.HexColor("#7A8490"))
        c.setFont("Helvetica", 8)
        c.drawString(xp, yp, lbl)
        c.setFillColor(colors.HexColor("#0F1419"))
        c.setFont("Helvetica-Bold", 12)
        c.drawString(xp, yp - 8*mm, str(val))
        c.setStrokeColor(colors.HexColor("#FF6B35"))
        c.setLineWidth(2)
        c.line(xp, yp - 11*mm, xp + 50*mm, yp - 11*mm)

    # Footer
    footer_y = 35*mm
    c.setFillColor(colors.HexColor("#FFF8E1"))
    c.roundRect(15*mm, footer_y - 18*mm, W - 30*mm, 18*mm, 4, fill=1, stroke=0)
    c.setStrokeColor(colors.HexColor("#FFB74D"))
    c.setLineWidth(1)
    c.roundRect(15*mm, footer_y - 18*mm, W - 30*mm, 18*mm, 4, fill=0, stroke=1)
    c.setFillColor(colors.HexColor("#E65100"))
    c.setFont("Helvetica-Bold", 8)
    c.drawString(20*mm, footer_y - 7*mm, "IMPORTANT:")
    c.setFillColor(colors.HexColor("#BF360C"))
    c.setFont("Helvetica", 8)
    c.drawString(20*mm, footer_y - 12*mm, "Please arrive 15 minutes before showtime. This ticket is non-transferable.")
    c.setFillColor(colors.HexColor("#999999"))
    c.setFont("Helvetica", 7)
    c.drawRightString(W - 15*mm, 8*mm, f"Generated: {dt.datetime.now().strftime('%d-%b-%Y %H:%M:%S')}")

    c.save()
    buf.seek(0)
    return buf.getvalue()


def _send_booking_confirmation_email(user_email, user_name, booking):
    """Send booking confirmation email with PDF ticket attached."""
    try:
        mail_username = current_app.config.get("MAIL_USERNAME")
        mail_password = current_app.config.get("MAIL_PASSWORD")
        mail_server   = current_app.config.get("MAIL_SERVER", "smtp.gmail.com")
        mail_port     = int(current_app.config.get("MAIL_PORT", 587))

        if not mail_username or not mail_password:
            return False

        pdf_bytes = _generate_ticket_pdf_bytes(booking)

        msg = MIMEMultipart("mixed")
        msg["From"]    = f"CineVerse <{mail_username}>"
        msg["To"]      = user_email
        msg["Subject"] = f"🎬 Booking Confirmed – {booking.movie_title} | Ref: {booking.booking_ref}"

        html_body = f"""
        <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;background:#0f1419;color:#fff;border-radius:12px;overflow:hidden;">
          <div style="background:linear-gradient(135deg,#6366f1,#4f46e5);padding:30px;text-align:center;">
            <h1 style="margin:0;font-size:28px;letter-spacing:2px;">CINEVERSE</h1>
            <p style="margin:6px 0 0;color:rgba(255,255,255,0.8);font-size:13px;">Your Booking is Confirmed!</p>
          </div>
          <div style="padding:28px 32px;">
            <p style="font-size:16px;margin-bottom:20px;">Hi <strong>{user_name}</strong>, 🎉</p>
            <p style="color:rgba(255,255,255,0.75);">Your ticket for <strong style="color:#fff;">{booking.movie_title}</strong> has been confirmed. Please find your ticket PDF attached.</p>
            <div style="background:rgba(255,255,255,0.05);border:1px solid rgba(255,255,255,0.1);border-radius:10px;padding:20px;margin:20px 0;">
              <table style="width:100%;border-collapse:collapse;font-size:14px;">
                <tr><td style="color:rgba(255,255,255,0.5);padding:6px 0;">Booking Ref</td><td style="color:#FF6B35;font-weight:bold;text-align:right;">{booking.booking_ref}</td></tr>
                <tr><td style="color:rgba(255,255,255,0.5);padding:6px 0;">Movie</td><td style="text-align:right;">{booking.movie_title}</td></tr>
                <tr><td style="color:rgba(255,255,255,0.5);padding:6px 0;">Theatre</td><td style="text-align:right;">{booking.theatre_name}</td></tr>
                <tr><td style="color:rgba(255,255,255,0.5);padding:6px 0;">Date & Time</td><td style="text-align:right;">{booking.show_date} at {booking.show_time}</td></tr>
                <tr><td style="color:rgba(255,255,255,0.5);padding:6px 0;">Tickets</td><td style="text-align:right;">{booking.num_tickets}</td></tr>
                <tr><td style="color:rgba(255,255,255,0.5);padding:6px 0;">Seats</td><td style="text-align:right;">{booking.seat_numbers or 'N/A'}</td></tr>
                <tr><td style="color:rgba(255,255,255,0.5);padding:6px 0;border-top:1px solid rgba(255,255,255,0.1);padding-top:12px;"><strong>Total Paid</strong></td><td style="text-align:right;border-top:1px solid rgba(255,255,255,0.1);padding-top:12px;"><strong style="color:#4ade80;font-size:16px;">₹{booking.total_amount:.2f}</strong></td></tr>
              </table>
            </div>
            <p style="color:rgba(255,255,255,0.5);font-size:12px;margin-top:24px;">Please arrive 15 minutes before showtime. This ticket is non-transferable.<br>Enjoy your movie! 🍿</p>
          </div>
          <div style="background:rgba(255,255,255,0.03);padding:16px 32px;text-align:center;font-size:11px;color:rgba(255,255,255,0.3);">
            © CineVerse · Book movies, create memories
          </div>
        </div>
        """

        alt = MIMEMultipart("alternative")
        alt.attach(MIMEText(f"Booking confirmed! Ref: {booking.booking_ref} | {booking.movie_title} on {booking.show_date} at {booking.show_time}", "plain"))
        alt.attach(MIMEText(html_body, "html"))
        msg.attach(alt)

        # Attach PDF
        part = MIMEBase("application", "octet-stream")
        part.set_payload(pdf_bytes)
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", f'attachment; filename="CineVerse_Ticket_{booking.booking_ref}.pdf"')
        msg.attach(part)

        context = ssl.create_default_context()
        with smtplib.SMTP(mail_server, mail_port) as server:
            server.ehlo()
            server.starttls(context=context)
            server.login(mail_username, mail_password)
            server.sendmail(mail_username, user_email, msg.as_string())
        return True
    except Exception as e:
        current_app.logger.warning(f"Booking email failed: {e}")
        return False




@user_bp.route("/dashboard")
@login_required
@role_required("user")
def dashboard():
    user_id = session.get("user_id")
    user = AppUser.query.get(user_id)
    bookings = UserBooking.query.filter_by(user_id=user_id).order_by(UserBooking.booked_at.desc()).limit(5).all()
    total_bookings = UserBooking.query.filter_by(user_id=user_id).count()
    confirmed = UserBooking.query.filter_by(user_id=user_id, status="Confirmed").count()
    cancelled = UserBooking.query.filter_by(user_id=user_id, status="Cancelled").count()

    return render_template("user/dashboard.html", user=user, bookings=bookings,
        total_bookings=total_bookings, confirmed=confirmed, cancelled=cancelled)


@user_bp.route("/bookings")
@login_required
@role_required("user")
def my_bookings():
    from models.models import ContactMessage
    user_id = session.get("user_id")
    user = AppUser.query.get(user_id)
    tab = request.args.get("tab", "upcoming")
    today = date.today()

    query = UserBooking.query.filter_by(user_id=user_id)
    now = _now_ist()
    if tab == "upcoming":
        # Upcoming: show_date is today or future, confirmed
        bookings = query.filter(UserBooking.show_date >= today, UserBooking.status == "Confirmed").order_by(UserBooking.show_date).all()
        # Further filter: exclude shows that already started and passed (today's shows whose time has passed)
        # We keep it simple here — just filter by date; time-based filtering done in template
    elif tab == "past":
        bookings = query.filter(UserBooking.show_date < today).order_by(UserBooking.show_date.desc()).all()
    elif tab == "cancelled":
        bookings = query.filter_by(status="Cancelled").order_by(UserBooking.booked_at.desc()).all()
    elif tab == "messages":
        bookings = []
    else:
        bookings = query.order_by(UserBooking.booked_at.desc()).all()

    # Build a map: booking_id -> contact_message (for cancelled tab refund/reply info)
    cancel_msg_map = {}
    if tab == "cancelled" and bookings:
        booking_ids = [b.id for b in bookings]
        cancel_msgs = ContactMessage.query.filter(
            ContactMessage.booking_id.in_(booking_ids),
            ContactMessage.is_cancellation == True
        ).all()
        for cm in cancel_msgs:
            cancel_msg_map[cm.booking_id] = cm

    # All contact messages for this user's email (for Messages tab)
    all_messages = []
    if tab == "messages" and user:
        all_messages = ContactMessage.query.filter_by(email=user.email).order_by(
            ContactMessage.created_at.desc()
        ).all()

    # Unread reply count for nav badge
    unread_replies = 0
    if user:
        unread_replies = ContactMessage.query.filter_by(
            email=user.email, status="Responded"
        ).count()

    return render_template("user/bookings.html", bookings=bookings, tab=tab,
                           cancel_msg_map=cancel_msg_map,
                           all_messages=all_messages,
                           unread_replies=unread_replies,
                           now=_now_ist())


@user_bp.route("/book/<path:show_id>", methods=["GET", "POST"])
@login_required
@role_required("user")
def book_ticket(show_id):
    import types as _types
    from datetime import datetime, date as _date

    show = None

    # ── Try real DB show first ──
    try:
        show = db.session.execute(text("""
            SELECT s.show_id, s.show_date, s.start_time, s.price_per_ticket, s.available_seats,
                   m.title as movie_title, m.language, m.genre, m.duration,
                   t.name as theatre_name, t.city, t.location, sc.screen_number
            FROM shows s
            JOIN movies m ON m.movie_id = s.movie_id
            JOIN theaters t ON t.theater_id = s.theater_id
            JOIN screens sc ON sc.screen_id = s.screen_id
            WHERE s.show_id = :sid
        """), {"sid": show_id}).fetchone()
    except Exception:
        show = None

    # ── Handle synthetic show IDs: DEMO-<movie_id>-<day>-<theatre>-<slot>
    #                                FILL-<movie_id>-<date>-<theatre_idx>-<slot>
    #                                EXT-<movie_id>-<date>-<theatre_name>-<time>
    if not show and (show_id.startswith("GEN-") or show_id.startswith("DEMO-") or show_id.startswith("FILL-") or show_id.startswith("EXT-")):
        try:
            parts = show_id.split("-")
            prefix = parts[0]  # GEN / DEMO / FILL / EXT
            movie_id = parts[1]

            # Look up movie info
            movie_row = db.session.execute(
                text("SELECT title, language, genre, duration FROM movies WHERE movie_id = :mid"),
                {"mid": movie_id}
            ).fetchone()
            movie_title = movie_row.title if movie_row else "Movie"
            language    = movie_row.language if movie_row else "Hindi"
            genre       = movie_row.genre if movie_row else "Drama"
            duration    = movie_row.duration if movie_row else 150

            # Time slot sets — must match exactly what public.py generates
            timing_sets = [
                ["09:15 AM", "12:00 PM", "03:00 PM", "06:15 PM", "09:00 PM", "11:30 PM"],
                ["10:00 AM", "01:00 PM", "04:00 PM", "07:00 PM", "10:00 PM", "11:45 PM"],
                ["09:45 AM", "12:45 PM", "03:45 PM", "06:45 PM", "09:45 PM", "11:15 PM"],
            ]
            demo_theatres = [
                {"name": "PVR Cinemas",    "city": "Mumbai", "location": "Phoenix Mall, Lower Parel"},
                {"name": "INOX Multiplex", "city": "Mumbai", "location": "R-City Mall, Ghatkopar"},
                {"name": "Cinepolis",      "city": "Delhi",  "location": "DLF Mall of India, Noida"},
            ]
            demo_prices = [220, 180, 260]

            if prefix == "GEN":
                # GEN-<movie_id>-<YYYY>-<MM>-<DD>-<theatre_idx>-<slot_idx>
                # parts: [GEN, MV_XXX, YYYY, MM, DD, theatre_idx, slot_idx]
                date_str    = f"{parts[2]}-{parts[3]}-{parts[4]}"
                theatre_idx = int(parts[5])
                slot_idx    = int(parts[6])
                show_date   = _date.fromisoformat(date_str)
                timings     = timing_sets[theatre_idx % len(timing_sets)]
                start_time  = timings[slot_idx % len(timings)]

                # Resolve theatre: use real DB theatres if available, else demo
                db_theatres_list = db.session.execute(text("""
                    SELECT DISTINCT t.name, t.city, t.location, s.price_per_ticket
                    FROM shows s JOIN theaters t ON t.theater_id = s.theater_id
                    WHERE s.movie_id = :mid ORDER BY t.name
                """), {"mid": movie_id}).fetchall()

                if db_theatres_list:
                    th = db_theatres_list[theatre_idx % len(db_theatres_list)]
                    theatre_name = th.name
                    city         = th.city
                    location     = th.location
                    price        = th.price_per_ticket
                else:
                    th = demo_theatres[theatre_idx % len(demo_theatres)]
                    theatre_name = th["name"]
                    city         = th["city"]
                    location     = th["location"]
                    price        = demo_prices[theatre_idx % len(demo_prices)]
                screen = f"Screen {slot_idx + 1}"

            elif prefix == "DEMO":
                # DEMO-<movie_id>-<day_offset>-<theatre_idx>-<slot_idx>
                day_offset  = int(parts[2])
                theatre_idx = int(parts[3])
                slot_idx    = int(parts[4])
                theatre     = demo_theatres[theatre_idx % len(demo_theatres)]
                timings     = timing_sets[theatre_idx % len(timing_sets)]
                show_date   = _date.today().__class__.fromordinal(_date.today().toordinal() + day_offset)
                start_time  = timings[slot_idx % len(timings)]
                price       = demo_prices[theatre_idx % len(demo_prices)]
                screen      = f"Screen {slot_idx + 1}"
                theatre_name = theatre["name"]
                city         = theatre["city"]
                location     = theatre["location"]

            elif prefix == "FILL":
                # FILL-<movie_id>-<date>-<theatre_idx>-<slot_idx>
                date_str    = parts[2]
                theatre_idx = int(parts[3])
                slot_idx    = int(parts[4])
                theatre     = demo_theatres[theatre_idx % len(demo_theatres)]
                timings     = timing_sets[theatre_idx % len(timing_sets)]
                show_date   = _date.fromisoformat(date_str)
                start_time  = timings[slot_idx % len(timings)]
                price       = demo_prices[theatre_idx % len(demo_prices)]
                screen      = f"Screen {slot_idx + 1}"
                theatre_name = theatre["name"]
                city         = theatre["city"]
                location     = theatre["location"]

            else:  # EXT
                first_real = db.session.execute(text("""
                    SELECT t.name, t.city, t.location, s.price_per_ticket
                    FROM shows s JOIN theaters t ON t.theater_id = s.theater_id
                    WHERE s.movie_id = :mid LIMIT 1
                """), {"mid": movie_id}).fetchone()
                date_str   = parts[2]
                show_date  = _date.fromisoformat(date_str)
                remaining  = parts[3:]
                start_time = remaining[-2] + " " + remaining[-1] if len(remaining) >= 2 else "09:00 AM"
                theatre_name = first_real.name if first_real else "Wave Cinemas"
                city         = first_real.city if first_real else "Delhi"
                location     = first_real.location if first_real else ""
                price        = first_real.price_per_ticket if first_real else 220
                screen       = "Screen 1"

            show = _types.SimpleNamespace(
                show_id=show_id,
                show_date=show_date,
                start_time=start_time,
                price_per_ticket=price,
                available_seats=max(1, 173 - len(get_presold_seats(show_id))),
                movie_title=movie_title,
                language=language,
                genre=genre,
                duration=duration,
                theatre_name=theatre_name,
                city=city,
                location=location,
                screen_number=screen,
            )
        except Exception as e:
            show = None

    if not show:
        flash("Show not found.", "danger")
        return redirect(url_for("public.home"))

    if request.method == "POST":
        data = request.get_json() if request.is_json else request.form
        num_tickets = int(data.get("num_tickets", 1))
        payment_method = data.get("payment_method", "Online")
        seat_numbers = data.get("seat_numbers", "")
        snacks = data.get("snacks", "")
        client_total = data.get("total_amount")

        if num_tickets < 1 or num_tickets > 10:
            msg = "Invalid number of tickets (1-10 allowed)."
            if request.is_json:
                return jsonify({"success": False, "message": msg}), 400
            flash(msg, "danger")

        # Use client-computed total if provided (includes F&B), else compute server-side
        if client_total:
            total_amount = float(client_total)
        else:
            total_amount = num_tickets * (show.price_per_ticket or 150) + 30

        # For synthetic show IDs, store a placeholder show_id so the DB FK doesn't break
        db_show_id = show_id if not (show_id.startswith("GEN-") or show_id.startswith("DEMO-") or show_id.startswith("FILL-") or show_id.startswith("EXT-")) else None

        booking = UserBooking(
            user_id=session.get("user_id"),
            show_id=db_show_id,
            movie_title=show.movie_title,
            theatre_name=show.theatre_name,
            theatre_city=getattr(show, 'city', ''),
            show_date=show.show_date,
            show_time=show.start_time,
            num_tickets=num_tickets,
            total_amount=total_amount,
            payment_method=payment_method,
            status="Confirmed",
            booking_ref=gen_booking_ref(),
            seat_numbers=seat_numbers + (" | Snacks: " + snacks if snacks else ""),
            booked_at=_now_ist()   # use system local time to match server timezone
        )
        db.session.add(booking)
        db.session.commit()

        # ── Permanently lock the booked seats in memory until show ends + 3 hours ──
        if seat_numbers:
            booked_seat_list = [s.strip() for s in seat_numbers.split(",") if s.strip()]
            if booked_seat_list:
                unlock_dt = _show_unlock_datetime(show.show_date, show.start_time)
                if unlock_dt:
                    if show_id not in _seat_locks:
                        _seat_locks[show_id] = {}
                    for s in booked_seat_list:
                        _seat_locks[show_id][s] = {
                            "user_id": session.get("user_id"),
                            "expires": unlock_dt,
                            "permanent": True
                        }

        # Send booking confirmation email with PDF ticket
        try:
            user_obj = AppUser.query.get(session.get("user_id"))
            if user_obj and user_obj.email:
                _send_booking_confirmation_email(user_obj.email, user_obj.name, booking)
        except Exception:
            pass  # Email failure should not break the booking flow

        if request.is_json:
            return jsonify({"success": True, "booking_ref": booking.booking_ref,
                            "redirect": url_for("user.booking_confirmation", booking_id=booking.id)})
        return redirect(url_for("user.booking_confirmation", booking_id=booking.id))

    return render_template("user/book_ticket.html", show=show)


@user_bp.route("/booking/confirmation/<int:booking_id>")
@login_required
@role_required("user")
def booking_confirmation(booking_id):
    booking = UserBooking.query.filter_by(id=booking_id, user_id=session.get("user_id")).first_or_404()
    user = AppUser.query.get(session.get("user_id"))
    # Fetch extra movie details for PDF
    try:
        show_extra = db.session.execute(text("""
            SELECT m.genre, m.language, m.duration, t.location as theatre_location
            FROM shows s JOIN movies m ON m.movie_id = s.movie_id
            JOIN theaters t ON t.theater_id = s.theater_id
            WHERE s.show_id = :sid
        """), {"sid": booking.show_id}).fetchone()
        if show_extra:
            booking.genre = show_extra.genre
            booking.language = show_extra.language
            booking.duration = show_extra.duration
            booking.theatre_location = show_extra.theatre_location
        else:
            booking.genre = booking.language = booking.duration = booking.theatre_location = None
    except:
        booking.genre = booking.language = booking.duration = booking.theatre_location = None
    return render_template("user/confirmation.html", booking=booking, user=user)


@user_bp.route("/booking/<int:booking_id>/download-ticket")
@login_required
@role_required("user")
def download_ticket(booking_id):
    from flask import send_file
    booking = UserBooking.query.filter_by(id=booking_id, user_id=session.get("user_id")).first_or_404()
    pdf_bytes = _generate_ticket_pdf_bytes(booking)
    buf = BytesIO(pdf_bytes)
    filename = f"CineVerse_Ticket_{booking.booking_ref}.pdf"
    return send_file(buf, mimetype="application/pdf", as_attachment=True, download_name=filename)

@user_bp.route("/booking/<int:booking_id>/cancel", methods=["POST"])
@login_required
@role_required("user")
def cancel_booking(booking_id):
    from models.models import ContactMessage
    booking = UserBooking.query.filter_by(id=booking_id, user_id=session.get("user_id")).first_or_404()
    if booking.status == "Cancelled":
        return jsonify({"success": False, "message": "Already cancelled."}), 400
    data = request.get_json() or {}
    cancel_reason = data.get("reason", "Not specified")
    booking.status = "Cancelled"
    if hasattr(booking, 'cancel_reason'):
        booking.cancel_reason = cancel_reason[:500]

    # Get user info
    user = AppUser.query.get(session.get("user_id"))

    # Create a contact message so admin can see the cancellation, reply, and process refund
    cancel_message = (
        f"[CANCELLATION REQUEST]\n\n"
        f"Booking Ref: {booking.booking_ref}\n"
        f"Movie: {booking.movie_title}\n"
        f"Theatre: {booking.theatre_name}, {booking.theatre_city}\n"
        f"Show Date: {booking.show_date} at {booking.show_time}\n"
        f"Seats: {booking.seat_numbers or 'N/A'}\n"
        f"Amount Paid: \u20b9{booking.total_amount:.2f}\n\n"
        f"Cancellation Reason:\n{cancel_reason}"
    )
    contact_msg = ContactMessage(
        name=user.name,
        email=user.email,
        message=cancel_message,
        status="New",
        is_cancellation=True,
        booking_id=booking.id,
        refund_status="Pending"
    )
    db.session.add(contact_msg)
    db.session.commit()

    # ── Keep seats locked in memory until admin refunds ──
    # Seats remain locked (marked permanent, far-future expiry) so no one else can book them.
    # They will only be freed when admin marks refund as "Refunded" (handled in admin route).
    if booking.seat_numbers and booking.show_id:
        seats_to_lock = [s.strip() for s in booking.seat_numbers.split(",") if s.strip()]
        if seats_to_lock:
            sid = booking.show_id
            unlock_dt = _show_unlock_datetime(booking.show_date, booking.show_time)
            # If show hasn't passed, keep locked until show+3h; else use far future
            lock_expiry = unlock_dt if unlock_dt and unlock_dt > _now_ist() else datetime(2099, 12, 31)
            if sid not in _seat_locks:
                _seat_locks[sid] = {}
            for s in seats_to_lock:
                _seat_locks[sid][s] = {
                    "user_id": session.get("user_id"),
                    "expires": lock_expiry,
                    "permanent": True,
                    "pending_cancel": True   # flag: only unlock when admin refunds
                }

    refund_amount = booking.total_amount
    return jsonify({
        "success": True,
        "message": f"Booking cancelled. Your refund of \u20b9{refund_amount:.0f} will be processed after admin review.",
        "refund_amount": refund_amount
    })


LOCK_DURATION_MINUTES = 5   # seats temporarily locked during payment flow (minutes)

# All seat IDs in the theatre layout — must match book_ticket.html seat map
_ALL_SEAT_IDS = (
    [f"A{c}" for c in range(1, 13)] +
    [f"{r}{c}" for r in ["B","C","D","E","F","G","H"] for c in range(1, 22)] +
    [f"I{c}" for c in range(1, 15)]
)
TOTAL_SEATS = len(_ALL_SEAT_IDS)  # 173


def get_presold_seats(show_id: str) -> set:
    """
    Deterministically generate pre-sold seats for a show.
    Uses a hash of show_id so each show always gets the same 'sold' seats,
    simulating real prior bookings. Fill rate 50-70% per show.
    """
    import hashlib, random as _rnd
    h = int(hashlib.md5(show_id.encode()).hexdigest(), 16)
    rng = _rnd.Random(h)
    fill_pct = 0.50 + (h % 20) / 100.0
    num_sold = int(TOTAL_SEATS * fill_pct)
    return set(rng.sample(_ALL_SEAT_IDS, num_sold))


def _get_all_booked_seats_for_show(show_id: str) -> set:
    """
    Gather all user-booked seats for a show (DB bookings + pre-sold).
    For synthetic GEN-/DEMO- show IDs the DB stores show_id=NULL,
    so we also match on movie_title for those bookings.
    Cancelled bookings whose refund is still Pending are also kept locked
    (seats only freed when admin approves the cancellation).
    """
    from models.models import ContactMessage
    booked = set()

    # Helper: check if a cancelled booking still has pending refund (seats stay locked)
    def _pending_cancel_booking_ids():
        pending = set()
        for cm in ContactMessage.query.filter_by(is_cancellation=True, refund_status="Pending").all():
            if cm.booking_id:
                pending.add(cm.booking_id)
        return pending

    pending_cancel_ids = _pending_cancel_booking_ids()

    def _extract_seats_from_booking(b):
        if b.seat_numbers:
            part = b.seat_numbers.split(" | Snacks:")[0].split(" | Cancel")[0]
            return [s.strip() for s in part.split(",") if s.strip()]
        return []

    # 1. Direct DB match (works for real show_ids)
    for b in UserBooking.query.filter(
        UserBooking.show_id == show_id,
        UserBooking.status.in_(["Confirmed", "Cancelled"])
    ).all():
        # Include cancelled seats only if admin hasn't approved cancellation yet
        if b.status == "Cancelled" and b.id not in pending_cancel_ids:
            continue  # Admin approved — seats are freed
        for s in _extract_seats_from_booking(b):
            booked.add(s)

    # 2. Fallback for synthetic show IDs (stored as NULL in DB)
    if show_id.startswith(("GEN-", "DEMO-", "FILL-", "EXT-")):
        try:
            movie_id = show_id.split("-")[1]
            movie_row = db.session.execute(
                text("SELECT title FROM movies WHERE movie_id = :mid"), {"mid": movie_id}
            ).fetchone()
            if movie_row:
                for b in UserBooking.query.filter(
                    UserBooking.show_id == None,
                    UserBooking.movie_title == movie_row.title,
                    UserBooking.status.in_(["Confirmed", "Cancelled"])
                ).all():
                    if b.status == "Cancelled" and b.id not in pending_cancel_ids:
                        continue  # Admin approved — seats are freed
                    for s in _extract_seats_from_booking(b):
                        booked.add(s)
        except Exception:
            pass

    # 3. Add deterministic pre-sold seats
    booked.update(get_presold_seats(show_id))

    return booked


def _clean_locks(show_id):
    """Remove expired temporary locks for a show. Permanent booking locks are kept until their show expires."""
    now = _now_ist()
    if show_id in _seat_locks:
        _seat_locks[show_id] = {
            s: v for s, v in _seat_locks[show_id].items()
            if v["expires"] > now  # includes both temp and permanent — both expire at their own time
        }


@user_bp.route("/api/lock-seats/<path:show_id>", methods=["POST"])
@login_required
def lock_seats(show_id):
    """Lock selected seats immediately. Returns conflict list if any seat is taken."""
    data = request.get_json() or {}
    seats = data.get("seats", [])
    user_id = session.get("user_id")
    now = _now_ist()
    expiry = now + timedelta(minutes=LOCK_DURATION_MINUTES)

    if show_id not in _seat_locks:
        _seat_locks[show_id] = {}

    _clean_locks(show_id)

    # Check for conflicts — seats locked by ANOTHER user (including permanently booked seats)
    conflicts = []
    for seat in seats:
        lock = _seat_locks[show_id].get(seat)
        if lock and lock["user_id"] != user_id:
            conflicts.append(seat)
        elif lock and lock.get("permanent"):
            # Permanent lock by same user means already booked — still a conflict
            conflicts.append(seat)

    if conflicts:
        return jsonify({
            "success": False,
            "conflicts": conflicts,
            "message": f"Seat(s) {', '.join(conflicts)} were just selected by another user."
        }), 409

    # Lock all seats for this user, refreshing expiry (temporary/payment-phase lock)
    for seat in seats:
        _seat_locks[show_id][seat] = {"user_id": user_id, "expires": expiry, "permanent": False}

    return jsonify({
        "success": True,
        "locked_until": expiry.isoformat(),
        "lock_minutes": LOCK_DURATION_MINUTES
    })


@user_bp.route("/api/unlock-seats/<path:show_id>", methods=["POST"])
@login_required
def unlock_seats(show_id):
    """Release seat locks when user deselects or abandons."""
    data = request.get_json() or {}
    seats = data.get("seats", [])
    user_id = session.get("user_id")

    if show_id in _seat_locks:
        for seat in seats:
            lock = _seat_locks[show_id].get(seat)
            if lock and lock["user_id"] == user_id:
                del _seat_locks[show_id][seat]

    return jsonify({"success": True})


@user_bp.route("/api/seat-status/<path:show_id>")
def seat_status(show_id):
    """
    Return full seat status for polling:
    - booked:  confirmed bookings (permanent)
    - locked:  temporarily locked by another user
    - mine:    locked by the current session user
    """
    _clean_locks(show_id)

    current_user_id = session.get("user_id")
    now = _now_ist()

    # Permanently booked seats (real bookings + pre-sold simulation)
    booked_seats = _get_all_booked_seats_for_show(show_id)

    # Temporarily locked seats
    locked_seats = {}   # seat -> seconds_remaining
    my_seats = {}
    if show_id in _seat_locks:
        for seat, lock in _seat_locks[show_id].items():
            if lock["expires"] > now:
                secs = int((lock["expires"] - now).total_seconds())
                if lock["user_id"] == current_user_id:
                    my_seats[seat] = secs
                else:
                    locked_seats[seat] = secs

    return jsonify({
        "booked": list(booked_seats),
        "locked": locked_seats,   # {seat: seconds_remaining}
        "mine":   my_seats,       # {seat: seconds_remaining}
    })


@user_bp.route("/api/booked-seats/<path:show_id>")
def get_booked_seats(show_id):
    """Legacy endpoint — kept for backward compat, delegates to seat_status."""
    _clean_locks(show_id)
    current_user_id = session.get("user_id")
    now = _now_ist()

    booked_seats = _get_all_booked_seats_for_show(show_id)

    if show_id in _seat_locks:
        for seat, lock in _seat_locks[show_id].items():
            if lock["expires"] > now and lock["user_id"] != current_user_id:
                booked_seats.add(seat)

    return jsonify({"booked_seats": list(booked_seats)})


@user_bp.route("/profile", methods=["GET", "POST"])
@login_required
@role_required("user")
def profile():
    user = AppUser.query.get(session.get("user_id"))
    if request.method == "POST":
        data = request.get_json() if request.is_json else request.form
        user.name = data.get("name", user.name)
        user.phone = data.get("phone", user.phone)
        user.city = data.get("city", user.city)
        db.session.commit()
        session["user_name"] = user.name
        if request.is_json:
            return jsonify({"success": True, "message": "Profile updated."})
        flash("Profile updated.", "success")
    return render_template("user/profile.html", user=user)
