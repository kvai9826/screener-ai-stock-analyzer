import unittest
from unittest.mock import patch, MagicMock
from ai_analyst import AIStockAnalyst

class TestAIStockAnalyst(unittest.TestCase):

    def setUp(self):
        self.analyst = AIStockAnalyst(
            openrouter_api_key="test_openrouter_key"
        )
        self.ratios = {'Stock P/E': '25.0', 'ROCE': '18.0%', 'ROE': '15.0%', 'Market Cap': '₹ 1,500,000 Cr.'}
        self.tables = {}
        self.news = [{'title': 'Test Headline', 'source': 'Test Source', 'date': '2026-10-03', 'link': 'http://example.com'}]

    def test_prompt_building_includes_grounding_rules(self):
        prompt = self.analyst._build_deep_prompt("Reliance", self.ratios, self.tables, self.news)
        self.assertIn("GROUNDING CRITICAL RULES", prompt)
        self.assertIn("untrusted DATA", prompt)
        self.assertIn("NEVER invent numbers", prompt)
        self.assertIn("Reliance", prompt)

    def test_comparison_prompt_building(self):
        comp1_data = {'top_ratios': {'Stock P/E': '20.0'}, 'tables': {}}
        comp2_data = {'top_ratios': {'Stock P/E': '30.0'}, 'tables': {}}
        prompt = self.analyst._build_comparison_prompt("TCS", comp1_data, "INFY", comp2_data)
        self.assertIn("TCS", prompt)
        self.assertIn("INFY", prompt)
        self.assertIn("Stock P/E", prompt)

    @patch.object(AIStockAnalyst, '_call_openrouter_with_retry')
    def test_openrouter_provider_execution(self, mock_openrouter):
        mock_openrouter.return_value = ("OpenRouter Report Content", None)
        report = self.analyst.generate_analysis("Reliance", self.ratios, self.tables, self.news)
        self.assertEqual(report, "OpenRouter Report Content")
        self.assertIn("OpenRouter", self.analyst.last_provider_used)

    def test_fallback_engine_when_no_keys_provided(self):
        empty_analyst = AIStockAnalyst(openrouter_api_key="")
        report = empty_analyst.generate_analysis("Reliance", self.ratios, self.tables, self.news)
        self.assertIn("Rule-Based Engine Active", report)
        self.assertIn("Local Rule-Based", empty_analyst.last_provider_used)

    def test_parse_http_error_classification(self):
        err401 = self.analyst._parse_http_error("OpenRouter", 401, "Unauthorized")
        self.assertIn("Authentication Error", err401)

        err429 = self.analyst._parse_http_error("OpenRouter", 429, "Rate limit")
        self.assertIn("Rate Limit Exceeded", err429)

        err500 = self.analyst._parse_http_error("OpenRouter", 500, "Server error")
        self.assertIn("Provider Server Error", err500)

if __name__ == '__main__':
    unittest.main()
