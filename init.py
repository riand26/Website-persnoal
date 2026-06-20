import sqlite3

# Membuat atau membuka database SQLite
conn = sqlite3.connect("database.db")
cursor = conn.cursor()

# ==========================
# Tabel Produk
# ==========================
cursor.execute("""
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nama TEXT NOT NULL,
    harga INTEGER NOT NULL,
    gambar TEXT NOT NULL,
    deskripsi TEXT NOT NULL
)
""")

# ==========================
# Tabel Admin
# ==========================
cursor.execute("""
CREATE TABLE IF NOT EXISTS admin (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL,
    nama_lengkap TEXT NOT NULL
)
""")

# ==========================
# Tabel Pesanan
# ==========================
cursor.execute("""
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nama_pelanggan TEXT NOT NULL,
    email TEXT,
    no_hp TEXT,
    alamat TEXT NOT NULL,
    product_id INTEGER NOT NULL,
    jumlah INTEGER NOT NULL DEFAULT 1,
    total_harga INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'Menunggu',
    tanggal_pesanan TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES products(id)
)
""")

# ==========================
# Data Awal Produk
# ==========================
cursor.execute("SELECT COUNT(*) FROM products")
jumlah_produk = cursor.fetchone()[0]

if jumlah_produk == 0:
    cursor.executemany("""
    INSERT INTO products (nama, harga, gambar, deskripsi)
    VALUES (?, ?, ?, ?)
    """, [
        (
            "Tas Tote Premium",
            175000,
            "tote.jpg",
            "Tas tote elegan berbahan kanvas premium."
        ),
        (
            "Tas Ransel Kasual",
            325000,
            "backpack.jpg",
            "Ransel multifungsi untuk sekolah maupun kerja."
        ),
        (
            "Tas Sling Wanita",
            215000,
            "sling.jpg",
            "Tas selempang modern dengan desain minimalis."
        )
    ])

# ==========================
# Data Awal Admin
# ==========================
cursor.execute("SELECT COUNT(*) FROM admin")
jumlah_admin = cursor.fetchone()[0]

if jumlah_admin == 0:
    cursor.execute("""
    INSERT INTO admin (username, password, nama_lengkap)
    VALUES (?, ?, ?)
    """, (
        "admin",
        "admin123",
        "Administrator"
    ))

# Simpan perubahan
conn.commit()

# Tutup koneksi
conn.close()

print("Database berhasil dibuat atau diperbarui.")
print("Akun admin default:")
print("Username : admin")
print("Password : admin123")