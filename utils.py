import re
import secrets
from functools import wraps
from flask import session, redirect, url_for, flash
from markupsafe import Markup, escape


def generate_csrf_token():
    if 'csrf_token' not in session:
        session['csrf_token'] = secrets.token_hex(32)
    return session['csrf_token']


def validate_csrf(token):
    return token and token == session.get('csrf_token')


_URL_RE = re.compile(r'(https?://[^\s<>"\']+)')

def linkify(text):
    escaped = escape(text)
    linked = _URL_RE.sub(
        lambda m: f'<a href="{m.group(1)}" target="_blank" rel="noopener noreferrer">{m.group(1)}</a>',
        str(escaped)
    )
    return Markup(linked)


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated
