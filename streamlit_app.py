import streamlit as st
import yfinance as yf
import pandas as pd
import MetaTrader5 as mt5

# 1. გვერდის კონფიგურაცია
st.set_page_config(page_title="FBS MT5 Algo Bot", page_icon="📈", layout="wide")

st.title("📈 FBS MetaTrader 5 - ავტომატური სავაჭრო ბოტი")
st.write("ტექნიკური ანალიზი + ავტომატური ვაჭრობა FBS MT5 ტერმინალში")

# 2. გვერდითა მენიუ
st.sidebar.header("⚙️ ბაზრის პარამეტრები")
symbol = st.sidebar.text_input("სავაჭრო წყვილი (MT5 Symbol):", value="EURUSD")
yf_ticker = st.sidebar.text_input("yFinance Ticker (ანალიზისთვის):", value="EURUSD=X")
period = st.sidebar.selectbox("პერიოდი:", ["3mo", "6mo", "1y"], index=1)

st.sidebar.markdown("---")
st.sidebar.header("💰 რისკების მართვა")
lot_size = st.sidebar.number_input("ლოტის ზომა (Lot Size):", min_value=0.01, value=0.1, step=0.01)
sl_pips = st.sidebar.number_input("Stop Loss (Pips):", min_value=5, value=20)
tp_pips = st.sidebar.number_input("Take Profit (Pips):", min_value=5, value=40)

# 3. ანალიზის ფუნქცია
def analyze_market():
    data = yf.download(yf_ticker, period=period, interval="1d")
    if data.empty:
        return None
    
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)
    
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
    
    return data

# 4. MT5-ში ორდერის გაგზავნის ფუნქცია
def send_mt5_order(order_type, symbol, lot, sl_pips, tp_pips):
    if not mt5.initialize():
        st.error(f"❌ MT5-თან კავშირი ვერ დამყარდა: {mt5.last_error()}")
        return False

    symbol_info = mt5.symbol_info(symbol)
    if symbol_info is None:
        st.error(f"❌ წყვილი {symbol} ვერ მოიძებნა MT5-ში!")
        mt5.shutdown()
        return False

    if not symbol_info.visible:
        if not mt5.symbol_select(symbol, True):
            st.error(f"❌ symbol_select ჩართვა ვერ მოხერხდა")
            mt5.shutdown()
            return False

    point = symbol_info.point
    price = mt5.symbol_info_tick(symbol).ask if order_type == "BUY" else mt5.symbol_info_tick(symbol).bid

    if order_type == "BUY":
        type_dict = mt5.ORDER_TYPE_BUY
        sl = price - (sl_pips * point * 10)
        tp = price + (tp_pips * point * 10)
    else:
        type_dict = mt5.ORDER_TYPE_SELL
        sl = price + (sl_pips * point * 10)
        tp = price - (tp_pips * point * 10)

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": lot,
        "type": type_dict,
        "price": price,
        "sl": sl,
        "tp": tp,
        "deviation": 20,
        "magic": 123456,
        "comment": "Python Bot Trade",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }

    result = mt5.order_send(request)
    mt5.shutdown()

    if result.retcode != mt5.TRADE_RETCODE_DONE:
        st.error(f"❌ ორდერი ვერ განხორციელდა: {result.comment} (code: {result.retcode})")
        return False
    else:
        st.success(f"✅ {order_type} ორდერი წარმატებით გაიხსნა FBS MT5-ში! Ticket: {result.order}")
        return True

# 5. მთავარი ეკრანი
data = analyze_market()

if data is not None:
    latest = data.iloc[-1]
    price = float(latest['Close'])
    rsi = float(latest['RSI'])
    ema20 = float(latest['EMA_20'])
    ema50 = float(latest['EMA_50'])
    macd = float(latest['MACD'])
    macd_signal = float(latest['Signal_Line'])

    buy_condition = (ema20 > ema50) and (40 < rsi < 65) and (macd > macd_signal)
    sell_condition = (ema20 < ema50) and (35 < rsi < 60) and (macd < macd_signal)

    col1, col2, col3 = st.columns(3)
    col1.metric("მიმდინარე ფასი", f"${price:,.4f}")
    col2.metric("RSI (14)", f"{rsi:.1f}")
    col3.metric("MACD", "Bullish 🚀" if macd > macd_signal else "Bearish 🔻")

    st.markdown("---")
    st.subheader("📊 ალგორითმის სტატუსი:")
    
    if buy_condition:
        st.success("🟢 **STRONG BUY SIGNAL** — ალგორითმი ყიდვის რეკომენდაციას იძლევა!")
    elif sell_condition:
        st.error("🔴 **STRONG SELL SIGNAL** — ალგორითმი გაყიდვის რეკომენდაციას იძლევა!")
    else:
        st.info("⚪ **NEUTRAL** — ბაზარზე მკვეთრი სიგნალი არ არის.")

    st.markdown("---")
    st.subheader("⚡ FBS MT5-ზე ორდერის გაგზავნა")

    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("🟢 BUY (ყიდვა MT5-ში)"):
            send_mt5_order("BUY", symbol, lot_size, sl_pips, tp_pips)
            
    with col_btn2:
        if st.button("🔴 SELL (გაყიდვა MT5-ში)"):
            send_mt5_order("SELL", symbol, lot_size, sl_pips, tp_pips)

    st.line_chart(data[['Close', 'EMA_20', 'EMA_50']])