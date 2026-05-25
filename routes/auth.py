from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from models import db
from models.user import User
from utils import validate_csrf

auth_bp = Blueprint('auth', __name__)

ALIGNMENTS = ['Progressive', 'Moderate Progressive', 'Moderate', 'Conservative', 'Libertarian', 'Other']


@auth_bp.route('/')
def landing():
    if session.get('user_id'):
        return redirect(url_for('topics.feed'))
    return render_template('landing.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if session.get('user_id'):
        return redirect(url_for('topics.feed'))

    if request.method == 'POST':
        if not validate_csrf(request.form.get('csrf_token')):
            flash('Invalid form submission.', 'error')
            return redirect(url_for('auth.register'))

        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        alignment = request.form.get('political_alignment', '')

        errors = []
        if not username:
            errors.append('Username is required.')
        if not email:
            errors.append('Email is required.')
        if len(password) < 8:
            errors.append('Password must be at least 8 characters.')
        if User.query.filter_by(username=username).first():
            errors.append('Username already taken.')
        if User.query.filter_by(email=email).first():
            errors.append('Email already registered.')

        if errors:
            for e in errors:
                flash(e, 'error')
            return render_template('register.html', alignments=ALIGNMENTS,
                                   form={'username': username, 'email': email, 'alignment': alignment})

        user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password),
            political_alignment=alignment,
        )
        db.session.add(user)
        db.session.commit()

        session['user_id'] = user.id
        session['username'] = user.username

        try:
            from models.thread import ThreadPost
            bot_id = user.id
            body = f'🆕 New member: {username} just joined Pulse. Welcome!'
            db.session.add(ThreadPost(user_id=bot_id, body=body))
            db.session.commit()
        except Exception:
            pass

        flash('Welcome to Pulse! Select your interests to personalize your feed.', 'success')
        return redirect(url_for('profile.interests'))

    return render_template('register.html', alignments=ALIGNMENTS, form={})


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('user_id'):
        return redirect(url_for('topics.feed'))

    if request.method == 'POST':
        if not validate_csrf(request.form.get('csrf_token')):
            flash('Invalid form submission.', 'error')
            return redirect(url_for('auth.login'))

        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        user = User.query.filter_by(email=email).first()
        if not user or not check_password_hash(user.password_hash, password):
            flash('Invalid email or password.', 'error')
            return render_template('login.html', form={'email': email},
                                   next=request.form.get('next', ''))

        if request.form.get('remember'):
            session.permanent = True

        session['user_id'] = user.id
        session['username'] = user.username

        next_url = request.form.get('next', '').strip()
        if next_url and next_url.startswith('/'):
            return redirect(next_url)
        return redirect(url_for('topics.feed'))

    return render_template('login.html', form={})


@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.landing'))
