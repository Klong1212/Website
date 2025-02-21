from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__, static_folder='static', static_url_path='/static')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SECRET_KEY'] = 'thisisasecretkey'
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # จำกัดขนาดไฟล์ที่ 16MB
ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
ALLOWED_AUDIO_EXTENSIONS = {'mp3', 'wav'}
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
def allowed_file(filename, allowed_extensions):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions
           
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    songs = db.relationship('Song', backref='user', lazy=True)
    likes = db.relationship('Like', backref='user', lazy=True)

class Song(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    artist = db.Column(db.String(200), nullable=False)
    image_url = db.Column(db.String(500), nullable=False)
    audio_url = db.Column(db.String(500), nullable=False)
    lyrics_url = db.Column(db.String(500), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    likes = db.relationship('Like', backref='song', lazy=True)

class Like(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    song_id = db.Column(db.Integer, db.ForeignKey('song.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def home():
    songs = Song.query.order_by(Song.created_at.desc()).all()
    if current_user.is_authenticated:
        liked_songs = [like.song_id for like in Like.query.filter_by(user_id=current_user.id).all()]
    else:
        liked_songs = []
    return render_template('home.html', songs=songs, liked_songs=liked_songs)

@app.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    if request.method == 'POST':
        title = request.form.get('title')
        artist = request.form.get('artist')
        lyrics = request.form.get('lyrics')
        
        # ตรวจสอบว่ามีไฟล์ถูกส่งมาไหม
        if 'image' not in request.files or 'audio' not in request.files:
            flash('No file uploaded', 'danger')
            return redirect(request.url)
            
        image_file = request.files['image']
        audio_file = request.files['audio']
        
        # ตรวจสอบว่าเลือกไฟล์หรือไม่
        if image_file.filename == '' or audio_file.filename == '':
            flash('No selected file', 'danger')
            return redirect(request.url)
            
        if image_file and allowed_file(image_file.filename, ALLOWED_IMAGE_EXTENSIONS):
            # บันทึกไฟล์รูปภาพ
            image_filename = secure_filename(image_file.filename)
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], 'images', image_filename)
            os.makedirs(os.path.dirname(image_path), exist_ok=True)
            image_file.save(image_path)
            image_url = url_for('static', filename=f'uploads/images/{image_filename}')
        else:
            flash('Invalid image file type', 'danger')
            return redirect(request.url)
            
        if audio_file and allowed_file(audio_file.filename, ALLOWED_AUDIO_EXTENSIONS):
            # บันทึกไฟล์เสียง
            audio_filename = secure_filename(audio_file.filename)
            audio_path = os.path.join(app.config['UPLOAD_FOLDER'], 'audio', audio_filename)
            os.makedirs(os.path.dirname(audio_path), exist_ok=True)
            audio_file.save(audio_path)
            audio_url = url_for('static', filename=f'uploads/audio/{audio_filename}')
        else:
            flash('Invalid audio file type', 'danger')
            return redirect(request.url)

        if title and artist and lyrics and image_url and audio_url:
            new_song = Song(
                title=title,
                artist=artist,
                image_url=image_url,
                audio_url=audio_url,
                lyrics_url=lyrics,  # เก็บเนื้อเพลงโดยตรงในฐานข้อมูล
                user_id=current_user.id
            )
            db.session.add(new_song)
            db.session.commit()
            flash('Song added successfully!', 'success')
            return redirect(url_for('home'))
        
        flash('Please fill all required fields', 'danger')
    return render_template('add.html')

@app.route('/like/<int:song_id>', methods=['POST'])
@login_required
def toggle_like(song_id):
    existing_like = Like.query.filter_by(user_id=current_user.id, song_id=song_id).first()
    
    if existing_like:
        db.session.delete(existing_like)
        db.session.commit()
        return jsonify({'status': 'unliked'})
    else:
        new_like = Like(user_id=current_user.id, song_id=song_id)
        db.session.add(new_like)
        db.session.commit()
        return jsonify({'status': 'liked'})



@app.route('/signin', methods=['GET', 'POST'])
def signin():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'error')
            return redirect(url_for('signin'))
            
        hashed_password = generate_password_hash(password)
        new_user = User(username=username, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        
        flash('Account created successfully!', 'success')
        return redirect(url_for('login'))
        
    return render_template('signin.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password, password):
            login_user(user)
            flash('Logged in successfully!', 'success')
            return redirect(url_for('home'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully!', 'success')
    return redirect(url_for('home'))


@app.route('/like')
@login_required
def liked_songs():
    likes = Like.query.filter_by(user_id=current_user.id).order_by(Like.created_at.desc()).all()
    songs = [like.song for like in likes]
    return render_template('like.html', songs=songs)

# ... (routes เดิมสำหรับ login/logout/signin คงเดิม)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)