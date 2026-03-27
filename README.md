# EMA/RSI Trading Bot – Alpaca Markets

Automatisierter Daytrading-Bot basierend auf der **EMA 9/21 + RSI 14 Strategie**.
Läuft täglich automatisch über GitHub Actions auf dem Alpaca Paper Trading Account.

## Strategie
- **Kaufsignal:** EMA 9 kreuzt EMA 21 von unten (Golden Cross) + RSI zwischen 40–70
- **Verkaufssignal:** EMA 9 kreuzt EMA 21 von oben (Death Cross)
- **Stop-Loss:** 2 % | **Take-Profit:** 4 % | **Risk/Reward:** 1:2
- **Instrumente:** SPY, QQQ, IWM (Fractional Shares)

## Automatischer Zeitplan
Der Bot läuft täglich (Mo–Fr) um:
- **15:30 UTC** – Börseneröffnung New York
- **21:00 UTC** – Kurz vor Börsenschluss New York

## Einrichtung

### 1. Repository forken oder klonen

### 2. GitHub Secrets hinterlegen
Gehe zu: **Settings → Secrets and variables → Actions → New repository secret**

| Secret Name | Wert |
|---|---|
| `ALPACA_API_KEY` | Dein Alpaca API Key (beginnt mit `PK...`) |
| `ALPACA_SECRET_KEY` | Dein Alpaca Secret Key |

### 3. Actions aktivieren
Gehe zum Tab **Actions** und bestätige die Aktivierung.

### 4. Manueller Testlauf
Actions → **EMA/RSI Trading Bot** → **Run workflow**

## Logs einsehen
Actions → Klick auf einen Workflow-Run → Schritt "Trading Bot ausführen"
