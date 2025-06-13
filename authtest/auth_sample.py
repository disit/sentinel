from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import check_password_hash
from datetime import timedelta


app = Flask(__name__)
app.secret_key = 'changeme'
app.permanent_session_lifetime = timedelta(minutes=15)  # session expires after 15 mins of inactivity

USERS_FILE = 'users.txt'

def load_users():
    users = {}
    with open(USERS_FILE, 'r') as f:
        for line in f:
            if ' ' in line:
                username, hashed = line.strip().split(': ', 1)
                users[username] = hashed
    print(users)
    return users

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        users = load_users()
        username = request.form['username']
        password = request.form['password']
        print(username)
        print(check_password_hash(users[username], password))
        if username in users and check_password_hash(users[username], password):
            session.permanent = True
            session['username'] = username
            return redirect(url_for('dashboard'))
        return "Invalid credentials", 401
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'username' in session:
        return render_template('dashboard.html', username=session['username'])
    return redirect(url_for('login'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
