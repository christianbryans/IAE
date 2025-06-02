from flask import Flask, request, jsonify, render_template, redirect, url_for, flash, session
from flask_cors import CORS
from database import get_db_connection, init_db, create_user, get_user_by_username, verify_password
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
            if create_user(username, password, full_name, email, phone, address):
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
            departure_airport = data.get('departure_airport')
            destination_airport = data.get('destination_airport')
            date = data.get('date')
        else:
            departure_airport = request.form.get('departure_airport')
            destination_airport = request.form.get('destination_airport')
            date = request.form.get('date')

        if not all([departure_airport, destination_airport, date]):
            if request.is_json:
                return jsonify({"error": "All fields are required"}), 400
            flash("All fields are required", "danger")
            return redirect(url_for('booking'))

        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Get user information
            user = get_user_by_username(session['username'])
            
            cursor.execute('''
                INSERT INTO bookings (
                    user_id, departure_airport, destination_airport, 
                    booking_date, created_at
                ) VALUES (?, ?, ?, ?, ?)
            ''', (
                user['id'], departure_airport, destination_airport,
                date, datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            ))
            
            conn.commit()
            conn.close()

            if request.is_json:
                return jsonify({"message": "Booking successful"}), 200
            flash("Booking successful!", "success")
            return redirect(url_for('tickets'))

        except Exception as e:
            print(f"Error creating booking: {e}")
            if request.is_json:
                return jsonify({"error": "Error creating booking"}), 500
            flash("Error creating booking", "danger")
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
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get user's reschedule history with booking and user information
    cursor.execute('''
        SELECT r.*, b.departure_airport, b.destination_airport, u.full_name
        FROM reschedule r
        JOIN bookings b ON r.booking_id = b.id
        JOIN users u ON b.user_id = u.id
        WHERE b.user_id = ?
        ORDER BY r.reschedule_date DESC
    ''', (session['user_id'],))
    
    history = cursor.fetchall()
    conn.close()
    
    return render_template('riwayat.html', history=history)

@app.route("/tickets")
def tickets():
    if 'user_id' not in session:
        flash('Please login to view your tickets', 'warning')
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get user's tickets with user information
    cursor.execute('''
        SELECT b.*, u.full_name, u.email, u.phone
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

if __name__ == "__main__":
    app.run(debug=True)