# CineVerse - Movie Ticket Booking System
## Complete Full-Stack Application

A comprehensive movie ticket booking system built with Flask, PostgreSQL, and modern web technologies.

---

## 📋 Features Overview

### 1. **User Features**
- ✅ Home Page with movie listing and filters
- ✅ Movie Details Page (unchanged)
- ✅ **Date & Time Selection** - Single unified page showing next 7 days with time slots
- ✅ **Seat Selection** - Theater-style interactive seat layout with price calculation
- ✅ Booking Confirmation with booking reference
- ✅ **PDF Ticket Download** - Professional themed PDF with all booking details
- ✅ User Dashboard and Booking History
- ✅ User Profile Management

### 2. **Contact Management** (NEW)
- ✅ **Public Contact Page** - Users can submit inquiries
- ✅ Contact form with Name, Email, Message
- ✅ Theme-matched contact page styling
- ✅ Database storage of all messages

### 3. **Admin Dashboard** (ENHANCED)
- ✅ Dashboard with system overview
- ✅ Movie Management
- ✅ Theatre Management
- ✅ Screen Management
- ✅ Show Management
- ✅ User Management
- ✅ **Contact Messages Panel** (NEW)
  - View all customer messages
  - Mark as read/responded
  - Delete messages
  - Pagination support
- ✅ **Analytics Dashboard** (NEW)
  - Total bookings count
  - Total revenue statistics
  - Most booked movies chart
  - City-wise bookings pie chart
  - Bookings trend (last 30 days line chart)
  - Seat occupancy metrics

### 4. **Theatre Owner Features**
- ✅ Theatre management
- ✅ Show management
- ✅ Dashboard
- ✅ Theatre details and editing

### 5. **Authentication & Authorization**
- ✅ Login/Sign Up
- ✅ Role-based access (Admin, Theatre Owner, User, Analyst)
- ✅ Session management

---

## 🗄️ Database Structure

### New Tables Added:
1. **contact_messages** - Stores all contact form submissions
   - id, name, email, message, status, created_at, updated_at

### Enhanced Tables:
- All existing tables remain functional
- User bookings now capture seat numbers

---

## 📦 Installation & Setup

### Prerequisites
- Python 3.8+
- PostgreSQL database
- pip (Python package manager)

### Step 1: Install Dependencies
```bash
cd movie_booking_modified
pip install -r requirements.txt
```

### Step 2: Configure Environment
Create a `.env` file in the root directory:
```
FLASK_ENV=development
FLASK_APP=app.py
DATABASE_URL=postgresql://username:password@localhost:5432/cineverse_db
SECRET_KEY=your_secret_key_here
```

### Step 3: Initialize Database
```bash
# Create database migrations
flask db upgrade

# Or manually create tables
python -c "from app import create_app; app = create_app(); app.app_context().push()"
```

### Step 4: Load Sample Data (Optional)
```bash
python load_excel.py
```

### Step 5: Run the Application
```bash
python run.py
```

The app will be available at: **http://localhost:5000**

---

## 👤 Default Login Credentials

### Admin Account
- Email: `admin@bookmyshow.com`
- Password: `Admin@123`

### Analyst Account
- Email: `analyst@bookmyshow.com`
- Password: `Analyst@123`

---

## 🌐 Application Flow

### User Booking Flow:
1. **Landing Page** → Home with movie listing
2. **Movie Details** → Click "Book" to view movie information
3. **Date & Time Selection** → Single page showing next 7 days + time slots
4. **Seat Selection** → Interactive theater layout with seat picking
5. **Booking Confirmation** → Shows booking reference and details
6. **PDF Download** → Download professional ticket PDF

### Admin Flow:
1. Login → Admin Dashboard
2. Navigate to different sections
3. **Contact Messages** - View and manage customer inquiries
4. **Analytics** - View business metrics and trends

### Contact Flow (Public):
1. Click "Contact" in navigation
2. Fill contact form
3. Submit message
4. Message stored in database for admin review

---

## 🎨 UI/UX Features

### Theme Consistency:
- ✅ Dark theme (Netflix-style) applied throughout
- ✅ Red accent color (#E50914) for CTAs
- ✅ Consistent spacing and typography
- ✅ Responsive design for all screen sizes

### New Components:
1. **Contact Page**
   - Beautiful form layout
   - Info cards for contact details
   - Success/error feedback

2. **Seat Selection**
   - 8x12 seat grid
   - Color-coded seats (available, selected, booked)
   - Real-time price calculation
   - Booking summary panel

3. **Contact Messages Admin**
   - Card-based message display
   - Status badges
   - Action buttons
   - Pagination

4. **Analytics Dashboard**
   - Key metrics cards
   - Chart visualizations
   - Responsive grid layout

---

## 📝 Key Modifications Made

### Backend Changes:
1. ✅ Added `ContactMessage` model in `models/models.py`
2. ✅ Added contact form route in `routes/public.py`
3. ✅ Added contact management routes in `routes/admin.py`
4. ✅ Added analytics routes in `routes/admin.py`
5. ✅ Added PDF generation in `routes/user.py` using reportlab
6. ✅ Updated `requirements.txt` with reportlab

### Frontend Changes:
1. ✅ Created `templates/public/contact.html`
2. ✅ Created `templates/public/seat_selection.html`
3. ✅ Created `templates/admin/contact_messages.html`
4. ✅ Created `templates/admin/analytics.html`
5. ✅ Updated `templates/base.html` with contact link
6. ✅ Updated `templates/admin/base_admin.html` with new sidebar links

---

## 🔧 Configuration Options

### Email Configuration (Optional)
For sending emails, update in `config.py`:
```python
MAIL_SERVER = 'smtp.gmail.com'
MAIL_PORT = 587
MAIL_USERNAME = 'your_email@gmail.com'
MAIL_PASSWORD = 'your_app_password'
```

### PDF Customization
Edit the PDF generation in `routes/user.py` to customize:
- Colors
- Fonts
- Layout
- Company information

---

## 📱 Responsive Design

All pages are fully responsive:
- ✅ Desktop (1200px+)
- ✅ Tablet (768px - 1199px)
- ✅ Mobile (< 768px)

---

## 🛠️ API Endpoints

### Public APIs:
- `GET /` - Home page
- `GET /movie/<movie_id>` - Movie details
- `GET /movie/<movie_id>/book` - Date & Time selection
- `POST /contact` - Submit contact form
- `GET /contact` - Contact page

### User APIs:
- `POST /user/book/<show_id>` - Complete booking
- `GET /user/booking/<id>/confirmation` - Booking confirmation
- `GET /user/booking/<id>/download-ticket` - Download PDF ticket
- `GET /user/dashboard` - User dashboard
- `GET /user/bookings` - View bookings

### Admin APIs:
- `GET /admin/contact-messages` - View messages
- `POST /admin/contact-messages/<id>/mark-read` - Mark as read
- `POST /admin/contact-messages/<id>/delete` - Delete message
- `GET /admin/analytics` - Analytics dashboard

---

## 🐛 Troubleshooting

### Issue: Blank PDF
**Solution**: Ensure reportlab is installed: `pip install reportlab==4.0.9`

### Issue: Database connection error
**Solution**: Verify PostgreSQL is running and DATABASE_URL is correct in `.env`

### Issue: Messages not showing in admin
**Solution**: Check that ContactMessage model is created: `python -c "from models.models import ContactMessage; db.create_all()"`

---

## 📚 Technology Stack

- **Backend**: Flask 3.0.3
- **Database**: PostgreSQL
- **Frontend**: Bootstrap 5, HTML5, CSS3, JavaScript
- **PDF Generation**: reportlab 4.0.9
- **ORM**: SQLAlchemy 2.0.31
- **Authentication**: Flask sessions with password hashing

---

## 🚀 Future Enhancements

- Payment gateway integration (Razorpay/Stripe)
- Email notifications
- SMS alerts
- Advanced analytics (machine learning predictions)
- Mobile app
- QR code ticket validation
- Referral system

---

## 📄 License

This project is part of the CineVerse movie ticketing platform.

---

## 🤝 Support

For issues or questions:
- Email: support@cineverse.com
- Phone: +91 9999-999-999

---

## ✨ Highlights of New Features

### 1. Contact Management System
- Users can easily reach out with inquiries
- Admin can manage and track all messages
- Status tracking (New, Read, Responded)
- Professional contact page with multiple contact methods

### 2. Analytics Dashboard
- Real-time business metrics
- Visual representations of bookings data
- City-wise performance analysis
- Revenue tracking
- Trend analysis for decision making

### 3. Seat Selection Enhancement
- Interactive theater layout
- Real-time price calculation
- Visual feedback for selections
- Booked seat visualization
- Responsive grid for all screen sizes

### 4. PDF Ticket Generation
- Professional ticket design
- All booking details included
- Themed with application colors
- No blank page issues
- Easy download from confirmation page

---

**Version**: 5.1.0  
**Last Updated**: May 1, 2026  
**Developed for**: CineVerse Movie Booking Platform
