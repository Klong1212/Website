from flask import Flask, request, session, render_template, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__, static_folder='static', static_url_path='/static')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SECRET_KEY'] = 'thisisasecretkey'

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/mail')
@login_required
def mail():
    return render_template('mail.html')

@app.route('/signin', methods=['GET', 'POST'])
def signin():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        # ตรวจสอบว่ามีอีเมลนี้ในระบบแล้วหรือไม่
        user = User.query.filter_by(email=email).first()
        if user:
            flash('อีเมลนี้มีในระบบแล้ว กรุณาใช้อีเมลอื่น')
            return redirect(url_for('signin'))
        
        # สร้าง user ใหม่
        new_user = User(
            email=email,
            password=generate_password_hash(password, method='sha256')
        )
        db.session.add(new_user)
        db.session.commit()
        
        flash('ลงทะเบียนสำเร็จ กรุณาเข้าสู่ระบบ')
        return redirect(url_for('login'))
    
    return render_template('signin.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False
        
        user = User.query.filter_by(email=email).first()
        if not user or not check_password_hash(user.password, password):
            flash('อีเมลหรือรหัสผ่านไม่ถูกต้อง')
            return redirect(url_for('login'))
        
        login_user(user, remember=remember)
        return redirect(url_for('mail'))
    
    return render_template('signin.html')  # ใช้ template เดียวกับ signin

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', debug=True, use_reloader=True)