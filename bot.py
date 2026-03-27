"""
EMA 9/21 + RSI Trading Bot
Alpaca Paper Trading | 500 EUR simuliert (~550 USD)
Strategie: Golden Cross EMA 9/21 + RSI Filter (40-70)
Risk/Reward: 1:2 | Stop-Loss 2% | Take-Profit 4%
"""

import os
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pandas as pd
import numpy as np

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import (
    MarketOrderRequest,
    StopLossRequest,
    TakeProfitRequest,
)
from alpaca.trading.enums import OrderSide, TimeInForce
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.data.enums import DataFeed

# ─── Konfiguration ────────────────────────────────────────────────────────────
# API-Keys werden sicher aus GitHub Secrets geladen (keine Passwörter im Code!)
API_KEY    = os.environ["ALPACA_API_KEY"]
SECRET_KEY = os.environ["ALPACA_SECRET_KEY"]

SYMBOLS         = ["SPY", "QQQ", "IWM"]
EMA_FAST        = 9
EMA_SLOW        = 21
RSI_PERIOD      = 14
RSI_MIN         = 40
RSI_MAX         = 70
STOP_LOSS_PCT   = 0.02
TAKE_PROFIT_PCT = 0.04
POSITION_PCT    = 0.30
SIMULATED_CAPITAL = 550.0  # ~500 EUR

# ─── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

# ─── Clients ──────────────────────────────────────────────────────────────────
trading_client = TradingClient(API_KEY, SECRET_KEY, paper=True)
data_client    = StockHistoricalDataClient(API_KEY, SECRET_KEY)


# ─── Hilfsfunktionen ──────────────────────────────────────────────────────────

def get_bars(symbol: str, days: int = 60) -> pd.DataFrame:
    end   = datetime.now(ZoneInfo("America/New_York"))
    start = end - timedelta(days=days)
    req = StockBarsRequest(
        symbol_or_symbols=symbol,
        timeframe=TimeFrame.Day,
        start=start,
        end=end,
        feed=DataFeed.IEX,
    )
    bars = data_client.get_stock_bars(req)
    df = bars.df
    if isinstance(df.index, pd.MultiIndex):
        df = df.xs(symbol, level="symbol")
    return df.sort_index()


def compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["ema_fast"] = df["close"].ewm(span=EMA_FAST, adjust=False).mean()
    df["ema_slow"] = df["close"].ewm(span=EMA_SLOW, adjust=False).mean()
    delta    = df["close"].diff()
    gain     = delta.clip(lower=0)
    loss     = -delta.clip(upper=0)
    avg_gain = gain.ewm(com=RSI_PERIOD - 1, adjust=False).mean()
    avg_loss = loss.ewm(com=RSI_PERIOD - 1, adjust=False).mean()
    rs       = avg_gain / avg_loss.replace(0, np.nan)
    df["rsi"] = 100 - (100 / (1 + rs))
    df["cross_above"] = (df["ema_fast"] > df["ema_slow"]) & \
                        (df["ema_fast"].shift(1) <= df["ema_slow"].shift(1))
    df["cross_below"] = (df["ema_fast"] < df["ema_slow"]) & \
                        (df["ema_fast"].shift(1) >= df["ema_slow"].shift(1))
    return df


def get_signal(symbol: str) -> dict:
    try:
        df   = get_bars(symbol)
        if len(df) < EMA_SLOW + 5:
            return {"symbol": symbol, "signal": "NONE", "reason": "Zu wenig Daten",
                    "close": 0, "ema_fast": 0, "ema_slow": 0, "rsi": 0}
        df   = compute_indicators(df)
        last = df.iloc[-1]
        signal, reason = "NONE", ""
        if last["cross_above"] and RSI_MIN <= last["rsi"] <= RSI_MAX:
            signal = "BUY"
            reason = f"Golden Cross | RSI={last['rsi']:.1f}"
        elif last["cross_below"]:
            signal = "SELL"
            reason = f"Death Cross | RSI={last['rsi']:.1f}"
        return {"symbol": symbol, "signal": signal, "reason": reason,
                "close": last["close"], "ema_fast": last["ema_fast"],
                "ema_slow": last["ema_slow"], "rsi": last["rsi"]}
    except Exception as e:
        return {"symbol": symbol, "signal": "ERROR", "reason": str(e),
                "close": 0, "ema_fast": 0, "ema_slow": 0, "rsi": 0}


def get_position(symbol: str):
    try:
        return trading_client.get_open_position(symbol)
    except Exception:
        return None


def place_buy_order(symbol: str, price: float) -> bool:
    try:
        notional     = round(SIMULATED_CAPITAL * POSITION_PCT, 2)
        stop_price   = round(price * (1 - STOP_LOSS_PCT), 2)
        target_price = round(price * (1 + TAKE_PROFIT_PCT), 2)
        log.info(f"  BUY {symbol}: ${notional:.2f} | SL=${stop_price:.2f} | TP=${target_price:.2f}")
        order = trading_client.submit_order(MarketOrderRequest(
            symbol=symbol,
            notional=notional,
            side=OrderSide.BUY,
            time_in_force=TimeInForce.DAY,
            order_class="bracket",
            stop_loss=StopLossRequest(stop_price=stop_price),
            take_profit=TakeProfitRequest(limit_price=target_price),
        ))
        log.info(f"  ✅ Order platziert: ID={order.id}")
        return True
    except Exception as e:
        log.error(f"  ❌ Fehler BUY {symbol}: {e}")
        return False


def place_sell_order(symbol: str) -> bool:
    try:
        trading_client.close_position(symbol)
        log.info(f"  ✅ Position {symbol} geschlossen")
        return True
    except Exception as e:
        log.error(f"  ❌ Fehler SELL {symbol}: {e}")
        return False


# ─── Hauptlogik ───────────────────────────────────────────────────────────────

def run():
    log.info("=" * 60)
    log.info(f"SCAN – {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    log.info("=" * 60)

    acc = trading_client.get_account()
    log.info(f"Konto: Kaufkraft=${float(acc.buying_power):,.2f} | "
             f"Portfolio=${float(acc.portfolio_value):,.2f}")

    for symbol in SYMBOLS:
        log.info(f"\n--- {symbol} ---")
        sig      = get_signal(symbol)
        position = get_position(symbol)

        log.info(f"  Kurs:   ${sig['close']:.2f} | "
                 f"EMA9={sig['ema_fast']:.2f} | EMA21={sig['ema_slow']:.2f} | "
                 f"RSI={sig['rsi']:.1f}")
        log.info(f"  Signal: {sig['signal']}  {sig['reason']}")

        if sig["signal"] == "BUY" and position is None:
            place_buy_order(symbol, sig["close"])
        elif sig["signal"] == "SELL" and position is not None:
            place_sell_order(symbol)
        elif sig["signal"] == "BUY" and position is not None:
            log.info("  → Position bereits offen – kein neuer Trade")
        else:
            log.info("  → Kein Handlungsbedarf")

    log.info("\n" + "=" * 60)
    log.info("SCAN ABGESCHLOSSEN")
    log.info("=" * 60)


if __name__ == "__main__":
    run()
