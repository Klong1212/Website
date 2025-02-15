from flask import Flask
from flask import render_template

app = Flask(__name__)
@app.route('/')
def main():
    return render_template('index.html')
@app.route('/signin')
def login():
    return render_template('signin.html')
if __name__ == '__main__':
    app.run(host='0.0.0.0',debug=True)