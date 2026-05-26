import os
import cloudinary
import cloudinary.uploader
from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify
from models import db
from models.thread import ThreadPost
from models.user import User
from utils import login_required, validate_csrf

thread_bp = Blueprint('thread', __name__)

cloudinary.config(
    cloud_name=os.environ.get('CLOUDINARY_CLOUD_NAME'),
    api_key=os.environ.get('CLOUDINARY_API_KEY'),
    api_secret=os.environ.get('CLOUDINARY_API_SECRET'),
    secure=True,
)


@thread_bp.route('/thread', methods=['GET', 'POST'])
def thread():
    user_id = session.get('user_id')

    if request.method == 'POST':
        if not user_id:
            return redirect(url_for('auth.login', next='/thread'))
        if validate_csrf(request.form.get('csrf_token')):
            body = request.form.get('body', '').strip()
            if body:
                db.session.add(ThreadPost(user_id=user_id, body=body))
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
    post_count = ThreadPost.query.count()
    return render_template('thread.html', posts=posts, post_count=post_count,
                           logged_in=bool(user_id))


@thread_bp.route('/thread/upload-image', methods=['POST'])
@login_required
def upload_image():
    if 'image' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    file = request.files['image']
    if not file.filename:
        return jsonify({'error': 'No file selected'}), 400
    try:
        result = cloudinary.uploader.upload(
            file,
            folder='pulse_thread',
            transformation=[{'width': 1200, 'crop': 'limit'}],
        )
        return jsonify({'url': result['secure_url']})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@thread_bp.route('/thread/<int:post_id>/delete', methods=['POST'])
@login_required
def delete_post(post_id):
    if not validate_csrf(request.form.get('csrf_token')):
        return jsonify({'error': 'Invalid CSRF'}), 403
    post = ThreadPost.query.get_or_404(post_id)
    if post.user_id != session['user_id']:
        return jsonify({'error': 'Forbidden'}), 403
    db.session.delete(post)
    db.session.commit()
    return jsonify({'deleted': post_id})


@thread_bp.route('/thread/poll')
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
