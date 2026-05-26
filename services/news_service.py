import os
import json
import re
import urllib.parse
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

Category guidance:
- Immigration = border policy, deportation, asylum seekers, visa rules — NOT January 6 or Capitol riot
- National Politics = Congress, elections, January 6, Supreme Court, White House, partisan legislation
- Foreign Policy = international relations, wars, NATO, sanctions, diplomacy

Return ONLY a raw JSON array — no explanation, no markdown, no code fences.
Example: [{"index": 0, "category": "Economy"}, {"index": 4, "category": "Healthcare"}]

Articles:
"""


def strip_html(text):
    text = text or ''
    # Convert block-level tags to newlines before stripping
    text = re.sub(r'<(?:p|br|div|li)[^>]*/?>',  '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'</(?:p|div|li)>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'<[^>]+>', '', text)
    lines = [l.strip() for l in text.split('\n')]
    return '\n'.join(l for l in lines if l).strip()


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


CATEGORIZE_PROMPT = """You are a news classifier for a civic news app called Pulse.

Given the JSON array of news articles below, assign a category to EVERY article.
Return a JSON array with ALL articles included, each with:
  "index": the original index number
  "category": one of [Economy, Immigration, Climate, Healthcare, Housing, Foreign Policy,
                       Education, Technology, Local Government, National Politics]

Choose the most relevant category. Use "National Politics" as the default if none fit well.
Return ONLY a raw JSON array — no explanation, no markdown, no code fences.

Articles:
"""


def categorize_articles(articles):
    """Assign categories to all articles without filtering any out."""
    from openai import OpenAI
    client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))
    batch = [
        {'index': i, 'title': a['title'], 'description': a['description']}
        for i, a in enumerate(articles)
    ]
    response = client.chat.completions.create(
        model='gpt-4o-mini',
        messages=[{'role': 'user', 'content': CATEGORIZE_PROMPT + json.dumps(batch)}],
        max_tokens=4000,
        temperature=0,
    )
    raw = response.choices[0].message.content.strip()
    if raw.startswith('```'):
        raw = re.sub(r'^```(?:json)?\s*', '', raw)
        raw = re.sub(r'\s*```$', '', raw.strip())
    parsed = json.loads(raw)
    valid = ['Economy','Immigration','Climate','Healthcare','Housing',
             'Foreign Policy','Education','Technology','Local Government','National Politics']
    return {item['index']: item['category'] for item in parsed
            if item.get('category') in valid}


def fetch_topic(query):
    """Fetch and store news articles for an ad-hoc search query via Google News RSS."""
    if not os.environ.get('OPENAI_API_KEY'):
        return {'error': 'OPENAI_API_KEY not set'}

    url = ('https://news.google.com/rss/search?q='
           + urllib.parse.quote(query)
           + '&hl=en-US&gl=US&ceid=US:en')

    try:
        feed = feedparser.parse(url)
    except Exception as e:
        return {'error': f'RSS fetch error: {e}', 'added': 0, 'skipped': 0}

    articles = []
    for entry in feed.entries:
        title = strip_html(entry.get('title', ''))
        description = strip_html(entry.get('summary', '') or entry.get('description', ''))
        link = entry.get('link', '')
        # Google News embeds source in title as "Headline - Source Name"
        source = 'Google News'
        if ' - ' in title:
            parts = title.rsplit(' - ', 1)
            title = parts[0].strip()
            source = parts[1].strip()
        articles.append({'title': title, 'description': description,
                         'url': link, 'source': source})

    candidates = [
        a for a in articles
        if a['title'] not in ('', '[Removed]')
        and len(a['description']) >= MIN_DESCRIPTION_LENGTH
        and not Topic.query.filter_by(title=a['title']).first()
        and not TopicSource.query.filter_by(source_url=a['url']).first()
    ]

    if not candidates:
        return {'added': 0, 'skipped': len(articles), 'query': query}

    print(f'Ad-hoc fetch "{query}": {len(candidates)} candidates → GPT')

    try:
        classifications = categorize_articles(candidates)
    except Exception as e:
        return {'added': 0, 'skipped': len(candidates),
                'errors': [f'GPT error: {str(e)}'], 'query': query}

    added = 0
    skipped = len(articles) - len(candidates)

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
    print(f'Ad-hoc done: {added} added, {skipped} skipped.')
    return {'added': added, 'skipped': skipped, 'query': query}


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
        max_tokens=4000,
        temperature=0,
    )

    raw = response.choices[0].message.content.strip()
    if raw.startswith('```'):
        raw = re.sub(r'^```(?:json)?\s*', '', raw)
        raw = re.sub(r'\s*```$', '', raw.strip())
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
