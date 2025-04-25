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
        data = request.form
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO bookings (name, destination, date) VALUES (?, ?, ?)", 
                       (data["name"], data["destination"], data["date"]))
        conn.commit()
        conn.close()
        return redirect(url_for("index"))
    return render_template("booking_form.html")

@app.route("/reschedule", methods=["GET", "POST"])
def reschedule():
    if request.method == "POST":
        data = request.form
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM bookings WHERE name = ? AND destination = ?", 
                       (data["name"], data["destination"]))
        result = cursor.fetchone()
        if not result:
            conn.close()
            return "Booking not found", 404
        booking_id = result[0]
        cursor.execute("UPDATE bookings SET date = ? WHERE id = ?", (data["new_date"], booking_id))
        cursor.execute("INSERT INTO reschedule (booking_id, new_date) VALUES (?, ?)", 
                       (booking_id, data["new_date"]))
        conn.commit()
        conn.close()
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