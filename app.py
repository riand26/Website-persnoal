from flask import (
    Flask,
    render_template,
    request,
    redirect,
    session,
    url_for
)
from urllib.parse import quote
import sqlite3

app = Flask(__name__)
app.secret_key = "kunci-rahasia-123"


# =====================================
# Koneksi Database SQLite
# =====================================
def get_connection():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn


def normalize_whatsapp_number(number):
    if not number:
        return ""

    phone = "".join(ch for ch in number if ch.isdigit())

    if phone.startswith("0"):
        phone = "62" + phone[1:]
    elif phone.startswith("+62"):
        phone = phone[1:]
    elif phone.startswith("8"):
        phone = "62" + phone

    return phone


# =====================================
# Beranda
# =====================================
@app.route("/")
def home():

    conn = get_connection()

    products = conn.execute("""
        SELECT *
        FROM products
        ORDER BY id DESC
    """).fetchall()

    conn.close()

    return render_template(
        "index.html",
        products=products
    )


# =====================================
# Semua Produk
# =====================================
@app.route("/products")
def products():

    conn = get_connection()

    sort = request.args.get("sort", default="newest")
    q = request.args.get("q", default="").strip()
    min_price = request.args.get("min", type=int)
    max_price = request.args.get("max", type=int)

    sql = "SELECT * FROM products"
    where_clauses = []
    params = []

    if q:
        where_clauses.append("(nama LIKE ? OR deskripsi LIKE ?)")
        params.extend([f"%{q}%", f"%{q}%"])

    if min_price is not None:
        where_clauses.append("harga >= ?")
        params.append(min_price)

    if max_price is not None:
        where_clauses.append("harga <= ?")
        params.append(max_price)

    if where_clauses:
        sql += " WHERE " + " AND ".join(where_clauses)

    if sort == "price-low":
        order = "harga ASC"
    elif sort == "price-high":
        order = "harga DESC"
    elif sort == "name":
        order = "nama COLLATE NOCASE ASC"
    else:
        order = "id DESC"

    sql += f" ORDER BY {order}"

    products = conn.execute(sql, params).fetchall()

    conn.close()

    return render_template(
        "products.html",
        products=products
    )


# =====================================
# Detail Produk
# =====================================
@app.route("/product/<int:product_id>")
def detail(product_id):

    conn = get_connection()

    product = conn.execute("""
        SELECT *
        FROM products
        WHERE id = ?
    """, (product_id,)).fetchone()

    conn.close()

    if product is None:
        return "Produk tidak ditemukan.", 404

    return render_template(
        "detail.html",
        product=product
    )


# =====================================
# Checkout
# =====================================
@app.route("/checkout/<int:product_id>", methods=["GET", "POST"])
def checkout(product_id):

    conn = get_connection()

    product = conn.execute("""
        SELECT *
        FROM products
        WHERE id = ?
    """, (product_id,)).fetchone()

    if product is None:
        conn.close()
        return "Produk tidak ditemukan.", 404

    if request.method == "POST":

        nama = request.form["nama"]
        email = request.form["email"]
        no_hp = normalize_whatsapp_number(request.form["no_hp"])
        alamat = request.form["alamat"]

        jumlah = int(request.form["jumlah"])

        if jumlah < 1:
            jumlah = 1

        total_harga = jumlah * product["harga"]

        conn.execute("""
            INSERT INTO orders
            (
                nama_pelanggan,
                email,
                no_hp,
                alamat,
                product_id,
                jumlah,
                total_harga
            )
            VALUES
            (?, ?, ?, ?, ?, ?, ?)
        """, (
            nama,
            email,
            no_hp,
            alamat,
            product["id"],
            jumlah,
            total_harga
        ))

        conn.commit()
        conn.close()

        return redirect(url_for("checkout_success"))

    qty = request.args.get("qty", default=1, type=int)

    conn.close()

    return render_template(
        "checkout.html",
        product=product,
        qty=qty
    )


# =====================================
# Checkout Berhasil
# =====================================
@app.route("/checkout/success")
def checkout_success():

    return render_template(
        "checkout_success.html"
    )


# =====================================
# Login Admin
# =====================================
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        conn = get_connection()

        admin = conn.execute("""
            SELECT *
            FROM admin
            WHERE username = ?
            AND password = ?
        """, (
            username,
            password
        )).fetchone()

        conn.close()

        if admin:

            session["admin_id"] = admin["id"]
            session["admin_name"] = admin["nama_lengkap"]

            return redirect(
                url_for("admin_dashboard")
            )

        return render_template(
            "admin/login.html",
            error="Username atau password salah."
        )

    return render_template(
        "admin/login.html"
    )


# =====================================
# Dashboard Admin
# =====================================
@app.route("/admin/dashboard")
def admin_dashboard():

    if "admin_id" not in session:
        return redirect(
            url_for("admin_login")
        )

    conn = get_connection()

    products = conn.execute("""
        SELECT *
        FROM products
        ORDER BY id DESC
    """).fetchall()

    total_products = conn.execute("""
        SELECT COUNT(*)
        FROM products
    """).fetchone()[0]

    total_orders = conn.execute("""
        SELECT COUNT(*)
        FROM orders
    """).fetchone()[0]

    total_admin = conn.execute("""
        SELECT COUNT(*)
        FROM admin
    """).fetchone()[0]

    orders = conn.execute("""
        SELECT
            orders.*,
            products.nama AS nama_produk,
            products.gambar AS gambar_produk
        FROM orders
        LEFT JOIN products
        ON orders.product_id = products.id
        ORDER BY orders.id DESC
    """).fetchall()

    conn.close()

    return render_template(
        "admin/dashboard.html",
        products=products,
        orders=orders,
        total_products=total_products,
        total_orders=total_orders,
        total_admin=total_admin
    )

# =====================================
# Pesanan Admin
# =====================================
@app.route("/admin/orders", methods=["GET", "POST"])
def admin_orders():

    if "admin_id" not in session:
        return redirect(url_for("admin_login"))

    conn = get_connection()

    if request.method == "POST":
        action = request.form.get("action", "").strip()
        if action == "update_status":
            order_id = request.form.get("order_id")
            status = request.form.get("status", "").strip()
            if order_id and status:
                conn.execute("""
                    UPDATE orders
                    SET status = ?
                    WHERE id = ?
                """, (status, order_id))
                conn.commit()
        conn.close()
        return redirect(url_for("admin_orders"))

    orders = conn.execute("""
        SELECT
            orders.*,
            products.nama AS nama_produk
        FROM orders
        LEFT JOIN products
        ON orders.product_id = products.id
        ORDER BY orders.id DESC
    """).fetchall()

    # Build WhatsApp links with pre-filled message for each order
    orders_processed = []
    for o in orders:
        row = dict(o)
        phone_raw = row.get("no_hp")
        phone = normalize_whatsapp_number(phone_raw) if phone_raw else ""

        if phone:
            status_text = row.get("status") or "Menunggu"
            produk_nama = row.get("nama_produk") or "Produk"
            jumlah = int(row.get("jumlah") or 1)
            total = row.get("total_harga") or 0
            total_formatted = "{:,.0f}".format(total)

            # Build image URL if available
            gambar = row.get("gambar_produk")
            img_url = ""
            if gambar:
                if isinstance(gambar, str) and gambar.lower().startswith('http'):
                    img_url = gambar
                else:
                    # generate absolute URL for static image
                    try:
                        img_url = url_for('static', filename='images/' + gambar, _external=True)
                    except Exception:
                        img_url = ''

            # Compose message including product name, qty, total and image link (image as URL)
            msg_parts = [f"Pesanan Anda #{row.get('id')} ({status_text})", f"{produk_nama} x{jumlah}", f"Total: Rp {total_formatted}", "Silakan lakukan pembayaran dan kirimkan bukti pembayaran di sini"]
            if img_url:
                msg_parts.append(f"Gambar: {img_url}")

            msg = " - ".join(msg_parts)
            wa_link = f"https://wa.me/{phone}?text={quote(msg)}"
        else:
            wa_link = ""

        row["wa_link"] = wa_link
        row["phone_normalized"] = phone
        orders_processed.append(row)

    total_products = conn.execute("""
        SELECT COUNT(*)
        FROM products
    """).fetchone()[0]

    total_orders = conn.execute("""
        SELECT COUNT(*)
        FROM orders
    """).fetchone()[0]

    total_admin = conn.execute("""
        SELECT COUNT(*)
        FROM admin
    """).fetchone()[0]

    conn.close()

    return render_template(
        "admin/orders.html",
        orders=orders_processed,
        total_products=total_products,
        total_orders=total_orders,
        total_admin=total_admin
    )


# =====================================
# Profil Admin
# =====================================
@app.route("/admin/profile", methods=["GET", "POST"])
def admin_profile():

    if "admin_id" not in session:
        return redirect(url_for("admin_login"))

    conn = get_connection()

    admin = conn.execute("""
        SELECT *
        FROM admin
        WHERE id = ?
    """, (session["admin_id"],)).fetchone()

    if request.method == "POST":
        nama_lengkap = request.form.get("nama_lengkap", "").strip()
        password = request.form.get("password", "").strip()

        if nama_lengkap:
            conn.execute("""
                UPDATE admin
                SET nama_lengkap = ?
                WHERE id = ?
            """, (nama_lengkap, session["admin_id"]))
            session["admin_name"] = nama_lengkap

        if password:
            conn.execute("""
                UPDATE admin
                SET password = ?
                WHERE id = ?
            """, (password, session["admin_id"]))

        conn.commit()

        conn.close()
        return redirect(url_for("admin_profile"))

    conn.close()

    return render_template(
        "admin/profile.html",
        admin=admin
    )

# =====================================
# Product Admin (CRUD)
# =====================================
@app.route("/admin/products", methods=["GET", "POST"])
@app.route("/admin/products/<int:product_id>", methods=["GET", "POST"])
def admin_products(product_id=None):

    if "admin_id" not in session:
        return redirect(url_for("admin_login"))

    conn = get_connection()

    # ------------------------------
    # Tambah / Update Produk
    # ------------------------------
    if request.method == "POST":

        action = request.form.get("action", "").strip()

        nama = request.form.get("nama", "").strip()
        harga = request.form.get("harga", 0)
        gambar = request.form.get("gambar", "").strip()
        deskripsi = request.form.get("deskripsi", "").strip()

        try:
            harga = int(harga)
        except ValueError:
            harga = 0

        if action == "add":

            conn.execute("""
                INSERT INTO products
                (nama, harga, gambar, deskripsi)
                VALUES (?, ?, ?, ?)
            """, (
                nama,
                harga,
                gambar,
                deskripsi
            ))

            conn.commit()

        elif action == "update":

            edit_id = request.form.get("product_id")

            conn.execute("""
                UPDATE products
                SET
                    nama = ?,
                    harga = ?,
                    gambar = ?,
                    deskripsi = ?
                WHERE id = ?
            """, (
                nama,
                harga,
                gambar,
                deskripsi,
                edit_id
            ))

            conn.commit()

        elif action == "delete":

            delete_id = request.form.get("product_id")

            conn.execute("""
                DELETE FROM products
                WHERE id = ?
            """, (delete_id,))

            conn.commit()

        conn.close()

        return redirect(url_for("admin_products"))

    # ------------------------------
    # Mode Edit
    # ------------------------------
    edit_product = None

    if product_id is not None:

        edit_product = conn.execute("""
            SELECT *
            FROM products
            WHERE id = ?
        """, (product_id,)).fetchone()

    # ------------------------------
    # Data Dashboard
    # ------------------------------
    products = conn.execute("""
        SELECT *
        FROM products
        ORDER BY id DESC
    """).fetchall()

    total_products = conn.execute("""
        SELECT COUNT(*)
        FROM products
    """).fetchone()[0]

    total_orders = conn.execute("""
        SELECT COUNT(*)
        FROM orders
    """).fetchone()[0]

    total_admin = conn.execute("""
        SELECT COUNT(*)
        FROM admin
    """).fetchone()[0]

    conn.close()

    return render_template(
        "admin/products.html",
        products=products,
        edit_product=edit_product,
        total_products=total_products,
        total_orders=total_orders,
        total_admin=total_admin
    )

# =====================================
# Logout Admin
# =====================================
@app.route("/admin/logout")
def admin_logout():

    session.clear()

    return redirect(
        url_for("admin_login")
    )


# =====================================
# Jalankan Flask
# =====================================
if __name__ == "__main__":
    app.run(
        debug=True
    )