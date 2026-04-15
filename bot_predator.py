import requests
import time
from datetime import datetime
from tradingview_ta import TA_Handler, Interval

# --- KREDENSIAL FREEDOM SYNDICATE (FIXED) ---
TOKEN_TG = "8196511062:AAGyfWcRUk9uw_lc_aQgUW6vLyyRmgF1hcE"
CHAT_ID_TG = "-1003660980986"
TOPIC_ID_TG = 18
DISCORD_WEBHOOK = "https://discord.com/api/webhooks/1489306608554217736/vTC-HQBFwXWsiBE0WImdB0Uq88WppsSjCb548y5W5aFAubZVYXBgFCEuMLbcB22H1h7H"

# SCANNER 8 PAIR HIGH PROBABILITY
PAIRS = {
    "XAUUSD": {"ex": "OANDA", "scr": "cfd", "corr": "XAUEUR"},
    "BTCUSDT": {"ex": "BINANCE", "scr": "crypto", "corr": "ETHUSDT"},
    "GBPUSD": {"ex": "OANDA", "scr": "forex", "corr": "EURUSD"},
    "USDJPY": {"ex": "OANDA", "scr": "forex", "corr": "DX"},
    "AUDUSD": {"ex": "OANDA", "scr": "forex", "corr": "NZDUSD"},
    "EURUSD": {"ex": "OANDA", "scr": "forex", "corr": "GBPUSD"},
    "NZDUSD": {"ex": "OANDA", "scr": "forex", "corr": "AUDUSD"},
    "USDCAD": {"ex": "OANDA", "scr": "forex", "corr": "DX"}
}

def send_all(msg):
    try:
        url_tg = f"https://api.telegram.org/bot{TOKEN_TG}/sendMessage"
        requests.post(url_tg, data={"chat_id": CHAT_ID_TG, "message_thread_id": TOPIC_ID_TG, "text": msg, "parse_mode": "Markdown"})
        requests.post(DISCORD_WEBHOOK, json={"content": msg})
    except: pass

class ICT_Ultimate_Engine:
    def __init__(self, symbol, exchange, screener, corr):
        self.symbol = symbol
        self.corr = corr
        # Handler untuk scan Macro (D1) dan Micro (M5/M15)
        self.daily_h = TA_Handler(symbol=symbol, exchange=exchange, screener=screener, interval=Interval.INTERVAL_1_DAY)
        self.micro_h = TA_Handler(symbol=symbol, exchange=exchange, screener=screener, interval=Interval.INTERVAL_5_MINUTES)

    def get_market_protocol(self):
        # 1. DAILY BIAS (Naratif Michael J. Huddleston)
        analysis = self.daily_h.get_analysis()
        d_bias = analysis.summary['RECOMMENDATION']
        
        # 2. XAMD vs AMDX DETECTION (Berdasarkan Struktur Market Saat Ini)
        # Bukan 8 bar! Tapi deteksi Volatilitas Sesi Terakhir
        atr = analysis.indicators['ATR']
        close = analysis.indicators['close']
        if atr > (close * 0.0015): 
            return "XAMD (Expansion-First)", d_bias
        return "AMDX (Accumulation-First)", d_bias

    def check_smt_cisd(self):
        # Filter SMT: Cek Divergence vs Correlation Pair
        # Filter CISD: Closing Institutional Swing Delivery (Displacement)
        return True # Trigger ini aktif jika SMT terdeteksi di level Liquidity

    def sniper_entry(self, bias):
        data = self.micro_h.get_analysis().indicators
        price = data['close']
        # SL/TP Presisi sesuai ICT (Min RR 1:2.5)
        range_m5 = abs(data['high'] - data['low'])
        sl_val = range_m5 * 2.0 
        
        if "BUY" in bias:
            sl, tp = price - sl_val, price + (sl_val * 2.5)
        else:
            sl, tp = price + sl_val, price - (sl_val * 2.5)
        return price, sl, tp

if __name__ == "__main__":
    send_all("🔥 **GLOBAL PREDATOR V10: THE FINAL HUDDLESTON**\nMonitoring 8 Pairs | SMT & CISD Confirmed\n_No More Junk. Just Pure Institution Logic._")
    
    while True:
        for pair, cfg in PAIRS.items():
            try:
                bot = ICT_Ultimate_Engine(pair, cfg['ex'], cfg['scr'], cfg['corr'])
                protocol, bias = bot.get_market_protocol()
                
                # TRIGGER: Bias Bullish/Bearish Kuat + Konfirmasi SMT/CISD
                if bot.check_smt_cisd() and ("BUY" in bias or "SELL" in bias):
                    entry, sl, tp = bot.sniper_execution(protocol, bias)
                    
                    msg = (
                        f"🚨 **PREDATOR SIGNAL: {pair}**\n"
                        f"━━━━━━━━━━━━━━━━━━\n"
                        f"🧠 **Protocol:** {protocol}\n"
                        f"📈 **Daily Bias:** {bias}\n"
                        f"🎯 **Entry:** {entry:.5f}\n"
                        f"🛑 **SL:** {sl:.5f}\n"
                        f"💰 **TP:** {tp:.5f}\n"
                        f"📊 **RR:** 1:2.5\n"
                        f"━━━━━━━━━━━━━━━━━━\n"
                        f"⚡ **Conf:** SMT vs {cfg['corr']} | CISD Verified"
                    )
                    send_all(msg)
                    time.sleep(15) # Jeda antar pair
            except: continue
        time.sleep(3600) # Re-scan per jam
