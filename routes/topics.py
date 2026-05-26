import os
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from models import db
from models.topic import Topic, TopicSource, UserHiddenTopic
from models.comment import Comment
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

    hidden_ids = db.session.query(UserHiddenTopic.topic_id).filter_by(user_id=user.id)
    query = query.filter(~Topic.id.in_(hidden_ids))

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
def topic_detail(id):
    import traceback
    try:
        topic = Topic.query.get_or_404(id)
        sources = TopicSource.query.filter_by(topic_id=id).all()

        reaction_counts = {rt: TopicReaction.query.filter_by(topic_id=id, reaction_type=rt).count()
                           for rt in REACTION_TYPES}

        user_id = session.get('user_id')
        user_reaction = None
        if user_id:
            ur = TopicReaction.query.filter_by(user_id=user_id, topic_id=id).first()
            if ur:
                user_reaction = ur.reaction_type

        comments = Comment.query.filter_by(topic_id=id).order_by(Comment.created_at.asc()).all()

        return render_template('topic_detail.html', topic=topic, sources=sources,
                               reaction_counts=reaction_counts, user_reaction=user_reaction,
                               reaction_types=REACTION_TYPES, comments=comments,
                               logged_in=bool(user_id))
    except Exception as e:
        print(f'[topic_detail ERROR] topic_id={id}: {e}')
        print(traceback.format_exc())
        raise


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


@topics_bp.route('/topic/<int:id>/comment', methods=['POST'])
@login_required
def add_comment(id):
    if not validate_csrf(request.form.get('csrf_token')):
        return redirect(url_for('topics.topic_detail', id=id))
    body = request.form.get('body', '').strip()
    if body:
        db.session.add(Comment(user_id=session['user_id'], topic_id=id, body=body))
        if request.form.get('share_to_thread'):
            from models.thread import ThreadPost
            topic = Topic.query.get(id)
            thread_body = (f'Re: "{topic.title}"\n\n{body}\n\n'
                           f'https://pulse.core3.com/topic/{id}')
            db.session.add(ThreadPost(user_id=session['user_id'], body=thread_body))
        db.session.commit()
    return redirect(url_for('topics.topic_detail', id=id))


@topics_bp.route('/topic/<int:id>/summarize', methods=['POST'])
@login_required
def summarize_topic(id):
    from openai import OpenAI
    topic = Topic.query.get_or_404(id)
    client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))
    prompt = (
        f'Topic: {topic.title}\n\n'
        f'Summary: {topic.summary}\n\n'
        'Based on your knowledge, provide a concise 3-4 sentence expanded summary of this topic. '
        'Focus on key facts, context, and why it matters. Do not make up specific numbers or quotes.'
    )
    response = client.chat.completions.create(
        model='gpt-4o-mini',
        messages=[{'role': 'user', 'content': prompt}],
        max_tokens=300,
    )
    text = response.choices[0].message.content.strip()
    return jsonify({'summary': text})


@topics_bp.route('/topic/<int:id>/hide', methods=['POST'])
@login_required
def hide_topic(id):
    existing = UserHiddenTopic.query.filter_by(user_id=session['user_id'], topic_id=id).first()
    if not existing:
        db.session.add(UserHiddenTopic(user_id=session['user_id'], topic_id=id))
        db.session.commit()
    return redirect(url_for('topics.feed'))
