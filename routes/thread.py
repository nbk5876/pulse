from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify
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
                db.session.flush()
                # Keep only the newest 500 posts
                cutoff = db.session.query(ThreadPost.id).order_by(
                    ThreadPost.created_at.desc()
                ).offset(500).limit(1).scalar()
                if cutoff:
                    ThreadPost.query.filter(ThreadPost.id <= cutoff).delete()
                db.session.commit()
        return redirect(url_for('thread.thread'))

    posts = ThreadPost.query.order_by(ThreadPost.created_at.desc()).limit(100).all()
    user = User.query.get(session['user_id'])
    return render_template('thread.html', posts=posts, user=user)


@thread_bp.route('/thread/poll')
@login_required
def thread_poll():
    since_id = request.args.get('since', 0, type=int)
    posts = ThreadPost.query.filter(ThreadPost.id > since_id)\
        .order_by(ThreadPost.created_at.asc()).all()
    return jsonify([{
        'id': p.id,
        'username': p.user.username,
        'body': p.body,
        'created_at': p.created_at.strftime('%b %d %I:%M %p'),
    } for p in posts])
