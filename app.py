from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import os
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'  # Change this to a secure secret key

# Ensure the data directory exists
data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
if not os.path.exists(data_dir):
    os.makedirs(data_dir)

# Use absolute path for database
db_path = os.path.join(data_dir, 'database.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Airport data
AIRPORTS = [
    {'code': 'CGK', 'name': 'Soekarno-Hatta International Airport', 'city': 'Jakarta'},
    {'code': 'DPS', 'name': 'Ngurah Rai International Airport', 'city': 'Denpasar'},
    {'code': 'SUB', 'name': 'Juanda International Airport', 'city': 'Surabaya'},
    {'code': 'MES', 'name': 'Kualanamu International Airport', 'city': 'Medan'},
    {'code': 'UPG', 'name': 'Sultan Hasanuddin International Airport', 'city': 'Makassar'},
    {'code': 'KNO', 'name': 'Kualanamu International Airport', 'city': 'Medan'},
    {'code': 'LOP', 'name': 'Lombok International Airport', 'city': 'Lombok'},
    {'code': 'PNK', 'name': 'Supadio International Airport', 'city': 'Pontianak'},
    {'code': 'BTG', 'name': 'Batu Licin Airport', 'city': 'Batu Licin'},
    {'code': 'BDO', 'name': 'Husein Sastranegara International Airport', 'city': 'Bandung'},
    {'code': 'SRG', 'name': 'Achmad Yani International Airport', 'city': 'Semarang'},
    {'code': 'YIA', 'name': 'Yogyakarta International Airport', 'city': 'Yogyakarta'},
    {'code': 'PLM', 'name': 'Sultan Mahmud Badaruddin II International Airport', 'city': 'Palembang'},
    {'code': 'PKU', 'name': 'Sultan Syarif Kasim II International Airport', 'city': 'Pekanbaru'},
    {'code': 'BTH', 'name': 'Hang Nadim International Airport', 'city': 'Batam'},
    {'code': 'KUL', 'name': 'Kuala Lumpur International Airport', 'city': 'Kuala Lumpur'},
    {'code': 'SIN', 'name': 'Changi International Airport', 'city': 'Singapore'},
    {'code': 'BKK', 'name': 'Suvarnabhumi International Airport', 'city': 'Bangkok'},
    {'code': 'HKG', 'name': 'Hong Kong International Airport', 'city': 'Hong Kong'},
    {'code': 'NRT', 'name': 'Narita International Airport', 'city': 'Tokyo'},
]

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# User Model
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# Booking Model
class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    passenger_name = db.Column(db.String(100), nullable=False)
    departure_airport = db.Column(db.String(100), nullable=False)
    destination_airport = db.Column(db.String(100), nullable=False)
    booking_date = db.Column(db.DateTime, nullable=False)
    seat_number = db.Column(db.String(10))
    status = db.Column(db.String(20), default='active')
    base_price = db.Column(db.Float, nullable=False, default=0.0)
    total_price = db.Column(db.Float, nullable=False, default=0.0)

    def calculate_price(self):
        # Base price calculation based on route
        base_prices = {
            'CGK-DPS': 1500000,  # Jakarta to Bali
            'CGK-SUB': 1200000,  # Jakarta to Surabaya
            'CGK-MES': 1800000,  # Jakarta to Medan
            'CGK-UPG': 2000000,  # Jakarta to Makassar
            'DPS-SUB': 1300000,  # Bali to Surabaya
            'DPS-CGK': 1500000,  # Bali to Jakarta
            'SUB-CGK': 1200000,  # Surabaya to Jakarta
            'MES-CGK': 1800000,  # Medan to Jakarta
            'UPG-CGK': 2000000,  # Makassar to Jakarta
        }
        
        # Get airport codes
        dep_code = self.departure_airport.split(' - ')[0]
        dest_code = self.destination_airport.split(' - ')[0]
        route = f"{dep_code}-{dest_code}"
        
        # Set base price
        self.base_price = base_prices.get(route, 1000000)  # Default price if route not found
        
        # Calculate total price (base price + seat price if selected)
        self.total_price = self.base_price
        if self.seat_number:
            # Add seat price based on seat type
            if self.seat_number.startswith('A') or self.seat_number.startswith('F'):
                self.total_price += 500000  # Window seats
            elif self.seat_number.startswith('B') or self.seat_number.startswith('E'):
                self.total_price += 300000  # Middle seats
            else:
                self.total_price += 400000  # Aisle seats

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('index'))
        flash('Invalid username or password')
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists')
            return redirect(url_for('signup'))
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered')
            return redirect(url_for('signup'))
        
        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/booking', methods=['GET', 'POST'])
@login_required
def booking():
    if request.method == 'POST':
        # Handle booking form submission
        passenger_name = request.form.get('passenger_name')
        departure = request.form.get('departure')
        destination = request.form.get('destination')
        date = request.form.get('date')
        
        booking = Booking(
            user_id=current_user.id,
            passenger_name=passenger_name,
            departure_airport=departure,
            destination_airport=destination,
            booking_date=datetime.strptime(date, '%Y-%m-%d')
        )
        booking.calculate_price()  # Calculate initial price
        db.session.add(booking)
        db.session.commit()
        
        return redirect(url_for('seat_selection', booking_id=booking.id))
    return render_template('booking_form.html', now=datetime.now(), airports=AIRPORTS)

@app.route('/seat-selection/<int:booking_id>', methods=['GET', 'POST'])
@login_required
def seat_selection(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    # Find all occupied seats for this flight (same route and date, and not cancelled)
    all_bookings = Booking.query.filter(
        Booking.departure_airport == booking.departure_airport,
        Booking.destination_airport == booking.destination_airport,
        Booking.booking_date == booking.booking_date,
        Booking.seat_number != None,
        Booking.status.in_(['active', 'paid'])
    ).all()
    occupied_seats = [b.seat_number for b in all_bookings]
    my_seat = booking.seat_number
    if request.method == 'POST':
        seat_number = request.form.get('seat_number')
        # Prevent double booking (except for user's own seat)
        if seat_number in occupied_seats and seat_number != my_seat:
            flash('Kursi sudah dipesan, silakan pilih kursi lain.', 'danger')
        else:
            booking.seat_number = seat_number
            booking.calculate_price()  # Recalculate price with seat
            db.session.commit()
            return redirect(url_for('payment', booking_id=booking_id))
    return render_template('seat_selection.html', booking=booking, occupied_seats=occupied_seats, my_seat=my_seat)

@app.route('/payment/<int:booking_id>', methods=['GET', 'POST'])
@login_required
def payment(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    if not booking.seat_number:
        flash('Silakan pilih kursi terlebih dahulu.', 'warning')
        return redirect(url_for('seat_selection', booking_id=booking_id))
    booking.calculate_price()  # Ensure price is always up-to-date
    if request.method == 'POST':
        # Handle payment processing
        booking.status = 'paid'
        db.session.commit()
        return redirect(url_for('tickets'))
    return render_template('payment.html', booking=booking)

@app.route('/tickets')
@login_required
def tickets():
    user_bookings = Booking.query.filter_by(user_id=current_user.id).all()
    return render_template('tickets.html', tickets=user_bookings)

@app.route('/reschedule/<int:booking_id>', methods=['GET', 'POST'])
@login_required
def reschedule(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    # Only allow reschedule if status is 'active' or 'paid'
    if booking.status not in ['active', 'paid']:
        flash('Tiket ini tidak dapat di-reschedule.', 'danger')
        return redirect(url_for('tickets'))
    if request.method == 'POST':
        new_date = request.form.get('new_date')
        booking.booking_date = datetime.strptime(new_date, '%Y-%m-%d')
        db.session.commit()
        flash('Booking rescheduled successfully')
        return redirect(url_for('tickets'))
    return render_template('reschedule.html', booking_data=booking, now=datetime.now())

@app.route('/cancel/<int:booking_id>', methods=['GET', 'POST'])
@login_required
def cancel_ticket(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    if request.method == 'POST':
        booking.status = 'cancelled'
        db.session.commit()
        flash('Ticket cancelled successfully')
        return redirect(url_for('tickets'))
    return render_template('cancel.html', booking_data=booking, now=datetime.now())

@app.route('/refund/<int:booking_id>', methods=['GET', 'POST'])
@login_required
def refund(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    if request.method == 'POST':
        booking.status = 'refunded'
        db.session.commit()
        flash('Refund request submitted successfully')
        return redirect(url_for('tickets'))
    return render_template('refund.html', booking_data=booking, now=datetime.now())

@app.route('/reschedule-form/<int:booking_id>', methods=['GET', 'POST'])
@login_required
def reschedule_form(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    if request.method == 'POST':
        new_date = request.form.get('new_date')
        booking.booking_date = datetime.strptime(new_date, '%Y-%m-%d')
        db.session.commit()
        flash('Booking rescheduled successfully')
        return redirect(url_for('tickets'))
    return render_template('reschedule_form.html', booking_data=booking, now=datetime.now())

@app.route('/riwayat')
@login_required
def riwayat():
    user_bookings = Booking.query.filter_by(user_id=current_user.id).all()
    return render_template('riwayat.html', bookings=user_bookings)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True) 