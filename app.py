# app.py
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__, static_folder='static', static_url_path='/static')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SECRET_KEY'] = 'thisisasecretkey'
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Models
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    links = db.relationship('SearchLink', backref='user', lazy=True)

class SearchLink(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    keyword = db.Column(db.String(200), nullable=False)
    url = db.Column(db.String(500), nullable=False)
    description = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Routes
@app.route('/')
def home():
    return render_template('home.html')

@app.route('/like')
def like():
    return render_template('like.html')

@app.route('/signin', methods=['GET', 'POST'])
def signin():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists. Try another one.', 'danger')
            return redirect(url_for('signin'))
            
        new_user = User(username=username, password=password)
        db.session.add(new_user)
        db.session.commit()
        
        flash('Account created successfully! You can now log in.', 'success')
        return redirect(url_for('login'))
        
    return render_template('signin.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.password == password:
            login_user(user)
            return redirect(url_for('home'))
        else:
            flash('Invalid username or password', 'danger')
            
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

# Search system routes
@app.route('/api/search')
def search_api():
    query = request.args.get('q', '').lower()
    links = SearchLink.query.filter(
        (SearchLink.keyword.ilike(f'%{query}%')) |
        (SearchLink.description.ilike(f'%{query}%'))
    ).all()
    
    results = []
    for link in links:
        results.append({
            'id': link.id,
            'text': link.keyword,
            'url': link.url,
            'description': link.description
        })
    
    return jsonify(results)

@app.route('/add', methods=['GET', 'POST'])
@login_required
def add_search():
    if request.method == 'POST':
        keyword = request.form.get('keyword')
        url = request.form.get('url')
        description = request.form.get('description')
        
        if keyword and url:
            new_link = SearchLink(
                keyword=keyword,
                url=url,
                description=description,
                user_id=current_user.id
            )
            db.session.add(new_link)
            db.session.commit()
            return jsonify({'status': 'success'})
    
    return render_template('add.html')

@app.route('/manage')
@login_required
def manage_links():
    links = SearchLink.query.filter_by(user_id=current_user.id).order_by(SearchLink.created_at.desc()).all()
    return render_template('manage.html', links=links)

@app.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete_link(id):
    link = SearchLink.query.get_or_404(id)
    if link.user_id == current_user.id:
        db.session.delete(link)
        db.session.commit()
        return jsonify({'status': 'success'})
    return jsonify({'status': 'error', 'message': 'Unauthorized'}), 403

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', debug=True, use_reloader=True)