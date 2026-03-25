# ============================================================================
#  PORTFOLIO RISK DASHBOARD — COMPLETE STREAMLIT APP
#  Save as app.py | Run with: streamlit run app.py
# ============================================================================

import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import yfinance as yf
import pdfplumber
import pandas as pd
import numpy as np
import re
import io
import plotly.express as px
from datetime import datetime, timedelta


st.set_page_config(
    page_title="Portfolio Risk Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Session state init ───────────────────────────────────────────────────────
if 'holdings' not in st.session_state:
    st.session_state.holdings = {}
if 'ticker_cache' not in st.session_state:
    st.session_state.ticker_cache = {}
if 'dashboards_ready' not in st.session_state:
    st.session_state.dashboards_ready = False


# ══════════════════════════════════════════════════════════════════════════════
#  HELPER FUNCTIONS
# ══════════════════════════════════════════════════════════════════════════════

def lookup_ticker(ticker):
    """Validate and look up any ticker via Yahoo Finance. Cached."""
    ticker = ticker.upper().strip().replace('.', '-')

    if ticker in st.session_state.ticker_cache:
        return st.session_state.ticker_cache[ticker]

    cash_tickers = {'SPAXX', 'FDRXX', 'SWVXX', 'VMFXX', 'TTTXX', 'SPRXX', 'FCASH'}
    if ticker in cash_tickers:
        result = {
            'valid': True,
            'name': f'{ticker} (Cash)',
            'sector': 'Cash',
            'type': 'Cash',
        }
        st.session_state.ticker_cache[ticker] = result
        return result

    # Hard-coded sector/type map for common tickers (avoids slow API calls)
    known_tickers = {
        'AAPL': ('Apple Inc', 'Technology', 'Stock'),
        'V': ('Visa Inc', 'Financials', 'Stock'),
        'COST': ('Costco Wholesale', 'Consumer', 'Stock'),
        'GOOGL': ('Alphabet Inc', 'Technology', 'Stock'),
        'GOOG': ('Alphabet Inc', 'Technology', 'Stock'),
        'AMZN': ('Amazon.com Inc', 'Technology', 'Stock'),
        'MSFT': ('Microsoft Corp', 'Technology', 'Stock'),
        'META': ('Meta Platforms Inc', 'Technology', 'Stock'),
        'NVDA': ('NVIDIA Corp', 'Technology', 'Stock'),
        'TSLA': ('Tesla Inc', 'Consumer', 'Stock'),
        'COST': ('Costco Wholesale', 'Consumer', 'Stock'),
        'DIS': ('Walt Disney Co', 'Technology', 'Stock'),
        'LLY': ('Eli Lilly & Co', 'Healthcare', 'Stock'),
        'PFE': ('Pfizer Inc', 'Healthcare', 'Stock'),
        'REGN': ('Regeneron Pharmaceuticals', 'Healthcare', 'Stock'),
        'TMO': ('Thermo Fisher Scientific', 'Healthcare', 'Stock'),
        'PLTR': ('Palantir Technologies', 'Technology', 'Stock'),
        'ACHR': ('Archer Aviation', 'Industrials', 'Stock'),
        'LULU': ('Lululemon Athletica', 'Consumer', 'Stock'),
        'MELI': ('MercadoLibre Inc', 'Technology', 'Stock'),
        'BRKB': ('Berkshire Hathaway B', 'Financials', 'Stock'),
        'BRK-B': ('Berkshire Hathaway B', 'Financials', 'Stock'),
        'JPM': ('JPMorgan Chase', 'Financials', 'Stock'),
        'V': ('Visa Inc', 'Financials', 'Stock'),
        'MA': ('Mastercard Inc', 'Financials', 'Stock'),
        'JNJ': ('Johnson & Johnson', 'Healthcare', 'Stock'),
        'UNH': ('UnitedHealth Group', 'Healthcare', 'Stock'),
        'HD': ('Home Depot', 'Consumer', 'Stock'),
        'PG': ('Procter & Gamble', 'Consumer', 'Stock'),
        'KO': ('Coca-Cola Co', 'Consumer', 'Stock'),
        'PEP': ('PepsiCo Inc', 'Consumer', 'Stock'),
        'ABBV': ('AbbVie Inc', 'Healthcare', 'Stock'),
        'MRK': ('Merck & Co', 'Healthcare', 'Stock'),
        'WMT': ('Walmart Inc', 'Consumer', 'Stock'),
        'BAC': ('Bank of America', 'Financials', 'Stock'),
        'CRM': ('Salesforce Inc', 'Technology', 'Stock'),
        'NFLX': ('Netflix Inc', 'Technology', 'Stock'),
        'AMD': ('Advanced Micro Devices', 'Technology', 'Stock'),
        'INTC': ('Intel Corp', 'Technology', 'Stock'),
        'CSCO': ('Cisco Systems', 'Technology', 'Stock'),
        'ADBE': ('Adobe Inc', 'Technology', 'Stock'),
        'ORCL': ('Oracle Corp', 'Technology', 'Stock'),
        'T': ('AT&T Inc', 'Technology', 'Stock'),
        'VZ': ('Verizon Communications', 'Technology', 'Stock'),
        'XOM': ('Exxon Mobil', 'Energy', 'Stock'),
        'CVX': ('Chevron Corp', 'Energy', 'Stock'),
        'AVGO': ('Broadcom Inc', 'Technology', 'Stock'),
        'NOW': ('ServiceNow Inc', 'Technology', 'Stock'),
        'UBER': ('Uber Technologies', 'Technology', 'Stock'),
        'SQ': ('Block Inc', 'Technology', 'Stock'),
        'SHOP': ('Shopify Inc', 'Technology', 'Stock'),
        'PYPL': ('PayPal Holdings', 'Technology', 'Stock'),
        'COIN': ('Coinbase Global', 'Financials', 'Stock'),
        'SNOW': ('Snowflake Inc', 'Technology', 'Stock'),
        'NET': ('Cloudflare Inc', 'Technology', 'Stock'),
        'ABNB': ('Airbnb Inc', 'Consumer', 'Stock'),
        'RIVN': ('Rivian Automotive', 'Consumer', 'Stock'),
        'LCID': ('Lucid Group', 'Consumer', 'Stock'),
        'SOFI': ('SoFi Technologies', 'Financials', 'Stock'),
        'NKE': ('Nike Inc', 'Consumer', 'Stock'),
        'SBUX': ('Starbucks Corp', 'Consumer', 'Stock'),
        # ETFs
        'SPY': ('SPDR S&P 500 ETF', 'Broad Market', 'ETF'),
        'QQQ': ('Invesco QQQ Trust', 'Technology', 'ETF'),
        'IWM': ('iShares Russell 2000', 'Broad Market', 'ETF'),
        'DIA': ('SPDR Dow Jones ETF', 'Broad Market', 'ETF'),
        'VOO': ('Vanguard S&P 500 ETF', 'Broad Market', 'ETF'),
        'VTI': ('Vanguard Total Stock Market', 'Broad Market', 'ETF'),
        'VGT': ('Vanguard Info Tech ETF', 'Technology', 'ETF'),
        'XLK': ('Technology Select Sector SPDR', 'Technology', 'ETF'),
        'XLV': ('Health Care Select Sector SPDR', 'Healthcare', 'ETF'),
        'XLE': ('Energy Select Sector SPDR', 'Energy', 'ETF'),
        'XLF': ('Financial Select Sector SPDR', 'Financials', 'ETF'),
        'XLI': ('Industrial Select Sector SPDR', 'Industrials', 'ETF'),
        'XLY': ('Consumer Discretionary SPDR', 'Consumer', 'ETF'),
        'XLP': ('Consumer Staples SPDR', 'Consumer', 'ETF'),
        'XLU': ('Utilities Select Sector SPDR', 'Utilities', 'ETF'),
        'XLB': ('Materials Select Sector SPDR', 'Industrials', 'ETF'),
        'XLRE': ('Real Estate Select SPDR', 'Real Estate', 'ETF'),
        'XLC': ('Communication Services SPDR', 'Technology', 'ETF'),
        'ARKK': ('ARK Innovation ETF', 'Technology', 'ETF'),
        'SOXX': ('iShares Semiconductor ETF', 'Technology', 'ETF'),
        'IXN': ('iShares Global Tech ETF', 'Technology', 'ETF'),
        'IDRV': ('iShares Self-Driving EV ETF', 'Technology', 'ETF'),
        'SCHD': ('Schwab US Dividend Equity', 'Broad Market', 'ETF'),
        'VYM': ('Vanguard High Dividend Yield', 'Broad Market', 'ETF'),
        'JEPI': ('JPMorgan Equity Premium Income', 'Broad Market', 'ETF'),
        'GLD': ('SPDR Gold Trust', 'Other', 'ETF'),
        'SLV': ('iShares Silver Trust', 'Other', 'ETF'),
        'TLT': ('iShares 20+ Year Treasury', 'Other', 'ETF'),
        'BND': ('Vanguard Total Bond Market', 'Other', 'ETF'),
        'AGG': ('iShares Core US Aggregate Bond', 'Other', 'ETF'),
        'VNQ': ('Vanguard Real Estate ETF', 'Real Estate', 'ETF'),
        'FBTC': ('Fidelity Wise Origin Bitcoin', 'Crypto', 'ETF'),
        'IBIT': ('iShares Bitcoin Trust', 'Crypto', 'ETF'),
        'GBTC': ('Grayscale Bitcoin Trust', 'Crypto', 'ETF'),
        'ETHE': ('Grayscale Ethereum Trust', 'Crypto', 'ETF'),
        # Add these to the known_tickers dict:
        'FBIOX': ('Fidelity Select Biotechnology', 'Healthcare', 'Fund'),
        'FSELX': ('Fidelity Select Semiconductors', 'Technology', 'Fund'),
        'BIIB': ('Biogen Inc', 'Healthcare', 'Stock'),
        'COKE': ('Coca-Cola Consolidated', 'Consumer', 'Stock'),
        'NUE': ('Nucor Corp', 'Industrials', 'Stock'),
        'MCD': ("McDonald's Corp", 'Consumer', 'Stock'),
        'VT': ('Vanguard Total World Stock ETF', 'Broad Market', 'ETF'),
        'XOM': ('Exxon Mobil', 'Energy', 'Stock'),
        'ABBV': ('AbbVie Inc', 'Healthcare', 'Stock'),
        'AMD': ('Advanced Micro Devices', 'Technology', 'Stock'),
        'HD': ('Home Depot', 'Consumer', 'Stock'),
        'JPM': ('JPMorgan Chase', 'Financials', 'Stock'),
        'JNJ': ('Johnson & Johnson', 'Healthcare', 'Stock'),
        'MA': ('Mastercard Inc', 'Financials', 'Stock'),
        'PEP': ('PepsiCo Inc', 'Consumer', 'Stock'),
        'PG': ('Procter & Gamble', 'Consumer', 'Stock'),
        'UNH': ('UnitedHealth Group', 'Healthcare', 'Stock'),
        'VZ': ('Verizon Communications', 'Technology', 'Stock'),
        'V': ('Visa Inc', 'Financials', 'Stock'),
    }

    if ticker in known_tickers:
        name, sector, asset_type = known_tickers[ticker]
        result = {
            'valid': True,
            'name': name,
            'sector': sector,
            'type': asset_type,
        }
        st.session_state.ticker_cache[ticker] = result
        return result

    # Fallback: validate via price history (faster than .info)
    try:
        test = yf.download(ticker, period='5d', progress=False)
        if test.empty or len(test) < 1:
            st.session_state.ticker_cache[ticker] = {'valid': False}
            return {'valid': False}

        # Valid ticker but not in our known list — use generic info
        result = {
            'valid': True,
            'name': ticker,
            'sector': 'Other',
            'type': 'Stock',
        }

        # Try to get name/sector from .info but don't fail if it times out
        try:
            info = yf.Ticker(ticker).info
            if info:
                result['name'] = info.get('shortName', info.get('longName', ticker))
                sector = info.get('sector', 'Other')
                qtype = info.get('quoteType', '').upper()

                sector_map = {
                    'Technology': 'Technology',
                    'Communication Services': 'Technology',
                    'Consumer Cyclical': 'Consumer',
                    'Consumer Defensive': 'Consumer',
                    'Healthcare': 'Healthcare',
                    'Health Care': 'Healthcare',
                    'Financial Services': 'Financials',
                    'Financials': 'Financials',
                    'Energy': 'Energy',
                    'Industrials': 'Industrials',
                    'Basic Materials': 'Industrials',
                    'Real Estate': 'Real Estate',
                    'Utilities': 'Utilities',
                }
                result['sector'] = sector_map.get(sector, sector)

                if qtype == 'ETF':
                    result['type'] = 'ETF'
                elif qtype == 'MUTUALFUND':
                    result['type'] = 'Fund'
                elif qtype == 'CRYPTOCURRENCY':
                    result['type'] = 'Crypto'
        except Exception:
            pass  # Keep generic info, at least we know the ticker is valid

        st.session_state.ticker_cache[ticker] = result
        return result

    except Exception:
        st.session_state.ticker_cache[ticker] = {'valid': False}
        return {'valid': False}
        


def parse_money(text):
    """Parse dollar string to float."""
    if not text:
        return None
    text = str(text).strip()
    negative = '(' in text or text.startswith('-')
    text = re.sub(r'[$()\s,]', '', text)
    try:
        val = float(text)
        return -abs(val) if negative and val > 0 else val
    except Exception:
        return None


FALSE_POSITIVES = {
    'THE', 'AND', 'FOR', 'YOU', 'YOUR', 'ARE', 'NOT', 'ALL', 'CAN', 'HAD',
    'HER', 'WAS', 'ONE', 'OUR', 'OUT', 'HAS', 'HIS', 'HOW', 'ITS', 'MAY',
    'NEW', 'NOW', 'OLD', 'SEE', 'WAY', 'WHO', 'DID', 'GET', 'HIM', 'LET',
    'SAY', 'SHE', 'TOO', 'USE', 'SET', 'TOP', 'END', 'FAR', 'RAN', 'RED',
    'BIG', 'OWN', 'PUT', 'ASK', 'MEN', 'RUN', 'TRY', 'TAX', 'FEE', 'NET',
    'PER', 'AVG', 'QTY', 'YTD', 'INC', 'LTD', 'LLC', 'USD', 'USA', 'EST',
    'PST', 'CST', 'APR', 'JAN', 'FEB', 'MAR', 'JUN', 'JUL', 'AUG', 'SEP',
    'OCT', 'NOV', 'DEC', 'MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN',
    'PDF', 'CSV', 'CEO', 'CFO', 'DIV', 'NAV', 'SEC', 'IRS', 'ACH', 'PIN',
    'ATM', 'APY', 'IRA', 'HSA', 'FSA', 'AGI', 'BUY', 'SELL', 'HOLD', 'LONG',
    'OPEN', 'HIGH', 'LOW', 'LAST', 'DATE', 'CALL', 'PAGE', 'PART', 'FROM',
    'WITH', 'THAT', 'THIS', 'HAVE', 'EACH', 'MAKE', 'LIKE', 'LOOK', 'MANY',
    'SOME', 'THEM', 'THAN', 'BEEN', 'COST', 'CASH', 'FUND', 'NOTE', 'BOND',
    'RATE', 'TERM', 'PLAN', 'TOTAL', 'NAME', 'TYPE', 'PRICE', 'VALUE',
    'SHARE', 'MARKET', 'GAIN', 'LOSS', 'INCOME', 'ANNUAL', 'CHANGE',
    'ACCOUNT', 'NUMBER', 'STREET', 'CITY', 'STATE', 'ZIP', 'PHONE', 'EMAIL',
    'DEAR', 'THANK', 'PLEASE', 'ALSO', 'WILL', 'WOULD', 'COULD', 'SHOULD',
    'ABOUT', 'ABOVE', 'AFTER', 'AGAIN', 'BELOW', 'BETWEEN', 'BOTH', 'DOWN',
    'DURING', 'FIRST', 'INTO', 'JUST', 'MORE', 'MOST', 'MUCH', 'MUST',
    'ONLY', 'OTHER', 'OVER', 'SAME', 'STILL', 'SUCH', 'TAKE', 'TELL',
    'THEN', 'THERE', 'THESE', 'THEY', 'THROUGH', 'UNDER', 'UNTIL', 'UPON',
    'VERY', 'WANT', 'WELL', 'WERE', 'WHAT', 'WHEN', 'WHERE', 'WHICH',
    'WHILE', 'WORK', 'YEAR', 'ALSO', 'BACK', 'BEEN', 'BEING', 'COME',
    'DAYS', 'DOES', 'DONE', 'DOWN', 'EVEN', 'FIND', 'GIVE', 'GOES', 'GONE',
    'GOOD', 'GREAT', 'HAND', 'HELP', 'HERE', 'HOME', 'HOUR', 'KEEP', 'KIND',
    'KNOW', 'LAND', 'LAST', 'LEFT', 'LIFE', 'LINE', 'LIST', 'LIVE', 'MADE',
    'MAIN', 'MARK', 'MEAN', 'MEET', 'MIND', 'MISS', 'MOVE', 'NEED', 'NEXT',
    'ONCE', 'PAID', 'PAST', 'PICK', 'PLAY', 'POINT', 'REAL', 'REST', 'RISK',
    'RULE', 'SAID', 'SAVE', 'SEND', 'SHOW', 'SIDE', 'SIZE', 'SORT', 'STEP',
    'STOP', 'SURE', 'TALK', 'TEAM', 'TEST', 'TEXT', 'TIME', 'TURN', 'UNIT',
    'USED', 'VIEW', 'WAIT', 'WALK', 'WEEK', 'WORD', 'ZERO',
}


def is_likely_ticker(word):
    """Quick heuristic: is this word likely a stock ticker?"""
    word = word.upper().strip()
    if len(word) < 1 or len(word) > 6:
        return False
    if not re.match(r'^[A-Z][A-Z0-9\-\.]{0,5}$', word):
        return False
    if word in FALSE_POSITIVES:
        return False
    return True


def parse_pdf(file_bytes):
    """Parse Fidelity brokerage PDF statement and extract holdings."""
    holdings = {}

    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        full_text = ""
        all_tables = []
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                full_text += text + "\n"
            tables = page.extract_tables()
            if tables:
                all_tables.extend(tables)

    lines = full_text.split('\n')

    paren_pattern = re.compile(r'\(([A-Z][A-Z0-9]{0,5})\)')
    number_pattern = re.compile(r'-?\$?[\d,]+\.\d{2,4}')

    # Non-ticker abbreviations found in Fidelity PDFs
    SKIP_PARENS = {
        'ETFS', 'ETNS', 'NYSE', 'SIPC', 'SIPA', 'CUSIP', 'FIFO', 'FDIC',
        'USD', 'IAD', 'DTC', 'FBS', 'NFS', 'FDC', 'HSA', 'IRA', 'LLC',
        'ROTH', 'FMTC', 'AI', 'FMR', 'ETF', 'CD', 'CDS', 'CUSC', 'CUSCS',
        'MLP', 'MLPS', 'REIT', 'REITS', 'UIT', 'UITS', 'LP', 'LPS',
        'S', 'OR', 'AND', 'THE', 'FOR', 'IN', 'OF', 'TO', 'AT', 'BY',
        'AN', 'IS', 'IT', 'IF', 'ON', 'AS', 'BE', 'DO', 'SO', 'UP',
        'FDC', 'FAST', 'II', 'III', 'IV', 'VI', 'VII', 'VIII', 'IX', 'XI',
    }

    # ── Step 1: Identify all ticker lines, including the data-line offset ──
    # Fidelity format puts numbers on the FIRST line of description,
    # but the ticker (in parens) may be on that same line or up to 3 lines later.

    def extract_nums(line_text):
        nums = []
        for m in number_pattern.finditer(line_text):
            end_pos = m.end()
            if end_pos < len(line_text) and line_text[end_pos] == '%':
                continue
            n_str = m.group().replace('$', '').replace(',', '').strip()
            try:
                nums.append(float(n_str))
            except:
                pass
        return nums

    def is_skip_line(line_text):
        low = line_text.strip().lower()
        skip_phrases = [
            'total ', 'top holdings', 'income summary', 'estimated cash flow',
            'dividend received', 'you bought', 'reinvestment', 'copyright',
            'moody', 'settlement', 'beginning', 'market value', 'description',
            'feb 1', 'feb 28', 'account #', 'account summary', 'account value',
            'account holdings', 'percent of', 'page ', 'envelope',
            'portfolio summary', 'portfolio value', 'portfolio change',
            'ending portfolio', 'beginning portfolio', 'additions', 'subtractions',
            'deposits', 'withdrawals', 'change in', 'accrued interest',
            'ending account', 'beginning account', 'contact information',
            'online fidelity', 'customer service', 'brokerage services',
            'save on your', 'fidelity.com', 'investment report',
            'all positions held', 'estimated annual', 'includes exchange',
            'core fund activity', 'anuveer', 'general investments',
            'personal retirement', 'fidelity account', 'fidelity roth',
            'common stock', 'equity etps', 'other etps', 'stock funds',
            'short-term funds', 'important:', 'asset allocation', 'asset class',
            'domestic stock', 'short term', 'foreign stock', 'other',
            'please note', 'additional information', 'fractional share',
            'payment for order', 'executing orders', 'sales loads',
            'statement discrepancies', 'material changes', 'mutual funds and',
            'information about', 'lost or stolen', 'additional investments',
            'free credit', 'miscellaneous', 'price information',
        ]
        for phrase in skip_phrases:
            if low.startswith(phrase) or (phrase in low and len(low) < 100 and not any(c.isdigit() for c in low[:20])):
                # But don't skip if the line has a ticker AND numbers
                if '(' in line_text and any(c.isdigit() for c in line_text):
                    has_ticker = False
                    for pm in paren_pattern.finditer(line_text):
                        t = pm.group(1)
                        if t not in SKIP_PARENS and len(t) >= 1:
                            has_ticker = True
                    if has_ticker:
                        return False
                return True
        return False

    # ── Step 2: Find all tickers and associate with their data numbers ──
    # Build a list of (ticker, data_numbers) pairs

    # First, find every line that has a (TICKER)
    ticker_lines = []
    for i, line in enumerate(lines):
        if is_skip_line(line):
            continue
        for match in paren_pattern.finditer(line):
            ticker = match.group(1)
            if ticker in SKIP_PARENS:
                continue
            if len(ticker) < 1 or len(ticker) > 5:
                continue
            ticker_lines.append((i, ticker))

    # For each ticker, find its numbers by searching backwards
    for t_idx, (line_idx, ticker) in enumerate(ticker_lines):
        # Get numbers on the ticker's own line
        own_nums = extract_nums(lines[line_idx])

        # If this line has 4+ numbers, the data is on the same line
        if len(own_nums) >= 4:
            block_nums = own_nums
        else:
            # Search backwards up to 4 lines for a line with 4+ numbers
            block_nums = []
            prev_ticker_line = ticker_lines[t_idx - 1][0] if t_idx > 0 else -1

            for si in range(line_idx - 1, max(prev_ticker_line, line_idx - 5), -1):
                if si < 0:
                    break
                candidate = lines[si].strip()
                low_c = candidate.lower()
                if low_c.startswith('total '):
                    break
                nums = extract_nums(candidate)
                if len(nums) >= 4:
                    block_nums = nums
                    break

            # If still nothing, combine ticker line nums with lines above
            if not block_nums:
                combined = []
                for si in range(max(0, max(prev_ticker_line + 1, line_idx - 3)), line_idx + 1):
                    candidate = lines[si].strip()
                    if candidate.lower().startswith('total '):
                        combined = []
                        continue
                    combined.extend(extract_nums(candidate))
                block_nums = combined

        if len(block_nums) < 3:
            continue

        # ── Identify: beg_value, quantity, price, ending_value, cost_basis ──
        best_ending = None
        best_cost = None
        found = False

        # Try all plausible (qty_index, price_index) combos
        for qi in range(min(4, len(block_nums) - 1)):
            for pi in range(qi + 1, min(qi + 3, len(block_nums))):
                qty = block_nums[qi]
                price = block_nums[pi]
                expected = qty * price

                if expected < 0.50:
                    continue

                # Look for ending value after price
                for ei in range(pi + 1, min(pi + 3, len(block_nums))):
                    ending = block_nums[ei]
                    tolerance = 0.02 if expected > 10 else 0.05
                    if abs(ending - expected) / max(expected, 0.01) < tolerance:
                        best_ending = ending
                        # Cost is typically the next number after ending
                        if ei + 1 < len(block_nums):
                            cost_val = abs(block_nums[ei + 1])
                            # Sanity: cost should be somewhat close to ending value
                            if cost_val < best_ending * 5 and cost_val > 0.5:
                                best_cost = cost_val
                            else:
                                best_cost = best_ending
                        else:
                            best_cost = best_ending
                        found = True
                        break
                if found:
                    break
            if found:
                break

        # Special case: money market funds where price = $1.0000
        if not found:
            for qi in range(len(block_nums) - 1):
                qty = block_nums[qi]
                price = block_nums[qi + 1]
                if abs(price - 1.0) < 0.001 and qty > 1:
                    best_ending = qty
                    best_cost = qty
                    found = True
                    break

        if not found or best_ending is None or best_ending < 0.01:
            continue

        if best_cost is None or best_cost <= 0:
            best_cost = best_ending

        # ── Validate ticker via lookup ──
        info = lookup_ticker(ticker)
        if not info.get('valid'):
            continue

        # ── Aggregate across accounts ──
        if ticker in holdings:
            holdings[ticker]['value'] = round(holdings[ticker]['value'] + best_ending, 2)
            holdings[ticker]['cost'] = round(holdings[ticker]['cost'] + best_cost, 2)
        else:
            holdings[ticker] = {
                'value': round(best_ending, 2),
                'cost': round(best_cost, 2),
                'type': info['type'],
                'name': info['name'],
                'sector': info.get('sector', 'Other'),
            }

    # ── Mark cash positions ──
    cash_tickers = {'SPAXX', 'FDRXX', 'SWVXX', 'VMFXX', 'FCASH', 'SPRXX'}
    for ticker in list(holdings.keys()):
        if ticker in cash_tickers:
            holdings[ticker]['type'] = 'Cash'
            holdings[ticker]['sector'] = 'Cash'
            holdings[ticker]['cost'] = holdings[ticker]['value']

    return holdings, full_text, all_tables

@st.cache_data(ttl=300, show_spinner="Downloading price data...")
def download_prices(tickers_tuple, period='1y'):
    """Download price data with caching."""
    tickers = list(tickers_tuple)
    if 'SPY' not in tickers:
        tickers.append('SPY')

    # Remove cash-like tickers that Yahoo can't price
    skip = {'SPAXX', 'FDRXX', 'SWVXX', 'VMFXX', 'FCASH', 'SPRXX', 'TTTXX'}
    tickers = [t for t in tickers if t not in skip]

    if not tickers:
        return pd.DataFrame()

    # Download in one batch
    prices = yf.download(tickers, period=period, auto_adjust=True, progress=False, threads=True)

    if prices.empty:
        return pd.DataFrame()

    if isinstance(prices.columns, pd.MultiIndex):
        if 'Close' in prices.columns.get_level_values(0):
            close = prices['Close']
        else:
            close = prices.droplevel(0, axis=1)
    else:
        close = prices

    close.columns = [str(c).strip() for c in close.columns]
    return close.dropna(how='all').ffill()


@st.cache_data(ttl=3600, show_spinner="Downloading S&P 500 history...")
def download_spy_alltime():
    """Download full SPY history."""
    spy = yf.download('SPY', period='max', auto_adjust=True, progress=False)

    if isinstance(spy.columns, pd.MultiIndex):
        spy = spy.droplevel(0, axis=1) if spy.columns.nlevels > 1 else spy

    if 'SPY' in spy.columns:
        return spy['SPY']
    elif 'Close' in spy.columns:
        return spy['Close']
    else:
        return spy.iloc[:, 0]


def calculate_metrics(holdings, close, valid_tickers, total_value):
    """Calculate all portfolio risk metrics."""
    returns = close.pct_change().dropna()

    total_stock_value = sum(holdings[t]['value'] for t in valid_tickers)
    if total_stock_value == 0:
        return None

    weights = {t: holdings[t]['value'] / total_stock_value for t in valid_tickers}
    weight_series = pd.Series(weights)

    port_returns = returns[valid_tickers].mul(weight_series).sum(axis=1)
    aligned = pd.DataFrame({
        'Portfolio': port_returns,
        'SPY': returns['SPY'],
    }).dropna()

    if len(aligned) < 10:
        return None

    rf_daily = 0.045 / 252
    m = {}

    # Annualized return and volatility
    m['port_ret_ann'] = aligned['Portfolio'].mean() * 252 * 100
    m['spy_ret_ann'] = aligned['SPY'].mean() * 252 * 100
    m['port_vol_ann'] = aligned['Portfolio'].std() * np.sqrt(252) * 100
    m['spy_vol_ann'] = aligned['SPY'].std() * np.sqrt(252) * 100

    # Sharpe ratio
    port_excess = aligned['Portfolio'].mean() - rf_daily
    spy_excess = aligned['SPY'].mean() - rf_daily
    port_std = aligned['Portfolio'].std()
    spy_std = aligned['SPY'].std()
    m['port_sharpe'] = (port_excess / port_std) * np.sqrt(252) if port_std > 0 else 0
    m['spy_sharpe'] = (spy_excess / spy_std) * np.sqrt(252) if spy_std > 0 else 0

    # Sortino ratio
    port_down = aligned['Portfolio'][aligned['Portfolio'] < 0].std()
    spy_down = aligned['SPY'][aligned['SPY'] < 0].std()
    m['port_sortino'] = (port_excess / port_down) * np.sqrt(252) if port_down > 0 else 0
    m['spy_sortino'] = (spy_excess / spy_down) * np.sqrt(252) if spy_down > 0 else 0

    # Beta and correlation
    cov = aligned[['Portfolio', 'SPY']].cov()
    spy_var = cov.loc['SPY', 'SPY']
    m['beta'] = cov.loc['Portfolio', 'SPY'] / spy_var if spy_var > 0 else 0
    m['correlation'] = aligned['Portfolio'].corr(aligned['SPY'])

    # Cumulative returns
    port_cum = (1 + aligned['Portfolio']).cumprod()
    spy_cum = (1 + aligned['SPY']).cumprod()
    m['port_cum'] = port_cum
    m['spy_cum'] = spy_cum

    # Drawdowns
    port_dd = ((port_cum - port_cum.cummax()) / port_cum.cummax()) * 100
    spy_dd = ((spy_cum - spy_cum.cummax()) / spy_cum.cummax()) * 100
    m['port_dd'] = port_dd
    m['spy_dd'] = spy_dd
    m['port_max_dd'] = port_dd.min()
    m['spy_max_dd'] = spy_dd.min()

    # Value at Risk
    m['port_var95'] = np.percentile(aligned['Portfolio'], 5)
    m['port_var99'] = np.percentile(aligned['Portfolio'], 1)
    m['spy_var95'] = np.percentile(aligned['SPY'], 5)
    m['spy_var99'] = np.percentile(aligned['SPY'], 1)
    m['port_cvar95'] = aligned['Portfolio'][aligned['Portfolio'] <= m['port_var95']].mean()
    m['spy_cvar95'] = aligned['SPY'][aligned['SPY'] <= m['spy_var95']].mean()

    # Best / worst day
    m['port_best'] = aligned['Portfolio'].max() * 100
    m['port_worst'] = aligned['Portfolio'].min() * 100
    m['spy_best'] = aligned['SPY'].max() * 100
    m['spy_worst'] = aligned['SPY'].min() * 100

    # Rolling volatility (30-day)
    m['port_roll_vol'] = aligned['Portfolio'].rolling(30).std() * np.sqrt(252) * 100
    m['spy_roll_vol'] = aligned['SPY'].rolling(30).std() * np.sqrt(252) * 100

    # Rolling Sharpe (60-day)
    m['port_roll_sharpe'] = aligned['Portfolio'].rolling(60).apply(
        lambda x: (x.mean() - rf_daily) / x.std() * np.sqrt(252) if x.std() > 0 else 0,
        raw=False,
    )
    m['spy_roll_sharpe'] = aligned['SPY'].rolling(60).apply(
        lambda x: (x.mean() - rf_daily) / x.std() * np.sqrt(252) if x.std() > 0 else 0,
        raw=False,
    )

    # Rolling beta and correlation (60-day)
    rolling_cov = aligned['Portfolio'].rolling(60).cov(aligned['SPY'])
    rolling_var = aligned['SPY'].rolling(60).var()
    m['rolling_beta'] = rolling_cov / rolling_var
    m['rolling_corr'] = aligned['Portfolio'].rolling(60).corr(aligned['SPY'])

    # Store aligned and returns for later use
    m['aligned'] = aligned
    m['returns'] = returns

    # Individual stock metrics
    m['ind_vol'] = returns[valid_tickers].std() * np.sqrt(252) * 100
    m['ind_ret'] = returns[valid_tickers].mean() * 252 * 100
    ind_sharpe = {}
    for t in valid_tickers:
        s = returns[t].std()
        ind_sharpe[t] = ((returns[t].mean() - rf_daily) / s) * np.sqrt(252) if s > 0 else 0
    m['ind_sharpe'] = pd.Series(ind_sharpe)

    return m

def render_risk_reward_scatter(holdings):
    """Render a Risk vs Reward scatter plot comparing portfolio against major indices."""
    st.markdown("---")
    st.subheader("📊 Risk vs. Reward Analysis")
    st.caption("Compares your portfolio's risk-adjusted performance against major benchmarks")

    total_value = sum(h['value'] for h in holdings.values())
    if total_value <= 0:
        st.warning("No holdings to analyze.")
        return

    # ── Time period selector ─────────────────────────────────────────────
    period_col1, period_col2 = st.columns([1, 3])
    with period_col1:
        period_choice = st.selectbox(
            "Time Period",
            ["1 Year", "3 Years", "5 Years"],
            index=0,
            key="risk_reward_period",
        )

    period_days = {"1 Year": 365, "3 Years": 365 * 3, "5 Years": 365 * 5}
    selected_days = period_days[period_choice]

    weights = {}
    for ticker, info in holdings.items():
        if info.get('type') == 'Cash':
            continue
        weights[ticker] = info['value'] / total_value

    benchmarks = {
        '^GSPC': 'S&P 500',
        '^IXIC': 'NASDAQ Composite',
        '^DJI': 'Dow Jones',
        '^RUT': 'Russell 2000',
        'VT': 'Total World (VT)',
        'AGG': 'US Agg Bond (AGG)',
        'QQQ': 'NASDAQ 100 (QQQ)',
        'VWO': 'Emerging Markets (VWO)',
        'GLD': 'Gold (GLD)',
        'VNQ': 'Real Estate (VNQ)',
        'TLT': '20+ Year Treasury (TLT)',
        'BTC-USD': 'Bitcoin',
    }

    end_date = datetime.now()
    start_date = end_date - timedelta(days=selected_days)

    @st.cache_data(ttl=3600, show_spinner=False)
    def get_scatter_returns(tickers_list, start, end):
        try:
            data = yf.download(
                tickers_list,
                start=start,
                end=end,
                progress=False,
                auto_adjust=True,
            )
            if isinstance(data.columns, pd.MultiIndex):
                if 'Close' in data.columns.get_level_values(0):
                    closes = data['Close']
                else:
                    closes = data.droplevel(0, axis=1)
            else:
                if len(tickers_list) == 1:
                    closes = data[['Close']]
                    closes.columns = [tickers_list[0]]
                else:
                    closes = data
            returns = closes.pct_change().dropna()
            return returns
        except Exception as e:
            st.warning(f"Error downloading data: {e}")
            return pd.DataFrame()

    ticker_remap = {'BRKB': 'BRK-B', 'BRK.B': 'BRK-B'}
    portfolio_tickers = []
    ticker_weight_map = {}
    for ticker, w in weights.items():
        yahoo_ticker = ticker_remap.get(ticker, ticker)
        portfolio_tickers.append(yahoo_ticker)
        ticker_weight_map[yahoo_ticker] = w

    benchmark_tickers = list(benchmarks.keys())
    all_tickers = list(set(portfolio_tickers + benchmark_tickers))

    with st.spinner(f"Downloading {period_choice.lower()} market data for risk analysis..."):
        returns_df = get_scatter_returns(all_tickers, start_date, end_date)

    if returns_df.empty:
        st.warning("Could not download market data for risk analysis.")
        return

    returns_df.columns = [str(c).strip() for c in returns_df.columns]

    portfolio_daily_returns = pd.Series(0.0, index=returns_df.index)
    total_matched_weight = 0

    for yahoo_ticker, w in ticker_weight_map.items():
        if yahoo_ticker in returns_df.columns:
            portfolio_daily_returns += returns_df[yahoo_ticker].fillna(0) * w
            total_matched_weight += w

    if total_matched_weight > 0 and total_matched_weight < 0.99:
        portfolio_daily_returns = portfolio_daily_returns / total_matched_weight

    trading_days = 252

    def calc_metrics_scatter(daily_returns_series):
        if daily_returns_series.empty or daily_returns_series.std() == 0:
            return None, None
        ann_return = daily_returns_series.mean() * trading_days * 100
        ann_vol = daily_returns_series.std() * (trading_days ** 0.5) * 100
        return round(ann_return, 2), round(ann_vol, 2)

    scatter_data = []

    p_ret, p_vol = calc_metrics_scatter(portfolio_daily_returns)
    if p_ret is not None:
        scatter_data.append({
            'Name': '⭐ Your Portfolio',
            'Annualized Return (%)': p_ret,
            'Annualized Volatility (%)': p_vol,
            'Sharpe Ratio': round(p_ret / p_vol, 2) if p_vol > 0 else 0,
            'Category': 'Your Portfolio',
        })

    for bench_ticker, bench_name in benchmarks.items():
        col_name = str(bench_ticker).strip()
        if col_name in returns_df.columns:
            b_ret, b_vol = calc_metrics_scatter(returns_df[col_name].dropna())
            if b_ret is not None:
                category = 'Equity Index'
                if bench_ticker in ('AGG', 'TLT'):
                    category = 'Fixed Income'
                elif bench_ticker == 'GLD':
                    category = 'Commodity'
                elif bench_ticker == 'VNQ':
                    category = 'Real Estate'
                elif bench_ticker == 'BTC-USD':
                    category = 'Crypto'
                elif bench_ticker in ('VWO', 'VT'):
                    category = 'International'

                scatter_data.append({
                    'Name': bench_name,
                    'Annualized Return (%)': b_ret,
                    'Annualized Volatility (%)': b_vol,
                    'Sharpe Ratio': round(b_ret / b_vol, 2) if b_vol > 0 else 0,
                    'Category': category,
                })

    if not scatter_data:
        st.warning("Could not compute risk/reward metrics.")
        return

    scatter_df = pd.DataFrame(scatter_data)

    color_map = {
        'Your Portfolio': '#FF4B4B',
        'Equity Index': '#636EFA',
        'Fixed Income': '#00CC96',
        'Commodity': '#FFA500',
        'Real Estate': '#AB63FA',
        'Crypto': '#EF553B',
        'International': '#19D3F3',
    }

    fig = px.scatter(
        scatter_df,
        x='Annualized Volatility (%)',
        y='Annualized Return (%)',
        color='Category',
        color_discrete_map=color_map,
        hover_name='Name',
        hover_data={
            'Annualized Return (%)': ':.2f',
            'Annualized Volatility (%)': ':.2f',
            'Sharpe Ratio': ':.2f',
            'Category': False,
        },
    )

    for trace in fig.data:
        if trace.name == 'Your Portfolio':
            trace.marker.size = 20
            trace.marker.symbol = 'star'
            trace.marker.line = dict(width=2, color='white')
        else:
            trace.marker.size = 12
            trace.marker.line = dict(width=1, color='white')

    for _, row in scatter_df.iterrows():
        fig.add_annotation(
            x=row['Annualized Volatility (%)'],
            y=row['Annualized Return (%)'],
            text=row['Name'],
            showarrow=False,
            yshift=15,
            font=dict(size=10),
        )

    sp500_row = scatter_df[scatter_df['Name'] == 'S&P 500']
    if not sp500_row.empty:
        sp_ret = sp500_row.iloc[0]['Annualized Return (%)']
        sp_vol = sp500_row.iloc[0]['Annualized Volatility (%)']

        fig.add_hline(
            y=sp_ret, line_dash="dot", line_color="gray", opacity=0.5,
            annotation_text="S&P 500 Return", annotation_position="top left",
        )
        fig.add_vline(
            x=sp_vol, line_dash="dot", line_color="gray", opacity=0.5,
            annotation_text="S&P 500 Risk", annotation_position="top right",
        )

        x_range = scatter_df['Annualized Volatility (%)']
        y_range = scatter_df['Annualized Return (%)']
        x_min = x_range.min() - 3
        x_max = x_range.max() + 3
        y_min = y_range.min() - 3
        y_max = y_range.max() + 3

        # ── Quadrant background shading ──────────────────────────────────
        # Top-left: lower risk, higher return → light green
        fig.add_shape(
            type="rect",
            x0=x_min, x1=sp_vol, y0=sp_ret, y1=y_max,
            fillcolor="rgba(39, 174, 96, 0.08)",
            line=dict(width=0),
            layer="below",
        )
        # Top-right: higher risk, higher return → light yellow
        fig.add_shape(
            type="rect",
            x0=sp_vol, x1=x_max, y0=sp_ret, y1=y_max,
            fillcolor="rgba(241, 196, 15, 0.08)",
            line=dict(width=0),
            layer="below",
        )
        # Bottom-left: lower risk, lower return → light yellow
        fig.add_shape(
            type="rect",
            x0=x_min, x1=sp_vol, y0=y_min, y1=sp_ret,
            fillcolor="rgba(241, 196, 15, 0.08)",
            line=dict(width=0),
            layer="below",
        )
        # Bottom-right: higher risk, lower return → light red
        fig.add_shape(
            type="rect",
            x0=sp_vol, x1=x_max, y0=y_min, y1=sp_ret,
            fillcolor="rgba(192, 57, 43, 0.08)",
            line=dict(width=0),
            layer="below",
        )

        quadrant_labels = [
            ((sp_vol + x_min) / 2, (sp_ret + y_max) / 2, "✅ Lower Risk\nHigher Return", "green"),
            ((sp_vol + x_max) / 2, (sp_ret + y_max) / 2, "⚠️ Higher Risk\nHigher Return", "orange"),
            ((sp_vol + x_min) / 2, (sp_ret + y_min) / 2, "⚠️ Lower Risk\nLower Return", "orange"),
            ((sp_vol + x_max) / 2, (sp_ret + y_min) / 2, "❌ Higher Risk\nLower Return", "red"),
        ]

        for qx, qy, label, color in quadrant_labels:
            fig.add_annotation(
                x=qx, y=qy, text=label, showarrow=False,
                font=dict(size=11, color=color), opacity=0.4,
            )

    fig.update_layout(
        title=f"Risk vs. Reward: Your Portfolio vs. Major Benchmarks ({period_choice})",
        xaxis_title="Annualized Volatility (Risk) %",
        yaxis_title="Annualized Return %",
        height=600,
        template="plotly_white",
        legend=dict(
            orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5,
        ),
    )

    st.plotly_chart(fig, use_container_width=True)

    st.subheader("📋 Comparison Metrics")

    display_df = scatter_df[['Name', 'Annualized Return (%)', 'Annualized Volatility (%)', 'Sharpe Ratio']].copy()
    display_df = display_df.sort_values('Sharpe Ratio', ascending=False).reset_index(drop=True)

    def highlight_portfolio(row):
        if '⭐' in str(row['Name']):
            return ['background-color: #fff3cd; font-weight: bold'] * len(row)
        return [''] * len(row)

    styled = display_df.style.apply(highlight_portfolio, axis=1).format({
        'Annualized Return (%)': '{:.2f}%',
        'Annualized Volatility (%)': '{:.2f}%',
        'Sharpe Ratio': '{:.2f}',
    })

    st.dataframe(styled, use_container_width=True, hide_index=True)

    if p_ret is not None and not sp500_row.empty:
        sp_ret = sp500_row.iloc[0]['Annualized Return (%)']
        sp_vol = sp500_row.iloc[0]['Annualized Volatility (%)']
        p_sharpe = p_ret / p_vol if p_vol > 0 else 0
        sp_sharpe = sp_ret / sp_vol if sp_vol > 0 else 0

        if p_ret > sp_ret and p_vol < sp_vol:
            verdict = "🟢 **Excellent** — Your portfolio has higher returns with lower risk than the S&P 500."
        elif p_ret > sp_ret and p_vol >= sp_vol:
            verdict = "🟡 **Good returns, but riskier** — You're outperforming the S&P 500 but taking on more volatility."
        elif p_ret <= sp_ret and p_vol < sp_vol:
            verdict = "🟡 **Conservative** — Lower risk than the S&P 500, but also lower returns."
        else:
            verdict = "🔴 **Underperforming** — Lower returns with higher risk than the S&P 500. Consider rebalancing."

        st.markdown(f"**Portfolio Assessment ({period_choice}):** {verdict}")
        st.markdown(
            f"Your Sharpe Ratio ({p_sharpe:.2f}) vs S&P 500 ({sp_sharpe:.2f}) — "
            f"{'higher is better, and yours is ahead!' if p_sharpe > sp_sharpe else 'the S&P 500 currently has better risk-adjusted returns.'}"
        )
# ══════════════════════════════════════════════════════════════════════════════
#  SIDEBAR — DATA INPUT
# ══════════════════════════════════════════════════════════════════════════════

with st.sidebar:
    st.title("📊 Portfolio Dashboard")
    st.markdown("---")

    input_method = st.radio(
        "How would you like to enter your portfolio?",
        ["📄 Upload PDF Statement", "✏️ Enter Manually"],
    )

    # ── PDF Upload ───────────────────────────────────────────────────────────
    if input_method == "📄 Upload PDF Statement":
        uploaded_file = st.file_uploader(
            "Upload your brokerage statement",
            type=['pdf'],
            help="Supports Fidelity, Schwab, Vanguard, E*Trade, Merrill, and more.",
        )

        if uploaded_file and st.button("🔍 Parse PDF", use_container_width=True):
            with st.spinner("Reading PDF and validating tickers..."):
                holdings, raw_text, raw_tables = parse_pdf(uploaded_file.read())

            if holdings:
                st.session_state.holdings = holdings
                st.success(f"Found {len(holdings)} holdings!")
            else:
                st.warning("Could not auto-parse holdings. Please enter manually.")

            # ── DEBUG: Always show raw PDF content ───────────────
            with st.expander("🔍 DEBUG: Raw PDF Text", expanded=True):
                st.text(raw_text[:10000])

            with st.expander("🔍 DEBUG: Raw PDF Tables"):
                for i, table in enumerate(raw_tables):
                    st.markdown(f"**Table {i+1}:**")
                    for row in table[:10]:
                        st.text(str(row))
                    st.markdown("---")

    # ── Manual Entry ─────────────────────────────────────────────────────────
    if input_method == "✏️ Enter Manually":
        st.markdown("#### Add Holdings")

        with st.form("add_holding"):
            col1, col2 = st.columns(2)
            with col1:
                new_ticker = st.text_input("Ticker", placeholder="AAPL").upper().strip()
            with col2:
                new_value = st.number_input("Current Value ($)", min_value=0.0, step=100.0)

            new_cost = st.number_input("Cost Basis ($)", min_value=0.0, step=100.0)
            submitted = st.form_submit_button("➕ Add", use_container_width=True)

            if submitted and new_ticker and new_value > 0:
                info = lookup_ticker(new_ticker)
                st.session_state.holdings[new_ticker] = {
                    'value': round(new_value, 2),
                    'cost': round(new_cost if new_cost > 0 else new_value, 2),
                    'type': info.get('type', 'Stock') if info.get('valid') else 'Stock',
                    'name': info.get('name', new_ticker) if info.get('valid') else new_ticker,
                    'sector': info.get('sector', 'Other') if info.get('valid') else 'Other',
                }
                if info.get('valid'):
                    st.success(f"Added {new_ticker} — {info['name']}")
                else:
                    st.warning(f"Added {new_ticker} (not found on Yahoo)")

    # ── Show current holdings ────────────────────────────────────────────────
    if st.session_state.holdings:
        st.markdown("---")
        st.markdown("#### Current Holdings")

        to_delete = None
        for ticker in sorted(st.session_state.holdings.keys()):
            h = st.session_state.holdings[ticker]
            gl = h['value'] - h['cost']
            icon = "🟢" if gl >= 0 else "🔴"
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"{icon} **{ticker}** — ${h['value']:,.2f}")
            with col2:
                if st.button("❌", key=f"del_{ticker}"):
                    to_delete = ticker

        if to_delete:
            del st.session_state.holdings[to_delete]
            st.rerun()

        total_v = sum(h['value'] for h in st.session_state.holdings.values())
        st.markdown(
            f"**Total: ${total_v:,.2f}** ({len(st.session_state.holdings)} positions)"
        )

        st.markdown("---")
        if st.button("🚀 Generate Dashboards", use_container_width=True, type="primary"):
            st.session_state.dashboards_ready = True
            st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN AREA — DASHBOARDS
# ══════════════════════════════════════════════════════════════════════════════

if not st.session_state.holdings:
    # ── Welcome screen ───────────────────────────────────────────────────────
    st.title("📊 Portfolio Risk Dashboard")
    st.markdown(
        """
        ### Welcome!

        Upload your brokerage statement PDF or enter your holdings manually
        using the sidebar on the left.

        **Supported brokerages:** Fidelity, Schwab, Vanguard, E*Trade,
        Merrill Lynch, Morgan Stanley, TD Ameritrade, Interactive Brokers,
        Robinhood, JPMorgan, and more.

        **What you'll get:**
        - Portfolio vs S&P 500 performance comparison
        - Sector allocation breakdown
        - Risk metrics (Sharpe, Sortino, Beta, VaR, drawdowns)
        - Individual stock analysis
        - Interactive downloadable charts
        """
    )

elif st.session_state.dashboards_ready:
    holdings = st.session_state.holdings
    total_value = sum(h['value'] for h in holdings.values())
    total_cost = sum(h['cost'] for h in holdings.values())
    total_gl = total_value - total_cost
    total_gl_pct = (total_gl / total_cost) * 100 if total_cost > 0 else 0

    # ── Sector allocation ────────────────────────────────────────────────────
    sector_values = {}
    for t, h in holdings.items():
        s = h.get('sector', 'Other')
        if h.get('type') == 'Cash':
            s = 'Cash'
        elif h.get('type') == 'Crypto':
            s = 'Crypto'
        sector_values[s] = sector_values.get(s, 0) + h['value']

    # ── Download prices ──────────────────────────────────────────────────────
    stock_tickers = [
        t for t, h in holdings.items()
        if h.get('type') not in ('Cash',) and t not in {'SPAXX', 'FDRXX', 'SWVXX', 'VMFXX', 'FCASH', 'SPRXX'}
    ]

    # Fix known ticker symbol mismatches
    ticker_remap = {
        'BRKB': 'BRK-B',
        'BRK.B': 'BRK-B',
    }

    # Remap holdings keys if needed
    for old_key, new_key in ticker_remap.items():
        if old_key in holdings and new_key not in holdings:
            holdings[new_key] = holdings.pop(old_key)

    stock_tickers = [
        t for t, h in holdings.items()
        if h.get('type') not in ('Cash',)
    ]

    close = download_prices(tuple(sorted(stock_tickers)))
    spy_alltime_close = download_spy_alltime()

    # Handle MultiIndex columns from yf.download
    if isinstance(close.columns, pd.MultiIndex):
        close = close.droplevel(0, axis=1) if close.columns.nlevels > 1 else close

    # Flatten column names
    close.columns = [str(c).strip() for c in close.columns]

    valid_tickers = [
        t for t in stock_tickers
        if t in close.columns and close[t].notna().sum() > 20
    ]

    # Debug info if things go wrong
    if not valid_tickers:
        st.error("No valid price data found.")
        with st.expander("🔍 Debug Info"):
            st.write("**Stock tickers sent to Yahoo:**", stock_tickers)
            st.write("**Columns returned:**", list(close.columns))
            st.write("**DataFrame shape:**", close.shape)
            st.write("**First few rows:**")
            st.dataframe(close.head())
        st.stop()

    # Show how many tickers matched
    missing = [t for t in stock_tickers if t not in valid_tickers]
    if missing:
        st.warning(f"Could not get price data for: {', '.join(missing)}")

    # ── Calculate metrics ────────────────────────────────────────────────────
    m = calculate_metrics(holdings, close, valid_tickers, total_value)

    if m is None:
        st.error("Not enough data to calculate metrics. Try different tickers.")
        st.stop()

    # ── Header metrics ───────────────────────────────────────────────────────
    st.title("📊 Portfolio Risk Dashboard")

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Total Value", f"${total_value:,.2f}")
    col2.metric("Gain/Loss", f"${total_gl:,.2f}", f"{total_gl_pct:+.1f}%")
    col3.metric("Positions", f"{len(holdings)}")
    col4.metric("Tracked", f"{len(valid_tickers)}/{len(stock_tickers)}")
    col5.metric("Sharpe", f"{m['port_sharpe']:.2f}")

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Ann. Return", f"{m['port_ret_ann']:.1f}%")
    col2.metric("Volatility", f"{m['port_vol_ann']:.1f}%")
    col3.metric("Beta", f"{m['beta']:.2f}")
    col4.metric("Sortino", f"{m['port_sortino']:.2f}")
    col5.metric("Max Drawdown", f"{m['port_max_dd']:.1f}%")

    st.markdown("---")

    # ── Color palette ────────────────────────────────────────────────────────
    colors = {
        'port': '#1B4F8A',
        'spy': '#E8A020',
        'danger': '#C0392B',
        'success': '#27AE60',
        'purple': '#8E44AD',
        'neutral': '#7F8C8D',
    }

    # ══════════════════════════════════════════════════════════════════════════
    #  TABS
    # ══════════════════════════════════════════════════════════════════════════
    tab1, tab2, tab3, tab4 = st.tabs([
        "📈 Overview",
        "⚠️ Risk Deep Dive",
        "📅 Historical Overlay",
        "📋 Scorecard",
    ])

    # ══════════════════════════════════════════════════════════════════════════
    #  TAB 1: OVERVIEW
    # ══════════════════════════════════════════════════════════════════════════
    with tab1:
        c1, c2 = st.columns([2, 1])

        with c1:
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=m['port_cum'].index,
                y=(m['port_cum'] - 1) * 100,
                name='Portfolio',
                line=dict(color=colors['port'], width=2.5),
                fill='tozeroy',
                fillcolor='rgba(27,79,138,0.08)',
            ))
            fig.add_trace(go.Scatter(
                x=m['spy_cum'].index,
                y=(m['spy_cum'] - 1) * 100,
                name='S&P 500',
                line=dict(color=colors['spy'], width=2, dash='dash'),
            ))
            fig.update_layout(
                title='Cumulative Return (%)',
                height=400,
                plot_bgcolor='#F8F9FA',
                hovermode='x unified',
            )
            st.plotly_chart(fig, use_container_width=True)

        with c2:
            fig = go.Figure(go.Pie(
                labels=list(sector_values.keys()),
                values=list(sector_values.values()),
                hole=0.45,
                textinfo='label+percent',
                textfont_size=10,
            ))
            fig.update_layout(
                title='Sector Allocation',
                height=400,
                showlegend=False,
            )
            st.plotly_chart(fig, use_container_width=True)

        # ── Drawdown + Distribution ──────────────────────────────────────────
        c1, c2 = st.columns(2)

        with c1:
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=m['port_dd'].index,
                y=m['port_dd'].values,
                name='Portfolio',
                line=dict(color=colors['port'], width=1.5),
                fill='tozeroy',
                fillcolor='rgba(27,79,138,0.10)',
            ))
            fig.add_trace(go.Scatter(
                x=m['spy_dd'].index,
                y=m['spy_dd'].values,
                name='S&P 500',
                line=dict(color=colors['spy'], width=1.5, dash='dash'),
                fill='tozeroy',
                fillcolor='rgba(232,160,32,0.10)',
            ))
            fig.update_layout(
                title='Drawdown (%)',
                height=350,
                plot_bgcolor='#F8F9FA',
                hovermode='x unified',
            )
            st.plotly_chart(fig, use_container_width=True)

        with c2:
            fig = go.Figure()
            fig.add_trace(go.Histogram(
                x=m['aligned']['Portfolio'] * 100,
                nbinsx=60,
                marker_color=colors['port'],
                opacity=0.65,
                name='Portfolio',
            ))
            fig.add_trace(go.Histogram(
                x=m['aligned']['SPY'] * 100,
                nbinsx=60,
                marker_color=colors['spy'],
                opacity=0.5,
                name='S&P 500',
            ))
            fig.update_layout(
                title='Daily Return Distribution (%)',
                height=350,
                barmode='overlay',
                plot_bgcolor='#F8F9FA',
            )
            st.plotly_chart(fig, use_container_width=True)

        # ── Top holdings bar chart ───────────────────────────────────────────
        top15 = sorted(
            holdings.items(),
            key=lambda x: x[1]['value'],
            reverse=True,
        )[:15]
        top_t = [t for t, _ in top15]
        top_v = [h['value'] for _, h in top15]
        top_c = [
            colors['success'] if h['value'] >= h['cost'] else colors['danger']
            for _, h in top15
        ]

        fig = go.Figure(go.Bar(
            x=top_t,
            y=top_v,
            marker_color=top_c,
            text=[f'${v:,.0f}' for v in top_v],
            textposition='outside',
        ))
        fig.update_layout(
            title='Top 15 Holdings by Value',
            height=350,
            plot_bgcolor='#F8F9FA',
            yaxis_tickformat='$,.0f',
        )
        st.plotly_chart(fig, use_container_width=True)

    # ══════════════════════════════════════════════════════════════════════════
    #  TAB 2: RISK DEEP DIVE
    # ══════════════════════════════════════════════════════════════════════════
    with tab2:
        c1, c2 = st.columns(2)

        # Rolling Sharpe
        with c1:
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=m['port_roll_sharpe'].index,
                y=m['port_roll_sharpe'].values,
                name='Portfolio',
                line=dict(color=colors['port'], width=2),
            ))
            fig.add_trace(go.Scatter(
                x=m['spy_roll_sharpe'].index,
                y=m['spy_roll_sharpe'].values,
                name='S&P 500',
                line=dict(color=colors['spy'], width=2, dash='dash'),
            ))
            fig.add_hline(y=0, line=dict(color='black', width=0.8, dash='dot'))
            fig.update_layout(
                title='Rolling 60-Day Sharpe Ratio',
                height=350,
                plot_bgcolor='#F8F9FA',
                hovermode='x unified',
            )
            st.plotly_chart(fig, use_container_width=True)

        # Rolling Beta
        with c2:
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=m['rolling_beta'].index,
                y=m['rolling_beta'].values,
                name='Rolling Beta',
                line=dict(color=colors['purple'], width=2),
                fill='tozeroy',
                fillcolor='rgba(142,68,173,0.06)',
            ))
            fig.add_hline(
                y=1,
                line=dict(color=colors['danger'], width=1.5, dash='dash'),
                annotation_text="β = 1",
            )
            fig.update_layout(
                title='Rolling 60-Day Beta',
                height=350,
                plot_bgcolor='#F8F9FA',
                hovermode='x unified',
            )
            st.plotly_chart(fig, use_container_width=True)

        c1, c2 = st.columns(2)

        # Rolling Correlation
        with c1:
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=m['rolling_corr'].index,
                y=m['rolling_corr'].values,
                name='Correlation',
                line=dict(color=colors['success'], width=2),
                fill='tozeroy',
                fillcolor='rgba(39,174,96,0.08)',
            ))
            fig.update_layout(
                title='Rolling 60-Day Correlation to SPY',
                height=350,
                plot_bgcolor='#F8F9FA',
                hovermode='x unified',
            )
            st.plotly_chart(fig, use_container_width=True)

        # Rolling Volatility
        with c2:
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=m['port_roll_vol'].index,
                y=m['port_roll_vol'].values,
                name='Portfolio',
                line=dict(color=colors['port'], width=2),
            ))
            fig.add_trace(go.Scatter(
                x=m['spy_roll_vol'].index,
                y=m['spy_roll_vol'].values,
                name='S&P 500',
                line=dict(color=colors['spy'], width=2, dash='dash'),
            ))
            fig.update_layout(
                title='Rolling 30-Day Volatility (%)',
                height=350,
                plot_bgcolor='#F8F9FA',
                hovermode='x unified',
            )
            st.plotly_chart(fig, use_container_width=True)

        # ── Individual stock volatility + sharpe ─────────────────────────────
        c1, c2 = st.columns(2)

        with c1:
            top20_vol = m['ind_vol'].sort_values(ascending=False)[:20]
            vol_colors = [
                colors['danger'] if v > m['port_vol_ann'] else colors['port']
                for v in top20_vol.values
            ]
            fig = go.Figure(go.Bar(
                x=top20_vol.index.tolist(),
                y=top20_vol.values,
                marker_color=vol_colors,
                text=[f'{v:.0f}%' for v in top20_vol.values],
                textposition='outside',
            ))
            fig.add_hline(
                y=m['port_vol_ann'],
                line=dict(color=colors['spy'], width=2, dash='dash'),
                annotation_text="Portfolio Avg",
            )
            fig.update_layout(
                title='Individual Stock Volatility (Top 20)',
                height=400,
                plot_bgcolor='#F8F9FA',
            )
            st.plotly_chart(fig, use_container_width=True)

        with c2:
            top20_sharpe = m['ind_sharpe'].sort_values(ascending=False)[:20]
            sharpe_colors = [
                colors['success'] if v > 0 else colors['danger']
                for v in top20_sharpe.values
            ]
            fig = go.Figure(go.Bar(
                x=top20_sharpe.index.tolist(),
                y=top20_sharpe.values,
                marker_color=sharpe_colors,
                text=[f'{v:.2f}' for v in top20_sharpe.values],
                textposition='outside',
            ))
            fig.add_hline(y=0, line=dict(color='black', width=0.8))
            fig.update_layout(
                title='Individual Stock Sharpe Ratio (Top 20)',
                height=400,
                plot_bgcolor='#F8F9FA',
            )
            st.plotly_chart(fig, use_container_width=True)

        # ── Value at Risk ────────────────────────────────────────────────────
        dollar_var95 = abs(m['port_var95']) * total_value
        dollar_var99 = abs(m['port_var99']) * total_value
        dollar_cvar = abs(m['port_cvar95']) * total_value

        var_labels = [
            '1-Day 95% VaR',
            '1-Day 99% VaR',
            '1-Day 95% CVaR',
            '1-Week 95% VaR',
            '1-Month 95% VaR',
        ]
        var_values = [
            dollar_var95,
            dollar_var99,
            dollar_cvar,
            dollar_var95 * np.sqrt(5),
            dollar_var95 * np.sqrt(21),
        ]

        fig = go.Figure(go.Bar(
            x=var_labels,
            y=var_values,
            marker_color=[
                colors['spy'],
                colors['danger'],
                colors['purple'],
                colors['port'],
                colors['neutral'],
            ],
            text=[f'${v:,.2f}' for v in var_values],
            textposition='outside',
        ))
        fig.update_layout(
            title='Dollar Value at Risk',
            height=400,
            plot_bgcolor='#F8F9FA',
            yaxis_title='Potential Loss ($)',
            yaxis_tickformat='$,.0f',
        )
        st.plotly_chart(fig, use_container_width=True)

    # ══════════════════════════════════════════════════════════════════════════
    #  TAB 3: HISTORICAL OVERLAY
    # ══════════════════════════════════════════════════════════════════════════
    with tab3:
        portfolio_value_ts = m['port_cum'] * total_value / m['port_cum'].iloc[0]

        spy_overlap = spy_alltime_close[
            spy_alltime_close.index >= portfolio_value_ts.index[0]
        ]
        spy_normalized = (
            spy_overlap / spy_overlap.iloc[0] * portfolio_value_ts.iloc[0]
        )

        port_return_total = (
            (portfolio_value_ts.iloc[-1] / portfolio_value_ts.iloc[0] - 1) * 100
        )
        spy_return_total = (
            (spy_normalized.iloc[-1] / spy_normalized.iloc[0] - 1) * 100
        )
        alpha_total = port_return_total - spy_return_total

        # Summary metrics row
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Portfolio Return", f"{port_return_total:+.1f}%")
        c2.metric("S&P 500 Return", f"{spy_return_total:+.1f}%")
        c3.metric(
            "Alpha",
            f"{alpha_total:+.1f}%",
            delta_color="normal" if alpha_total >= 0 else "inverse",
        )
        c4.metric("If You Held SPY", f"${spy_normalized.iloc[-1]:,.2f}")

        fig = make_subplots(specs=[[{"secondary_y": True}]])

        # SPY all-time faded background
        fig.add_trace(
            go.Scatter(
                x=spy_alltime_close.index,
                y=spy_alltime_close.values,
                mode='lines',
                name='S&P 500 (All Time)',
                line=dict(color='#B0B0B0', width=1),
                opacity=0.3,
            ),
            secondary_y=True,
        )

        # Portfolio value
        fig.add_trace(
            go.Scatter(
                x=portfolio_value_ts.index,
                y=portfolio_value_ts.values,
                mode='lines',
                name='Portfolio Value',
                line=dict(color=colors['port'], width=2.5),
                fill='tozeroy',
                fillcolor='rgba(27,79,138,0.06)',
            ),
            secondary_y=False,
        )

        # SPY normalized
        fig.add_trace(
            go.Scatter(
                x=spy_normalized.index,
                y=spy_normalized.values,
                mode='lines',
                name='S&P 500 (Normalized)',
                line=dict(color=colors['spy'], width=2, dash='dash'),
            ),
            secondary_y=False,
        )

        fig.update_layout(
            title='Portfolio vs S&P 500 — Historical Overlay',
            height=550,
            plot_bgcolor='#F8F9FA',
            hovermode='x unified',
            legend=dict(orientation='h', y=-0.1, x=0.25),
        )
        fig.update_yaxes(
            title_text='Portfolio Value ($)',
            tickformat='$,.0f',
            secondary_y=False,
        )
        fig.update_yaxes(
            title_text='S&P 500 Price ($)',
            tickformat='$,.0f',
            showgrid=False,
            secondary_y=True,
        )

        st.plotly_chart(fig, use_container_width=True)

        # Outperformance message
        if alpha_total > 0:
            st.success(
                f"✅ Portfolio OUTPERFORMED S&P 500 by {alpha_total:.1f}%"
            )
        else:
            st.error(
                f"🔴 Portfolio UNDERPERFORMED S&P 500 by {abs(alpha_total):.1f}%"
            )

    # ══════════════════════════════════════════════════════════════════════════
    #  TAB 4: SCORECARD
    # ══════════════════════════════════════════════════════════════════════════
    with tab4:
        metrics_list = [
            'Ann. Return',
            'Ann. Volatility',
            'Sharpe Ratio',
            'Sortino Ratio',
            'Beta',
            'Max Drawdown',
            'Best Day',
            'Worst Day',
            '95% VaR',
            '99% VaR',
            '95% CVaR',
            'Correlation',
        ]

        port_vals = [
            f"{m['port_ret_ann']:.1f}%",
            f"{m['port_vol_ann']:.1f}%",
            f"{m['port_sharpe']:.2f}",
            f"{m['port_sortino']:.2f}",
            f"{m['beta']:.2f}",
            f"{m['port_max_dd']:.1f}%",
            f"{m['port_best']:.2f}%",
            f"{m['port_worst']:.2f}%",
            f"{m['port_var95'] * 100:.2f}%",
            f"{m['port_var99'] * 100:.2f}%",
            f"{m['port_cvar95'] * 100:.2f}%",
            f"{m['correlation']:.2f}",
        ]

        spy_vals = [
            f"{m['spy_ret_ann']:.1f}%",
            f"{m['spy_vol_ann']:.1f}%",
            f"{m['spy_sharpe']:.2f}",
            f"{m['spy_sortino']:.2f}",
            "1.00",
            f"{m['spy_max_dd']:.1f}%",
            f"{m['spy_best']:.2f}%",
            f"{m['spy_worst']:.2f}%",
            f"{m['spy_var95'] * 100:.2f}%",
            f"{m['spy_var99'] * 100:.2f}%",
            f"{m['spy_cvar95'] * 100:.2f}%",
            "1.00",
        ]

        port_nums = [
            m['port_ret_ann'], m['port_vol_ann'], m['port_sharpe'],
            m['port_sortino'], m['beta'], m['port_max_dd'],
            m['port_best'], m['port_worst'], m['port_var95'] * 100,
            m['port_var99'] * 100, m['port_cvar95'] * 100, m['correlation'],
        ]
        spy_nums = [
            m['spy_ret_ann'], m['spy_vol_ann'], m['spy_sharpe'],
            m['spy_sortino'], 1.0, m['spy_max_dd'],
            m['spy_best'], m['spy_worst'], m['spy_var95'] * 100,
            m['spy_var99'] * 100, m['spy_cvar95'] * 100, 1.0,
        ]

        higher_better = [
            True, False, True, True, False, False,
            True, False, False, False, False, False,
        ]

        winners = []
        for pv, sv, hb in zip(port_nums, spy_nums, higher_better):
            if hb:
                winners.append("✅ Portfolio" if pv > sv else "✅ S&P 500")
            else:
                winners.append(
                    "✅ Portfolio" if abs(pv) < abs(sv) else "✅ S&P 500"
                )

        scorecard_df = pd.DataFrame({
            'Metric': metrics_list,
            'Portfolio': port_vals,
            'S&P 500': spy_vals,
            'Winner': winners,
        })

        def color_winner(row):
            if row['Winner'] == '✅ Portfolio':
                return ['background-color: #EAFAF1'] * 4
            else:
                return ['background-color: #FDEDEC'] * 4

        styled = scorecard_df.style.apply(color_winner, axis=1)
        st.dataframe(styled, use_container_width=True, hide_index=True, height=480)

        port_wins = sum(1 for w in winners if 'Portfolio' in w)
        spy_wins = len(winners) - port_wins

        if port_wins > spy_wins:
            st.success(
                f"Portfolio wins {port_wins}/{len(metrics_list)} metrics 🏆"
            )
        elif spy_wins > port_wins:
            st.warning(
                f"S&P 500 wins {spy_wins}/{len(metrics_list)} metrics"
            )
        else:
            st.info(f"Tied — {port_wins}/{len(metrics_list)} each")

        # ── Gain/Loss table ──────────────────────────────────────────────────
        st.markdown("---")
        st.markdown("#### Individual Holdings — Gain/Loss")

        gl_rows = []
        for t, h in sorted(
            holdings.items(),
            key=lambda x: x[1]['value'],
            reverse=True,
        ):
            gl = h['value'] - h['cost']
            pct = (gl / h['cost']) * 100 if h['cost'] > 0 else 0
            gl_rows.append({
                'Ticker': t,
                'Name': h.get('name', t),
                'Value': f"${h['value']:,.2f}",
                'Cost': f"${h['cost']:,.2f}",
                'Gain/Loss': f"${gl:,.2f}",
                'Return': f"{pct:+.1f}%",
                'Type': h.get('type', 'Stock'),
                'Sector': h.get('sector', 'Other'),
            })

        gl_table = pd.DataFrame(gl_rows)

        def color_gl(row):
            gl_str = row['Gain/Loss'].replace('$', '').replace(',', '')
            if gl_str.startswith('-'):
                return ['background-color: #FDEDEC'] * len(row)
            else:
                return ['background-color: #EAFAF1'] * len(row)

        styled_gl = gl_table.style.apply(color_gl, axis=1)
        st.dataframe(styled_gl, use_container_width=True, hide_index=True)

    # ══════════════════════════════════════════════════════════════════════════
    #  RISK vs REWARD SCATTER (outside tabs, below all tab content)
    # ══════════════════════════════════════════════════════════════════════════
    render_risk_reward_scatter(holdings)

    
    # ══════════════════════════════════════════════════════════════════════════
    #  FOOTER
    # ══════════════════════════════════════════════════════════════════════════
    st.markdown("---")
    st.caption(
        f"Last updated: {pd.Timestamp.now().strftime('%B %d, %Y at %I:%M %p')} | "
        f"Prices refresh every 5 minutes | "
        f"Data source: Yahoo Finance"
    )

else:
    # Holdings exist but dashboards not yet generated
    st.title("📊 Portfolio Risk Dashboard")
    st.info(
        "👈 Add your holdings in the sidebar, then click "
        "**Generate Dashboards**."
    )
