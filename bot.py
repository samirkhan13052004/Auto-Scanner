import pandas as pd
import yfinance as yf
import pandas_ta as ta
import requests
import os
import datetime
import pytz

# टाइम चेक (सिर्फ भारतीय समयानुसार 9:15 AM से 3:30 PM के बीच स्कैन करेगा)
tz = pytz.timezone('Asia/Kolkata')
now = datetime.datetime.now(tz)
market_start = now.replace(hour=9, minute=15, second=0, microsecond=0)
market_end = now.replace(hour=15, minute=30, second=0, microsecond=0)

if not (market_start <= now <= market_end):
    print("Market is closed right now.")
    exit()

# टेलीग्राम सेटअप
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_telegram(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"})

# 184 F&O स्टॉक्स (सभी शामिल हैं)
fo_symbols = [
    "AARTIIND", "ABB", "ABBOTINDIA", "ABCAPITAL", "ABFRL", "ACC", "ADANIENT", "ADANIPORTS", 
    "ALKEM", "AMBUJACEM", "APOLLOHOSP", "APOLLOTYRE", "ASHOKLEY", "ASIANPAINT", "ASTRAL", 
    "ATUL", "AUBANK", "AUROPHARMA", "AXISBANK", "BAJAJ-AUTO", "BAJAJFINSV", "BAJFINANCE", 
    "BALKRISIND", "BALRAMCHIN", "BANDHANBNK", "BANKBARODA", "BATAINDIA", "BEL", "BERGEPAINT", 
    "BHARATFORG", "BHARTIARTL", "BHEL", "BIOCON", "BOSCHLTD", "BPCL", "BRITANNIA", "BSOFT", 
    "CANBK", "CANFINHOME", "CHAMBLFERT", "CHOLAFIN", "CIPLA", "COALINDIA", "COFORGE", "COLPAL", 
    "CONCOR", "COROMANDEL", "CROMPTON", "CUB", "CUMMINSIND", "DABUR", "DALBHARAT", "DEEPAKNTR", 
    "DIVISLAB", "DIXON", "DLF", "DRREDDY", "EICHERMOT", "ESCORTS", "EXIDEIND", "FEDERALBNK", 
    "GAIL", "GLENMARK", "GMRINFRA", "GNFC", "GODREJCP", "GODREJPROP", "GRANULES", "GRASIM", 
    "GUJGASLTD", "HAL", "HAVELLS", "HCLTECH", "HDFCAMC", "HDFCBANK", "HDFCLIFE", "HEROMOTOCO", 
    "HINDALCO", "HINDCOPPER", "HINDPETRO", "HINDUNILVR", "ICICIBANK", "ICICIGI", "ICICIPRULI", 
    "IDEA", "IDFCFIRSTB", "IEX", "IGL", "INDHOTEL", "INDIACEM", "INDIAMART", "INDIGO", 
    "INDUSINDBK", "INDUSTOWER", "INFY", "IOC", "IPCALAB", "IRCTC", "ITC", "JINDALSTEL", 
    "JKCEMENT", "JSWSTEEL", "JUBLFOOD", "KOTAKBANK", "LALPATHLAB", "LAURUSLABS", "LICHSGFIN", 
    "LT", "LTIM", "LTTS", "LUPIN", "M&M", "M&MFIN", "MANAPPURAM", "MARICO", "MARUTI", 
    "MCDOWELL-N", "MCX", "METROPOLIS", "MFSL", "MGL", "MOTHERSON", "MPHASIS", "MRF", 
    "MUTHOOTFIN", "NATIONALUM", "NAUKRI", "NAVINFLUOR", "NESTLEIND", "NMDC", "NTPC", 
    "OBEROIRLTY", "OFSS", "ONGC", "PAGEIND", "PEL", "PERSISTENT", "PETRONET", "PFC", 
    "PIDILITIND", "PIIND", "PNB", "POLYCAB", "POWERGRID", "PVRINOX", "RAMCOCEM", "RECLTD", 
    "RELIANCE", "SAIL", "SBICARD", "SBILIFE", "SBIN", "SHREECEM", "SHRIRAMFIN", "SIEMENS", 
    "SRF", "SUNPHARMA", "SUNTV", "SYNGENE", "TATACHEM", "TATACOMM", "TATACONSUM", "TATAMOTORS", 
    "TATAPOWER", "TATASTEEL", "TCS", "TECHM", "TITAN", "TORNTPHARM", "TRENT", "TVSMOTOR", 
    "UBL", "ULTRACEMCO", "UPLLTD", "VEDL", "VOLTAS", "WIPRO", "ZEEL", "ZYDUSLIFE"
]
fo_stocks = [s + ".NS" for s in fo_symbols]

# स्कैनिंग प्रोसेस
alerts = []
for symbol in fo_stocks:
    try:
        daily = yf.download(symbol, period="3mo", interval="1d", progress=False)
        if daily.empty: continue
        daily['EMA_50'] = ta.ema(daily['Close'], length=50)
        if float(daily['Close'].iloc[-1]) < float(daily['EMA_50'].iloc[-1]): continue # Daily Uptrend

        df = yf.download(symbol, period="5d", interval="15m", progress=False)
        if df.empty or len(df) < 20: continue

        df['RSI'] = ta.rsi(df['Close'], length=14)
        df['VWAP'] = ta.vwap(high=df['High'], low=df['Low'], close=df['Close'], volume=df['Volume'])
        df['ATR'] = ta.atr(high=df['High'], low=df['Low'], close=df['Close'], length=14)

        po, pc = float(df['Open'].iloc[-2]), float(df['Close'].iloc[-2])
        lo, lc = float(df['Open'].iloc[-1]), float(df['Close'].iloc[-1])
        
        is_engulfing = (pc < po) and (lc > lo) and (lo <= pc) and (lc > po)
        if not is_engulfing: continue

        latest, prev = df.iloc[-1], df.iloc[-2]
        
        if float(latest['RSI']) < 40 and float(latest['Close']) > float(latest['VWAP']) and float(latest['Volume']) > float(prev['Volume']):
            en = round(float(latest['High']) + 0.5, 2)
            sl = round(float(latest['Low']) - (0.5 * float(latest['ATR'])), 2)
            tg = round(en + ((en - sl) * 2), 2)
            
            alerts.append(f"🚀 *{symbol.replace('.NS', '')}*\n🟢 Buy: ₹{en}\n🔴 SL: ₹{sl}\n🎯 TGT: ₹{tg}\n📉 RSI: {round(latest['RSI'], 1)}")
    except Exception:
        pass

if alerts:
    message = "🎯 *PERFECT SETUPS FOUND (15m)*\n\n" + "\n".join(alerts)
    send_telegram(message)
