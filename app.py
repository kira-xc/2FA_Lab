
from flask import Flask, render_template, redirect, request, session,send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.orm import Mapped, mapped_column
import random
import datetime
import os

app = Flask(__name__)
app.secret_key = "your-secret-key"

# Database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
db = SQLAlchemy(app)

# Email Config
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'your_sender_email@mail.com'
app.config['MAIL_PASSWORD'] = 'your_password'
mail = Mail(app)

# ===============================
# Models with SQLAlchemy 2.x Typing
# ===============================
class User(db.Model):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(db.String(80), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(db.String(120), unique=True, nullable=False)
    password: Mapped[str] = mapped_column(db.String(200), nullable=False)


class TwoFactor(db.Model):
    __tablename__ = "twofactor"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(db.ForeignKey("users.id"))
    code: Mapped[str] = mapped_column(db.String(6))
    created_at: Mapped[datetime.datetime] = mapped_column(default=datetime.datetime.now)


# ===============================
# Routes
# ===============================

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')

@app.route('/')
def home():
    if 'user_id' not in session:
        return redirect('/login')
    return render_template('home.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])

        user = User(username=username, email=email, password=password)
        db.session.add(user)
        db.session.commit()
        return redirect('/login')

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session['temp_user_id'] = user.id

            code = str(random.randint(100000, 999999))
            auth = TwoFactor(user_id=user.id, code=code)
            db.session.add(auth)
            db.session.commit()

            msg = Message('Your Login Code', sender='no-reply@example.com', recipients=[user.email])
            html_body = f"""
            <h2>🔐 Login Verification</h2>
            <p>Your verification code is:</p>
            <h1 style='font-size:28px; font-weight:bold; letter-spacing:4px;'>{code}</h1>
            <p>This code expires in 5 minutes.</p>
            """
            msg.html = html_body
            mail.send(msg)

            return redirect('/2fa')

    return render_template('login.html')


@app.route('/2fa', methods=['GET', 'POST'])
def two_factor():
    if 'temp_user_id' not in session:
        return redirect('/login')

    if request.method == 'POST':
        code = request.form['code']
        user_id = session['temp_user_id']

        record = TwoFactor.query.filter_by(user_id=user_id, code=code).first()
        if record:
            session['user_id'] = user_id
            session.pop('temp_user_id')
            return redirect('/')

    return render_template('two_factor.html')


# ===============================
# Logout
# ===============================
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')


# ===============================
# Profile Page
# ===============================
@app.route('/profile')
def profile():
    if 'user_id' not in session:
        return redirect('/login')
    user = User.query.get(session['user_id'])
    return render_template('profile.html', user=user)


if __name__ == '__main__':
    app.run()


