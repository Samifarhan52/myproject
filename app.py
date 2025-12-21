import os
import sqlite3
from datetime import datetime, date
from functools import wraps

from flask import (
    Flask, render_template, request,
    redirect, url_for, session, flash
)

from werkzeug.security import generate_password_hash, check_password_hash
from modules.email_utils import send_email

# -----------------------------------------------------------------------------
# App setup
# -----------------------------------------------------------------------------
app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev_secret_key")
app.config["DATABASE"] = os.path.join(app.root_path, "database.db")

# -----------------------------------------------------------------------------
# Database helpers
# -----------------------------------------------------------------------------
def get_db():
    conn = sqlite3.connect(app.config["DATABASE"])
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cur = conn.cursor()

    # Users
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        created_at TEXT NOT NULL
    );
    """)

    # Contact messages
    cur.execute("""
    CREATE TABLE IF NOT EXISTS contact_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT NOT NULL,
        phone TEXT NOT NULL,
        message TEXT NOT NULL,
        created_at TEXT NOT NULL
    );
    """)

    # Bikes
    cur.execute("""
    CREATE TABLE IF NOT EXISTS bikes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        type TEXT NOT NULL,
        price_per_day REAL NOT NULL,
        description TEXT,
        image_url TEXT
    );
    """)

    # Bike bookings
    cur.execute("""
    CREATE TABLE IF NOT EXISTS bike_bookings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        bike_id INTEGER NOT NULL,
        customer_name TEXT NOT NULL,
        email TEXT NOT NULL,
        phone TEXT NOT NULL,
        start_date TEXT NOT NULL,
        end_date TEXT NOT NULL,
        total_price REAL NOT NULL,
        created_at TEXT NOT NULL
    );
    """)

    # Pet products
    cur.execute("""
    CREATE TABLE IF NOT EXISTS pet_products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        category TEXT NOT NULL,
        price REAL NOT NULL,
        description TEXT,
        image_url TEXT
    );
    """)

    # DataHub
    cur.execute("""
    CREATE TABLE IF NOT EXISTS datahub_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        content TEXT NOT NULL,
        created_at TEXT NOT NULL
    );
    """)

    conn.commit()
    conn.close()


def seed_demo_data():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM bikes;")
    if cur.fetchone()[0] == 0:
        bikes = [
            ("Yamaha MT-15", "Sport", 900, "Lightweight city sport bike.", ""),
            ("Royal Enfield Classic 350", "Cruiser", 1100, "Comfortable long-ride cruiser.", ""),
        ]
        cur.executemany("""
        INSERT INTO bikes (name, type, price_per_day, description, image_url)
        VALUES (?, ?, ?, ?, ?);
        """, bikes)

    cur.execute("SELECT COUNT(*) FROM pet_products;")
    if cur.fetchone()[0] == 0:
        pets = [
            ("Golden Retriever", "Dog", 25000, "Friendly family dog.", ""),
            ("Persian Cat", "Cat", 18000, "Calm indoor cat.", ""),
        ]
        cur.executemany("""
        INSERT INTO pet_products (name, category, price, description, image_url)
        VALUES (?, ?, ?, ?, ?);
        """, pets)

    conn.commit()
    conn.close()


init_db()
seed_demo_data()

# -----------------------------------------------------------------------------
# Auth helpers
# -----------------------------------------------------------------------------
def current_user():
    uid = session.get("user_id")
    if not uid:
        return None
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id = ?;", (uid,)).fetchone()
    conn.close()
    return user


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            flash("Please login first.")
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped

# -----------------------------------------------------------------------------
# Routes
# -----------------------------------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html", user=current_user())


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        conn = get_db()
        cur = conn.cursor()

        email = request.form["email"]
        cur.execute("SELECT id FROM users WHERE email = ?;", (email,))
        if cur.fetchone():
            flash("Email already exists")
            conn.close()
            return redirect(url_for("signup"))

        cur.execute("""
        INSERT INTO users (name, email, password_hash, created_at)
        VALUES (?, ?, ?, ?);
        """, (
            request.form["name"],
            email,
            generate_password_hash(request.form["password"]),
            datetime.now().isoformat()
        ))
        conn.commit()
        conn.close()

        flash("Account created")
        return redirect(url_for("login"))

    return render_template("signup.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        conn = get_db()
        user = conn.execute(
            "SELECT * FROM users WHERE email = ?;",
            (request.form["email"],)
        ).fetchone()
        conn.close()

        if user and check_password_hash(user["password_hash"], request.form["password"]):
            session["user_id"] = user["id"]
            return redirect(url_for("index"))

        flash("Invalid credentials")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

# -----------------------------------------------------------------------------
# Bike Rental
# -----------------------------------------------------------------------------
@app.route("/bike-rental")
@login_required
def bike_rental():
    conn = get_db()
    bikes = conn.execute("SELECT * FROM bikes;").fetchall()
    conn.close()
    return render_template("bike_home.html", bikes=bikes)


@app.route("/bike-rental/<int:bike_id>", methods=["GET", "POST"])
@login_required
def bike_detail(bike_id):
    conn = get_db()
    bike = conn.execute("SELECT * FROM bikes WHERE id = ?;", (bike_id,)).fetchone()

    if request.method == "POST":
        start = date.fromisoformat(request.form["start_date"])
        end = date.fromisoformat(request.form["end_date"])
        days = (end - start).days + 1
        total = days * bike["price_per_day"]

        conn.execute("""
        INSERT INTO bike_bookings
        (bike_id, customer_name, email, phone, start_date, end_date, total_price, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            bike_id,
            request.form["name"],
            request.form["email"],
            request.form["phone"],
            start, end, total,
            datetime.now().isoformat()
        ))
        conn.commit()
        conn.close()
        return redirect(url_for("bike_rental"))

    conn.close()
    return render_template("bike_detail.html", bike=bike)

# -----------------------------------------------------------------------------
# Pet Shop
# -----------------------------------------------------------------------------
@app.route("/petshop")
@login_required
def pet_home():
    conn = get_db()
    products = conn.execute("SELECT * FROM pet_products;").fetchall()
    conn.close()
    return render_template("pet_home.html", products=products)

# -----------------------------------------------------------------------------
# DataHub
# -----------------------------------------------------------------------------
@app.route("/datahub", methods=["GET", "POST"])
@login_required
def datahub():
    conn = get_db()
    cur = conn.cursor()

    if request.method == "POST":
        cur.execute("""
        INSERT INTO datahub_records (title, content, created_at)
        VALUES (?, ?, ?);
        """, (
            request.form["title"],
            request.form["content"],
            datetime.now().isoformat()
        ))
        conn.commit()

    records = cur.execute(
        "SELECT * FROM datahub_records ORDER BY created_at DESC;"
    ).fetchall()
    conn.close()

    return render_template("datahub.html", records=records)

# -----------------------------------------------------------------------------
# Contact
# -----------------------------------------------------------------------------
@app.route("/contact", methods=["POST"])
def contact():
    conn = get_db()
    conn.execute("""
    INSERT INTO contact_messages
    (name, email, phone, message, created_at)
    VALUES (?, ?, ?, ?, ?);
    """, (
        request.form["name"],
        request.form["email"],
        request.form["phone"],
        request.form["message"],
        datetime.now().isoformat()
    ))
    conn.commit()
    conn.close()

    try:
        send_email(
            "samifarhan64@gmail.com",
            "New Contact Message",
            request.form["message"]
        )
        flash("Message sent successfully")
    except Exception as e:
        flash("Message saved, but email failed")

    return redirect(url_for("index") + "#contact")

# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
