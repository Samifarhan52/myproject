import os
import sqlite3
from datetime import datetime, date
from functools import wraps

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

# Secret key from Render Environment Variables
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY")

# Database (later can be moved to /data/database.db for persistence)
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
        CREATE TABLE IF NOT EXISTS contact_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            phone TEXT NOT NULL,
            message TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
    """)

    conn.commit()
    conn.close()


init_db()

# -----------------------------------------------------------------------------
# Auth helpers
# -----------------------------------------------------------------------------
def current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE id = ?;", (user_id,))
    row = cur.fetchone()
    conn.close()
    return row


def login_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            flash(("error", "Please log in to access this page."))
            return redirect(url_for("login"))
        return view_func(*args, **kwargs)
    return wrapper

# -----------------------------------------------------------------------------
# Routes
# -----------------------------------------------------------------------------
@app.route("/")
def index():
    user = current_user()
    return render_template("index.html", user=user)


@app.route("/signup", methods=["GET", "POST"])
def signup():
    error = None

    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        password = request.form.get("password")

        if not name or not email or not password:
            error = "All fields are required."
        else:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("SELECT id FROM users WHERE email = ?;", (email,))
            if cur.fetchone():
                error = "Email already registered."
            else:
                cur.execute(
                    "INSERT INTO users (name, email, password_hash, created_at) VALUES (?, ?, ?, ?);",
                    (
                        name,
                        email,
                        generate_password_hash(password),
                        datetime.now().isoformat(timespec="seconds"),
                    ),
                )
                conn.commit()
                conn.close()
                flash(("success", "Account created. Please login."))
                return redirect(url_for("login"))
            conn.close()

    return render_template("signup.html", error=error)


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None

    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE email = ?;", (email,))
        user = cur.fetchone()
        conn.close()

        if user and check_password_hash(user["password_hash"], password):
            session["user_id"] = user["id"]
            flash(("success", "Login successful."))
            return redirect(url_for("index"))
        else:
            error = "Invalid credentials."

    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.clear()
    flash(("success", "Logged out successfully."))
    return redirect(url_for("index"))

# -----------------------------------------------------------------------------
# CONTACT – SEND MESSAGE → RECEIPT (FIXED)
# -----------------------------------------------------------------------------
@app.route("/contact", methods=["POST"])
def contact():
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()
    phone = request.form.get("phone", "").strip()
    message = request.form.get("message", "").strip()

    if not name or not email or not phone or not message:
        flash(("error", "Please fill in all fields."))
        return redirect(url_for("index") + "#contact")

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO contact_messages
            (name, email, phone, message, created_at)
            VALUES (?, ?, ?, ?, ?);
            """,
            (name, email, phone, message, datetime.now().isoformat(timespec="seconds")),
        )
        conn.commit()
        msg_id = cur.lastrowid
        conn.close()

        html_body = f"""
        <h2>New Contact Message</h2>
        <p><b>Name:</b> {name}</p>
        <p><b>Email:</b> {email}</p>
        <p><b>Phone:</b> {phone}</p>
        <p>{message}</p>
        """

        send_email(
            "samifarhan64@gmail.com",
            "New Portfolio Contact Message",
            html_body,
        )

        return redirect(url_for("contact_receipt", msg_id=msg_id))

    except Exception as e:
        print("CONTACT ERROR:", e)
        flash(("error", "Something went wrong."))
        return redirect(url_for("index") + "#contact")


@app.route("/contact/receipt/<int:msg_id>")
def contact_receipt(msg_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM contact_messages WHERE id = ?;", (msg_id,))
    message = cur.fetchone()
    conn.close()

    if not message:
        return "Invalid receipt", 404

    return render_template("contact_receipt.html", message=message)

# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
