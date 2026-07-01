# app.py
from flask import request, render_template, redirect, url_for, flash, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
import bcrypt
import paramiko
from models import app, db, User, Template

# --- KONFIGURASI FLASK-LOGIN ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'  # Jika belum login, lempar ke rute ini


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# --- RUTE AUTENTIKASI ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password').encode('utf-8')

        user = User.query.filter_by(username=username).first()

        # Pengecekan password menggunakan bcrypt
        if user and bcrypt.checkpw(password, user.password_hash.encode('utf-8')):
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('Username atau password salah!', 'error')

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# --- RUTE LANDING PAGE (PUBLIK) ---
@app.route('/')
def index():
    # Jika user sudah login, langsung lempar ke dashboard
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('landing.html')

# --- RUTE DASHBOARD (HARUS LOGIN) ---
# Ubah rute dashboard yang tadinya '/' menjadi '/dashboard'
@app.route('/dashboard')
@login_required
def dashboard():
    templates = Template.query.filter(
        (Template.is_global == True) | (Template.user_id == current_user.id)
    ).all()
    return render_template('dashboard.html', templates=templates)


# --- API UNTUK MENGAMBIL PERINTAH OTOMATIS SAAT DROPDOWN DIPILIH ---
@app.route('/api/get_template/<int:template_id>', methods=['GET'])
@login_required
def get_template(template_id):
    template = Template.query.get(template_id)

    # Pastikan template ada dan user berhak melihatnya
    if template and (template.is_global or template.user_id == current_user.id):
        return jsonify({
            'status': 'success',
            'perintah_default': template.perintah_default
        })

    return jsonify({'status': 'error', 'message': 'Template tidak ditemukan'}), 404


# --- API UNTUK MENGEKSEKUSI SSH (TAHAP 4) ---
# --- API UNTUK MENGEKSEKUSI SSH (TAHAP 4 & LOGIKA PORT) ---
@app.route('/api/execute_deploy', methods=['POST'])
@login_required
def execute_deploy():
    data = request.json
    print(data)
    return
    ip = data.get('ip')
    password = data.get('password')
    github_link = data.get('github_link')
    perintah_mentah = data.get('perintah')
    port = data.get('port', '')
    kill_port = data.get('kill_port', False)  # Menangkap perintah dari kotak dialog

    username = data.get('username', 'root')

    if not all([ip, password, github_link, perintah_mentah]):
        return jsonify({'status': 'error', 'log': 'Semua field utama harus diisi!'}), 400

    # 1. LOGIKA PEMBENTUKAN TARGET DIR
    # Mengambil username dan nama repo dari link GitHub
    # Contoh: https://github.com/petani/aplikasiku.git -> petani_aplikasiku
    try:
        link_bersih = github_link.replace('.git', '').rstrip('/')
        parts = link_bersih.split('/')
        if len(parts) >= 2:
            target_dir = f"{parts[-2]}_{parts[-1]}"
        else:
            target_dir = "app_deployment_default"
    except Exception:
        target_dir = "app_deployment_default"

    # 2. LOGIKA PENGECEKAN & PENGHANCURAN PORT
    perintah_awal = ""
    if port and kill_port:
        # fuser -k akan mematikan proses (kill) yang memakai port tersebut
        # "|| true" digunakan agar script tidak error jika port ternyata kosong
        perintah_awal = f"fuser -k {port}/tcp || true ; "

    # 3. MENGGANTI SEMUA VARIABEL DI TEMPLATE
    perintah_siap_eksekusi = perintah_mentah.replace('{github_link}', github_link)
    perintah_siap_eksekusi = perintah_siap_eksekusi.replace('{target_dir}', target_dir)
    perintah_siap_eksekusi = perintah_siap_eksekusi.replace('{port}', str(port))

    # Gabungkan perintah matikan port dengan perintah template
    perintah_final = perintah_awal + perintah_siap_eksekusi

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        ssh.connect(hostname=ip, port=22, username=username, password=password, timeout=10)
        
        # Eksekusi perintah final di VPS
        stdin, stdout, stderr = ssh.exec_command(perintah_final)
        exit_status = stdout.channel.recv_exit_status()

        out = stdout.read().decode('utf-8')
        err = stderr.read().decode('utf-8')

        full_log = f"--- VARIABEL OTOMATIS ---\nTarget Dir: {target_dir}\nPort: {port}\n\n"
        full_log += f"--- OUTPUT TANGGAPAN ---\n{out}\n"

        if err:
            full_log += f"--- PESAN ERROR / PERINGATAN ---\n{err}"

        return jsonify({
            'status': 'success' if exit_status == 0 else 'warning',
            'log': full_log
        })

    except paramiko.AuthenticationException:
        return jsonify({'status': 'error', 'log': 'Autentikasi gagal. Periksa IP atau Password VPS.'})
    except Exception as e:
        return jsonify({'status': 'error', 'log': f'Terjadi kesalahan koneksi SSH: {str(e)}'})
    finally:
        ssh.close()

# --- RUTE MANAJEMEN TEMPLATE ---
@app.route('/manage-templates', methods=['GET', 'POST'])
@login_required
def manage_templates():
    if request.method == 'POST':
        nama_teknologi = request.form.get('nama_teknologi')
        perintah_default = request.form.get('perintah_default')

        # Cek apakah ini dicentang sebagai template global
        # (Hanya berlaku jika yang menekan tombol adalah admin)
        is_global = False
        if current_user.role == 'admin' and request.form.get('is_global') == 'on':
            is_global = True

        if nama_teknologi and perintah_default:
            new_template = Template(
                nama_teknologi=nama_teknologi,
                perintah_default=perintah_default,
                is_global=is_global,
                # Jika global, user_id dikosongkan. Jika pribadi, isi dengan ID pembuatnya.
                user_id=None if is_global else current_user.id
            )
            db.session.add(new_template)
            db.session.commit()
            flash('Template baru berhasil ditambahkan!', 'success')
        else:
            flash('Gagal! Nama teknologi dan perintah tidak boleh kosong.', 'error')

        return redirect(url_for('manage_templates'))

    # Menampilkan daftar template di tabel
    # Jika Admin: Bisa melihat SEMUA template di database
    # Jika User biasa: Hanya bisa melihat template pribadi miliknya
    if current_user.role == 'admin':
        templates = Template.query.all()
    else:
        templates = Template.query.filter_by(user_id=current_user.id).all()

    return render_template('manage_template.html', templates=templates)


# --- RUTE UNTUK MENGEDIT TEMPLATE ---
@app.route('/edit-template/<int:id>', methods=['POST'])
@login_required
def edit_template(id):
    template = Template.query.get_or_404(id)

    # Validasi Keamanan: Hanya Admin atau Pembuat Template yang boleh mengedit
    if current_user.role == 'admin' or template.user_id == current_user.id:
        template.nama_teknologi = request.form.get('nama_teknologi')
        template.perintah_default = request.form.get('perintah_default')

        # Cek checkbox global (Hanya Admin)
        if current_user.role == 'admin':
            template.is_global = True if request.form.get('is_global') == 'on' else False

        db.session.commit()
        flash('Template berhasil diperbarui!', 'success')
    else:
        flash('Akses ditolak! Anda tidak diizinkan mengedit template ini.', 'error')

    return redirect(url_for('manage_templates'))


# --- RUTE UNTUK MENGHAPUS TEMPLATE ---
@app.route('/delete-template/<int:id>', methods=['POST'])
@login_required
def delete_template(id):
    template = Template.query.get_or_404(id)

    # Validasi Keamanan: Admin bisa hapus apapun, User hanya bisa hapus miliknya sendiri
    if current_user.role == 'admin' or template.user_id == current_user.id:
        db.session.delete(template)
        db.session.commit()
        flash('Template berhasil dihapus!', 'success')
    else:
        flash('Akses ditolak! Anda tidak bisa menghapus template ini.', 'error')

    return redirect(url_for('manage_templates'))


# --- JALANKAN APLIKASI & AUTO SETUP DATABASE ---
if __name__ == '__main__':
    # 1. Buka konteks aplikasi agar bisa berinteraksi dengan database
    with app.app_context():
        # 2. Buat file SQLite dan tabel-tabelnya jika belum ada
        db.create_all()

        # 3. Cek apakah tabel User masih kosong
        if not User.query.first():
            print("Database kosong terdeteksi. Memulai proses seeding...")

            # Buat password (menggunakan bcrypt yang sudah di-import di atas)
            hashed_pw = bcrypt.hashpw(b'123', bcrypt.gensalt()).decode('utf-8')

            # Buat User Admin
            admin = User(username='admin', password_hash=hashed_pw, role='admin')
            db.session.add(admin)

            # Buat Template Global
            template = Template(
                nama_teknologi='Python Flask (Gunicorn)',
                perintah_default='cd {target_dir} && git pull origin main && source venv/bin/activate && pip install -r requirements.txt && sudo systemctl restart gunicorn',
                is_global=True
            )
            db.session.add(template)

            # Simpan perubahan ke database
            db.session.commit()
            print("Data awal (seeding) berhasil dibuat! Akun 'admin' dengan password '123' siap digunakan.")
        else:
            print("Database sudah berisi data. Melewati proses seeding.")

    # 4. Jalankan server Flask
    app.run(debug=True, port=5000)