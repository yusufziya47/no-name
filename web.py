from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
import random
import string
import json
import os

app = Flask(__name__)
app.secret_key = "supersecretkey"

DB_PATH = "orders.db"

# Ürünler
products = [
    {"id": 1, "name": "Telefon Kılıfı", "price": 150},
    {"id": 2, "name": "Kulaklık", "price": 300},
    {"id": 3, "name": "Esp32", "price": 50}
]

# --- Veritabanı ---
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE,
            name TEXT,
            address TEXT,
            card TEXT,
            urun TEXT,
            status INTEGER DEFAULT ''
        )
    """)
    conn.commit()
    conn.close()

def save_order(code, name, address, card, urun):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT INTO orders (code, name, address, card, urun, status) VALUES (?, ?, ?, ?, ?, ?)",
        (code, name, address, card, json.dumps(urun, ensure_ascii=False), 0)
    )
    conn.commit()
    conn.close()

def get_order(code):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT code, name, address, card, urun, status FROM orders WHERE code=?", (code,))
    row = c.fetchone()
    conn.close()
    return row


@app.route("/")
def index():
    return render_template("index.html", products=products)

@app.route("/add_to_cart/<int:product_id>")
def add_to_cart(product_id):
    if "cart" not in session:
        session["cart"] = []
    session["cart"].append(product_id)
    session.modified = True
    return redirect(url_for("cart"))

@app.route("/remove_from_cart/<int:product_id>")
def remove_from_cart(product_id):
    if "cart" in session:
        try:
            session["cart"].remove(product_id)
            session.modified = True
        except ValueError:
            pass
    return redirect(url_for("cart"))

@app.route("/cart")
def cart():
    cart_items = []
    if "cart" in session:
        for pid in session["cart"]:
            for p in products:
                if p["id"] == pid:
                    cart_items.append(p)
    return render_template("cart.html", cart=cart_items)

@app.route("/checkout", methods=["GET", "POST"])
def checkout():
    if request.method == "POST":
        name = request.form["name"]
        address = request.form["address"]
        card = request.form["card"]

        # Sipariş kodu
        order_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

        # Sepetteki ürünler
        cart_items = []
        if "cart" in session:
            for pid in session["cart"]:
                for p in products:
                    if p["id"] == pid:
                        cart_items.append(p)

        # DB'ye kaydet
        save_order(order_code, name, address, card, cart_items)

        # Sepeti sıfırla
        session.pop("cart", None)

        return render_template("checkout.html", order_code=order_code)

    return render_template("checkout.html")


if __name__ == "__main__":
    if not os.path.exists(DB_PATH):
        init_db()
    app.run(debug=True)
