from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from models import db
from models.topic import Topic, TopicSource
from models.reaction import TopicReaction
from models.user import User
from utils import login_required, validate_csrf

topics_bp = Blueprint('topics', __name__)

REACTION_TYPES = ['Important', 'Interested', 'Discuss Locally', 'Needs Fact Check']


@topics_bp.route('/feed')
@login_required
def feed():
    user = User.query.get(session['user_id'])
    category = request.args.get('category', '')

    query = Topic.query.filter_by(active_flag=True)

    if user.interests:
        interest_names = [i.name for i in user.interests]
        query = query.filter(Topic.category.in_(interest_names))

    if category:
        query = query.filter_by(category=category)

    topics = query.order_by(Topic.created_at.desc()).all()

    topic_data = []
    for topic in topics:
        count = TopicReaction.query.filter_by(topic_id=topic.id).count()
        topic_data.append({'topic': topic, 'reaction_count': count})

    all_cats = db.session.query(Topic.category).filter(
        Topic.active_flag == True, Topic.category.isnot(None)
    ).distinct().order_by(Topic.category).all()
    categories = [c[0] for c in all_cats]

    return render_template('feed.html', topic_data=topic_data, categories=categories,
                           selected_category=category, user=user)


@topics_bp.route('/topic/<int:id>')
@login_required
def topic_detail(id):
    topic = Topic.query.get_or_404(id)
    sources = TopicSource.query.filter_by(topic_id=id).all()

    reaction_counts = {rt: TopicReaction.query.filter_by(topic_id=id, reaction_type=rt).count()
                       for rt in REACTION_TYPES}

    user_reaction = None
    ur = TopicReaction.query.filter_by(user_id=session['user_id'], topic_id=id).first()
    if ur:
        user_reaction = ur.reaction_type

    return render_template('topic_detail.html', topic=topic, sources=sources,
                           reaction_counts=reaction_counts, user_reaction=user_reaction,
                           reaction_types=REACTION_TYPES)


@topics_bp.route('/topic/<int:id>/react', methods=['POST'])
@login_required
def react(id):
    if not validate_csrf(request.form.get('csrf_token')):
        flash('Invalid form submission.', 'error')
        return redirect(url_for('topics.topic_detail', id=id))

    reaction_type = request.form.get('reaction_type')
    if reaction_type not in REACTION_TYPES:
        flash('Invalid reaction.', 'error')
        return redirect(url_for('topics.topic_detail', id=id))

    existing = TopicReaction.query.filter_by(user_id=session['user_id'], topic_id=id).first()

    if existing:
        if existing.reaction_type == reaction_type:
            db.session.delete(existing)
        else:
            existing.reaction_type = reaction_type
    else:
        db.session.add(TopicReaction(user_id=session['user_id'], topic_id=id, reaction_type=reaction_type))

    db.session.commit()
    return redirect(url_for('topics.topic_detail', id=id))
