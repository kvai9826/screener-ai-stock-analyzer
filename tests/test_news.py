import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone
from news_search import NewsFetcher

SAMPLE_RSS_XML = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Google News</title>
    <item>
      <title>Reliance Industries Q3 profits surge 12% - Economic Times</title>
      <link>https://news.google.com/rss/articles/CBMi1?</link>
      <pubDate>Mon, 03 Oct 2026 10:00:00 GMT</pubDate>
      <source url="https://economictimes.indiatimes.com">Economic Times</source>
    </item>
    <item>
      <title>Reliance Industries Q3 profits surge 12% - Economic Times</title>
      <link>https://news.google.com/rss/articles/CBMi1?</link>
      <pubDate>Mon, 03 Oct 2026 10:00:00 GMT</pubDate>
      <source url="https://economictimes.indiatimes.com">Economic Times</source>
    </item>
    <item>
      <title>Reliance Jio expands 5G footprint nationwide - Business Standard</title>
      <link>https://news.google.com/rss/articles/CBMi2?</link>
      <pubDate>Sun, 02 Oct 2026 14:30:00 GMT</pubDate>
      <source url="https://business-standard.com">Business Standard</source>
    </item>
  </channel>
</rss>
"""

class TestNewsFetcher(unittest.TestCase):

    def setUp(self):
        self.fetcher = NewsFetcher()

    @patch('urllib.request.urlopen')
    def test_get_stock_news_parsing(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.read.return_value = SAMPLE_RSS_XML.encode('utf-8')
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        articles = self.fetcher.get_stock_news("RELIANCE", limit=5, freshness_days=30)
        
        # Deduplication check: XML had 3 items with 1 duplicate -> should return 2 articles
        self.assertEqual(len(articles), 2)
        
        # Source metadata tag check
        self.assertEqual(articles[0]['source'], "Economic Times")
        self.assertEqual(articles[1]['source'], "Business Standard")
        
        self.assertIn("Reliance Industries", articles[0]['title'])

    @patch('urllib.request.urlopen')
    def test_empty_news_on_error(self, mock_urlopen):
        mock_urlopen.side_effect = Exception("Network Error")
        articles = self.fetcher.get_stock_news("RELIANCE")
        self.assertEqual(articles, [])

if __name__ == '__main__':
    unittest.main()
