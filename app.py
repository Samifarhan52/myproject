import os
import sqlite3
from datetime import datetime, date
from functools import wraps
import re

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
)

from werkzeug.security import generate_password_hash, check_password_hash
from modules.email_utils import send_email


# -----------------------------------------------------------------------------
# App setup
# -----------------------------------------------------------------------------
app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "replace_this_with_a_better_random_secret")
app.config["DATABASE"] = os.path.join(app.root_path, "database.db")


# -----------------------------------------------------------------------------
# Database helpers
# -----------------------------------------------------------------------------
def get_db_connection():
    conn = sqlite3.connect(app.config["DATABASE"])
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        created_at TEXT NOT NULL
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS datahub_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        content TEXT NOT NULL,
        created_at TEXT NOT NULL
    );
    """)

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

    cur.execute("""
    CREATE TABLE IF NOT EXISTS pet_orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_name TEXT NOT NULL,
        email TEXT NOT NULL,
        phone TEXT NOT NULL,
        total_amount REAL NOT NULL,
        created_at TEXT NOT NULL
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS pet_order_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER NOT NULL,
        product_name TEXT NOT NULL,
        quantity INTEGER NOT NULL,
        price_each REAL NOT NULL
    );
    """)

    conn.commit()
    conn.close()


init_db()


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
def current_user():
    uid = session.get("user_id")
    if not uid:
        return None
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (uid,)).fetchone()
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


def is_strong_password(password):
    return (
        len(password) >= 8
        and re.search(r"[A-Z]", password)
        and re.search(r"[0-9]", password)
        and re.search(r"[^A-Za-z0-9]", password)
    )


# -----------------------------------------------------------------------------
# Routes
# -----------------------------------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html", user=current_user())


# ---------------- SIGNUP ----------------
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "").strip()

        if not is_strong_password(password):
            flash("Password must contain 1 uppercase letter, 1 number, and 1 special character.")
            return redirect(url_for("signup"))

        if not name or not email or not password:
            flash("All fields are required.")
            return redirect(url_for("signup"))

        conn = get_db_connection()
        if conn.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone():
            conn.close()
            flash("Email already exists.")
            return redirect(url_for("signup"))

        conn.execute(
            "INSERT INTO users (name, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
            (name, email, generate_password_hash(password), datetime.now().isoformat()),
        )
        conn.commit()
        conn.close()

        flash("Account created. Please login.")
        return redirect(url_for("login"))

    return render_template("signup.html", user=current_user())


# ---------------- LOGIN ----------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "").strip()

        conn = get_db_connection()
        user = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        conn.close()

        if user and check_password_hash(user["password_hash"], password):
            session["user_id"] = user["id"]
            flash("Logged in successfully.")
            return redirect(url_for("index"))

        flash("Invalid email or password.")

    return render_template("login.html", user=current_user())


@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out.")
    return redirect(url_for("index"))


# ---------------- DATAHUB ----------------
@app.route("/datahub", methods=["GET", "POST"])
@login_required
def datahub():
    conn = get_db_connection()
    cur = conn.cursor()

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        content = request.form.get("content", "").strip()
        if title and content:
            cur.execute(
                "INSERT INTO datahub_records (title, content, created_at) VALUES (?, ?, ?)",
                (title, content, datetime.now().isoformat()),
            )
            conn.commit()
            flash("Record added.")

    records = cur.execute("SELECT * FROM datahub_records ORDER BY created_at DESC").fetchall()
    conn.close()
    return render_template("datahub.html", records=records, user=current_user())


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True)
