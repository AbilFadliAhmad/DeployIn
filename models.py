# models.py
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
import os # Tambahkan ini di atas
from datetime import datetime, timezone

# Inisialisasi Flask
app = Flask(__name__)

# Gunakan database SQLite yang disimpan di folder yang sama dengan aplikasi
BASE_DIR = os.path.abspath(os.path.dirname(__name__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASE_DIR, 'deployin.db')

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'rahasia_super_aman_untuk_session'

db = SQLAlchemy(app)


# --- TABEL USERS ---
class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default='user')  # Akan berisi 'admin' atau 'user'

    # Relasi ke template yang dibuat user ini
    templates = db.relationship('Template', backref='pemilik', lazy=True)


# --- TABEL TEMPLATES ---
class Template(db.Model):
    __tablename__ = 'templates'
    id = db.Column(db.Integer, primary_key=True)
    nama_teknologi = db.Column(db.String(100), nullable=False)  # Contoh: "Python Flask"
    perintah_default = db.Column(db.Text, nullable=False)  # Perintah terminal bash
    is_global = db.Column(db.Boolean, default=False)  # True jika dibuat admin untuk semua orang
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # Null jika global

# --- TABEL UNTUK MENYIMPAN SARAN & LAPORAN BUG ---
class Feedback(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    jenis = db.Column(db.String(20), nullable=False) # Isinya: 'bug' atau 'saran'
    pesan = db.Column(db.Text, nullable=False)
    tanggal = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Relasi agar kita tahu siapa yang mengirim feedback
    user = db.relationship('User', backref='feedbacks')


# --- TABEL UNTUK MELACAK AKTIVITAS DEPLOYMENT (UNTUK GRAFIK ANALISA) ---
class DeploymentLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    status = db.Column(db.String(20), nullable=False)

    # PENAMBAHAN KOLOM BARU:
    github_link = db.Column(db.String(255), nullable=True)  # Nilai True jika link opsional
    app = db.Column(db.String(100), nullable=False)  # Nama aplikasi yang di-deploy

    # Hubungkan ke id dari tabel 'templates'
    template_id = db.Column(db.Integer, db.ForeignKey('templates.id'), nullable=True)

    # PERBAIKAN: Menambahkan nama variabel 'tanggal'
    tanggal = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # RELASI:
    user = db.relationship('User', backref='deployments')
    # Relasi agar bisa memanggil log.template langsung di python
    template = db.relationship('Template', backref='deployment_logs')


# Fungsi untuk membuat database pertama kali
def init_db():
    with app.app_context():
        db.create_all()
        print("Tabel database berhasil dibuat!")


if __name__ == '__main__':
    # Jalankan file ini secara langsung (python models.py) untuk membuat tabel
    init_db()