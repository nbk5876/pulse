import os
import requests
from models import db
from models.topic import Topic, TopicSource


CATEGORY_QUERIES = {
    'Economy':          '"economy" OR "inflation" OR "federal reserve" OR "unemployment" OR "GDP"',
    'Immigration':      '"immigration policy" OR "border security" OR "deportation" OR "asylum"',
    'Climate':          '"climate change" OR "climate policy" OR "clean energy" OR "carbon emissions"',
    'Healthcare':       '"health care" OR "health insurance" OR "Medicare" OR "Medicaid" OR "drug prices"',
    'Housing':          '"housing costs" OR "rent prices" OR "affordable housing" OR "housing market"',
    'Foreign Policy':   '"foreign policy" OR "Iran" OR "Ukraine" OR "NATO" OR "diplomacy" OR "sanctions"',
    'Education':        '"education policy" OR "student loans" OR "school funding" OR "college tuition"',
    'Technology':       '"artificial intelligence" OR "AI regulation" OR "tech policy" OR "cybersecurity"',
    'Local Government': '"local government" OR "city council" OR "municipal budget" OR "zoning"',
    'National Politics': '"Congress" OR "Senate" OR "House of Representatives" OR "White House" OR "legislation"',
}

MIN_DESCRIPTION_LENGTH = 80


def fetch_news_for_category(category, api_key, page_size=5):
    query = CATEGORY_QUERIES.get(category)
    if not query:
        return [], None

    url = 'https://newsapi.org/v2/top-headlines'
    params = {
        'q': query,
        'country': 'us',
        'pageSize': page_size,
        'apiKey': api_key,
    }
    resp = requests.get(url, params=params, timeout=10)
    if resp.status_code != 200:
        error_msg = f'HTTP {resp.status_code}: {resp.json().get("message", resp.text)}'
        print(f'NewsAPI error for {category}: {error_msg}')
        return [], error_msg
    return resp.json().get('articles', []), None


def fetch_and_store_news():
    api_key = os.environ.get('NEWS_API_KEY')
    if not api_key:
        return {'error': 'NEWS_API_KEY not set'}

    added = 0
    skipped = 0
    errors = []

    for category in CATEGORY_QUERIES:
        articles, error = fetch_news_for_category(category, api_key)
        if error:
            errors.append(f'{category}: {error}')
            continue
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

            # Skip if title already exists
            if Topic.query.filter_by(title=title).first():
                skipped += 1
                continue

            # Skip if source URL already exists
            if TopicSource.query.filter_by(source_url=url).first():
                skipped += 1
                continue

            summary = description or title
            topic = Topic(title=title, summary=summary, category=category)
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
    result = {'added': added, 'skipped': skipped}
    if errors:
        result['errors'] = errors
    return result
