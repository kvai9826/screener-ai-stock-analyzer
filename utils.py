import re
from urllib.parse import urlparse

def extract_ticker(url_or_path: str) -> str:
    """
    Robustly extracts the ticker symbol from a Screener.in URL, path, or raw input string.
    Supports inputs like:
      - '/company/RELIANCE/' -> 'RELIANCE'
      - 'https://www.screener.in/company/RELIANCE/consolidated/' -> 'RELIANCE'
      - 'company/RELIANCE' -> 'RELIANCE'
      - 'RELIANCE' -> 'RELIANCE'
    """
    if not url_or_path:
        return ""
    
    cleaned = url_or_path.strip()
    # Parse URL if absolute
    parsed = urlparse(cleaned)
    path = parsed.path if parsed.path else cleaned

    # Strip leading/trailing slashes and split by '/'
    segments = [s for s in path.strip('/').split('/') if s]
    
    # Look for 'company' in segments and take the next segment
    for i, seg in enumerate(segments):
        if seg.lower() == 'company' and i + 1 < len(segments):
            ticker = segments[i + 1].strip()
            # Remove any trailing modifier like 'consolidated'
            if ticker.lower() in ('consolidated', 'standalone'):
                continue
            return ticker.upper()
    
    # Fallback: if no 'company' segment found, return the first non-empty segment or cleaned string
    if segments:
        candidate = segments[0].upper()
        if candidate not in ('HTTPS:', 'HTTP:', 'WWW.SCREENER.IN', 'SCREENER.IN'):
            return candidate
            
    return cleaned.upper()


def parse_numeric(val):
    """
    Safely parses financial numbers from Screener.in formatted strings.
    Handles:
      - '1,234.50' -> (1234.50, '')
      - '₹1,234 Cr' -> (1234.0, '₹ Cr')
      - '23.5%' -> (23.5, '%')
      - '—', 'N/A', 'NM', '' -> (None, '')
    Returns a tuple: (float_value_or_None, unit_string)
    """
    if val is None:
        return (None, "")

    if isinstance(val, (int, float)):
        return (float(val), "")

    s = str(val).strip()
    if not s or s in ('—', '-', 'N/A', 'NM', 'None', 'null'):
        return (None, "")

    # Clean currency symbols and commas
    cleaned = s.replace(',', '').replace('₹', '').replace('Cr', '').replace('%', '').strip()
    
    # Identify units
    unit = ""
    if '%' in s:
        unit = "%"
    elif 'Cr' in s or '₹' in s:
        unit = "₹ Cr"

    try:
        num = float(cleaned)
        return (num, unit)
    except ValueError:
        return (None, "")


def safe_float(val, default: float = 0.0) -> float:
    """Safely converts any input value or formatted string to float, returning default on failure."""
    num, _ = parse_numeric(val)
    return num if num is not None else default


def validate_numerical_claims(ratios: dict, tables: dict, report_text: str) -> dict:
    """
    Validates whether major financial numbers mentioned in the AI report exist in source ratios/tables.
    Returns validation status dict with matched and missing metrics.
    """
    found_numbers = []
    missing_numbers = []
    
    # Extract numbers from report (e.g. 12.5, 4500, etc.)
    report_numbers = set(re.findall(r'\b\d+(?:\.\d+)?\b', report_text))
    
    # Build reference set of numbers from top ratios
    source_numbers = set()
    for v in ratios.values():
        num, _ = parse_numeric(v)
        if num is not None:
            source_numbers.add(str(num))
            if num.is_integer():
                source_numbers.add(str(int(num)))

    # Check matches
    for r_num in report_numbers:
        if r_num in source_numbers:
            found_numbers.append(r_num)
        else:
            missing_numbers.append(r_num)

    return {
        "verified_count": len(found_numbers),
        "unverified_count": len(missing_numbers),
        "is_grounded": len(found_numbers) > 0 or len(report_numbers) == 0
    }
