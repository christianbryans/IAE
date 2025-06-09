from flask import Flask, request, jsonify, render_template, redirect, url_for, flash, session
from flask_cors import CORS
from database import get_db_connection, init_db, register_user, get_user_by_username, verify_password
from datetime import datetime
from airports import get_airport_suggestions

app = Flask(__name__)
CORS(app)
app.secret_key = 'your-secret-key-here'  # Change this to a secure secret key

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
    
    if request.method == "POST":
        # Handle JSON or form data
        if request.is_json:
            data = request.get_json()
            departure_airport = data.get('departure_airport_code')
            destination_airport = data.get('destination_airport_code')
            date = data.get('date')
            passenger_name = data.get('passenger_name')
        else:
            departure_airport = request.form.get('departure_airport_code')
            destination_airport = request.form.get('destination_airport_code')
            date = request.form.get('date')
            passenger_name = request.form.get('passenger_name')

        if not all([departure_airport, destination_airport, date, passenger_name]):
            if request.is_json:
                return jsonify({"error": "All fields are required"}), 400
            flash("All fields are required", "danger")
            return redirect(url_for('booking'))

        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Get user information directly from database
            cursor.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],))
            user = cursor.fetchone()
            
            if not user:
                conn.close()
                flash('User not found. Please login again.', 'danger')
                return redirect(url_for('login'))
            
            cursor.execute('''
                INSERT INTO bookings (
                    user_id, passenger_name, departure_airport, destination_airport, 
                    booking_date, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                user['id'], passenger_name, departure_airport, destination_airport,
                date, datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            ))
            
            booking_id = cursor.lastrowid # Get the ID of the newly created booking

            conn.commit()
            conn.close()

            if request.is_json:
                return jsonify({"message": "Booking successful", "booking_id": booking_id}), 200
            flash("Booking successful! Please select your seat.", "success")
            return redirect(url_for('seat_selection', booking_id=booking_id))

        except Exception as e:
            print(f"Error creating booking: {e}")
            if request.is_json:
                return jsonify({"error": str(e)}), 500
            flash(f"Error creating booking: {str(e)}", "danger")
            return redirect(url_for('booking'))

    return render_template('booking_form.html')

@app.route("/reschedule/<int:booking_id>", methods=["GET", "POST"])
def reschedule(booking_id):
    if 'user_id' not in session:
        flash('Please login to reschedule your ticket', 'warning')
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get booking details and verify ownership
    cursor.execute('''
        SELECT b.*, u.full_name, u.email, u.phone
        FROM bookings b
        JOIN users u ON b.user_id = u.id
        WHERE b.id = ? AND b.user_id = ?
    ''', (booking_id, session['user_id']))
    
    booking = cursor.fetchone()
    
    if not booking:
        conn.close()
        flash('Ticket not found or you do not have permission to reschedule it', 'danger')
        return redirect(url_for('tickets'))
    
    if request.method == "POST":
        new_date = request.form.get('date')
        
        if not new_date:
            flash('Please select a new date', 'danger')
            return render_template('reschedule_form.html', booking=booking)
        
        try:
            # Update booking date
            cursor.execute('''
                UPDATE bookings 
                SET booking_date = ? 
                WHERE id = ? AND user_id = ?
            ''', (new_date, booking_id, session['user_id']))
            
            # Record reschedule history
            cursor.execute('''
                INSERT INTO reschedule (
                    booking_id, old_date, new_date, reschedule_date
                ) VALUES (?, ?, ?, ?)
            ''', (
                booking_id, 
                booking[4],  # old booking date
                new_date,
                datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            ))
            
            conn.commit()
            flash('Ticket rescheduled successfully!', 'success')
            return redirect(url_for('tickets'))
            
        except Exception as e:
            print(f"Error rescheduling ticket: {e}")
            flash('Error rescheduling ticket', 'danger')
            return render_template('reschedule_form.html', booking=booking)
    
    conn.close()
    return render_template('reschedule_form.html', booking=booking)

@app.route("/riwayat")
def riwayat():
    if 'user_id' not in session:
        flash('Please login to view your history', 'warning')
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    conn = get_db_connection()
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
               NULL AS amount, NULL AS status, NULL AS method, NULL AS reason, NULL AS seat_number
        FROM reschedule r
        JOIN bookings b ON r.booking_id = b.id
        WHERE b.user_id = ?
    ''', (user_id,))
    reschedules = cursor.fetchall()
    for row in reschedules:
        item = dict(row)
        item['link'] = url_for('reschedule', booking_id=row['booking_id']) # Link to specific reschedule
        all_history.append(item)

    # Fetch Cancellation History
    cursor.execute('''
        SELECT c.id AS item_id, 'Cancellation' AS type, c.created_at AS date,
               'Ticket ' || c.origin || ' to ' || c.destination || ' cancelled due to ' || c.reason AS description,
               NULL AS amount, NULL AS status, NULL AS method, c.reason AS reason, NULL AS seat_number
        FROM cancellations c
        WHERE c.user_id = ?
    ''', (user_id,))
    cancellations = cursor.fetchall()
    for row in cancellations:
        item = dict(row)
        item['link'] = url_for('cancel_ticket') # Link to cancel page (could be more specific if detailed history exists)
        all_history.append(item)

    # Fetch Payment History
    cursor.execute('''
        SELECT p.id AS item_id, 'Payment' AS type, p.created_at AS date,
               'Paid Rp' || p.amount || ' via ' || p.method || ' (Status: ' || p.status || ')' AS description,
               p.amount AS amount, p.status AS status, p.method AS method, NULL AS reason, NULL AS seat_number
        FROM payments p
        WHERE p.user_id = ?
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
        WHERE s.user_id = ?
    ''', (user_id,))
    seat_selections = cursor.fetchall()
    for row in seat_selections:
        item = dict(row)
        item['link'] = url_for('seat_selection') # Link to seat selection page
        all_history.append(item)

    # Sort all history items by date
    all_history.sort(key=lambda x: datetime.strptime(x['date'].split('.')[0], '%Y-%m-%d %H:%M:%S') if '.' in x['date'] else datetime.strptime(x['date'], '%Y-%m-%d %H:%M:%S'), reverse=True)
    
    conn.close()
    
    return render_template('riwayat.html', all_history=all_history)

@app.route("/tickets")
def tickets():
    if 'user_id' not in session:
        flash('Please login to view your tickets', 'warning')
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get user's tickets with user information
    cursor.execute('''
        SELECT b.*, u.email, u.phone
        FROM bookings b
        JOIN users u ON b.user_id = u.id
        WHERE b.user_id = ?
        ORDER BY b.booking_date DESC
    ''', (session['user_id'],))
    
    tickets = cursor.fetchall()
    conn.close()
    
    return render_template('tickets.html', tickets=tickets)

@app.route("/tickets/delete/<int:id>", methods=["POST"])
def delete_ticket(id):
    if 'user_id' not in session:
        flash('Please login to delete your ticket', 'warning')
        return redirect(url_for('login'))
    
    conn = get_db_connection()
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

    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get booking_id from URL parameter
    booking_id = request.args.get('booking_id', type=int)
    booking_data = None
    
    if booking_id:
        cursor.execute('''
            SELECT b.*, u.full_name 
            FROM bookings b
            JOIN users u ON b.user_id = u.id
            WHERE b.id = ? AND b.user_id = ?
        ''', (booking_id, session['user_id']))
        booking_data = cursor.fetchone()
        
        if not booking_data:
            flash('Booking not found or you do not have permission to cancel it.', 'danger')
            return redirect(url_for('tickets'))
    
    if request.method == 'POST':
        booking_id = request.form['booking_id']
        passenger_name = request.form['passenger']
        origin = request.form['origin']
        destination = request.form['destination']
        reason = request.form['reason']
        canceled_on = request.form['canceled_on']
        user_id = session['user_id']

        try:
            cursor.execute('SELECT id FROM bookings WHERE id = ? AND user_id = ?', (booking_id, user_id))
            existing_booking = cursor.fetchone()

            if not existing_booking:
                flash('Booking not found or you do not have permission to cancel it.', 'danger')
            else:
                cursor.execute('''
                    INSERT INTO cancellations (
                        booking_id, user_id, passenger_name, origin, destination, 
                        reason, canceled_on
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (booking_id, user_id, passenger_name, origin, destination, reason, canceled_on))
                
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
        SELECT c.*, b.departure_airport, b.destination_airport
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

    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get booking_id from URL parameter
    booking_id = request.args.get('booking_id', type=int)
    booking_data = None
    
    if booking_id:
        cursor.execute('''
            SELECT b.*, u.full_name, p.amount
            FROM bookings b
            JOIN users u ON b.user_id = u.id
            LEFT JOIN payments p ON b.id = p.booking_id
            WHERE b.id = ? AND b.user_id = ?
        ''', (booking_id, session['user_id']))
        booking_data = cursor.fetchone()
        
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
                    INSERT INTO payments (booking_id, user_id, passenger_name, amount, method, status, paid_on)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (booking_id, user_id, passenger_name, amount, refund_method, 'pending', refund_date))
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
        SELECT p.*, b.departure_airport, b.destination_airport
        FROM payments p
        JOIN bookings b ON p.booking_id = b.id
        WHERE p.user_id = ? AND p.status = 'pending'
        ORDER BY p.created_at DESC
    ''', (session['user_id'],))
    refund_history = cursor.fetchall()
    conn.close()

    return render_template('refund.html', refund_history=refund_history, booking_data=booking_data)

@app.route('/payment', methods=['GET', 'POST'])
def payment():
    if 'user_id' not in session:
        flash('Please login first', 'warning')
        return redirect(url_for('login'))
    
    booking_id = request.args.get('booking_id')
    if booking_id:
        # Get booking data
        booking_data = get_booking_by_id(booking_id)
        if not booking_data:
            flash('Booking not found', 'error')
            return redirect(url_for('tickets'))
        
        # Calculate payment amount based on route and seat
        base_price = 1000000  # Base price Rp 1,000,000
        seat_multiplier = {
            'A': 1.2,  # Premium seats (front row)
            'B': 1.1,  # Business seats
            'C': 1.0,  # Standard seats
            'D': 0.9   # Economy seats
        }
        
        # Get seat row (first character of seat number)
        seat_row = booking_data[6][0] if booking_data[6] else 'C'
        multiplier = seat_multiplier.get(seat_row, 1.0)
        
        # Calculate final amount
        amount = int(base_price * multiplier)
        
        if request.method == 'POST':
            payment_method = request.form.get('payment_method')
            payment_date = request.form.get('payment_date')
            
            if not all([payment_method, payment_date]):
                flash('Please fill in all required fields', 'error')
                return render_template('payment.html', booking_data=booking_data, amount=amount)
            
            try:
                # Insert payment record
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO payments (booking_id, amount, method, payment_date)
                    VALUES (?, ?, ?, ?)
                ''', (booking_id, amount, payment_method, payment_date))
                conn.commit()
                conn.close()
                
                flash('Payment successful!', 'success')
                return redirect(url_for('tickets'))
            except Exception as e:
                print(f"Error processing payment: {e}")
                flash('Error processing payment', 'error')
                return render_template('payment.html', booking_data=booking_data, amount=amount)
        
        # Get payment history
        payment_history = get_payment_history(session['user_id'])
        return render_template('payment.html', booking_data=booking_data, amount=amount, payment_history=payment_history)
    
    flash('No booking selected', 'error')
    return redirect(url_for('tickets'))

def get_booking_by_id(booking_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM bookings WHERE id = ?', (booking_id,))
    booking = cursor.fetchone()
    conn.close()
    return booking

def get_payment_history(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT p.*, b.passenger_name 
        FROM payments p
        JOIN bookings b ON p.booking_id = b.id
        WHERE b.user_id = ?
        ORDER BY p.payment_date DESC
    ''', (user_id,))
    history = cursor.fetchall()
    conn.close()
    return history

@app.route('/seat', methods=['GET', 'POST'])
def seat_selection():
    if 'user_id' not in session:
        flash('Please login first', 'warning')
        return redirect(url_for('login'))
    
    booking_id = request.args.get('booking_id')
    if booking_id:
        # Get booking data
        booking_data = get_booking_by_id(booking_id)
        if not booking_data:
            flash('Booking not found', 'error')
            return redirect(url_for('tickets'))
        
        if request.method == 'POST':
            seat_number = request.form.get('seat_number')
            passenger = request.form.get('passenger')
            
            if not seat_number:
                flash('Please select a seat', 'error')
                return render_template('seat.html', booking_data=booking_data)
            
            try:
                # Insert seat selection record
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO seat_selections (booking_id, passenger_name, seat_number, selected_on)
                    VALUES (?, ?, ?, ?)
                ''', (booking_id, passenger, seat_number, datetime.now().strftime('%Y-%m-%d')))
                conn.commit()
                conn.close()
                
                flash('Seat selection successful!', 'success')
                return redirect(url_for('payment', booking_id=booking_id))
            except Exception as e:
                print(f"Error selecting seat: {e}")
                flash('Error selecting seat', 'error')
                return render_template('seat.html', booking_data=booking_data)
        
        # Get seat selection history
        seat_selection_history = get_seat_selection_history(session['user_id'])
        return render_template('seat.html', booking_data=booking_data, seat_selection_history=seat_selection_history)
    
    flash('No booking selected', 'error')
    return redirect(url_for('tickets'))

def get_seat_selection_history(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT ss.*, b.passenger_name 
        FROM seat_selections ss
        JOIN bookings b ON ss.booking_id = b.id
        WHERE b.user_id = ?
        ORDER BY ss.selected_on DESC
    ''', (user_id,))
    history = cursor.fetchall()
    conn.close()
    return history

if __name__ == "__main__":
    init_db() # Ensure database tables are created
    app.run(debug=True)