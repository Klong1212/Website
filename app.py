from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os
from werkzeug.utils import secure_filename

# สร้าง Flask application และกำหนดค่าต่างๆ
app = Flask(__name__, static_folder='static', static_url_path='/static')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'  # กำหนดที่อยู่ของฐานข้อมูล SQLite
app.config['SECRET_KEY'] = 'thisisasecretkey'  # คีย์ลับสำหรับการเข้ารหัส session
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')  # โฟลเดอร์สำหรับเก็บไฟล์ที่อัปโหลด
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # จำกัดขนาดไฟล์ที่อัปโหลดไม่เกิน 16MB

# กำหนดประเภทไฟล์ที่อนุญาตให้อัปโหลด
ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
ALLOWED_AUDIO_EXTENSIONS = {'mp3', 'wav'}

# เริ่มต้น SQLAlchemy และ LoginManager
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'  # กำหนดหน้า login เป็นหน้าเริ่มต้นหากผู้ใช้ยังไม่ได้ล็อกอิน

# ฟังก์ชันตรวจสอบประเภทไฟล์ที่อนุญาตให้อัปโหลด
def allowed_file(filename, allowed_extensions):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions

# กำหนดโมเดล User สำหรับเก็บข้อมูลผู้ใช้
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)  # ชื่อผู้ใช้
    password = db.Column(db.String(150), nullable=False)  # รหัสผ่าน (เข้ารหัสแล้ว)
    name = db.Column(db.String(150), default='Noman')  # ชื่อแสดง
    profile_pic = db.Column(db.String(500), default='/static/uploads/profile/default.png')  # รูปโปรไฟล์
    is_admin = db.Column(db.Boolean, default=False)  # สถานะผู้ดูแลระบบ
    songs = db.relationship('Song', backref='user', lazy=True)  # ความสัมพันธ์กับโมเดล Song
    likes = db.relationship('Like', backref='user', lazy=True)  # ความสัมพันธ์กับโมเดล Like

# กำหนดโมเดล Song สำหรับเก็บข้อมูลเพลง
class Song(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)  # ชื่อเพลง
    artist = db.Column(db.String(200), nullable=False)  # ชื่อศิลปิน
    image_url = db.Column(db.String(500), nullable=False)  # URL รูปภาพปกเพลง
    audio_url = db.Column(db.String(500), nullable=False)  # URL ไฟล์เสียงเพลง
    lyrics_url = db.Column(db.Text, nullable=False)  # เนื้อเพลง
    created_at = db.Column(db.DateTime, default=datetime.utcnow)  # เวลาที่สร้างเพลง
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # ไอดีผู้ใช้ที่สร้างเพลง
    likes = db.relationship('Like', backref='song', lazy=True)  # ความสัมพันธ์กับโมเดล Like

# กำหนดโมเดล Like สำหรับเก็บข้อมูลการกดไลค์เพลง
class Like(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # ไอดีผู้ใช้ที่กดไลค์
    song_id = db.Column(db.Integer, db.ForeignKey('song.id'), nullable=False)  # ไอดีเพลงที่ถูกไลค์
    created_at = db.Column(db.DateTime, default=datetime.utcnow)  # เวลาที่กดไลค์

# ฟังก์ชันสำหรับโหลดผู้ใช้จากฐานข้อมูล
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# หน้าแรกของเว็บแอป
@app.route('/')
def home():
    songs = Song.query.order_by(Song.created_at.desc()).all()  # ดึงข้อมูลเพลงทั้งหมดเรียงจากใหม่ไปเก่า
    if current_user.is_authenticated:  # ตรวจสอบว่าผู้ใช้ล็อกอินอยู่หรือไม่
        liked_songs = [like.song_id for like in Like.query.filter_by(user_id=current_user.id).all()]  # ดึงรายการเพลงที่ผู้ใช้ไลค์
    else:
        liked_songs = []
    return render_template('home.html', songs=songs, liked_songs=liked_songs)  # แสดงหน้า home.html พร้อมข้อมูลเพลง

# หน้าจัดการเพลงสำหรับผู้ดูแลระบบ
@app.route('/admin/songs')
@login_required  # ต้องล็อกอินก่อนเข้าถึง
def admin_songs():
    if not current_user.is_admin:  # ตรวจสอบว่าผู้ใช้เป็นผู้ดูแลระบบหรือไม่
        return redirect(url_for('home'))
    songs = Song.query.all()  # ดึงข้อมูลเพลงทั้งหมด
    return render_template('admin_songs.html', songs=songs)  # แสดงหน้า admin_songs.html พร้อมข้อมูลเพลง

# ลบผู้ใช้ (สำหรับผู้ดูแลระบบ)
@app.route('/admin/delete-user/<int:user_id>', methods=['POST'])
@login_required
def delete_user(user_id):
    if not current_user.is_admin:  # ตรวจสอบสิทธิ์ผู้ดูแลระบบ
        return jsonify({"status": "error", "message": "Unauthorized action!"})

    try:
        user = User.query.get(user_id)  # ค้นหาผู้ใช้จากไอดี
        if user:
            # ลบเพลงและไฟล์ที่เกี่ยวข้องกับผู้ใช้
            songs = Song.query.filter_by(user_id=user.id).all()
            for song in songs:
                if os.path.exists(os.path.join(app.root_path, song.image_url.lstrip('/'))):
                    os.remove(os.path.join(app.root_path, song.image_url.lstrip('/')))  # ลบไฟล์รูปภาพ
                if os.path.exists(os.path.join(app.root_path, song.audio_url.lstrip('/'))):
                    os.remove(os.path.join(app.root_path, song.audio_url.lstrip('/')))  # ลบไฟล์เสียง

            Like.query.filter_by(user_id=user.id).delete()  # ลบข้อมูลไลค์
            Song.query.filter_by(user_id=user.id).delete()  # ลบเพลง
            db.session.delete(user)  # ลบผู้ใช้
            db.session.commit()  # บันทึกการเปลี่ยนแปลง
            return jsonify({"status": "success", "message": "User deleted successfully!"})
        else:
            return jsonify({"status": "error", "message": "User not found!"})
    except Exception as e:
        db.session.rollback()  # ยกเลิกการเปลี่ยนแปลงหากเกิดข้อผิดพลาด
        return jsonify({"status": "error", "message": str(e)})

# ลบเพลง (สำหรับผู้ดูแลระบบ)
@app.route('/admin/delete-song/<int:song_id>', methods=['POST'])
@login_required
def delete_song(song_id):
    if not current_user.is_admin:  # ตรวจสอบสิทธิ์ผู้ดูแลระบบ
        return jsonify({'status': 'error', 'message': 'Unauthorized'})
    try:
        song = Song.query.get_or_404(song_id)  # ค้นหาเพลงจากไอดี
        # ลบไฟล์รูปภาพและเสียง
        if os.path.exists(os.path.join(app.root_path, song.image_url.lstrip('/'))):
            os.remove(os.path.join(app.root_path, song.image_url.lstrip('/')))
        if os.path.exists(os.path.join(app.root_path, song.audio_url.lstrip('/'))):
            os.remove(os.path.join(app.root_path, song.audio_url.lstrip('/')))

        Like.query.filter_by(song_id=song.id).delete()  # ลบข้อมูลไลค์
        db.session.delete(song)  # ลบเพลง
        db.session.commit()  # บันทึกการเปลี่ยนแปลง
        return jsonify({'status': 'success'})
    except Exception as e:
        db.session.rollback()  # ยกเลิกการเปลี่ยนแปลงหากเกิดข้อผิดพลาด
        return jsonify({'status': 'error', 'message': str(e)})

# เพิ่มเพลงใหม่
@app.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    if request.method == 'POST':
        title = request.form.get('title')  # ชื่อเพลง
        artist = request.form.get('artist')  # ชื่อศิลปิน
        lyrics = request.form.get('lyrics')  # เนื้อเพลง

        # ตรวจสอบว่ามีไฟล์ถูกอัปโหลดหรือไม่
        if 'image' not in request.files or 'audio' not in request.files:
            flash('No file uploaded', 'danger')
            return redirect(request.url)

        image_file = request.files['image']  # ไฟล์รูปภาพ
        audio_file = request.files['audio']  # ไฟล์เสียง

        # ตรวจสอบว่าไฟล์ถูกเลือกหรือไม่
        if image_file.filename == '' or audio_file.filename == '':
            flash('No selected file', 'danger')
            return redirect(request.url)

        # ตรวจสอบประเภทไฟล์รูปภาพ
        if image_file and allowed_file(image_file.filename, ALLOWED_IMAGE_EXTENSIONS):
            image_filename = secure_filename(image_file.filename)  # ป้องกันชื่อไฟล์ไม่ปลอดภัย
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], 'images', image_filename)
            os.makedirs(os.path.dirname(image_path), exist_ok=True)  # สร้างโฟลเดอร์หากไม่มี
            image_file.save(image_path)  # บันทึกไฟล์
            image_url = url_for('static', filename=f'uploads/images/{image_filename}')  # สร้าง URL สำหรับไฟล์
        else:
            flash('Invalid image file type', 'danger')
            return redirect(request.url)

        # ตรวจสอบประเภทไฟล์เสียง
        if audio_file and allowed_file(audio_file.filename, ALLOWED_AUDIO_EXTENSIONS):
            audio_filename = secure_filename(audio_file.filename)
            audio_path = os.path.join(app.config['UPLOAD_FOLDER'], 'audio', audio_filename)
            os.makedirs(os.path.dirname(audio_path), exist_ok=True)
            audio_file.save(audio_path)
            audio_url = url_for('static', filename=f'uploads/audio/{audio_filename}')
        else:
            flash('Invalid audio file type', 'danger')
            return redirect(request.url)

        # บันทึกเพลงใหม่ลงฐานข้อมูล
        if title and artist and lyrics and image_url and audio_url:
            new_song = Song(
                title=title,
                artist=artist,
                image_url=image_url,
                audio_url=audio_url,
                lyrics_url=lyrics,
                user_id=current_user.id
            )
            db.session.add(new_song)
            db.session.commit()
            flash('Song added successfully!', 'success')
            return redirect(url_for('home'))

        flash('Please fill all required fields', 'danger')
    return render_template('add.html')

# ไลค์หรือยกเลิกไลค์เพลง
@app.route('/like/<int:song_id>', methods=['POST'])
@login_required
def toggle_like(song_id):
    existing_like = Like.query.filter_by(user_id=current_user.id, song_id=song_id).first()  # ตรวจสอบว่าผู้ใช้ไลค์เพลงนี้แล้วหรือไม่
    if existing_like:
        db.session.delete(existing_like)  # ยกเลิกไลค์
        db.session.commit()
        return jsonify({'status': 'unliked'})
    else:
        new_like = Like(user_id=current_user.id, song_id=song_id)  # เพิ่มไลค์ใหม่
        db.session.add(new_like)
        db.session.commit()
        return jsonify({'status': 'liked'})

# แก้ไขโปรไฟล์ผู้ใช้
@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        name = request.form.get('name')  # ชื่อแสดง
        profile_pic = request.files.get('profile_pic')  # รูปโปรไฟล์

        if name:
            current_user.name = name  # อัปเดตชื่อแสดง

        if profile_pic and allowed_file(profile_pic.filename, ALLOWED_IMAGE_EXTENSIONS):
            filename = secure_filename(profile_pic.filename)
            profile_pic_path = os.path.join(app.config['UPLOAD_FOLDER'], 'profile', filename)
            os.makedirs(os.path.dirname(profile_pic_path), exist_ok=True)
            profile_pic.save(profile_pic_path)
            current_user.profile_pic = url_for('static', filename=f'uploads/profile/{filename}')  # อัปเดตรูปโปรไฟล์

        db.session.commit()  # บันทึกการเปลี่ยนแปลง
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('profile'))

    return render_template('profile.html')

# ล็อกอินสำหรับผู้ดูแลระบบ
@app.route('/admin-login', methods=['GET', 'POST'])
@login_required
def admin_login():
    if request.method == 'POST':
        password = request.form.get('password')
        if password == '12345678':  # รหัสผ่านสำหรับผู้ดูแลระบบ
            current_user.is_admin = True
            db.session.commit()
            return redirect(url_for('admin'))
        flash('Invalid admin password', 'error')
    return redirect(url_for('profile'))

# หน้าผู้ดูแลระบบ
@app.route('/admin')
@login_required
def admin():
    if not current_user.is_admin:  # ตรวจสอบสิทธิ์ผู้ดูแลระบบ
        return redirect(url_for('home'))
    users = User.query.all()  # ดึงข้อมูลผู้ใช้ทั้งหมด
    songs = Song.query.all()  # ดึงข้อมูลเพลงทั้งหมด
    return render_template('admin.html', users=users, songs=songs)

# หน้าสมัครสมาชิก
@app.route('/signin', methods=['GET', 'POST'])
def signin():
    if request.method == 'POST':
        username = request.form.get('username')  # ชื่อผู้ใช้
        password = request.form.get('password')  # รหัสผ่าน

        if User.query.filter_by(username=username).first():  # ตรวจสอบว่าชื่อผู้ใช้มีอยู่แล้วหรือไม่
            flash('Username already exists', 'error')
            return redirect(url_for('signin'))

        hashed_password = generate_password_hash(password)  # เข้ารหัสรหัสผ่าน
        new_user = User(username=username, password=hashed_password)  # สร้างผู้ใช้ใหม่
        db.session.add(new_user)
        db.session.commit()

        flash('Account created successfully!', 'success')
        return redirect(url_for('login'))

    return render_template('signin.html')

# หน้าล็อกอิน
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')  # ชื่อผู้ใช้
        password = request.form.get('password')  # รหัสผ่าน
        user = User.query.filter_by(username=username).first()  # ค้นหาผู้ใช้จากชื่อผู้ใช้

        if user and check_password_hash(user.password, password):  # ตรวจสอบรหัสผ่าน
            login_user(user)  # ล็อกอินผู้ใช้
            flash('Logged in successfully!', 'success')
            return redirect(url_for('home'))
        else:
            flash('Invalid username or password', 'error')

    return render_template('login.html')

# ออกจากระบบ
@app.route('/logout')
@login_required
def logout():
    logout_user()  # ล็อกเอาท์ผู้ใช้
    flash('Logged out successfully!', 'success')
    return redirect(url_for('home'))

# หน้าเพลงที่ถูกไลค์มากที่สุด
@app.route('/favorite')
def favorite():
    song_likes = db.session.query(Song, db.func.count(Like.id).label('like_count')) \
        .join(Like, Song.id == Like.song_id, isouter=True) \
        .group_by(Song.id) \
        .order_by(db.desc('like_count')) \
        .all()  # ดึงข้อมูลเพลงพร้อมจำนวนไลค์เรียงจากมากไปน้อย
    return render_template('favorite.html', song_likes=song_likes)

# หน้าผู้ใช้ทั้งหมด
@app.route('/people')
def people():
    users = User.query.all()  # ดึงข้อมูลผู้ใช้ทั้งหมด
    return render_template('people.html', users=users)

# หน้าโปรไฟล์ผู้ใช้
@app.route('/user/<int:user_id>')
def user_profile(user_id):
    user = User.query.get_or_404(user_id)  # ค้นหาผู้ใช้จากไอดี
    songs = Song.query.filter_by(user_id=user_id).order_by(Song.created_at.desc()).all()  # ดึงเพลงของผู้ใช้
    return render_template('user_profile.html', user=user, songs=songs)

# หน้าเพลงที่ผู้ใช้ไลค์
@app.route('/like')
@login_required
def liked_songs():
    likes = Like.query.filter_by(user_id=current_user.id).order_by(Like.created_at.desc()).all()  # ดึงรายการไลค์ของผู้ใช้
    songs = [like.song for like in likes]  # ดึงข้อมูลเพลงที่ถูกไลค์
    return render_template('like.html', songs=songs)

# เริ่มต้นการทำงานของแอปพลิเคชัน
if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # สร้างตารางในฐานข้อมูลหากยังไม่มี
    app.run(debug=True)  # เริ่มเซิร์ฟเวอร์ในโหมด debug