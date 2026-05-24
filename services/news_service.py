import os
import json
import requests
from models import db
from models.topic import Topic, TopicSource


MIN_DESCRIPTION_LENGTH = 80

VALID_CATEGORIES = [
    'Economy', 'Immigration', 'Climate', 'Healthcare', 'Housing',
    'Foreign Policy', 'Education', 'Technology', 'Local Government', 'National Politics',
]

CLASSIFY_PROMPT = """You are a news classifier for a civic news app called Pulse.
The app covers topics relevant to citizens: economy, immigration, climate, healthcare,
housing, foreign policy, education, technology policy, local government, and national politics.

Given the JSON array of news articles below, return a JSON array containing only the articles
that are relevant to civic or policy topics. For each relevant article include:
  "index": the original index number
  "category": one of [Economy, Immigration, Climate, Healthcare, Housing, Foreign Policy,
                       Education, Technology, Local Government, National Politics]

EXCLUDE articles about: sports, entertainment, celebrity gossip, crime (unless policy-related),
weather (unless climate policy), lifestyle, food, travel, TV shows, movies, music.

Return ONLY a raw JSON array — no explanation, no markdown, no code fences.
Example: [{"index": 0, "category": "Economy"}, {"index": 4, "category": "Healthcare"}]

Articles:
"""


def classify_articles(articles):
    """Send article titles+descriptions to GPT-4o-mini for filtering and categorization.
    Returns a dict mapping article index -> category for relevant articles only."""
    from openai import OpenAI
    client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))

    batch = [
        {'index': i, 'title': a.get('title', ''), 'description': a.get('description', '')}
        for i, a in enumerate(articles)
    ]

    response = client.chat.completions.create(
        model='gpt-4o-mini',
        messages=[{'role': 'user', 'content': CLASSIFY_PROMPT + json.dumps(batch)}],
        max_tokens=1000,
        temperature=0,
    )

    raw = response.choices[0].message.content.strip()
    parsed = json.loads(raw)
    return {item['index']: item['category'] for item in parsed
            if item.get('category') in VALID_CATEGORIES}


def fetch_and_store_news():
    api_key = os.environ.get('NEWS_API_KEY')
    if not api_key:
        return {'error': 'NEWS_API_KEY not set'}

    if not os.environ.get('OPENAI_API_KEY'):
        return {'error': 'OPENAI_API_KEY not set'}

    # Single NewsAPI call — fetch top 100 US headlines
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
    if not articles:
        return {'added': 0, 'skipped': 0}

    # Filter articles that are too short before sending to GPT
    candidates = [a for a in articles
                  if (a.get('title') or '').strip() not in ('', '[Removed]')
                  and len((a.get('description') or '').strip()) >= MIN_DESCRIPTION_LENGTH]

    print(f'Sending {len(candidates)} articles to GPT for classification...')

    try:
        classifications = classify_articles(candidates)
    except Exception as e:
        print(f'GPT classification error: {e}')
        return {'added': 0, 'skipped': len(candidates), 'errors': [f'GPT error: {e}']}

    print(f'GPT selected {len(classifications)} relevant articles.')

    added = 0
    skipped = 0

    for idx, category in classifications.items():
        article = candidates[idx]
        title = article.get('title', '').strip()
        url = article.get('url', '')
        source_name = article.get('source', {}).get('name', 'Unknown')
        description = article.get('description', '').strip()

        if Topic.query.filter_by(title=title).first():
            skipped += 1
            continue

        if TopicSource.query.filter_by(source_url=url).first():
            skipped += 1
            continue

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
