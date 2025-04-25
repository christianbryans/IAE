from flask import Flask, request, jsonify, render_template, redirect, url_for
from flask_cors import CORS
from database import get_db_connection, init_db

app = Flask(__name__)
CORS(app)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/booking", methods=["GET", "POST"])
def booking():
    if request.method == "POST":
        # Handle JSON or form data
        if request.is_json:
            data = request.get_json()
            name = data.get("name")
            destination = data.get("destination")
            date = data.get("date")
        else:
            data = request.form
            name = data.get("name")
            destination = data.get("destination")
            date = data.get("date")

        # Validate required fields
        if not all([name, destination, date]):
            return jsonify({"error": "Missing required fields"}), 400

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO bookings (name, destination, date) VALUES (?, ?, ?)", 
                       (name, destination, date))
        conn.commit()
        conn.close()

        if request.is_json:
            return jsonify({"message": "Booking created successfully"}), 201
        return redirect(url_for("index"))
    
    return render_template("booking_form.html")

@app.route("/reschedule", methods=["GET", "POST"])
def reschedule():
    if request.method == "POST":
        # Handle JSON or form data
        if request.is_json:
            data = request.get_json()
            name = data.get("name")
            destination = data.get("destination")
            new_date = data.get("new_date")
        else:
            data = request.form
            name = data.get("name")
            destination = data.get("destination")
            new_date = data.get("new_date")

        # Validate required fields
        if not all([name, destination, new_date]):
            return jsonify({"error": "Missing required fields"}), 400

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM bookings WHERE name = ? AND destination = ?", 
                       (name, destination))
        result = cursor.fetchone()
        
        if not result:
            conn.close()
            if request.is_json:
                return jsonify({"error": "Booking not found"}), 404
            return "Booking not found", 404
        
        booking_id = result[0]
        cursor.execute("UPDATE bookings SET date = ? WHERE id = ?", (new_date, booking_id))
        cursor.execute("INSERT INTO reschedule (booking_id, new_date) VALUES (?, ?)", 
                       (booking_id, new_date))
        conn.commit()
        conn.close()

        if request.is_json:
            return jsonify({"message": "Booking rescheduled successfully"}), 200
        return redirect(url_for("index"))
    
    return render_template("reschedule_form.html")

@app.route("/riwayat")
def riwayat():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT r.id, b.name, b.destination, r.new_date FROM reschedule r JOIN bookings b ON r.booking_id = b.id ORDER BY r.id DESC")
    data = cursor.fetchall()
    conn.close()
    return render_template("riwayat.html", riwayat=data)

@app.route("/tickets")
def tickets():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM bookings")
    data = cursor.fetchall()
    conn.close()
    return render_template("tickets.html", tickets=data)

@app.route("/tickets/delete/<int:id>", methods=["POST"])
def delete_ticket(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM bookings WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for("tickets"))

if __name__ == "__main__":
    init_db()
    app.run(debug=True)