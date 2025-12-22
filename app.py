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
import re


# -----------------------------------------------------------------------------
# App setup
# -----------------------------------------------------------------------------
app = Flask(__name__)
app.config["SECRET_KEY"] = "replace_this_with_a_better_random_secret"
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

    # Users
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        """
    )

    # DataHub records
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS datahub_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        """
    )

    # Bikes
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS bikes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            type TEXT NOT NULL,
            price_per_day REAL NOT NULL,
            description TEXT,
            image_url TEXT
        );
        """
    )

    # Bike bookings
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS bike_bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bike_id INTEGER NOT NULL,
            customer_name TEXT NOT NULL,
            email TEXT NOT NULL,
            phone TEXT NOT NULL,
            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL,
            total_price REAL NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (bike_id) REFERENCES bikes (id)
        );
        """
    )

    # Pet products
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS pet_products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            price REAL NOT NULL,
            description TEXT,
            image_url TEXT
        );
        """
    )

    # Pet orders
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS pet_orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT NOT NULL,
            email TEXT NOT NULL,
            phone TEXT NOT NULL,
            total_amount REAL NOT NULL,
            created_at TEXT NOT NULL
        );
        """
    )

    # Pet order items
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS pet_order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            product_name TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            price_each REAL NOT NULL,
            FOREIGN KEY (order_id) REFERENCES pet_orders (id)
        );
        """
    )

    # Seed bikes if empty
    cur.execute("SELECT COUNT(*) AS c FROM bikes;")
    if cur.fetchone()["c"] == 0:
        bikes_seed = [
            (
                "Yamaha MT-15",
                "Sport",
                900.0,
                "Lightweight city sport bike, great mileage and torque.",
                "https://images.pexels.com/photos/977003/pexels-photo-977003.jpeg",
            ),
            (
                "Royal Enfield Classic 350",
                "Cruiser",
                1100.0,
                "Comfortable cruiser for highway and city rides.",
                "https://images.pexels.com/photos/210182/pexels-photo-210182.jpeg",
            ),
            (
                "Honda Activa 6G",
                "Scooter",
                600.0,
                "Practical scooter perfect for daily commuting.",
                "https://images.pexels.com/photos/806835/pexels-photo-806835.jpeg",
            ),
        ]
        cur.executemany(
            "INSERT INTO bikes (name, type, price_per_day, description, image_url) VALUES (?, ?, ?, ?, ?);",
            bikes_seed,
        )

    # Seed pet products if empty
    cur.execute("SELECT COUNT(*) AS c FROM pet_products;")
    if cur.fetchone()["c"] == 0:
        pets_seed = [
            (
                "Premium Dog Food",
                "Food",
                799.0,
                "High-protein dry food for adult dogs.",
                "https://images.pexels.com/photos/3299905/pexels-photo-3299905.jpeg",
            ),
            (
                "Cat Scratching Post",
                "Accessories",
                1299.0,
                "Sturdy scratching post to keep your cat active.",
                "https://images.pexels.com/photos/347600/pexels-photo-347600.jpeg",
            ),
            (
                "Pet Water Bowl",
                "Accessories",
                299.0,
                "Non-slip stainless steel water bowl.",
                "https://images.pexels.com/photos/731022/pexels-photo-731022.jpeg",
            ),
        ]
        cur.executemany(
            "INSERT INTO pet_products (name, category, price, description, image_url) VALUES (?, ?, ?, ?, ?);",
            pets_seed,
        )

    conn.commit()
    conn.close()


# Initialize DB immediately on import
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
            # redirect to login but remember where we wanted to go
            next_url = request.path
            return redirect(url_for("login", next=next_url))
        return view_func(*args, **kwargs)

    return wrapper


def is_strong_password(password):
    if len(password) < 8:
        return False
    if not re.search(r"[A-Z]", password):
        return False
    if not re.search(r"[0-9]", password):
        return False
    if not re.search(r"[^A-Za-z0-9]", password):
        return False
    return True



# -----------------------------------------------------------------------------
# Routes: Portfolio Home
# -----------------------------------------------------------------------------
@app.route("/")
def index():
    user = current_user()
    return render_template("index.html", user=user)


# -----------------------------------------------------------------------------
# Routes: Auth
# -----------------------------------------------------------------------------
@app.route("/signup", methods=["GET", "POST"])
def signup():
    user = current_user()
    error = None

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "").strip()
        if not is_strong_password(password):
    flash(
        "Password must contain at least 1 uppercase letter, 1 number, and 1 special character",
        "danger"
    )
    return redirect(url_for("signup"))


        if not name or not email or not password:
            error = "All fields are required."
        else:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("SELECT id FROM users WHERE email = ?;", (email,))
            exists = cur.fetchone()
            if exists:
                error = "An account with this email already exists."
            else:
                password_hash = generate_password_hash(password)
                cur.execute(
                    "INSERT INTO users (name, email, password_hash, created_at) VALUES (?, ?, ?, ?);",
                    (name, email, password_hash, datetime.now().isoformat(timespec="seconds")),
                )
                conn.commit()
                conn.close()
                flash(("success", "Account created. Please log in."))
                return redirect(url_for("login"))

            conn.close()

    return render_template("signup.html", user=user, error=error)


@app.route("/login", methods=["GET", "POST"])
def login():
    user = current_user()
    error = None
    next_url = request.args.get("next") or url_for("index")

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "").strip()

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE email = ?;", (email,))
        row = cur.fetchone()
        conn.close()

        if row and check_password_hash(row["password_hash"], password):
            session["user_id"] = row["id"]
            flash(("success", "Logged in successfully."))
            return redirect(next_url)
        else:
            error = "Invalid email or password."

    return render_template("login.html", user=user, error=error)


@app.route("/logout")
def logout():
    session.clear()
    flash(("success", "You have been logged out."))
    return redirect(url_for("index"))


# -----------------------------------------------------------------------------
# Routes: DataHub
# -----------------------------------------------------------------------------
@app.route("/datahub", methods=["GET", "POST"])
@login_required
def datahub():
    user = current_user()
    conn = get_db_connection()
    cur = conn.cursor()

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        content = request.form.get("content", "").strip()
        if title and content:
            cur.execute(
                "INSERT INTO datahub_records (title, content, created_at) VALUES (?, ?, ?);",
                (title, content, datetime.now().isoformat(timespec="seconds")),
            )
            conn.commit()
            flash(("success", "Record added to DataHub."))
        else:
            flash(("error", "Both title and content are required."))

    cur.execute("SELECT * FROM datahub_records ORDER BY created_at DESC;")
    records = cur.fetchall()
    conn.close()

    return render_template("datahub.html", user=user, records=records)


@app.route("/datahub/delete/<int:record_id>", methods=["POST"])
@login_required
def delete_datahub_record(record_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM datahub_records WHERE id = ?;", (record_id,))
    conn.commit()
    conn.close()
    flash(("success", "Record deleted."))
    return redirect(url_for("datahub"))


# -----------------------------------------------------------------------------
# Routes: Bike Rental
# -----------------------------------------------------------------------------
@app.route("/bike-rental")
@login_required
def bike_rental():
    user = current_user()
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM bikes;")
    bikes = cur.fetchall()
    conn.close()
    return render_template("bike_home.html", user=user, bikes=bikes)


@app.route("/bike-rental/<int:bike_id>", methods=["GET", "POST"])
@login_required
def bike_detail(bike_id):
    user = current_user()
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM bikes WHERE id = ?;", (bike_id,))
    bike = cur.fetchone()

    if not bike:
        conn.close()
        return "Bike not found", 404

    error = None

    if request.method == "POST":
        customer_name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        start_date_str = request.form.get("start_date", "").strip()
        end_date_str = request.form.get("end_date", "").strip()

        if not customer_name or not email or not phone or not start_date_str or not end_date_str:
            error = "All fields are required."
        else:
            try:
                start_date = date.fromisoformat(start_date_str)
                end_date = date.fromisoformat(end_date_str)
                days = (end_date - start_date).days + 1
                if days <= 0:
                    error = "End date must be on or after start date."
                else:
                    total_price = days * bike["price_per_day"]
                    cur.execute(
                        """
                        INSERT INTO bike_bookings
                        (bike_id, customer_name, email, phone, start_date, end_date, total_price, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                        """,
                        (
                            bike_id,
                            customer_name,
                            email,
                            phone,
                            start_date_str,
                            end_date_str,
                            total_price,
                            datetime.now().isoformat(timespec="seconds"),
                        ),
                    )
                    conn.commit()
                    booking_id = cur.lastrowid
                    conn.close()
                    flash(("success", "Bike booked successfully."))
                    return redirect(url_for("bike_booking_success", booking_id=booking_id))
            except ValueError:
                error = "Please enter valid dates (YYYY-MM-DD)."

    conn.close()
    return render_template("bike_detail.html", user=user, bike=bike, error=error)


@app.route("/bike-rental/booking/<int:booking_id>")
@login_required
def bike_booking_success(booking_id):
    user = current_user()
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT b.*, bk.customer_name, bk.email, bk.phone, bk.start_date, bk.end_date,
               bk.total_price, bk.created_at, bk.id AS booking_id
        FROM bike_bookings bk
        JOIN bikes b ON bk.bike_id = b.id
        WHERE bk.id = ?;
        """,
        (booking_id,),
    )
    booking = cur.fetchone()
    conn.close()

    if not booking:
        return "Booking not found", 404

    email_message = f"""
    <h2>Bike Rental Receipt</h2>
    <p>Thank you for booking a bike with BikeRent!</p>
    <p><strong>Name:</strong> {booking["customer_name"]}</p>
    <p><strong>Bike:</strong> {booking["name"]} ({booking["type"]})</p>
    <p><strong>From:</strong> {booking["start_date"]}</p>
    <p><strong>To:</strong> {booking["end_date"]}</p>
    <p><strong>Total Price:</strong> ₹{booking["total_price"]}</p>
    <p><strong>Booking ID:</strong> {booking["booking_id"]}</p>
    """

    try:
        send_email(
            booking["email"],
            "Your Bike Rental Receipt",
            email_message,
        )
    except Exception as e:
        print("EMAIL SEND ERROR (Bike Rental):", e)

    return render_template("bike_booking_success.html", user=user, booking=booking)


# -----------------------------------------------------------------------------
# Helpers: PetShop cart in session
# -----------------------------------------------------------------------------
def get_cart():
    return session.get("cart", {})


def save_cart(cart):
    session["cart"] = cart
    session.modified = True


# -----------------------------------------------------------------------------
# Routes: PetShop
# -----------------------------------------------------------------------------
@app.route("/petshop", methods=["GET", "POST"])
@login_required
def pet_home():
    user = current_user()
    conn = get_db_connection()
    cur = conn.cursor()

    if request.method == "POST":
        product_id = request.form.get("product_id")
        if product_id:
            product_id = str(product_id)
            cart = get_cart()
            cart[product_id] = cart.get(product_id, 0) + 1
            save_cart(cart)
            flash(("success", "Item added to cart."))

    cur.execute("SELECT * FROM pet_products;")
    products = cur.fetchall()
    conn.close()

    cart = get_cart()
    cart_count = sum(cart.values())

    return render_template("pet_home.html", user=user, products=products, cart_count=cart_count)


@app.route("/petshop/cart", methods=["GET", "POST"])
@login_required
def pet_cart():
    user = current_user()
    cart = get_cart()
    conn = get_db_connection()
    cur = conn.cursor()

    product_ids = list(map(int, cart.keys()))
    products = []
    total_amount = 0.0

    if product_ids:
        placeholders = ",".join("?" for _ in product_ids)
        cur.execute(f"SELECT * FROM pet_products WHERE id IN ({placeholders});", product_ids)
        rows = cur.fetchall()
        for row in rows:
            qty = cart.get(str(row["id"]), 0)
            subtotal = qty * row["price"]
            total_amount += subtotal
            products.append(
                {
                    "id": row["id"],
                    "name": row["name"],
                    "category": row["category"],
                    "price": row["price"],
                    "quantity": qty,
                    "subtotal": subtotal,
                }
            )

    if request.method == "POST":
        remove_id = request.form.get("remove_id")
        if remove_id and remove_id in cart:
            del cart[remove_id]
            save_cart(cart)
            conn.close()
            flash(("success", "Item removed from cart."))
            return redirect(url_for("pet_cart"))

    conn.close()

    return render_template(
        "pet_cart.html",
        user=user,
        products=products,
        total_amount=total_amount,
    )


@app.route("/petshop/checkout", methods=["GET", "POST"])
@login_required
def pet_checkout():
    user = current_user()
    cart = get_cart()
    if not cart:
        flash(("error", "Your cart is empty."))
        return redirect(url_for("pet_home"))

    conn = get_db_connection()
    cur = conn.cursor()

    product_ids = list(map(int, cart.keys()))
    products = []
    total_amount = 0.0

    placeholders = ",".join("?" for _ in product_ids)
    cur.execute(f"SELECT * FROM pet_products WHERE id IN ({placeholders});", product_ids)
    rows = cur.fetchall()
    for row in rows:
        qty = cart.get(str(row["id"]), 0)
        subtotal = qty * row["price"]
        total_amount += subtotal
        products.append(
            {
                "id": row["id"],
                "name": row["name"],
                "quantity": qty,
                "price": row["price"],
            }
        )

    error = None
    order_id = None

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()

        if not name or not email or not phone:
            error = "Name, email, and mobile number are required."
        else:
            cur.execute(
                "INSERT INTO pet_orders (customer_name, email, phone, total_amount, created_at) VALUES (?, ?, ?, ?, ?);",
                (name, email, phone, total_amount, datetime.now().isoformat(timespec="seconds")),
            )
            order_id = cur.lastrowid

            for p in products:
                cur.execute(
                    "INSERT INTO pet_order_items (order_id, product_name, quantity, price_each) VALUES (?, ?, ?, ?);",
                    (order_id, p["name"], p["quantity"], p["price"]),
                )

            conn.commit()
            conn.close()

            # Clear cart
            save_cart({})

            # Send order email
            html_body = f"""
            <h2>PetShop Order Confirmation</h2>
            <p>Thank you for your order, {name}!</p>
            <p><strong>Order ID:</strong> {order_id}</p>
            <p><strong>Total Amount:</strong> ₹{total_amount}</p>
            <p>We will process your order shortly.</p>
            """
            try:
                send_email(
                    email,
                    "Your PetShop Order Confirmation",
                    html_body,
                )
            except Exception as e:
                print("EMAIL SEND ERROR (PetShop):", e)

            return render_template(
                "pet_checkout_success.html",
                user=user,
                customer_name=name,
                total_amount=total_amount,
                order_id=order_id,
            )

    conn.close()
    return render_template(
        "pet_checkout.html",
        user=user,
        products=products,
        total_amount=total_amount,
        error=error,
    )


# -----------------------------------------------------------------------------
# Contact: from portfolio
# -----------------------------------------------------------------------------
@app.route("/contact", methods=["POST"])
def contact():
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()
    phone = request.form.get("phone", "").strip()
    message = request.form.get("message", "").strip()

    if not name or not email or not phone or not message:
        flash(("error", "Please fill in all the fields."))

    else:
        html_body = f"""
        <h2>New Contact Message from Portfolio</h2>
        <p><strong>Name:</strong> {name}</p>
        <p><strong>Email:</strong> {email}</p>
        <p><strong>Mobile Number:</strong> {phone}</p>
        <p><strong>Message:</strong></p>
        <p>{message}</p>
        """
        try:
            send_email(
                "samifarhan64@gmail.com",
                "New Portfolio Contact Message",
                html_body,
            )
            flash(("success", "Message sent successfully! I will contact you soon."))
        except Exception as e:
            print("CONTACT EMAIL ERROR:", e)
            flash(("error", "Something went wrong while sending your message."))

    return redirect(url_for("index") + "#contact")


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True)
