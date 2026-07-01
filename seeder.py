from models import app, db, User, Template
import bcrypt

with app.app_context():
    # Buat password
    hashed_pw = bcrypt.hashpw(b'123', bcrypt.gensalt()).decode('utf-8')

    # Buat User Admin
    admin = User(username='admin', password_hash=hashed_pw, role='admin')
    db.session.add(admin)
    db.session.commit()

    # Buat Template Global
    template = Template(
        nama_teknologi='Python Flask (Gunicorn)',
        perintah_default='cd {target_dir} && git pull origin main && source venv/bin/activate && pip install -r requirements.txt && sudo systemctl restart gunicorn',
        is_global=True
    )
    db.session.add(template)
    db.session.commit()
    print("Data awal berhasil dibuat!")
