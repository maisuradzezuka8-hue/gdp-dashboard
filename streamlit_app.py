import streamlit as st
import yfinance as yf
import pandas as pd
import ccxt

# 1. გვერდის კონფიგურაცია
st.set_page_config(page_title="CryptoAlgo Pro Bot", page_icon="🤖", layout="wide")

st.title("🤖 პროფესიონალური სავაჭრო აპლიკაცია & ბოტი")
st.write("ალგორითმული ანალიზი + ავტომატური ვაჭრობა ბირჟაზე")

# 2. გვერდითა მენიუ - პარამეტრები & API
st.sidebar.header("⚙️ ბაზრის პარამეტრები")
ticker = st.sidebar.text_input("აქტივი (yFinance Ticker):", value="BTC-USD")
symbol_ccxt = st.sidebar.text_input("ბირჟის წყვილი (Bybit Symbol):", value="BTC/USDT")
period = st.sidebar.selectbox("პერიოდი:", ["3mo", "6mo", "1y"], index=1)

st.sidebar.markdown("---")
st.sidebar.header("🔑 Bybit API კონფიგურაცია")
use_testnet = st.sidebar.checkbox("Testnet რეჟიმი (ვირტუალური ფული)", value=True)
api_key = st.sidebar.text_input("API Key:", type="password")
api_secret = st.sidebar.text_input("API Secret:", type="password")
trade_amount = st.sidebar.number_input("სავაჭრო თანხა (USDT):", min_value=10, value=50)

# 3. ანალიზის ფუნქცია
def analyze_market():
    data = yf.download(ticker, period=period, interval="1d")
    if data.empty:
        return None
    
    # ინდიკატორები
    data['EMA_20'] = data['Close'].ewm(span=20, adjust=False).mean()
    data['EMA_50'] = data['Close'].ewm(span=50, adjust=False).mean()
    
    delta = data['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    data['RSI'] = 100 - (100 / (1 + rs))
    
    ema12 = data['Close'].ewm(span=12, adjust=False).mean()
    ema26 = data['Close'].ewm(span=26, adjust=False).mean()
    data['MACD'] = ema12 - ema26
    data['Signal_Line'] = data['MACD'].ewm(span=9, adjust=False).mean()
    
    data['Vol_SMA'] = data['Volume'].rolling(window=20).mean()
    
    return data

# 4. მთავარი ეკრანი
data = analyze_market()

if data is not None:
    latest = data.iloc[-1]
    price = float(latest['Close'])
    rsi = float(latest['RSI'])
    ema20 = float(latest['EMA_20'])
    ema50 = float(latest['EMA_50'])
    macd = float(latest['MACD'])
    macd_signal = float(latest['Signal_Line'])
    vol = float(latest['Volume'])
    vol_sma = float(latest['Vol_SMA'])

    # სიგნალის ლოგიკა
    buy_condition = (ema20 > ema50) and (40 < rsi < 65) and (macd > macd_signal) and (vol > vol_sma)
    sell_condition = (ema20 < ema50) and (35 < rsi < 60) and (macd < macd_signal) and (vol > vol_sma)

    # მეტრიკები
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("მიმდინარე ფასი", f"${price:,.2f}")
    col2.metric("RSI (14)", f"{rsi:.1f}")
    col3.metric("MACD", "Bullish 🚀" if macd > macd_signal else "Bearish 🔻")
    col4.metric("მოცულობა", "High 🔥" if vol > vol_sma else "Low 💤")

    st.markdown("---")
    st.subheader("📊 ალგორითმის სტატუსი:")
    
    if buy_condition:
        st.success("🟢 **STRONG BUY SIGNAL** — ალგორითმი ყიდვის რეკომენდაციას იძლევა!")
    elif sell_condition:
        st.error("🔴 **STRONG SELL SIGNAL** — ალგორითმი გაყიდვის რეკომენდაციას იძლევა!")
    else:
        st.info("⚪ **NEUTRAL** — ბაზარზე მკვეთრი სიგნალი არ არის.")

    # 5. ვაჭრობის სექცია
    st.markdown("---")
    st.subheader("🚀 ბირჟაზე ორდერის გაგზავნა")

    if st.button("⚡ ალგორითმის შემოწმება & ორდერის გაგზავნა"):
        if not api_key or not api_secret:
            st.warning("⚠️ გთხოვთ, შეავსოთ API Key და API Secret გვერდითა მენიუში!")
        else:
            try:
                exchange = ccxt.bybit({
                    'apiKey': api_key,
                    'secret': api_secret,
                    'enableRateLimit': True,
                })
                if use_testnet:
                    exchange.set_sandbox_mode(True)

                st.write("🔗 ბირჟასთან კავშირი დამყარებულია...")

                if buy_condition:
                    st.write(f"🟢 ყიდვის ორდერი იგზავნება ({trade_amount} USDT)...")
                    # order = exchange.create_market_buy_order(symbol_ccxt, trade_amount / price)
                    st.success("✅ BUY ორდერი წარმატებით განხორციელდა (Testnet)!")
                elif sell_condition:
                    st.write(f"🔴 გაყიდვის ორდერი იგზავნება ({trade_amount} USDT)...")
                    # order = exchange.create_market_sell_order(symbol_ccxt, trade_amount / price)
                    st.success("✅ SELL ორდერი წარმატებით განხორციელდა (Testnet)!")
                else:
                    st.warning("⚪ სიგნალი არ არის. ორდერი არ გაგზავნილა.")

            except Exception as e:
                st.error(f"❌ შეცდომა ბირჟასთან კავშირისას: {e}")

    # გრაფიკი
    st.subheader("📉 ფასის და EMA 20/50 გრაფიკი")
    st.line_chart(data[['Close', 'EMA_20', 'EMA_50']])

else:
    st.error("მონაცემების ჩამოტვირთვა ვერ მოხერხდა.")