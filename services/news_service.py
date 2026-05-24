import os
import json
import re
import feedparser
from models import db
from models.topic import Topic, TopicSource


MIN_DESCRIPTION_LENGTH = 80

RSS_FEEDS = [
    {'url': 'https://feeds.apnews.com/rss/apf-politics',           'source': 'AP News'},
    {'url': 'https://feeds.apnews.com/rss/apf-topnews',            'source': 'AP News'},
    {'url': 'https://feeds.npr.org/1001/rss.xml',                   'source': 'NPR'},
    {'url': 'https://feeds.npr.org/1014/rss.xml',                   'source': 'NPR Politics'},
    {'url': 'https://www.pbs.org/newshour/feeds/rss/headlines',     'source': 'PBS NewsHour'},
    {'url': 'https://thehill.com/news/feed/',                       'source': 'The Hill'},
    {'url': 'https://www.politico.com/rss/politicopicks.xml',       'source': 'Politico'},
    {'url': 'https://feeds.abcnews.com/abcnews/topstories',         'source': 'ABC News'},
    {'url': 'https://www.cbsnews.com/latest/rss/main',              'source': 'CBS News'},
    {'url': 'https://api.axios.com/feed/',                          'source': 'Axios'},
]

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


def strip_html(text):
    return re.sub(r'<[^>]+>', '', text or '').strip()


def fetch_all_feeds():
    """Fetch articles from all RSS feeds, deduplicated by URL."""
    seen_urls = set()
    articles = []

    for feed_def in RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_def['url'])
            for entry in feed.entries:
                url = entry.get('link', '')
                if not url or url in seen_urls:
                    continue
                seen_urls.add(url)

                title = strip_html(entry.get('title', ''))
                description = strip_html(
                    entry.get('summary', '') or entry.get('description', '')
                )

                articles.append({
                    'title': title,
                    'description': description,
                    'url': url,
                    'source': feed_def['source'],
                })
        except Exception as e:
            print(f'RSS error ({feed_def["source"]}): {e}')

    return articles


def classify_articles(articles):
    """Send article titles+descriptions to GPT-4o-mini for filtering and categorization.
    Returns a dict mapping article index -> category for relevant articles only."""
    from openai import OpenAI
    client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))

    batch = [
        {'index': i, 'title': a['title'], 'description': a['description']}
        for i, a in enumerate(articles)
    ]

    response = client.chat.completions.create(
        model='gpt-4o-mini',
        messages=[{'role': 'user', 'content': CLASSIFY_PROMPT + json.dumps(batch)}],
        max_tokens=1500,
        temperature=0,
    )

    raw = response.choices[0].message.content.strip()
    parsed = json.loads(raw)
    return {item['index']: item['category'] for item in parsed
            if item.get('category') in VALID_CATEGORIES}


def fetch_and_store_news():
    if not os.environ.get('OPENAI_API_KEY'):
        return {'error': 'OPENAI_API_KEY not set'}

    # Collect articles from all RSS feeds
    all_articles = fetch_all_feeds()
    print(f'Fetched {len(all_articles)} articles from RSS feeds.')

    # Filter obvious junk before sending to GPT
    candidates = [
        a for a in all_articles
        if a['title'] not in ('', '[Removed]')
        and len(a['description']) >= MIN_DESCRIPTION_LENGTH
        and not Topic.query.filter_by(title=a['title']).first()
        and not TopicSource.query.filter_by(source_url=a['url']).first()
    ]

    if not candidates:
        print('No new candidates after deduplication.')
        return {'added': 0, 'skipped': len(all_articles)}

    print(f'Sending {len(candidates)} candidates to GPT for classification...')

    try:
        classifications = classify_articles(candidates)
    except Exception as e:
        print(f'GPT classification error: {e}')
        return {'added': 0, 'skipped': len(candidates), 'errors': [f'GPT error: {str(e)}']}

    print(f'GPT selected {len(classifications)} relevant articles.')

    added = 0
    skipped = len(all_articles) - len(candidates)

    for idx, category in classifications.items():
        article = candidates[idx]
        topic = Topic(title=article['title'], summary=article['description'], category=category)
        db.session.add(topic)
        db.session.flush()
        db.session.add(TopicSource(
            topic_id=topic.id,
            source_name=article['source'],
            source_url=article['url'],
        ))
        print(f'[+] Added ({category}): {article["title"]}')
        added += 1

    db.session.commit()
    print(f'Done: {added} added, {skipped} skipped.')
    return {'added': added, 'skipped': skipped}
