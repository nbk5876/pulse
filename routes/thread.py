from flask import Blueprint, render_template, request, redirect, url_for, session
from models import db
from models.thread import ThreadPost
from models.user import User
from utils import login_required, validate_csrf

thread_bp = Blueprint('thread', __name__)


@thread_bp.route('/thread', methods=['GET', 'POST'])
@login_required
def thread():
    if request.method == 'POST':
        if validate_csrf(request.form.get('csrf_token')):
            body = request.form.get('body', '').strip()
            if body:
                db.session.add(ThreadPost(user_id=session['user_id'], body=body))
                db.session.commit()
        return redirect(url_for('thread.thread'))

    posts = ThreadPost.query.order_by(ThreadPost.created_at.desc()).limit(100).all()
    user = User.query.get(session['user_id'])
    return render_template('thread.html', posts=posts, user=user)
