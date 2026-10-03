import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
import ssl
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from config import Config

try:
    import certifi
    SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    SSL_CONTEXT = ssl.create_default_context()

class NewsFetcher:
    """Fetches recent web news headlines, publication metadata, and sources for a stock symbol."""

    def __init__(self, timeout=None):
        self.headers = {
            'User-Agent': Config.USER_AGENT
        }
        self.ctx = SSL_CONTEXT
        self.timeout = timeout or Config.DEFAULT_TIMEOUT

    def get_stock_news(self, stock_name: str, limit=None, freshness_days=None) -> list:
        """
        Fetches top news headlines for a stock from Google News RSS.
        
        Parameters:
            stock_name (str): Company name or ticker.
            limit (int): Maximum number of articles to return.
            freshness_days (int): Filter articles published within the last N days (e.g. 1, 7, 30).
        """
        if not stock_name or not stock_name.strip():
            return []

        limit = limit or Config.DEFAULT_NEWS_LIMIT
        freshness_days = freshness_days or Config.DEFAULT_NEWS_FRESHNESS_DAYS

        query = f"{stock_name.strip()} stock news financial"
        rss_url = f"https://news.google.com/rss/search?q={urllib.parse.quote(query)}&hl=en-IN&gl=IN&ceid=IN:en"

        articles = []
        seen_titles = set()
        seen_links = set()

        cutoff_date = datetime.now(timezone.utc) - timedelta(days=freshness_days)

        try:
            req = urllib.request.Request(rss_url, headers=self.headers)
            with urllib.request.urlopen(req, context=self.ctx, timeout=self.timeout) as resp:
                xml_data = resp.read()

            root = ET.fromstring(xml_data)
            for item in root.findall('.//item'):
                if len(articles) >= limit:
                    break

                raw_title = item.find('title').text.strip() if item.find('title') is not None and item.find('title').text else ''
                pub_date_str = item.find('pubDate').text.strip() if item.find('pubDate') is not None and item.find('pubDate').text else ''
                link = item.find('link').text.strip() if item.find('link') is not None and item.find('link').text else ''

                # 1. Parse source from RSS <source> element metadata
                source_el = item.find('source')
                source = ""
                if source_el is not None and source_el.text:
                    source = source_el.text.strip()
                elif " - " in raw_title:
                    # Fallback title split if source element absent
                    parts = raw_title.rsplit(" - ", 1)
                    title_clean = parts[0]
                    source = parts[1]
                else:
                    title_clean = raw_title

                title = title_clean if 'title_clean' in locals() else raw_title

                # 2. Parse publication date & enforce freshness window
                pub_datetime = None
                if pub_date_str:
                    try:
                        pub_datetime = parsedate_to_datetime(pub_date_str)
                    except Exception:
                        pub_datetime = None

                if pub_datetime and pub_datetime < cutoff_date:
                    continue  # Skip articles older than freshness threshold

                # 3. Deduplicate by canonical title and link
                norm_title = title.lower()
                if norm_title in seen_titles or link in seen_links:
                    continue

                seen_titles.add(norm_title)
                if link:
                    seen_links.add(link)

                articles.append({
                    'title': title,
                    'source': source if source else 'Financial News',
                    'date': pub_date_str,
                    'pub_datetime': pub_datetime.isoformat() if pub_datetime else None,
                    'link': link
                })

        except Exception as e:
            print(f"Error fetching news headlines for '{stock_name}': {e}")

        return articles


# Backward compatibility alias
NewsSentimentExtractor = NewsFetcher


if __name__ == '__main__':
    fetcher = NewsFetcher()
    news = fetcher.get_stock_news("RELIANCE", limit=5, freshness_days=7)
    print(f"Fetched {len(news)} deduplicated fresh news articles:")
    for n in news:
        print(f"  - [{n['source']}] {n['title']} ({n['date']})")
