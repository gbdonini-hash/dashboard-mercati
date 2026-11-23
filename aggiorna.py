"""
Genera dati.json per la dashboard mercati.

Per ogni strumento calcola: ultimo prezzo, variazione giornaliera reale
(ultima chiusura vs chiusura precedente), rendimenti 1S/1M/3M/YTD/1A,
massimo/minimo a 52 settimane e lo storico giornaliero di ~13 mesi.
Per i tassi (kind = "rate") le variazioni sono espresse in punti base.
"""
import datetime as dt
import json
import math

import pandas as pd
import yfinance as yf

# ---------------------------------------------------------------------------
# Configurazione strumenti: [id, nome, ticker Yahoo, tipo]
# tipo: "price" (variazioni %), "rate" (rendimento: variazioni in bp), "fx"
# ---------------------------------------------------------------------------
GROUPS = [
    ("indices", "Azionario", [
        ("FTSEMIB", "FTSE MIB", "FTSEMIB.MI", "price"),
        ("SX5E", "Euro Stoxx 50", "^STOXX50E", "price"),
        ("DAX", "DAX", "^GDAXI", "price"),
        ("CAC", "CAC 40", "^FCHI", "price"),
        ("UKX", "FTSE 100", "^FTSE", "price"),
        ("SPX", "S&P 500", "^GSPC", "price"),
        ("NDX", "Nasdaq 100", "^NDX", "price"),
        ("DJI", "Dow Jones", "^DJI", "price"),
        ("NKY", "Nikkei 225", "^N225", "price"),
        ("HSI", "Hang Seng", "^HSI", "price"),
        ("SHCOMP", "Shanghai Comp.", "000001.SS", "price"),
        ("EEM", "Emergenti (EEM)", "EEM", "price"),
        ("URTH", "MSCI World (URTH)", "URTH", "price"),
    ]),
    ("fx", "Valute", [
        ("EURUSD", "EUR/USD", "EURUSD=X", "fx"),
        ("EURGBP", "EUR/GBP", "EURGBP=X", "fx"),
        ("EURCHF", "EUR/CHF", "EURCHF=X", "fx"),
        ("EURJPY", "EUR/JPY", "EURJPY=X", "fx"),
        ("GBPUSD", "GBP/USD", "GBPUSD=X", "fx"),
        ("USDJPY", "USD/JPY", "USDJPY=X", "fx"),
        ("USDCHF", "USD/CHF", "USDCHF=X", "fx"),
        ("AUDUSD", "AUD/USD", "AUDUSD=X", "fx"),
        ("USDCAD", "USD/CAD", "USDCAD=X", "fx"),
        ("DXY", "Dollar Index", "DX-Y.NYB", "price"),
    ]),
    ("rates", "Tassi", [
        ("US3M", "Treasury 3 mesi", "^IRX", "rate"),
        ("US5Y", "Treasury 5 anni", "^FVX", "rate"),
        ("US10Y", "Treasury 10 anni", "^TNX", "rate"),
        ("US30Y", "Treasury 30 anni", "^TYX", "rate"),
    ]),
    ("commodities", "Materie prime", [
        ("GOLD", "Oro", "GC=F", "price"),
        ("SILVER", "Argento", "SI=F", "price"),
        ("BRENT", "Petrolio Brent", "BZ=F", "price"),
        ("WTI", "Petrolio WTI", "CL=F", "price"),
        ("NATGAS", "Gas naturale (US)", "NG=F", "price"),
        ("COPPER", "Rame", "HG=F", "price"),
    ]),
    ("sectors", "Settori USA", [
        ("XLK", "Tecnologia", "XLK", "price"),
        ("XLF", "Finanziari", "XLF", "price"),
        ("XLV", "Salute", "XLV", "price"),
        ("XLE", "Energia", "XLE", "price"),
        ("XLI", "Industriali", "XLI", "price"),
        ("XLY", "Consumi discrezionali", "XLY", "price"),
        ("XLP", "Beni di prima necessità", "XLP", "price"),
        ("XLU", "Utility", "XLU", "price"),
        ("XLB", "Materiali", "XLB", "price"),
        ("XLRE", "Immobiliare", "XLRE", "price"),
        ("XLC", "Comunicazioni", "XLC", "price"),
    ]),
    ("risk", "Rischio & Crypto", [
        ("VIX", "VIX", "^VIX", "price"),
        ("BTC", "Bitcoin", "BTC-USD", "price"),
        ("ETH", "Ethereum", "ETH-USD", "price"),
    ]),
]

# Strumenti mostrati nella barra in alto
HEADLINE = ["FTSEMIB", "SX5E", "SPX", "NDX", "EURUSD", "US10Y", "GOLD", "BRENT", "BTC", "VIX"]

HISTORY_DAYS = 400  # ~13 mesi: copre 1A e YTD


def sig(x, digits=6):
    """Arrotonda a cifre significative per contenere la dimensione del file."""
    if x is None or (isinstance(x, float) and (math.isnan(x) or math.isinf(x))):
        return None
    if x == 0:
        return 0.0
    return round(float(x), max(0, digits - int(math.floor(math.log10(abs(x)))) - 1))


def change(last, ref, kind):
    if ref is None or last is None or ref == 0:
        return None
    if kind == "rate":
        return round((last - ref) * 100, 1)  # punti base
    return round((last / ref - 1) * 100, 2)


def ref_at(series, when):
    """Ultima chiusura disponibile alla data `when` (o prima)."""
    s = series[series.index <= pd.Timestamp(when)]
    return float(s.iloc[-1]) if len(s) else None


def build_asset(series, kind):
    series = series.dropna()
    series = series[series > 0] if kind != "rate" else series
    if len(series) < 2:
        return None
    last_day = series.index[-1]
    last = float(series.iloc[-1])
    prev = float(series.iloc[-2])
    year_ago = last_day - pd.Timedelta(days=365)
    ytd_ref = ref_at(series, pd.Timestamp(last_day.year - 1, 12, 31))
    window = series[series.index > year_ago]

    return {
        "last": sig(last),
        "prev": sig(prev),
        "chg": sig(last - prev),
        "asOf": last_day.strftime("%Y-%m-%d"),
        "ret": {
            "1D": change(last, prev, kind),
            "1W": change(last, ref_at(series, last_day - pd.Timedelta(days=7)), kind),
            "1M": change(last, ref_at(series, last_day - pd.DateOffset(months=1)), kind),
            "3M": change(last, ref_at(series, last_day - pd.DateOffset(months=3)), kind),
            "YTD": change(last, ytd_ref, kind),
            "1Y": change(last, ref_at(series, year_ago), kind),
        },
        "hi52": sig(window.max()),
        "lo52": sig(window.min()),
        "hist": {
            "d": [d.strftime("%Y-%m-%d") for d in series.index],
            "c": [sig(v) for v in series.values],
        },
    }


def main():
    symbols = [a[2] for _, _, items in GROUPS for a in items]
    start = (dt.date.today() - dt.timedelta(days=HISTORY_DAYS)).isoformat()
    print(f"Scarico {len(symbols)} strumenti da {start}...")

    raw = yf.download(
        symbols, start=start, interval="1d", group_by="ticker",
        auto_adjust=False, progress=False, threads=True,
    )

    assets, groups, errors = {}, [], []
    for gid, glabel, items in GROUPS:
        ids = []
        for aid, name, symbol, kind in items:
            try:
                series = raw[symbol]["Close"]
                series.index = pd.to_datetime(series.index).tz_localize(None).normalize()
                series = series[~series.index.duplicated(keep="last")]
                data = build_asset(series, kind)
            except Exception as exc:  # strumento non disponibile
                data = None
                print(f"  ! {symbol}: {exc}")
            if not data:
                errors.append(symbol)
                continue
            data.update({"name": name, "symbol": symbol, "kind": kind, "group": gid})
            assets[aid] = data
            ids.append(aid)
        groups.append({"id": gid, "label": glabel, "items": ids})

    if not assets:
        raise SystemExit("Nessun dato scaricato: dati.json non aggiornato.")

    output = {
        "version": 2,
        "updated": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": "Yahoo Finance",
        "headline": [h for h in HEADLINE if h in assets],
        "groups": groups,
        "assets": assets,
        "missing": errors,
    }
    with open("dati.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, separators=(",", ":"))

    print(f"dati.json generato: {len(assets)} strumenti, {len(errors)} mancanti {errors}")


if __name__ == "__main__":
    main()
