import unittest
from utils import extract_ticker, parse_numeric, safe_float, validate_numerical_claims

class TestUtils(unittest.TestCase):

    def test_extract_ticker(self):
        self.assertEqual(extract_ticker('/company/RELIANCE/'), 'RELIANCE')
        self.assertEqual(extract_ticker('https://www.screener.in/company/RELIANCE/consolidated/'), 'RELIANCE')
        self.assertEqual(extract_ticker('company/TCS'), 'TCS')
        self.assertEqual(extract_ticker('INFY'), 'INFY')
        self.assertEqual(extract_ticker('/company/TATAMOTORS/standalone/'), 'TATAMOTORS')
        self.assertEqual(extract_ticker(''), '')

    def test_parse_numeric(self):
        self.assertEqual(parse_numeric('1,234.50'), (1234.5, ''))
        self.assertEqual(parse_numeric('₹1,234 Cr'), (1234.0, '₹ Cr'))
        self.assertEqual(parse_numeric('23.5%'), (23.5, '%'))
        self.assertEqual(parse_numeric('—'), (None, ''))
        self.assertEqual(parse_numeric('N/A'), (None, ''))
        self.assertEqual(parse_numeric('NM'), (None, ''))
        self.assertEqual(parse_numeric(None), (None, ''))

    def test_safe_float(self):
        self.assertEqual(safe_float('1,500.25'), 1500.25)
        self.assertEqual(safe_float('25.5%'), 25.5)
        self.assertEqual(safe_float('invalid', default=-1.0), -1.0)
        self.assertEqual(safe_float(None, default=0.0), 0.0)

    def test_validate_numerical_claims(self):
        ratios = {'Stock P/E': '25.5', 'ROCE': '18.2%'}
        report = "The company trades at a P/E of 25.5 with ROCE of 18.2%."
        res = validate_numerical_claims(ratios, {}, report)
        self.assertTrue(res['is_grounded'])

if __name__ == '__main__':
    unittest.main()
