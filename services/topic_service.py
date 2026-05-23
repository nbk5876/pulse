from models import db
from models.topic import Topic, TopicSource
from models.user import Interest

SEED_INTERESTS = [
    'Economy', 'Immigration', 'Climate', 'Healthcare',
    'Housing', 'Foreign Policy', 'Education', 'Technology', 'Local Government',
    'National Politics',
]

SEED_TOPICS = [
    {
        'title': 'U.S.-Iran War and the Strait of Hormuz Crisis',
        'summary': (
            'The United States and Israel launched military strikes against Iran on '
            'February 28, 2026, triggering the largest oil supply disruption in the history '
            'of global energy markets. Iran responded by declaring the Strait of Hormuz '
            'closed on March 4th and has since threatened or attacked ships attempting to '
            'transit the waterway, through which roughly 20% of the world\'s oil normally '
            'flows. Brent crude surged from around $72 a barrel before the war to a peak '
            'near $120, sending U.S. gas prices above $4 a gallon and pushing inflation '
            'noticeably higher. As of late May 2026, the U.S. and Iran are in active '
            'negotiations — President Trump called off additional strikes to allow talks '
            'to continue — but the two sides remain deadlocked over Iran\'s uranium '
            'stockpile and future control of the strait, with analysts warning full '
            'supply normalization may not come until 2027.'
        ),
        'category': 'Foreign Policy',
        'sources': [
            {'name': 'Reuters', 'url': 'https://www.reuters.com'},
            {'name': 'The Wall Street Journal', 'url': 'https://www.wsj.com'},
        ],
    },
    {
        'title': 'Republican Senators Break with DOJ Over $1.8B Anti-Weaponization Fund',
        'summary': (
            'The Justice Department has proposed a $1.776 billion compensation fund for '
            'individuals who claim they were unfairly targeted by the federal government '
            'during the Biden administration. The fund stems from a January 2026 lawsuit '
            'filed by Donald Trump against the IRS over the 2019 leak of his tax returns '
            '-- a case seeking $10 billion in damages that was dropped in exchange for the '
            'fund\'s creation. Several Republican senators have publicly questioned or '
            'criticized the proposal: Sen. Bill Cassidy (R-LA) called it a "slush fund"; '
            'Sen. John Thune (R-SD), the Senate Majority Leader, said he is "not a big '
            'fan" and questioned its purpose; Sen. Tommy Tuberville (R-AL) described it '
            'as a "curveball" after a DOJ briefing; and Sen. Susan Collins (R-ME) pressed '
            'for more clarity. The fund has not yet been authorized by Congress.'
        ),
        'category': 'National Politics',
        'sources': [
            {'name': 'Politico', 'url': 'https://www.politico.com'},
            {'name': 'The Hill', 'url': 'https://thehill.com'},
        ],
    },
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
