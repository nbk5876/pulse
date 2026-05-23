from models import db
from models.topic import Topic, TopicSource
from models.user import Interest

SEED_INTERESTS = [
    'Economy', 'Immigration', 'Climate', 'Healthcare',
    'Housing', 'Foreign Policy', 'Education', 'Technology', 'Local Government',
]

SEED_TOPICS = [
    {
        'title': 'Cities Begin Using AI to Triage 311 Service Requests',
        'summary': (
            'Several major U.S. cities have started piloting AI systems to automatically '
            'categorize and route non-emergency service requests. Proponents say it cuts '
            'response times by up to 40%, while critics raise concerns about algorithmic '
            'bias in underserved neighborhoods and the displacement of municipal workers. '
            'The rollouts have reignited debate over what role automated decision-making '
            'should play in local government services.'
        ),
        'category': 'AI',
        'sources': [
            {'name': 'Governing Magazine', 'url': 'https://www.governing.com'},
            {'name': 'The Markup', 'url': 'https://themarkup.org'},
        ],
    },
    {
        'title': 'Housing Costs Outpace Wage Growth for Third Consecutive Year',
        'summary': (
            'A new report from the National Low Income Housing Coalition finds that in '
            '47 states, a full-time minimum-wage worker cannot afford a two-bedroom '
            'rental home. The gap between housing costs and median wages has widened '
            'every year since 2022, driven by supply constraints, rising construction '
            'costs, and investor activity in single-family home markets. State '
            'legislatures are debating a range of responses from rent stabilization '
            'to zoning reform.'
        ),
        'category': 'Housing',
        'sources': [
            {'name': 'NLIHC', 'url': 'https://nlihc.org'},
            {'name': 'Pew Research Center', 'url': 'https://pewresearch.org'},
        ],
    },
    {
        'title': 'Senate Debates New Framework for Healthcare Price Transparency',
        'summary': (
            'A bipartisan Senate bill would require hospitals and insurers to publish '
            'machine-readable pricing for all common procedures and make that data '
            'searchable by consumers. Supporters argue that transparency will drive '
            'competition and reduce costs. Hospital industry groups counter that '
            'pricing complexity makes simple comparisons misleading and that the '
            'administrative burden of compliance would ultimately raise costs.'
        ),
        'category': 'Healthcare',
        'sources': [
            {'name': 'KFF Health News', 'url': 'https://kffhealthnews.org'},
            {'name': 'Health Affairs', 'url': 'https://healthaffairs.org'},
        ],
    },
]


def seed_interests():
    for name in SEED_INTERESTS:
        if not Interest.query.filter_by(name=name).first():
            db.session.add(Interest(name=name))
    db.session.commit()


def seed_topics():
    for t in SEED_TOPICS:
        if not Topic.query.filter_by(title=t['title']).first():
            topic = Topic(title=t['title'], summary=t['summary'], category=t['category'])
            db.session.add(topic)
            db.session.flush()
            for s in t['sources']:
                db.session.add(TopicSource(topic_id=topic.id,
                                           source_name=s['name'], source_url=s['url']))
    db.session.commit()
