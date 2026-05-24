import os
import requests
from models import db
from models.topic import Topic, TopicSource


MIN_DESCRIPTION_LENGTH = 80

CATEGORY_KEYWORDS = {
    'Economy':          ['economy', 'inflation', 'federal reserve', 'unemployment', 'gdp', 'recession',
                         'interest rate', 'stock market', 'trade', 'tariff', 'deficit', 'debt', 'wages'],
    'Immigration':      ['immigration', 'border', 'deportation', 'asylum', 'migrant', 'visa', 'refugee'],
    'Climate':          ['climate', 'environment', 'carbon', 'emissions', 'clean energy', 'renewable',
                         'fossil fuel', 'global warming', 'epa', 'weather disaster'],
    'Healthcare':       ['health care', 'healthcare', 'insurance', 'medicare', 'medicaid', 'drug price',
                         'hospital', 'medical', 'fda', 'vaccine', 'prescription'],
    'Housing':          ['housing', 'rent', 'mortgage', 'real estate', 'home price', 'affordable housing',
                         'eviction', 'zoning', 'homelessness'],
    'Foreign Policy':   ['ukraine', 'russia', 'china', 'iran', 'nato', 'sanctions', 'diplomacy',
                         'foreign policy', 'military', 'war', 'middle east', 'israel', 'gaza', 'taiwan'],
    'Education':        ['education', 'school', 'student loan', 'college', 'university', 'tuition',
                         'classroom', 'teacher', 'curriculum'],
    'Technology':       ['artificial intelligence', ' ai ', 'cybersecurity', 'data privacy', 'tech policy',
                         'social media', 'algorithm', 'surveillance', 'big tech'],
    'Local Government': ['city council', 'municipal', 'mayor', 'local government', 'county', 'zoning',
                         'state legislature', 'ballot measure'],
    'National Politics': ['congress', 'senate', 'house of representatives', 'white house', 'legislation',
                          'democrat', 'republican', 'president', 'election', 'vote', 'bill passed',
                          'supreme court', 'justice department'],
}


def detect_category(text):
    text_lower = text.lower()
    best_category = 'National Politics'
    best_count = 0
    for category, keywords in CATEGORY_KEYWORDS.items():
        count = sum(1 for kw in keywords if kw in text_lower)
        if count > best_count:
            best_count = count
            best_category = category
    return best_category


def fetch_and_store_news():
    api_key = os.environ.get('NEWS_API_KEY')
    if not api_key:
        return {'error': 'NEWS_API_KEY not set'}

    resp = requests.get(
        'https://newsapi.org/v2/top-headlines',
        params={'country': 'us', 'pageSize': 100, 'apiKey': api_key},
        timeout=10,
    )
    if resp.status_code != 200:
        error_msg = f'HTTP {resp.status_code}: {resp.json().get("message", resp.text)}'
        print(f'NewsAPI error: {error_msg}')
        return {'added': 0, 'skipped': 0, 'errors': [error_msg]}

    articles = resp.json().get('articles', [])
    added = 0
    skipped = 0

    for article in articles:
        title = (article.get('title') or '').strip()
        url = article.get('url', '')
        source_name = article.get('source', {}).get('name', 'Unknown')
        description = (article.get('description') or '').strip()

        if not title or title == '[Removed]':
            skipped += 1
            continue

        if len(description) < MIN_DESCRIPTION_LENGTH:
            skipped += 1
            continue

        if Topic.query.filter_by(title=title).first():
            skipped += 1
            continue

        if TopicSource.query.filter_by(source_url=url).first():
            skipped += 1
            continue

        category = detect_category(title + ' ' + description)
        topic = Topic(title=title, summary=description, category=category)
        db.session.add(topic)
        db.session.flush()
        db.session.add(TopicSource(
            topic_id=topic.id,
            source_name=source_name,
            source_url=url,
        ))
        print(f'[+] Added ({category}): {title}')
        added += 1

    db.session.commit()
    print(f'Done: {added} added, {skipped} skipped.')
    return {'added': added, 'skipped': skipped}
