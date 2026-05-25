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


_MARKDOWN_LINK_RE = re.compile(r'\[([^\]]+)\]\((https?://[^\)]+)\)')
_IMAGE_URL_RE = re.compile(
    r'(?<!href=")(https?://(?:res\.cloudinary\.com/[^\s<>"\']+|[^\s<>"\']+\.(?:jpg|jpeg|png|gif|webp))(?:\?[^\s<>"\']*)?)',
    re.IGNORECASE,
)
_URL_RE = re.compile(r'(?<!href=")(?<!src=")(https?://[^\s<>"\']+)')

def linkify(text):
    escaped = str(escape(text))
    escaped = _MARKDOWN_LINK_RE.sub(
        lambda m: f'<a href="{m.group(2)}" target="_blank" rel="noopener noreferrer">{m.group(1)}</a>',
        escaped
    )
    escaped = _IMAGE_URL_RE.sub(
        lambda m: f'<img src="{m.group(1)}" class="thread-img" alt="image">',
        escaped
    )
    escaped = _URL_RE.sub(
        lambda m: f'<a href="{m.group(1)}" target="_blank" rel="noopener noreferrer">{m.group(1)}</a>',
        escaped
    )
    return Markup(escaped)


_AXIOS_LABELS = re.compile(
    r'((?:Why it matters|The big picture|The intrigue|Between the lines|'
    r"What(?:'s| is) inside|What(?:'s| is) next|Yes, but|Zoom in|Zoom out|"
    r'State of play|What they(?:\'re| are) saying|What to watch|'
    r'Driving the news|By the numbers|Of note|The bottom line|'
    r'How it works|What we know|Catch up quick):)',
    re.IGNORECASE,
)

def format_summary(text):
    if not text:
        return Markup('')
    escaped = str(escape(text))
    # Insert paragraph breaks before Axios-style section labels
    escaped = _AXIOS_LABELS.sub(r'\n\n\1', escaped)
    # Split into paragraphs
    paragraphs = re.split(r'\n{2,}', escaped)
    parts = []
    for para in paragraphs:
        para = para.strip().replace('\n', '<br>')
        if para:
            parts.append(f'<p class="summary-para">{para}</p>')
    return Markup('\n'.join(parts))


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated
