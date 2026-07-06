from models import app, db, User, Template
import bcrypt

with app.app_context():
    # 1. Buat password hash (Sandi: 123)
    hashed_pw = bcrypt.hashpw(b'123', bcrypt.gensalt()).decode('utf-8')

    # 2. Buat User Admin
    admin = User(username='admin', password_hash=hashed_pw, role='admin')
    db.session.add(admin)

    # 3. Daftar nama user yang ingin ditambahkan
    daftar_nama = [
        'abdul', 'wildan', 'galang', 'fadli', 'mukaim', 'fachrul',
        'satrio', 'huda', 'alana', 'yafi', 'alfan', 'bayu',
        'riswan', 'ilham', 'fardhan', 'ridho', 'leo', 'abrar'
    ]

    # 4. Looping untuk membuat object User secara massal
    for nama in daftar_nama:
        baru = User(username=nama, password_hash=hashed_pw, role='user')
        db.session.add(baru)

    # 5. Buat Template Global
    template = Template(
        nama_teknologi='Python Flask (Gunicorn)',
        perintah_default='mkdir -p /deployin && cd /deployin && mkdir -p flask && cd flask && rm -rf {target_dir} && git clone {github_link} {target_dir} && sudo apt update && sudo apt upgrade -y && sudo apt install python3-pip python3-venv -y && cd {target_dir} && python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt && pip install gunicorn && sudo ufw allow {port} && gunicorn --bind 0.0.0.0:{port} app:app --daemon',
        is_global=True
    )
    db.session.add(template)

    # 6. Simpan semua data sekaligus ke database
    db.session.commit()
    print(f"Data awal berhasil dibuat! Admin dan {len(daftar_nama)} user telah ditambahkan.")
