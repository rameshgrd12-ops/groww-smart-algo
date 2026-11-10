import json
import math
import os
import re
from datetime import datetime
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import streamlit as st


class GrowwPriceError(Exception):
    pass


class NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def fetch_groww_price(token, exchange, segment, symbol):
    exchange_symbol = f"{exchange}_{symbol}"
    params = urlencode({"segment": segment, "exchange_symbols": exchange_symbol})
    request = Request(
        f"https://api.groww.in/v1/live-data/ltp?{params}",
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {token}",
            "X-API-VERSION": "1.0",
        },
        method="GET",
    )

    try:
        with build_opener(NoRedirects).open(request, timeout=10) as response:
            data = json.load(response)
    except HTTPError as error:
        if error.code in (401, 403):
            message = "Groww denied access. Check your access token and Trading API access."
        elif error.code == 429:
            message = "Groww is limiting requests. Try again shortly."
        else:
            message = "Groww could not return a price. Check the exchange, segment and symbol."
        error.close()
        raise GrowwPriceError(message) from None
    except (URLError, OSError, ValueError):
        raise GrowwPriceError("Could not read a price from Groww. Try again shortly.") from None

    if not isinstance(data, dict) or data.get("status") != "SUCCESS":
        raise GrowwPriceError("Groww could not return a price. Check the exchange, segment and symbol.")

    payload = data.get("payload")
    price = payload.get(exchange_symbol) if isinstance(payload, dict) else None
    if type(price) not in (int, float) or not math.isfinite(price) or price <= 0:
        raise GrowwPriceError("Groww returned no usable price for this symbol.")
    return price


st.set_page_config(page_title="Groww Smart Algo", page_icon="📈", layout="wide")

LANG = st.sidebar.selectbox("Language / ಭಾಷೆ", ["English", "ಕನ್ನಡ"])
KN = LANG == "ಕನ್ನಡ"
def t(en, kn): return kn if KN else en

st.title("📈 Groww Smart Algo – Advanced Dashboard")
st.caption(t("NSE + BSE | Signals + paper trading | Manual approval workflow", "NSE + BSE | ಸಿಗ್ನಲ್‌ಗಳು + ಪೇಪರ್ ಟ್ರೇಡಿಂಗ್ | ಕೈಯಾರೆ ಅನುಮೋದನೆ"))
st.warning(t("Groww prices are read-only. The signal scanner uses uploaded candles and approvals are for paper review only.", "Groww ಬೆಲೆಗಳನ್ನು ನೋಡಬಹುದು. ಸಿಗ್ನಲ್‌ಗಳಿಗೆ ಕ್ಯಾಂಡಲ್ CSV ಬಳಸಿ. ಅನುಮೋದನೆ ಪೇಪರ್ ಟ್ರೇಡಿಂಗ್‌ಗೆ ಮಾತ್ರ."))

with st.sidebar:
    st.header(t("Strategy settings", "ತಂತ್ರದ ಸೆಟ್ಟಿಂಗ್‌ಗಳು"))
    market = st.selectbox(t("Exchange", "ಎಕ್ಸ್‌ಚೇಂಜ್"), ["NSE", "BSE"])
    segment = st.selectbox(t("Segment", "ವಿಭಾಗ"), ["Equity Intraday", "Equity Swing", "Index F&O (analysis only)", "Stock F&O (analysis only)"])
    fast_n = st.number_input("Fast EMA", 2, 50, 9)
    slow_n = st.number_input("Slow EMA", 5, 200, 21)
    rsi_n = st.number_input("RSI period", 2, 50, 14)
    risk_pct = st.number_input(t("Illustrative stop distance (%)", "ಉದಾಹರಣೆಯ ಸ್ಟಾಪ್ ದೂರ (%)"), 0.1, 10.0, 1.0, 0.1)
    rr = st.number_input(t("Reward / Risk", "ಲಾಭ / ಅಪಾಯ ಅನುಪಾತ"), 0.5, 5.0, 2.0, 0.5)
    capital = st.number_input(t("Reference capital (₹)", "ಉಲ್ಲೇಖ ಬಂಡವಾಳ (₹)"), 1000, 100000000, 100000, 5000)
    risk_trade = st.number_input(t("Paper risk per trade (%)", "ಪ್ರತಿ ಪೇಪರ್ ಟ್ರೇಡ್ ಅಪಾಯ (%)"), 0.1, 2.0, 0.5, 0.1)

st.subheader(t("Groww live price check", "Groww ಲೈವ್ ಬೆಲೆ ಪರಿಶೀಲನೆ"))
st.caption(t(
    "Fetch the latest traded price on demand. Outside market hours it may be from the last trading session.",
    "ಇತ್ತೀಚಿನ ವಹಿವಾಟಿನ ಬೆಲೆಯನ್ನು ನೋಡಿ. ಮಾರುಕಟ್ಟೆ ಮುಚ್ಚಿದ್ದರೆ ಹಿಂದಿನ ಅವಧಿಯ ಬೆಲೆ ಕಾಣಬಹುದು.",
))
token = os.environ.get("GROWW_ACCESS_TOKEN", "").strip()
if not token:
    st.info(t(
        "Add GROWW_ACCESS_TOKEN as a GitHub Codespaces secret for this repository, then restart your Codespace.",
        "ಈ ರೆಪೊಸಿಟರಿಗೆ GROWW_ACCESS_TOKEN ಅನ್ನು GitHub Codespaces secret ಆಗಿ ಸೇರಿಸಿ. ನಂತರ Codespace ಅನ್ನು ಮರುಪ್ರಾರಂಭಿಸಿ.",
    ))

with st.form("groww_price_check"):
    quote_exchange = st.selectbox(t("Price exchange", "ಬೆಲೆಯ ಎಕ್ಸ್‌ಚೇಂಜ್"), ["NSE", "BSE"])
    quote_segment = st.selectbox(t("Price segment", "ಬೆಲೆಯ ವಿಭಾಗ"), ["CASH", "FNO"])
    quote_symbol = st.text_input(t("Trading symbol", "ವಹಿವಾಟಿನ ಚಿಹ್ನೆ"), "RELIANCE", max_chars=60)
    check_price = st.form_submit_button(t("Check live price", "ಲೈವ್ ಬೆಲೆ ಪರಿಶೀಲಿಸಿ"), disabled=not token)

if check_price:
    symbol = quote_symbol.strip().upper()
    if not re.fullmatch(r"[A-Z0-9][A-Z0-9&._-]{0,59}", symbol):
        st.error(t("Enter a Groww trading symbol, such as RELIANCE.", "RELIANCE ನಂತಹ Groww ವಹಿವಾಟಿನ ಚಿಹ್ನೆಯನ್ನು ನಮೂದಿಸಿ."))
    elif not re.fullmatch(r"[A-Za-z0-9._~+/=-]{16,4096}", token):
        st.error(t("Check your GROWW_ACCESS_TOKEN setting.", "GROWW_ACCESS_TOKEN ಸೆಟ್ಟಿಂಗ್ ಪರಿಶೀಲಿಸಿ."))
    else:
        try:
            with st.spinner(t("Checking Groww…", "Groww ಪರಿಶೀಲಿಸಲಾಗುತ್ತಿದೆ…")):
                price = fetch_groww_price(token, quote_exchange, quote_segment, symbol)
        except GrowwPriceError as error:
            st.error(str(error))
        else:
            checked_at = datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%d %b %Y, %I:%M:%S %p IST")
            st.metric(f"{quote_exchange} {symbol} · {quote_segment}", f"₹{price:,.2f}")
            st.caption(t(f"Checked {checked_at}", f"ಪರಿಶೀಲಿಸಿದ ಸಮಯ {checked_at}"))

st.divider()

st.subheader(t("Signal scanner", "ಸಿಗ್ನಲ್ ಸ್ಕ್ಯಾನರ್"))
st.write(t("Upload OHLCV candles for one symbol. Required columns: datetime, open, high, low, close, volume.", "ಒಂದು ಚಿಹ್ನೆಗೆ OHLCV ಕ್ಯಾಂಡಲ್‌ಗಳನ್ನು ಅಪ್‌ಲೋಡ್ ಮಾಡಿ. ಅಗತ್ಯ ಕಾಲಮ್‌ಗಳು: datetime, open, high, low, close, volume."))
file = st.file_uploader(t("Upload candle CSV", "ಕ್ಯಾಂಡಲ್ CSV ಅಪ್‌ಲೋಡ್ ಮಾಡಿ"), type=["csv"])

def calc_rsi(s, n):
    delta=s.diff(); gain=delta.clip(lower=0).ewm(alpha=1/n, adjust=False).mean(); loss=(-delta.clip(upper=0)).ewm(alpha=1/n, adjust=False).mean()
    rs=gain/loss.replace(0,np.nan)
    return 100-(100/(1+rs))

if file:
    try:
        df=pd.read_csv(file); df.columns=[x.strip().lower() for x in df.columns]
        required={"datetime","open","high","low","close","volume"}
        if not required.issubset(df.columns):
            st.error("Missing columns: " + ", ".join(sorted(required-set(df.columns))))
            st.stop()
        df["datetime"]=pd.to_datetime(df["datetime"], errors="coerce")
        for col in ["open","high","low","close","volume"]: df[col]=pd.to_numeric(df[col],errors="coerce")
        df=df.dropna(subset=list(required)).sort_values("datetime").reset_index(drop=True)
        if len(df)<max(slow_n,rsi_n)+3: st.error("Upload more candles to warm up the indicators."); st.stop()
        df["ema_fast"]=df.close.ewm(span=int(fast_n),adjust=False).mean()
        df["ema_slow"]=df.close.ewm(span=int(slow_n),adjust=False).mean()
        df["rsi"]=calc_rsi(df.close,int(rsi_n))
        typical=(df.high+df.low+df.close)/3
        sessions=df.datetime.dt.date
        df["vwap"]=(typical*df.volume).groupby(sessions).cumsum()/df.volume.groupby(sessions).cumsum().replace(0,np.nan)
        # Supertrend is intentionally omitted from signal logic in this first build; avoid presenting a fake indicator.
        buy=(df.ema_fast>df.ema_slow)&(df.close>df.vwap)&(df.rsi>=50)
        sell=(df.ema_fast<df.ema_slow)&(df.close<df.vwap)&(df.rsi<=50)
        df["signal"]=np.select([buy,sell],["BUY WATCH","SELL WATCH"],default="WAIT")
        last=df.iloc[-1]
        x1,x2,x3,x4=st.columns(4)
        x1.metric(t("Latest close", "ಕೊನೆಯ ಕ್ಲೋಸ್"),f"₹{last.close:,.2f}")
        x2.metric("EMA trend", "Bullish" if last.ema_fast>last.ema_slow else "Bearish")
        x3.metric("RSI",f"{last.rsi:.1f}" if pd.notna(last.rsi) else "—")
        x4.metric(t("Latest signal", "ಇತ್ತೀಚಿನ ಸಿಗ್ನಲ್"),last.signal)
        if last.signal != "WAIT":
            long=last.signal=="BUY WATCH"; entry=float(last.close)
            stop=entry*(1-risk_pct/100) if long else entry*(1+risk_pct/100)
            target=entry+(entry-stop)*rr if long else entry-(stop-entry)*rr
            risk_rupees=capital*risk_trade/100
            risk_per_unit=abs(entry-stop)
            qty=max(0,int(risk_rupees/risk_per_unit)) if risk_per_unit else 0
            st.markdown("### "+t("Manual review card (paper trading)","ಕೈಯಾರೆ ಪರಿಶೀಲನೆ (ಪೇಪರ್ ಟ್ರೇಡಿಂಗ್)"))
            st.write(f"**{t('Exchange','ಎಕ್ಸ್‌ಚೇಂಜ್')}:** {market} | **{t('Segment','ವಿಭಾಗ')}:** {segment}")
            st.write(f"**{t('Reference entry','ಉಲ್ಲೇಖ ಪ್ರವೇಶ')}:** ₹{entry:,.2f}  |  **Stop:** ₹{stop:,.2f}  |  **Target:** ₹{target:,.2f}")
            st.write(f"**{t('Illustrative quantity','ಉದಾಹರಣೆಯ ಪ್ರಮಾಣ')}:** {qty} units (risk-budget estimate; excludes costs/slippage)")
            st.caption(t("Levels are illustrative calculations from the last uploaded candle, not a recommendation or executable order.","ಈ ಮಟ್ಟಗಳು ಅಪ್‌ಲೋಡ್ ಮಾಡಿದ ಕೊನೆಯ ಕ್ಯಾಂಡಲ್ ಆಧಾರಿತ ಉದಾಹರಣೆ ಮಾತ್ರ; ಶಿಫಾರಸು ಅಥವಾ ಕಾರ್ಯಗತಗೊಳಿಸಬಹುದಾದ ಆರ್ಡರ್ ಅಲ್ಲ."))
            c1,c2=st.columns(2)
            if c1.button(t("Approve for paper journal", "ಪೇಪರ್ ಜರ್ನಲ್‌ಗೆ ಅನುಮೋದಿಸಿ"), use_container_width=True):
                st.success(t("Marked for paper review only. No broker order was sent.","ಪೇಪರ್ ಪರಿಶೀಲನೆಗೆ ಮಾತ್ರ ಗುರುತಿಸಲಾಗಿದೆ. ಬ್ರೋಕರ್ ಆರ್ಡರ್ ಕಳುಹಿಸಲಾಗಿಲ್ಲ."))
            if c2.button(t("Reject signal", "ಸಿಗ್ನಲ್ ತಿರಸ್ಕರಿಸಿ"), use_container_width=True): st.info(t("Rejected. No order was sent.","ತಿರಸ್ಕರಿಸಲಾಗಿದೆ. ಯಾವುದೇ ಆರ್ಡರ್ ಕಳುಹಿಸಲಾಗಿಲ್ಲ."))
        else: st.info(t("No setup under current rules.","ಪ್ರಸ್ತುತ ನಿಯಮಗಳ ಪ್ರಕಾರ ಯಾವುದೇ ಸೆಟಪ್ ಇಲ್ಲ."))
        st.subheader(t("Recent signals", "ಇತ್ತೀಚಿನ ಸಿಗ್ನಲ್‌ಗಳು"))
        st.dataframe(df[["datetime","open","high","low","close","volume","ema_fast","ema_slow","rsi","vwap","signal"]].tail(100),use_container_width=True)
        st.download_button(t("Download analysis CSV", "ವಿಶ್ಲೇಷಣೆ CSV ಡೌನ್‌ಲೋಡ್ ಮಾಡಿ"),df.to_csv(index=False),"signal_analysis.csv","text/csv")
    except Exception as e: st.error(f"Could not read CSV: {e}")

st.divider()
st.subheader(t("Portfolio & trade journal", "ಪೋರ್ಟ್‌ಫೋಲಿಯೊ ಮತ್ತು ಟ್ರೇಡ್ ಜರ್ನಲ್"))
st.info(t("Portfolio, order status, live P&L and Telegram alerts are pending. The Groww connection only fetches prices.","ಪೋರ್ಟ್‌ಫೋಲಿಯೊ, ಆರ್ಡರ್ ಸ್ಥಿತಿ, ಲೈವ್ P&L ಮತ್ತು Telegram ಎಚ್ಚರಿಕೆಗಳು ಬಾಕಿಯಿವೆ. Groww ಸಂಪರ್ಕ ಬೆಲೆಗಳನ್ನು ಮಾತ್ರ ಪಡೆಯುತ್ತದೆ."))
st.caption("Read-only build 1.1 | " + datetime.now().strftime("%Y-%m-%d"))
