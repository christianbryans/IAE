from flask import Flask, request, jsonify, render_template, redirect, url_for, flash, session, g
from flask_cors import CORS
from database import get_db_connection, init_db, register_user, get_user_by_username, verify_password
from datetime import datetime
from airports import get_airport_suggestions
import sqlite3
from flask_graphql import GraphQLView
from schema import schema
import os

app = Flask(__name__)
CORS(app)
app.secret_key = 'your-secret-key-here'  # Change this to a secure secret key

# Add GraphQL endpoint
app.add_url_rule(
    '/graphql',
    view_func=GraphQLView.as_view(
        'graphql',
        schema=schema,
        graphiql=True  # Enable GraphiQL interface
    )
)

# Database setup
DATABASE = os.path.join('data', 'database.db')

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

@app.context_processor
def inject_now():
    return {'now': datetime.now()}

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = get_user_by_username(username)
        if user and verify_password(user, password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            flash('Login successful!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password', 'danger')
    
    return render_template('login.html')

@app.route("/signup", methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        email = request.form.get('email')
        full_name = request.form.get('full_name')
        phone = request.form.get('phone')
        address = request.form.get('address')
        
        # Validate passwords match
        if password != confirm_password:
            flash('Passwords do not match', 'danger')
            return render_template('signup.html')
        
        # Check if username already exists
        if get_user_by_username(username):
            flash('Username already exists', 'danger')
            return render_template('signup.html')
        
        # Create new user
        try:
            if register_user(username, password, full_name, email, phone):
                flash('Account created successfully! Please login.', 'success')
                return redirect(url_for('login'))
            else:
                flash('Username or email already exists. Please use a different one.', 'danger')
                return render_template('signup.html')
        except Exception as e:
            flash('Error creating account. Please try again.', 'danger')
            print(f"Error creating user: {e}")
    
    return render_template('signup.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('login'))

@app.route("/api/airports")
def search_airports():
    query = request.args.get('q', '')
    if not query:
        return jsonify([])
    return jsonify(get_airport_suggestions(query))

@app.route("/booking", methods=["GET", "POST"])
def booking():
    if 'user_id' not in session:
        flash('Please login to book a ticket', 'warning')
        return redirect(url_for('login'))
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Get all airlines for the form
    cursor.execute('SELECT * FROM airlines ORDER BY base_price')
    airlines = cursor.fetchall()
    
    if request.method == "POST":
        # Get form data
        passenger_name = request.form.get('passenger_name')
        departure = request.form.get('departure_airport_code')
        destination = request.form.get('destination_airport_code')
        date = request.form.get('date')
        airline_id = request.form.get('airline_id')

        # Debugging: Print received form data
        print(f"Received booking data: ")
        print(f"  User ID: {session['user_id']}")
        print(f"  Passenger Name: {passenger_name}")
        print(f"  Departure: {departure}")
        print(f"  Destination: {destination}")
        print(f"  Date: {date}")
        print(f"  Airline ID: {airline_id}")
        
        # Validate required fields
        if not all([passenger_name, departure, destination, date, airline_id]):
            flash('Please fill in all required fields', 'danger')
            return render_template('booking_form.html', airlines=airlines, today=datetime.now().strftime('%Y-%m-%d'))
        
        try:
            # Get airline price
            cursor.execute('SELECT base_price FROM airlines WHERE id = ?', (airline_id,))
            airline = cursor.fetchone()
            if not airline:
                flash('Selected airline not found', 'danger')
                return render_template('booking_form.html', airlines=airlines, today=datetime.now().strftime('%Y-%m-%d'))
            
            # Calculate total price (base price + any additional fees)
            total_price = airline[0]  # base_price
            
            # Insert booking
            cursor.execute('''
                INSERT INTO bookings (
                    user_id, airline_id, passenger_name, departure_airport, 
                    destination_airport, booking_date, total_price
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (session['user_id'], airline_id, passenger_name, departure, destination, date, total_price))
            
            # Debug: Print the last inserted row ID
            booking_id = cursor.lastrowid
            print(f"Created booking with ID: {booking_id}")
            
            # Verify the booking was created
            cursor.execute('SELECT * FROM bookings WHERE id = ?', (booking_id,))
            created_booking = cursor.fetchone()
            print(f"Verified booking: {dict(created_booking) if created_booking else 'Not found'}")
            
            conn.commit()
            flash('Booking successful! Please proceed to seat selection.', 'success')
            return redirect(url_for('seat_selection', booking_id=booking_id))
            
        except Exception as e:
            print(f"Error creating booking: {str(e)}")
            flash(f'Error creating booking: {str(e)}', 'danger')
            return render_template('booking_form.html', airlines=airlines, today=datetime.now().strftime('%Y-%m-%d'))
    
    return render_template('booking_form.html', airlines=airlines, today=datetime.now().strftime('%Y-%m-%d'))

@app.route('/reschedule', methods=['GET', 'POST'])
def reschedule():
    if 'user_id' not in session:
        flash('Please login first', 'warning')
        return redirect(url_for('login'))
    
    booking_id = request.args.get('booking_id')
    if not booking_id:
        flash('No booking selected', 'error')
        return redirect(url_for('tickets'))
    
    try:
        # Get booking data
        booking_data = get_booking_by_id(booking_id)
        if not booking_data:
            flash('Booking not found', 'error')
            return redirect(url_for('tickets'))
        
        if request.method == 'POST':
            new_date = request.form.get('new_date')
            
            if not new_date:
                flash('Please select a new date', 'error')
                return render_template('reschedule.html', 
                                     booking_data=booking_data,
                                     today=datetime.now().strftime('%Y-%m-%d'))
            
            try:
                conn = get_db()
                cursor = conn.cursor()
                
                # First, check if the booking exists and belongs to the user
                cursor.execute('SELECT * FROM bookings WHERE id = ? AND user_id = ?', 
                             (booking_id, session['user_id']))
                booking = cursor.fetchone()
                
                if not booking:
                    flash('Booking not found or you do not have permission to reschedule it', 'error')
                    return redirect(url_for('tickets'))
                
                # Insert reschedule record
                cursor.execute('''
                    INSERT INTO reschedule (booking_id, old_date, new_date, reschedule_date)
                    VALUES (?, ?, ?, ?)
                ''', (booking_id, booking_data['booking_date'], new_date, datetime.now().strftime('%Y-%m-%d')))
                
                # Update booking date
                cursor.execute('''
                    UPDATE bookings 
                    SET booking_date = ?
                    WHERE id = ? AND user_id = ?
                ''', (new_date, booking_id, session['user_id']))
                
                conn.commit()
                conn.close()
                
                flash('Reschedule successful!', 'success')
                return redirect(url_for('tickets'))
            except Exception as e:
                print(f"Database error during reschedule: {str(e)}")
                flash(f'Error rescheduling ticket: {str(e)}', 'error')
                return render_template('reschedule.html', 
                                     booking_data=booking_data,
                                     today=datetime.now().strftime('%Y-%m-%d'))
        
        # Get reschedule history
        reschedule_history = get_reschedule_history(session['user_id'])
        return render_template('reschedule.html', 
                             booking_data=booking_data, 
                             reschedule_history=reschedule_history,
                             today=datetime.now().strftime('%Y-%m-%d'))
    
    except Exception as e:
        print(f"Error in reschedule route: {str(e)}")
        flash(f'An error occurred: {str(e)}', 'error')
        return redirect(url_for('tickets'))

def get_reschedule_history(user_id):
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT r.id, r.booking_id, r.old_date, r.new_date, b.passenger_name, r.reschedule_date
            FROM reschedule r
            JOIN bookings b ON r.booking_id = b.id
            WHERE b.user_id = ?
            ORDER BY r.reschedule_date DESC
        ''', (user_id,))
        history = cursor.fetchall()
        conn.close()
        
        # Convert to list of dictionaries for easier template access
        formatted_history = []
        for record in history:
            formatted_history.append({
                'id': record[0],
                'booking_id': record[1],
                'old_date': record[2],
                'new_date': record[3],
                'passenger_name': record[4],
                'reschedule_date': record[5]
            })
        return formatted_history
    except Exception as e:
        print(f"Error fetching reschedule history: {str(e)}")
        return []

@app.route("/riwayat")
def riwayat():
    if 'user_id' not in session:
        flash('Please login to view your history', 'warning')
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    conn = get_db()
    cursor = conn.cursor()
    
    all_history = []

    # Fetch Booking History
    cursor.execute('''
        SELECT b.id AS item_id, 'Booking' AS type, b.created_at AS date,
               b.departure_airport || ' to ' || b.destination_airport AS description,
               NULL AS amount, NULL AS status, NULL AS method, NULL AS reason, NULL AS seat_number
        FROM bookings b
        WHERE b.user_id = ?
    ''', (user_id,))
    bookings = cursor.fetchall()
    for row in bookings:
        item = dict(row)
        item['link'] = url_for('tickets') # Link to My Tickets
        all_history.append(item)

    # Fetch Reschedule History
    cursor.execute('''
        SELECT r.id AS item_id, 'Reschedule' AS type, r.reschedule_date AS date,
               'From ' || r.old_date || ' to ' || r.new_date AS description,
               NULL AS amount, NULL AS status, NULL AS method, NULL AS reason, NULL AS seat_number,
               r.booking_id
        FROM reschedule r
        JOIN bookings b ON r.booking_id = b.id
        WHERE b.user_id = ?
    ''', (user_id,))
    reschedules = cursor.fetchall()
    for row in reschedules:
        item = dict(row)
        item['link'] = url_for('reschedule', booking_id=item['booking_id']) # Link to specific reschedule
        all_history.append(item)

    # Fetch Cancellation History
    cursor.execute('''
        SELECT c.id AS item_id, 'Cancellation' AS type, c.created_at AS date,
               b.departure_airport || ' to ' || b.destination_airport AS description,
               NULL AS amount, NULL AS status, NULL AS method, c.reason, NULL AS seat_number
        FROM cancellations c
        JOIN bookings b ON c.booking_id = b.id
        WHERE b.user_id = ?
    ''', (user_id,))
    cancellations = cursor.fetchall()
    for row in cancellations:
        item = dict(row)
        item['link'] = url_for('cancel_ticket') # Link to cancellation page
        all_history.append(item)

    # Fetch Payment History
    cursor.execute('''
        SELECT p.id AS item_id, 'Payment' AS type, p.created_at AS date,
               'Paid Rp' || p.amount || ' via ' || p.method || ' (Status: ' || p.status || ')' AS description,
               p.amount AS amount, p.status AS status, p.method AS method, NULL AS reason, NULL AS seat_number
        FROM payments p
        JOIN bookings b ON p.booking_id = b.id
        WHERE b.user_id = ?
    ''', (user_id,))
    payments = cursor.fetchall()
    for row in payments:
        item = dict(row)
        item['link'] = url_for('payment') # Link to payment page
        all_history.append(item)
        
    # Fetch Seat Selection History
    cursor.execute('''
        SELECT s.id AS item_id, 'Seat Selection' AS type, s.created_at AS date,
               'Selected seat ' || s.seat_number || ' for ' || s.passenger_name AS description,
               NULL AS amount, NULL AS status, NULL AS method, NULL AS reason, s.seat_number AS seat_number
        FROM seat_selections s
        JOIN bookings b ON s.booking_id = b.id
        WHERE b.user_id = ?
    ''', (user_id,))
    seat_selections = cursor.fetchall()
    for row in seat_selections:
        item = dict(row)
        item['link'] = url_for('seat_selection') # Link to seat selection page
        all_history.append(item)

    # Sort all history items by date
    def parse_date(date_str):
        try:
            # Try parsing as datetime first
            return datetime.strptime(date_str.split('.')[0], '%Y-%m-%d %H:%M:%S')
        except ValueError:
            try:
                # Try parsing as date
                return datetime.strptime(date_str, '%Y-%m-%d')
            except ValueError:
                # If both fail, return a very old date
                return datetime.min

    all_history.sort(key=lambda x: parse_date(x['date']), reverse=True)
    
    conn.close()
    
    return render_template('riwayat.html', all_history=all_history)

@app.route("/tickets")
def tickets():
    if 'user_id' not in session:
        flash('Please login first', 'warning')
        return redirect(url_for('login'))
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Get user's tickets with passenger name from bookings
    cursor.execute('''
        SELECT b.*, u.email, u.phone
        FROM bookings b
        JOIN users u ON b.user_id = u.id
        WHERE b.user_id = ?
        ORDER BY b.created_at DESC
    ''', (session['user_id'],))
    tickets = cursor.fetchall()
    conn.close()
    
    return render_template('tickets.html', tickets=tickets)

@app.route("/tickets/delete/<int:id>", methods=["POST"])
def delete_ticket(id):
    if 'user_id' not in session:
        flash('Please login to delete your ticket', 'warning')
        return redirect(url_for('login'))
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Verify ticket ownership
    cursor.execute('SELECT id FROM bookings WHERE id = ? AND user_id = ?', (id, session['user_id']))
    ticket = cursor.fetchone()
    
    if not ticket:
        conn.close()
        flash('Ticket not found or you do not have permission to delete it', 'danger')
        return redirect(url_for('tickets'))
    
    try:
        # Delete associated reschedule records first
        cursor.execute('DELETE FROM reschedule WHERE booking_id = ?', (id,))
        # Delete the ticket
        cursor.execute('DELETE FROM bookings WHERE id = ?', (id,))
        conn.commit()
        flash('Ticket deleted successfully', 'success')
    except Exception as e:
        print(f"Error deleting ticket: {e}")
        flash('Error deleting ticket', 'danger')
    finally:
        conn.close()
    
    return redirect(url_for('tickets'))

@app.route('/cancel', methods=['GET', 'POST'])
def cancel_ticket():
    if 'user_id' not in session:
        flash('Please login to cancel your ticket', 'warning')
        return redirect(url_for('login'))

    conn = get_db()
    cursor = conn.cursor()
    
    # Get booking_id from URL parameter
    booking_id = request.args.get('booking_id', type=int)
    booking_data = None
    
    if booking_id:
        cursor.execute('''
            SELECT b.* 
            FROM bookings b
            WHERE b.id = ? AND b.user_id = ?
        ''', (booking_id, session['user_id']))
        booking_data = dict(cursor.fetchone())
        
        if not booking_data:
            flash('Booking not found or you do not have permission to cancel it.', 'danger')
            return redirect(url_for('tickets'))
    
    if request.method == 'POST':
        booking_id = request.form['booking_id']
        reason = request.form['reason']
        canceled_on = request.form['canceled_on']
        user_id = session['user_id']

        try:
            cursor.execute('SELECT id, passenger_name, departure_airport, destination_airport FROM bookings WHERE id = ? AND user_id = ?', (booking_id, user_id))
            existing_booking = cursor.fetchone()

            if not existing_booking:
                flash('Booking not found or you do not have permission to cancel it.', 'danger')
            else:
                cursor.execute('''
                    INSERT INTO cancellations (
                        booking_id, user_id, passenger_name, departure_airport, 
                        destination_airport, reason, cancelled_on
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (booking_id, user_id, existing_booking[1], existing_booking[2], existing_booking[3], reason, canceled_on))
                
                # Delete the booking after cancellation
                cursor.execute('DELETE FROM bookings WHERE id = ?', (booking_id,))
                
                conn.commit()
                flash('Tiket berhasil dibatalkan!', 'success')
                return redirect(url_for('tickets'))
        except Exception as e:
            flash(f'Error canceling ticket: {e}', 'danger')
            print(f"Error canceling ticket: {e}")
        finally:
            conn.close()
        return redirect(url_for('cancel_ticket'))

    # Get cancellation history
    cursor.execute('''
        SELECT c.*, b.departure_airport AS origin, b.destination_airport AS destination
        FROM cancellations c
        JOIN bookings b ON c.booking_id = b.id
        WHERE c.user_id = ?
        ORDER BY c.created_at DESC
    ''', (session['user_id'],))
    cancel_history = cursor.fetchall()
    conn.close()

    return render_template('cancel.html', cancel_history=cancel_history, booking_data=booking_data)

@app.route('/refund', methods=['GET', 'POST'])
def refund():
    if 'user_id' not in session:
        flash('Please login to request a refund', 'warning')
        return redirect(url_for('login'))

    conn = get_db()
    cursor = conn.cursor()
    
    # Get booking_id from URL parameter
    booking_id = request.args.get('booking_id', type=int)
    booking_data = None
    
    if booking_id:
        cursor.execute('''
            SELECT b.*, u.full_name, p.amount as paid_amount
            FROM bookings b
            JOIN users u ON b.user_id = u.id
            LEFT JOIN payments p ON b.id = p.booking_id AND p.status = 'completed'
            WHERE b.id = ? AND b.user_id = ?
        ''', (booking_id, session['user_id']))
        booking_data = dict(cursor.fetchone())
        
        if not booking_data:
            flash('Booking not found or you do not have permission to request refund for it.', 'danger')
            return redirect(url_for('tickets'))
    
    if request.method == 'POST':
        booking_id = request.form['booking_id']
        passenger_name = request.form['passenger']
        amount = request.form['amount']
        refund_method = request.form['refund_method']
        refund_reason = request.form['refund_reason']
        refund_date = request.form['refund_date']
        user_id = session['user_id']
        bank_account = request.form.get('bank_account', '') # Optional

        try:
            cursor.execute('SELECT id FROM bookings WHERE id = ? AND user_id = ?', (booking_id, user_id))
            existing_booking = cursor.fetchone()

            if not existing_booking:
                flash('Booking not found or you do not have permission to request refund for it.', 'danger')
            else:
                cursor.execute('''
                    INSERT INTO refunds (booking_id, user_id, passenger_name, amount, method, reason, refund_date)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (booking_id, user_id, passenger_name, amount, refund_method, refund_reason, refund_date))
                conn.commit()
                flash('Permintaan refund diajukan!', 'success')
                return redirect(url_for('tickets'))
        except Exception as e:
            flash(f'Error requesting refund: {e}', 'danger')
            print(f"Error requesting refund: {e}")
        finally:
            conn.close()
        return redirect(url_for('refund'))

    # Get refund history
    cursor.execute('''
        SELECT r.id, r.booking_id, r.passenger_name, r.amount, r.reason, r.refund_date, p.method
        FROM refunds r
        JOIN bookings b ON r.booking_id = b.id
        LEFT JOIN payments p ON r.booking_id = p.booking_id
        WHERE b.user_id = ?
        ORDER BY r.created_at DESC
    ''', (session['user_id'],))
    refund_history = cursor.fetchall()
    conn.close()

    formatted_refund_history = []
    for record in refund_history:
        formatted_refund_history.append({
            'id': record[0],
            'booking_id': record[1],
            'passenger_name': record[2],
            'amount': record[3],
            'reason': record[4],
            'refund_date': record[5],
            'method': record[6]
        })

    return render_template('refund.html', refund_history=formatted_refund_history, booking_data=booking_data)

def get_payment_history(user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT p.id, p.booking_id, p.amount, p.method, p.payment_date, p.status
        FROM payments p
        JOIN bookings b ON p.booking_id = b.id
        WHERE b.user_id = ?
        ORDER BY p.payment_date DESC
    ''', (user_id,))
    history = cursor.fetchall()
    
    # Convert to list of dictionaries for easier template access
    formatted_history = []
    for record in history:
        formatted_history.append({
            'id': record[0],
            'booking_id': record[1],
            'amount': record[2],
            'method': record[3],
            'payment_date': record[4],
            'status': record[5]
        })
    return formatted_history

@app.route('/payment', methods=['GET', 'POST'])
def payment():
    if 'user_id' not in session:
        flash('Please login first', 'warning')
        return redirect(url_for('login'))
    
    booking_id = request.args.get('booking_id')
    if not booking_id:
        flash('No booking selected', 'error')
        return redirect(url_for('tickets'))
    
    # Get booking data
    booking_data = get_booking_by_id(booking_id)
    if not booking_data:
        flash('Booking not found', 'error')
        return redirect(url_for('tickets'))
    
    # Calculate amount based on seat class
    base_price = 1000000  # Base price Rp 1,000,000
    seat_multiplier = {
        'A': 1.2,  # Premium seats (front row)
        'B': 1.1,  # Business seats
        'C': 1.0,  # Standard seats
        'D': 0.9   # Economy seats
    }
    
    # Get seat row (first character of seat number)
    seat_row = booking_data['seat_number'][0] if booking_data['seat_number'] else 'C'
    multiplier = seat_multiplier.get(seat_row, 1.0)
    
    # Calculate final amount
    amount = int(base_price * multiplier)
    
    if request.method == 'POST':
        payment_method = request.form.get('payment_method')
        
        if not payment_method:
            flash('Please select a payment method', 'error')
            return render_template('payment.html', booking_data=booking_data, amount=amount)
        
        try:
            # Insert payment record with current date
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO payments (booking_id, amount, method, payment_date)
                VALUES (?, ?, ?, ?)
            ''', (booking_id, amount, payment_method, datetime.now().strftime('%Y-%m-%d')))
            conn.commit()
            
            flash('Payment successful!', 'success')
            return redirect(url_for('tickets'))
        except Exception as e:
            print(f"Error processing payment: {e}")
            flash('Error processing payment', 'error')
            return render_template('payment.html', booking_data=booking_data, amount=amount)
    
    # Get payment history for GET requests
    payment_history = get_payment_history(session['user_id'])
    return render_template('payment.html', booking_data=booking_data, amount=amount, payment_history=payment_history)

def get_booking_by_id(booking_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT b.*, a.name as airline_name, a.code as airline_code, a.logo_url as airline_logo
        FROM bookings b
        JOIN airlines a ON b.airline_id = a.id
        WHERE b.id = ?
    ''', (booking_id,))
    booking = cursor.fetchone()
    
    if booking:
        # Convert to dictionary with column names
        return dict(booking)
    return None

@app.route('/seat_selection', methods=['GET', 'POST'])
def seat_selection():
    if 'user_id' not in session:
        flash('Please login to select your seat', 'warning')
        return redirect(url_for('login'))
    
    booking_id = request.args.get('booking_id')
    if not booking_id:
        flash('No booking selected', 'warning')
        return redirect(url_for('tickets'))
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Get booking details with airline information
    cursor.execute('''
        SELECT b.*, a.name as airline_name, a.code as airline_code, a.logo_url as airline_logo
        FROM bookings b
        JOIN airlines a ON b.airline_id = a.id
        WHERE b.id = ? AND b.user_id = ?
    ''', (booking_id, session['user_id']))
    booking = cursor.fetchone()
    
    if not booking:
        conn.close()
        flash('Booking not found or you do not have permission to select a seat', 'danger')
        return redirect(url_for('tickets'))
    
    # Convert booking to dictionary to access by key
    booking_dict = dict(booking)
    
    # Get occupied seats
    cursor.execute('''
        SELECT DISTINCT b.seat_number
        FROM bookings b
        LEFT JOIN cancellations c ON b.id = c.booking_id
        WHERE b.booking_date = ?
        AND b.seat_number IS NOT NULL
        AND c.booking_id IS NULL
        AND b.id != ?
    ''', (booking_dict['booking_date'], booking_id))
    occupied_seats = [row[0] for row in cursor.fetchall()]
    
    # Get currently selected seat
    cursor.execute('SELECT seat_number FROM bookings WHERE id = ?', (booking_id,))
    selected_seat_data = cursor.fetchone()
    selected_seat = selected_seat_data[0] if selected_seat_data else None
    
    # Get user's active bookings for the same date
    cursor.execute('''
        SELECT b.id, b.passenger_name, b.seat_number
        FROM bookings b
        LEFT JOIN cancellations c ON b.id = c.booking_id
        WHERE b.user_id = ?
        AND b.booking_date = ?
        AND c.booking_id IS NULL
        AND b.id != ?
        AND b.seat_number IS NOT NULL
    ''', (session['user_id'], booking_dict['booking_date'], booking_id))
    user_bookings = [{'id': row[0], 'passenger_name': row[1], 'seat_number': row[2]} for row in cursor.fetchall()]
    
    # Debug print
    print(f"Flight date: {booking_dict['booking_date']}")
    print(f"Occupied seats received from DB: {occupied_seats}")
    print(f"Selected seat received from DB: {selected_seat}")
    print(f"User bookings received from DB: {user_bookings}")
    
    if request.method == 'POST':
        seat_number = request.form.get('seat_number')
        if not seat_number:
            flash('Please select a seat', 'warning')
            return redirect(url_for('seat_selection', booking_id=booking_id))
        
        try:
            # Check if seat is already taken
            if seat_number in occupied_seats:
                flash('This seat is already taken', 'warning')
                return redirect(url_for('seat_selection', booking_id=booking_id))
            
            # Update booking with seat number
            cursor.execute('''
                UPDATE bookings 
                SET seat_number = ?
                WHERE id = ?
            ''', (seat_number, booking_id))
            
            conn.commit()
            flash('Seat selected successfully! Please proceed to payment.', 'success')
            return redirect(url_for('payment', booking_id=booking_id))
            
        except Exception as e:
            print(f"Error selecting seat: {str(e)}")
            flash(f'Error selecting seat: {str(e)}', 'danger')
            return redirect(url_for('seat_selection', booking_id=booking_id))
    
    conn.close()
    return render_template('seat_selection.html', 
                         booking=booking_dict,
                         occupied_seats=occupied_seats,
                         selected_seat=selected_seat,
                         user_bookings=user_bookings)

if __name__ == "__main__":
    init_db()
    app.run(debug=True)