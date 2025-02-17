from flask import Flask, render_template, request, redirect, url_for, flash
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
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
@app.route('/')
def home():
    return render_template('home.html')
@app.route('/mail')
def mail():
    return render_template('mail.html')
@app.route('/signin', methods=['GET', 'POST'])
def signin():
    if request.method == 'POST':  # ตรวจสอบว่าผู้ใช้กด Submit ฟอร์มหรือไม่
        username = request.form['username']  # รับค่าจาก input username
        password = request.form['password']  # รับค่าจาก input password

        # 🔹 ตรวจสอบว่ามี username นี้อยู่ในระบบแล้วหรือยัง
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists. Try another one.', 'danger')
            return redirect(url_for('signin'))

        # 🔹 เข้ารหัสรหัสผ่านก่อนเก็บในฐานข้อมูล

        # 🔹 สร้างผู้ใช้ใหม่ในฐานข้อมูล
        new_user = User(username=username, password=password)
        db.session.add(new_user)  # เพิ่มข้อมูลไปที่ฐานข้อมูล
        db.session.commit()  # บันทึกข้อมูลลงฐานข้อมูลจริงๆ

        flash('Account created successfully! You can now log in.', 'success')
        return redirect(url_for('login'))  # รีไดเร็กต์ไปหน้า Login

    return render_template('signin.html')  # ถ้าเป็น GET ให้แสดงฟอร์ม
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':  # ตรวจสอบว่าผู้ใช้กด Submit หรือไม่
        username = request.form['username']
        password = request.form['password']

        # 🔹 ค้นหาผู้ใช้จากฐานข้อมูล
        user = User.query.filter_by(username=username).first()

        if user and user.password == password:  
            login_user(user)  # ทำให้ผู้ใช้ล็อกอิน
            return redirect(url_for('home'))  # พาไปหน้า home
        else:
            flash('Invalid username or password', 'danger')  # แจ้งเตือนถ้าผิด

    return render_template('login.html')  # แสดงหน้า login

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', debug=True,use_reloader=True)