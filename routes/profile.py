from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from models import db
from models.user import User, Interest
from utils import login_required, validate_csrf

profile_bp = Blueprint('profile', __name__)

ALIGNMENTS = ['Progressive', 'Moderate Progressive', 'Moderate', 'Conservative', 'Libertarian', 'Other']


@profile_bp.route('/profile')
@login_required
def profile():
    user = User.query.get(session['user_id'])
    return render_template('profile.html', user=user)


@profile_bp.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    user = User.query.get(session['user_id'])

    if request.method == 'POST':
        if not validate_csrf(request.form.get('csrf_token')):
            flash('Invalid form submission.', 'error')
            return redirect(url_for('profile.edit_profile'))

        user.bio = request.form.get('bio', '').strip() or None
        user.city = request.form.get('city', '').strip() or None
        user.state = request.form.get('state', '').strip() or None
        user.political_alignment = request.form.get('political_alignment', '') or None
        db.session.commit()
        flash('Profile updated.', 'success')
        return redirect(url_for('profile.profile'))

    return render_template('profile_edit.html', user=user, alignments=ALIGNMENTS)


@profile_bp.route('/interests', methods=['GET', 'POST'])
@login_required
def interests():
    user = User.query.get(session['user_id'])
    all_interests = Interest.query.order_by(Interest.name).all()

    if request.method == 'POST':
        if not validate_csrf(request.form.get('csrf_token')):
            flash('Invalid form submission.', 'error')
            return redirect(url_for('profile.interests'))

        selected_ids = request.form.getlist('interests')
        user.interests = Interest.query.filter(Interest.id.in_(selected_ids)).all()
        db.session.commit()
        flash('Interests saved.', 'success')
        return redirect(url_for('topics.feed'))

    user_interest_ids = [i.id for i in user.interests]
    return render_template('interests.html', all_interests=all_interests,
                           user_interest_ids=user_interest_ids)
