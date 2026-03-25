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

    try:
        info = yf.Ticker(ticker).info
        if not info or info.get('regularMarketPrice') is None:
            st.session_state.ticker_cache[ticker] = {'valid': False}
            return {'valid': False}

        name = info.get('shortName', info.get('longName', ticker))
        sector = info.get('sector', 'Other')
        qtype = info.get('quoteType', '').upper()

        if qtype == 'ETF':
            asset_type = 'ETF'
        elif qtype == 'MUTUALFUND':
            asset_type = 'Fund'
        elif qtype == 'CRYPTOCURRENCY':
            asset_type = 'Crypto'
        else:
            asset_type = 'Stock'

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
        sector = sector_map.get(sector, sector)

        result = {
            'valid': True,
            'name': name,
            'sector': sector,
            'type': asset_type,
        }
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
    """Parse brokerage PDF statement and extract holdings.
    Optimized for Fidelity, with fallback for other brokerages."""
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
    number_pattern = re.compile(r'-?[\d,]+\.\d{2,4}')
    paren_pattern = re.compile(r'\(([A-Z][A-Z0-9]{0,5})\)')

    # ══════════════════════════════════════════════════════════════════════
    #  STRATEGY 1: Fidelity-style — tickers in parentheses
    #  Format: COMPANY NAME (TICKER)  beg_val qty price end_val cost g/l eai
    #  Ticker can be on same line as numbers or 1-3 lines after
    # ══════════════════════════════════════════════════════════════════════

    ticker_locations = []
    for i, line in enumerate(lines):
        for match in paren_pattern.finditer(line):
            ticker = match.group(1)
            if ticker in FALSE_POSITIVES:
                continue
            if len(ticker) < 2 or len(ticker) > 5:
                continue
            if 'account' in line.lower() and 'holdings' in line.lower():
                continue
            if line.strip().lower().startswith('total '):
                continue
            ticker_locations.append((i, ticker))

    for line_idx, ticker in ticker_locations:
        search_start = max(0, line_idx - 4)
        search_end = min(len(lines), line_idx + 2)

        best_line_idx = None
        best_line_count = 0
        for si in range(search_start, search_end):
            line_text = lines[si]
            if line_text.strip().lower().startswith('total '):
                continue
            if 'Beginning' in line_text and 'Ending' in line_text:
                continue
            if 'Market Value' in line_text and 'Quantity' in line_text:
                continue
            if 'Description' in line_text and 'Cost Basis' in line_text:
                continue
            count = len(number_pattern.findall(line_text))
            if count > best_line_count:
                best_line_count = count
                best_line_idx = si

        if best_line_idx is None or best_line_count < 4:
            continue

        data_nums = []
        for si in range(best_line_idx, min(len(lines), best_line_idx + 2)):
            for n in number_pattern.findall(lines[si]):
                try:
                    val = float(n.replace(',', ''))
                    data_nums.append(val)
                except:
                    pass

        if len(data_nums) >= 5:
            beginning = data_nums[0]
            quantity = data_nums[1]
            price = data_nums[2]
            ending_value = data_nums[3]
            cost_basis = data_nums[4]

            expected = quantity * price
            if expected > 0 and abs(ending_value - expected) / expected > 0.5:
                if len(data_nums) >= 6:
                    alt_ending = data_nums[4]
                    alt_cost = data_nums[5]
                    alt_expected = data_nums[2] * data_nums[3]
                    if alt_expected > 0 and abs(alt_ending - alt_expected) / alt_expected < 0.5:
                        ending_value = alt_ending
                        cost_basis = alt_cost

            if ending_value < 0.50:
                continue
            if cost_basis <= 0:
                cost_basis = ending_value

            info = lookup_ticker(ticker)
            if info.get('valid'):
                if ticker in holdings:
                    holdings[ticker]['value'] = round(
                        holdings[ticker]['value'] + ending_value, 2
                    )
                    holdings[ticker]['cost'] = round(
                        holdings[ticker]['cost'] + cost_basis, 2
                    )
                else:
                    holdings[ticker] = {
                        'value': round(ending_value, 2),
                        'cost': round(cost_basis, 2),
                        'type': info['type'],
                        'name': info['name'],
                        'sector': info.get('sector', 'Other'),
                    }

    # Mark cash positions
    cash_tickers = {'SPAXX', 'FDRXX', 'SWVXX', 'VMFXX', 'FCASH', 'SPRXX'}
    for ticker in list(holdings.keys()):
        if ticker in cash_tickers:
            holdings[ticker]['type'] = 'Cash'
            holdings[ticker]['sector'] = 'Cash'
            holdings[ticker]['cost'] = holdings[ticker]['value']

    # ══════════════════════════════════════════════════════════════════════
    #  STRATEGY 2: Generic fallback — standalone tickers near dollar amounts
    #  Works for Schwab, Vanguard, E*Trade, Merrill, etc.
    # ══════════════════════════════════════════════════════════════════════

    if len(holdings) < 3:
        # Strategy 1 didn't find much — try generic approach
        candidates = {}

        # Scan tables first
        for table in all_tables:
            for row in table:
                if not row:
                    continue
                row_str = [str(cell).strip() if cell else '' for cell in row]
                for cell in row_str:
                    for word in cell.split():
                        w = word.upper().strip('.,;:()').replace('.', '-')
                        if is_likely_ticker(w) and w not in holdings:
                            money = [parse_money(c) for c in row_str]
                            money = [v for v in money if v is not None and abs(v) > 0.5]
                            if money:
                                if w not in candidates:
                                    candidates[w] = []
                                candidates[w].append(money)

        # Scan text lines
        for i, line in enumerate(lines):
            for word in line.split():
                w = word.upper().strip('.,;:()').replace('.', '-')
                if is_likely_ticker(w) and w not in candidates and w not in holdings:
                    context = ' '.join(lines[max(0, i):min(len(lines), i + 3)])
                    amounts = re.findall(r'\$?\s*([\d,]+\.\d{2})', context)
                    money = [parse_money(a) for a in amounts]
                    money = [v for v in money if v and abs(v) > 0.5]
                    if money:
                        candidates[w] = [money]

        # Validate via Yahoo
        progress_bar = st.progress(0, text="Validating tickers...")
        total = len(candidates)
        for idx, (ticker, money_lists) in enumerate(candidates.items()):
            progress_bar.progress(
                (idx + 1) / max(total, 1),
                text=f"Validating {ticker}...",
            )
            info = lookup_ticker(ticker)
            if not info['valid']:
                continue

            all_money = []
            for ml in money_lists:
                all_money.extend(ml)
            positives = sorted([v for v in all_money if v > 0], reverse=True)
            if not positives:
                continue

            value = positives[0]
            cost = positives[1] if len(positives) >= 2 and positives[1] > 1 else value

            holdings[ticker] = {
                'value': round(value, 2),
                'cost': round(cost, 2),
                'type': info['type'],
                'name': info['name'],
                'sector': info.get('sector', 'Other'),
            }

        progress_bar.empty()

    return holdings, full_text, all_tables
    

@st.cache_data(ttl=300, show_spinner="Downloading price data...")
def download_prices(tickers_tuple, period='1y'):
    """Download price data with caching (refreshes every 5 min)."""
    tickers = list(tickers_tuple)
    if 'SPY' not in tickers:
        tickers.append('SPY')
    prices = yf.download(tickers, period=period, auto_adjust=True, progress=False)
    if isinstance(prices.columns, pd.MultiIndex):
        close = prices['Close']
    else:
        close = prices
    return close.dropna(how='all').ffill()


@st.cache_data(ttl=3600, show_spinner="Downloading S&P 500 history...")
def download_spy_alltime():
    """Download full SPY history."""
    spy = yf.download('SPY', period='max', auto_adjust=True, progress=False)
    if isinstance(spy.columns, pd.MultiIndex):
        return spy['Close']['SPY']
    return spy['Close']


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
        if h.get('type') not in ('Cash',)
    ]

    close = download_prices(tuple(sorted(stock_tickers)))
    spy_alltime_close = download_spy_alltime()

    valid_tickers = [
        t for t in stock_tickers
        if t in close.columns and close[t].notna().sum() > 20
    ]

    if not valid_tickers:
        st.error("No valid price data found for any tickers. Please check your holdings.")
        st.stop()

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
