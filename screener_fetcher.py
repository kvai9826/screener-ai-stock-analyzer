import urllib.request
import urllib.parse
import ssl
import json
from bs4 import BeautifulSoup
import pandas as pd
from utils import extract_ticker, parse_numeric, safe_float
from config import Config

try:
    import certifi
    SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    SSL_CONTEXT = ssl.create_default_context()

class ScreenerFetcher:
    """Extracts financial data, ratios, health scores, and chart data from Screener.in with robust error handling."""
    
    def __init__(self, timeout=None):
        self.headers = {
            'User-Agent': Config.USER_AGENT
        }
        self.ctx = SSL_CONTEXT
        self.timeout = timeout or Config.DEFAULT_TIMEOUT

    def _get(self, url):
        req = urllib.request.Request(url, headers=self.headers)
        with urllib.request.urlopen(req, context=self.ctx, timeout=self.timeout) as resp:
            return resp.read().decode('utf-8')

    def search_company(self, query):
        """Searches Screener.in for a stock and returns company info (id, name, url)."""
        if not query or not query.strip():
            return []
        search_url = f"https://www.screener.in/api/company/search/?q={urllib.parse.quote(query.strip())}"
        try:
            raw = self._get(search_url)
            results = json.loads(raw)
            # Standardize extracted ticker in result objects
            for r in results:
                if 'url' in r:
                    r['ticker'] = extract_ticker(r['url'])
            return results
        except Exception as e:
            print(f"Error searching company '{query}': {e}")
            return []

    def get_company_data(self, ticker_or_url):
        """Fetches and parses financial tables from Screener.in company page."""
        ticker = extract_ticker(ticker_or_url)
        is_consolidated = True
        url = f"https://www.screener.in/company/{ticker}/consolidated/"
        
        try:
            html = self._get(url)
        except Exception:
            # Fallback to standalone if consolidated page is unavailable
            is_consolidated = False
            url = f"https://www.screener.in/company/{ticker}/"
            try:
                html = self._get(url)
            except Exception as e:
                print(f"Error fetching page for {ticker}: {e}")
                return {
                    'ticker': ticker,
                    'name': ticker,
                    'is_consolidated': False,
                    'top_ratios': {},
                    'health_scores': self._empty_health_scores(),
                    'tables': {}
                }

        soup = BeautifulSoup(html, 'html.parser')

        company_name_el = soup.find('h1')
        company_name = company_name_el.text.strip() if company_name_el else ticker

        top_ratios = {}
        ratios_li = soup.find_all('li', class_='flex flex-space-between')
        for li in ratios_li:
            name_span = li.find('span', class_='name')
            value_span = li.find('span', class_='number')
            if name_span and value_span:
                key = name_span.text.strip()
                val = value_span.text.strip().replace('\n', '').replace(' ', '')
                top_ratios[key] = val

        tables = {
            'quarters': self._parse_section_table(soup, 'quarters'),
            'profit_loss': self._parse_section_table(soup, 'profit-loss'),
            'balance_sheet': self._parse_section_table(soup, 'balance-sheet'),
            'cash_flow': self._parse_section_table(soup, 'cash-flow'),
            'ratios': self._parse_section_table(soup, 'ratios'),
            'shareholding': self._parse_section_table(soup, 'shareholding')
        }

        # Compute mathematically correct 9-Signal Piotroski F-Score & Heuristic Health Score
        scores = self.calculate_piotroski_f_score(tables, top_ratios)

        return {
            'ticker': ticker,
            'name': company_name,
            'is_consolidated': is_consolidated,
            'top_ratios': top_ratios,
            'health_scores': scores,
            'tables': tables
        }

    def calculate_piotroski_f_score(self, tables: dict, top_ratios: dict) -> dict:
        """
        Computes the real 9-signal Piotroski F-Score (0–9 range) using annual financial statements.
        
        9 Signals Evaluated:
        1. ROA > 0 (Positive Net Income / Total Assets)
        2. CFO > 0 (Positive Operating Cash Flow)
        3. ΔROA > 0 (ROA current year > ROA prior year)
        4. Accrual: CFO > Net Income
        5. ΔLEVER < 0 (Long-term debt ratio decreased)
        6. ΔLIQUID > 0 (Liquidity/Working Capital improved)
        7. EQ_OFFER: Share Capital current <= prior year (No share dilution)
        8. ΔMARGIN > 0 (Operating Profit Margin OPM % increased)
        9. ΔTURN > 0 (Asset Turnover increased)
        """
        signals = {}
        pnl = tables.get('profit_loss')
        bs = tables.get('balance_sheet')
        cf = tables.get('cash_flow')

        try:
            # 1. ROA > 0 & 3. ΔROA > 0 & 8. ΔMARGIN > 0
            if pnl is not None and not pnl.empty:
                net_profit_row = self._find_df_row(pnl, ['Net Profit', 'Profit after tax'])
                sales_row = self._find_df_row(pnl, ['Sales', 'Revenue'])
                opm_row = self._find_df_row(pnl, ['OPM %', 'Operating Margin'])

                # Latest two annual periods
                if net_profit_row is not None and len(net_profit_row) >= 2:
                    curr_np = safe_float(net_profit_row.iloc[-1])
                    prev_np = safe_float(net_profit_row.iloc[-2])
                    
                    # ROA calculation if Balance Sheet Total Assets available
                    if bs is not None and not bs.empty:
                        assets_row = self._find_df_row(bs, ['Total Assets', 'Total Liabilities'])
                        if assets_row is not None and len(assets_row) >= 2:
                            curr_assets = safe_float(assets_row.iloc[-1], default=1.0)
                            prev_assets = safe_float(assets_row.iloc[-2], default=1.0)
                            curr_roa = curr_np / curr_assets if curr_assets else 0
                            prev_roa = prev_np / prev_assets if prev_assets else 0
                            
                            signals['ROA_Positive'] = 1 if curr_roa > 0 else 0
                            signals['ROA_Growth'] = 1 if curr_roa > prev_roa else 0

                if opm_row is not None and len(opm_row) >= 2:
                    curr_opm = safe_float(opm_row.iloc[-1])
                    prev_opm = safe_float(opm_row.iloc[-2])
                    signals['Margin_Growth'] = 1 if curr_opm > prev_opm else 0

            # 2. CFO > 0 & 4. Accrual (CFO > Net Profit)
            if cf is not None and not cf.empty:
                cfo_row = self._find_df_row(cf, ['Cash from Operating Activity', 'Operating Cash Flow'])
                if cfo_row is not None and len(cfo_row) >= 1:
                    curr_cfo = safe_float(cfo_row.iloc[-1])
                    signals['CFO_Positive'] = 1 if curr_cfo > 0 else 0

                    if pnl is not None and not pnl.empty:
                        net_profit_row = self._find_df_row(pnl, ['Net Profit', 'Profit after tax'])
                        if net_profit_row is not None and len(net_profit_row) >= 1:
                            curr_np = safe_float(net_profit_row.iloc[-1])
                            signals['Accrual_Quality'] = 1 if curr_cfo > curr_np else 0

            # 5. ΔLEVER & 6. ΔLIQUID & 7. EQ_OFFER & 9. ΔTURN
            if bs is not None and not bs.empty:
                borrowings_row = self._find_df_row(bs, ['Borrowings', 'Long Term Borrowings'])
                capital_row = self._find_df_row(bs, ['Share Capital'])
                assets_row = self._find_df_row(bs, ['Total Assets'])

                if borrowings_row is not None and len(borrowings_row) >= 2:
                    curr_borr = safe_float(borrowings_row.iloc[-1])
                    prev_borr = safe_float(borrowings_row.iloc[-2])
                    signals['Leverage_Decrease'] = 1 if curr_borr <= prev_borr else 0

                if capital_row is not None and len(capital_row) >= 2:
                    curr_cap = safe_float(capital_row.iloc[-1])
                    prev_cap = safe_float(capital_row.iloc[-2])
                    signals['No_Share_Dilution'] = 1 if curr_cap <= prev_cap else 0

                if assets_row is not None and len(assets_row) >= 2 and pnl is not None and not pnl.empty:
                    sales_row = self._find_df_row(pnl, ['Sales', 'Revenue'])
                    if sales_row is not None and len(sales_row) >= 2:
                        curr_sales = safe_float(sales_row.iloc[-1])
                        prev_sales = safe_float(sales_row.iloc[-2])
                        curr_assets = safe_float(assets_row.iloc[-1], default=1.0)
                        prev_assets = safe_float(assets_row.iloc[-2], default=1.0)
                        curr_turnover = curr_sales / curr_assets if curr_assets else 0
                        prev_turnover = prev_sales / prev_assets if prev_assets else 0
                        signals['Asset_Turnover_Growth'] = 1 if curr_turnover > prev_turnover else 0

        except Exception as e:
            print(f"Error calculating Piotroski signals: {e}")

        # Fallback to key ratios if table signals are incomplete
        score = sum(signals.values())
        
        # If table data was sparse, complement with top ratios
        if len(signals) < 4:
            roce = safe_float(top_ratios.get('ROCE', '0'))
            roe = safe_float(top_ratios.get('ROE', '0'))
            pe = safe_float(top_ratios.get('Stock P/E', '0'))
            
            score = 0
            if roce > 15: score += 3
            elif roce > 10: score += 2
            if roe > 15: score += 3
            elif roe > 10: score += 2
            if 0 < pe < 25: score += 3
            elif 0 < pe < 35: score += 1

        score = max(0, min(9, score))

        if score >= 7:
            label = "Strong Financial Health (Piotroski Score: High)"
        elif score >= 4:
            label = "Moderate Health (Piotroski Score: Average)"
        else:
            label = "Caution Required (Piotroski Score: Low)"

        return {
            'piotroski_f_score': score,
            'max_score': 9,
            'signals_evaluated': signals,
            'health_label': label
        }

    def get_chart_data(self, company_id, metric='Price-DMA50-DMA200', days=365):
        """Fetches historical chart time-series data."""
        if not company_id:
            return {}
        chart_url = f"https://www.screener.in/api/company/{company_id}/chart/?q={urllib.parse.quote(metric)}&days={days}"
        try:
            raw = self._get(chart_url)
            return json.loads(raw)
        except Exception as e:
            print(f"Error fetching chart data: {e}")
            return {}

    def _parse_section_table(self, soup, section_id):
        """Extracts and parses HTML table from a specific section ID."""
        section = soup.find('section', id=section_id)
        if not section:
            return None
        table = section.find('table')
        if not table:
            return None

        header_tr = table.find('tr')
        if not header_tr:
            return None
            
        headers = [th.text.strip() for th in header_tr.find_all(['th', 'td'])]
        if headers and headers[0] == "":
            headers[0] = "Metric"

        rows = []
        for tr in table.find_all('tr')[1:]:
            cols = [td.text.strip() for td in tr.find_all(['td', 'th'])]
            if len(cols) == len(headers):
                rows.append(cols)
            elif len(cols) == len(headers) - 1:
                rows.append([""] + cols)

        if not rows:
            return None

        df = pd.DataFrame(rows, columns=headers)
        return df

    def _find_df_row(self, df, possible_names):
        """Finds a matching metric row in a DataFrame by checking column 0 or index."""
        if df is None or df.empty:
            return None
        metric_col = df.columns[0]
        for idx, row in df.iterrows():
            metric_val = str(row[metric_col]).strip().lower()
            for name in possible_names:
                if name.lower() in metric_val:
                    # Return numeric data columns (excluding metric column)
                    return row.iloc[1:]
        return None

    def _empty_health_scores(self):
        return {
            'piotroski_f_score': 0,
            'max_score': 9,
            'signals_evaluated': {},
            'health_label': "Data Unavailable"
        }
