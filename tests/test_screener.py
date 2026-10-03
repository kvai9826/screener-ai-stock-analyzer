import unittest
from unittest.mock import patch, MagicMock
import pandas as pd
from screener_fetcher import ScreenerFetcher

SAMPLE_HTML = """
<html>
<body>
  <h1>Reliance Industries Ltd</h1>
  <ul id="top-ratios">
    <li class="flex flex-space-between"><span class="name">Market Cap</span><span class="number">1,800,000 Cr</span></li>
    <li class="flex flex-space-between"><span class="name">Stock P/E</span><span class="number">24.5</span></li>
    <li class="flex flex-space-between"><span class="name">ROCE</span><span class="number">14.2%</span></li>
    <li class="flex flex-space-between"><span class="name">ROE</span><span class="number">12.5%</span></li>
  </ul>
  <section id="quarters">
    <table>
      <tr><th></th><th>Mar 2023</th><th>Jun 2023</th><th>Sep 2023</th></tr>
      <tr><td>Sales</td><td>200,000</td><td>210,000</td><td>220,000</td></tr>
      <tr><td>Net Profit</td><td>18,000</td><td>19,000</td><td>20,000</td></tr>
    </table>
  </section>
  <section id="profit-loss">
    <table>
      <tr><th></th><th>Mar 2022</th><th>Mar 2023</th></tr>
      <tr><td>Sales</td><td>700,000</td><td>850,000</td></tr>
      <tr><td>Net Profit</td><td>60,000</td><td>73,000</td></tr>
      <tr><td>OPM %</td><td>16%</td><td>18%</td></tr>
    </table>
  </section>
  <section id="balance-sheet">
    <table>
      <tr><th></th><th>Mar 2022</th><th>Mar 2023</th></tr>
      <tr><td>Share Capital</td><td>6,700</td><td>6,700</td></tr>
      <tr><td>Borrowings</td><td>300,000</td><td>290,000</td></tr>
      <tr><td>Total Assets</td><td>1,400,000</td><td>1,600,000</td></tr>
    </table>
  </section>
  <section id="cash-flow">
    <table>
      <tr><th></th><th>Mar 2022</th><th>Mar 2023</th></tr>
      <tr><td>Cash from Operating Activity</td><td>90,000</td><td>110,000</td></tr>
    </table>
  </section>
</body>
</html>
"""

class TestScreenerFetcher(unittest.TestCase):

    def setUp(self):
        self.fetcher = ScreenerFetcher()

    @patch.object(ScreenerFetcher, '_get')
    def test_search_company(self, mock_get):
        mock_get.return_value = '[{"id": 123, "name": "Reliance Industries", "url": "/company/RELIANCE/"}]'
        results = self.fetcher.search_company("RELIANCE")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['name'], "Reliance Industries")
        self.assertEqual(results[0]['ticker'], "RELIANCE")

    @patch.object(ScreenerFetcher, '_get')
    def test_get_company_data(self, mock_get):
        mock_get.return_value = SAMPLE_HTML
        data = self.fetcher.get_company_data("RELIANCE")
        self.assertEqual(data['ticker'], "RELIANCE")
        self.assertEqual(data['name'], "Reliance Industries Ltd")
        self.assertTrue(data['is_consolidated'])
        self.assertIn('Market Cap', data['top_ratios'])
        self.assertEqual(data['top_ratios']['Stock P/E'], '24.5')

    def test_piotroski_f_score_calculation(self):
        # Create mock financial DataFrames for testing 9 signals
        pnl = pd.DataFrame([
            ['Sales', '700,000', '850,000'],
            ['Net Profit', '60,000', '73,000'],
            ['OPM %', '16%', '18%']
        ], columns=['Metric', 'Mar 2022', 'Mar 2023'])

        bs = pd.DataFrame([
            ['Share Capital', '6,700', '6,700'],
            ['Borrowings', '300,000', '290,000'],
            ['Total Assets', '1,400,000', '1,600,000']
        ], columns=['Metric', 'Mar 2022', 'Mar 2023'])

        cf = pd.DataFrame([
            ['Cash from Operating Activity', '90,000', '110,000']
        ], columns=['Metric', 'Mar 2022', 'Mar 2023'])

        tables = {'profit_loss': pnl, 'balance_sheet': bs, 'cash_flow': cf}
        scores = self.fetcher.calculate_piotroski_f_score(tables, {})
        
        # 0 to 9 integer range check
        f_score = scores['piotroski_f_score']
        self.assertIsInstance(f_score, int)
        self.assertTrue(0 <= f_score <= 9)
        self.assertIn('Piotroski Score', scores['health_label'])

    @patch.object(ScreenerFetcher, '_get')
    def test_missing_data_resilience(self, mock_get):
        mock_get.side_effect = Exception("HTTP 404")
        data = self.fetcher.get_company_data("INVALID_TICKER")
        self.assertEqual(data['ticker'], "INVALID_TICKER")
        self.assertFalse(data['is_consolidated'])
        self.assertEqual(data['top_ratios'], {})

if __name__ == '__main__':
    unittest.main()
