import yfinance as yf
import json
import datetime

def fetch_data():
    # Definiamo i ticker di Yahoo Finance
    # Formato: [Nome visualizzato, Ticker Yahoo]
    tickers_D = {
        "forex": [
            ["EUR/USD", "EURUSD=X"], ["GBP/USD", "GBPUSD=X"], ["USD/JPY", "USDJPY=X"], 
            ["USD/CHF", "USDCHF=X"], ["AUD/USD", "AUDUSD=X"], ["USD/CAD", "USDCAD=X"], 
            ["EUR/GBP", "EURGBP=X"], ["EUR/JPY", "EURJPY=X"]
        ],
        "indices": [
            ["FTSE MIB", "FTSEMIB.MI"], ["S&P 500", "^GSPC"], ["NASDAQ", "^IXIC"], 
            ["DAX", "^GDAXI"], ["Euro Stoxx 50", "^STOXX50E"], ["Nikkei 225", "^N225"]
        ],
        "sectors": [
            ["Tecnologia (XLK)", "XLK"], ["Finanza (XLF)", "XLF"], ["Energia (XLE)", "XLE"], 
            ["Industriale (XLI)", "XLI"], ["Consumer (XLY)", "XLY"]
        ],
        "macro": [
            ["VIX", "^VIX"], ["Dollar Index (DXY)", "DX-Y.NYB"], ["Oro (GC=F)", "GC=F"], 
            ["Petrolio WTI (CL=F)", "CL=F"], ["US Treasury 10Y", "^TNX"], ["US Treasury 5Y", "^FVX"], 
            ["Bitcoin (BTC)", "BTC-USD"], ["Ethereum (ETH)", "ETH-USD"]
        ]
    }

    tickers_L = {
        "S&P 500": "^GSPC",
        "NASDAQ": "^IXIC",
        "Paesi Emergenti (EEM)": "EEM",
        "Cina (Shanghai)": "000001.SS",
        "Europa (Euro Stoxx 50)": "^STOXX50E"
    }

    D = {}
    L = {}

    print("Scaricamento dati in corso...")

    # Funzione di supporto per scaricare i dati di un singolo ticker
    def get_ticker_info(symbol):
        try:
            ticker = yf.Ticker(symbol)
            # Scarichiamo gli ultimi 10 giorni per il mini grafico
            hist = ticker.history(period="10d", interval="1d")
            if hist.empty:
                return None
            
            current_price = hist['Close'].iloc[-1]
            prev_close = hist['Open'].iloc[0]
            change = current_price - prev_close
            change_pct = (change / prev_close) * 100 if prev_close else 0
            
            # Costruiamo le candele per il mini grafico
            candles = []
            for index, row in hist.iterrows():
                candles.append([round(row['Open'], 4), round(row['High'], 4), round(row['Low'], 4), round(row['Close'], 4)])
            
            min_val = round(hist['Low'].min(), 4)
            max_val = round(hist['High'].max(), 4)
            
            return [round(current_price, 4), round(change, 4), round(change_pct, 2), candles, min_val, max_val]
        except Exception as e:
            print(f"Errore su {symbol}: {e}")
            return None

    # Popoliamo la struttura D
    for category, items in tickers_D.items():
        D[category] = []
        for name, symbol in items:
            info = get_ticker_info(symbol)
            if info:
                D[category].append([name, info[0], info[1], info[2], info[3], info[4], info[5]])

    # Popoliamo la struttura L (storico 12 mesi)
    mesi = ["gen", "feb", "mar", "apr", "mag", "giu", "lug", "ago", "set", "ott", "nov", "dic"]
    for name, symbol in tickers_L.items():
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="1y", interval="1mo")
            if not hist.empty:
                labels = [f"{mesi[index.month-1]} {index.year}" for index in hist.index]
                prices = [round(val, 2) for val in hist['Close'].tolist()]
                L[name] = [labels, prices, round(min(prices), 2), round(max(prices), 2)]
        except Exception as e:
            print(f"Errore storico su {symbol}: {e}")

    # Aggiungiamo il timestamp dell'ultimo aggiornamento
    ora_attuale = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
    
    output = {
        "timestamp": ora_attuale,
        "D": D,
        "L": L
    }

    # Salviamo tutto nel file JSON
    with open("dati.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print("File dati.json generato con successo!")

if __name__ == "__main__":
    fetch_data()
