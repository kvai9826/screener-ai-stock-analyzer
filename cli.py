import sys
import argparse
from config import Config
from screener_fetcher import ScreenerFetcher
from news_search import NewsFetcher
from ai_analyst import AIStockAnalyst
from utils import extract_ticker

def main():
    parser = argparse.ArgumentParser(description="Screener.in AI Stock Analyzer CLI")
    parser.add_argument("stock", type=str, help="Company Name or Ticker (e.g. RELIANCE, TCS, INFY)")
    parser.add_argument("--openrouter-key", type=str, help="OpenRouter free API key")
    parser.add_argument("--model", type=str, help="OpenRouter model (e.g. google/gemma-2-9b-it:free)")
    args = parser.parse_args()

    stock_query = args.stock
    print(f"\n🔍 Searching Screener.in for: {stock_query}...")

    fetcher = ScreenerFetcher()
    news_fetcher = NewsFetcher()
    analyst = AIStockAnalyst(
        openrouter_api_key=args.openrouter_key,
        model=args.model
    )

    search_results = fetcher.search_company(stock_query)
    if not search_results:
        print(f"❌ Error: Could not find any company matching '{stock_query}'.")
        sys.exit(1)

    company_info = search_results[0]
    ticker = extract_ticker(company_info['url'])
    print(f"✅ Found: {company_info['name']} (Ticker: {ticker})")

    print("📊 Extracting financial statements from Screener.in...")
    company_data = fetcher.get_company_data(ticker)

    print("🌐 Surfing the web for news headlines & metadata...")
    news_articles = news_fetcher.get_stock_news(company_info['name'])

    print("\n" + "="*80)
    print("📈 TOP FINANCIAL RATIOS")
    print("="*80)
    for k, v in company_data['top_ratios'].items():
        print(f"  • {k:25s}: {v}")

    scores = company_data.get('health_scores', {})
    print(f"  • Piotroski F-Score      : {scores.get('piotroski_f_score', 0)}/9 ({scores.get('health_label', '')})")

    print("\n" + "="*80)
    print("🌐 RECENT NEWS HEADLINES")
    print("="*80)
    for n in news_articles[:5]:
        print(f"  • [{n['date']}] {n['title']} ({n['source']})")

    print("\n" + "="*80)
    print("🤖 AI FINANCIAL ANALYST REPORT")
    print("="*80)
    report = analyst.generate_analysis(
        company_data['name'], 
        company_data['top_ratios'], 
        company_data['tables'], 
        news_articles
    )
    print(report)

if __name__ == '__main__':
    main()
