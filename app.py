import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime

st.set_page_config(page_title="Groww Smart Algo", page_icon="📈", layout="wide")

LANG = st.sidebar.selectbox("Language / ಭಾಷೆ", ["English", "ಕನ್ನಡ"])
KN = LANG == "ಕನ್ನಡ"
def t(en, kn): return kn if KN else en

st.title("📈 Groww Smart Algo – Advanced Dashboard")
st.caption(t("NSE + BSE | Signals + paper trading | Manual approval workflow", "NSE + BSE | ಸಿಗ್ನಲ್‌ಗಳು + ಪೇಪರ್ ಟ್ರೇಡಿಂಗ್ | ಕೈಯಾರೆ ಅನುಮೋದನೆ"))
st.warning(t("Starter prototype only: this app does not connect to Groww, fetch live prices, or place real orders. Upload candle data to test signals. Do not use signals as investment advice.", "ಇದು ಪ್ರಾರಂಭಿಕ ಮಾದರಿ ಮಾತ್ರ: ಈ ಆಪ್ Groww ಗೆ ಸಂಪರ್ಕಿಸುವುದಿಲ್ಲ, ಲೈವ್ ಬೆಲೆಗಳನ್ನು ಪಡೆಯುವುದಿಲ್ಲ ಅಥವಾ ನೈಜ ಆರ್ಡರ್‌ಗಳನ್ನು ಮಾಡುವುದಿಲ್ಲ. ಸಿಗ್ನಲ್ ಪರೀಕ್ಷಿಸಲು ಕ್ಯಾಂಡಲ್ ಡೇಟಾ ಅಪ್‌ಲೋಡ್ ಮಾಡಿ. ಇದನ್ನು ಹೂಡಿಕೆ ಸಲಹೆಯಾಗಿ ಪರಿಗಣಿಸಬೇಡಿ."))

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

st.subheader(t("Market overview", "ಮಾರುಕಟ್ಟೆ ಅವಲೋಕನ"))
a,b,c,d = st.columns(4)
a.metric("NIFTY 50", t("Upload data", "ಡೇಟಾ ಅಪ್‌ಲೋಡ್ ಮಾಡಿ"))
b.metric("BANK NIFTY", t("Upload data", "ಡೇಟಾ ಅಪ್‌ಲೋಡ್ ಮಾಡಿ"))
c.metric("SENSEX", t("Upload data", "ಡೇಟಾ ಅಪ್‌ಲೋಡ್ ಮಾಡಿ"))
d.metric(t("Data status", "ಡೇಟಾ ಸ್ಥಿತಿ"), t("Awaiting CSV", "CSV ನಿರೀಕ್ಷೆಯಲ್ಲಿದೆ"))

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
st.info(t("Portfolio, order status, live P&L, Telegram alerts and Groww connection are not enabled in this starter build. Add them only after verifying current Groww API access and applicable exchange/SEBI requirements.","ಈ ಪ್ರಾರಂಭಿಕ ಆವೃತ್ತಿಯಲ್ಲಿ ಪೋರ್ಟ್‌ಫೋಲಿಯೊ, ಆರ್ಡರ್ ಸ್ಥಿತಿ, ಲೈವ್ P&L, Telegram ಎಚ್ಚರಿಕೆಗಳು ಮತ್ತು Groww ಸಂಪರ್ಕ ಸಕ್ರಿಯವಾಗಿಲ್ಲ. Groww API ಪ್ರವೇಶ ಮತ್ತು ಅನ್ವಯಿಸುವ ಎಕ್ಸ್‌ಚೇಂಜ್/SEBI ನಿಯಮಗಳನ್ನು ಪರಿಶೀಲಿಸಿದ ನಂತರ ಮಾತ್ರ ಸೇರಿಸಿ."))
st.caption("Prototype build 1.0 | " + datetime.now().strftime("%Y-%m-%d"))
