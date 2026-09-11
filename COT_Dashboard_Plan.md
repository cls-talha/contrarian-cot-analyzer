# CFTC COT Positioning Dashboard — Build Plan

## 1. Objective
A Streamlit app that tracks CFTC Commitment of Traders (COT) data for major
commodities, forex, metals, and indices — showing multi-year history of
positioning by trader category (Commercials/Dealers vs. Large Speculators vs.
Small Speculators), auto-updating weekly when CFTC releases new data.

Core use case: spot extremes/reversals in positioning (e.g., commercials
maximally short = potential top, commercials covering = potential bottom) and
watch the trend of net positioning over time via line charts instead of bars.

---

## 2. Data Source

**CFTC publishes two report types** — pick based on instrument type:

| Report | Covers | Categories |
|---|---|---|
| **Legacy COT** (Futures Only / Futures+Options) | Ag commodities, metals, energy | Commercial, Non-Commercial (Large Spec), Non-Reportable (Small Spec) |
| **TFF (Traders in Financial Futures)** | FX, indices, interest rates | Dealer/Intermediary, Asset Manager, Leveraged Funds, Other Reportables, Non-Reportable |

**Access methods:**
- **Socrata Open Data API (recommended)**: CFTC hosts historical + weekly data at `publicreporting.cftc.gov`. No key needed for light use; free API token recommended for reliability.
  - Legacy (Futures Only): dataset id `6dca-aqww`
  - Legacy (Combined Futures+Options): `jun7-fc8e`
  - TFF (Futures Only): `gpe5-46if`
  - TFF (Combined): `yw9f-hn96`
  - Query via `https://publicreporting.cftc.gov/resource/{dataset_id}.json` with SoQL filters (`$where`, `$limit`, `$order`)
- **Release cadence**: Every Friday ~3:30pm ET, reporting Tuesday's data (report lags market by 3 trading days — build this lag into the UI).
- Filter by `market_and_exchange_names` (contains contract name) or `cftc_contract_market_code`.

---

## 3. Instrument Universe (Full List)

Expanded to the full set of liquid CFTC-reportable futures across every asset
class. Note: **not everything below is COT-reportable** — LME metals (Aluminum,
Zinc, Lead, Tin), most European/Asian exchange contracts (Euro STOXX 50, FTSE
100, Nikkei, Dutch TTF), and some newer contracts (Lithium, Cobalt, EUA/CCA
carbon) are **not** on CFTC's report since they trade on non-US exchanges (LME,
Eurex, ICE Europe, EEX) — CFTC only covers US-regulated (CME, ICE US, CBOT,
NYMEX, COMEX) markets. Mark these clearly as "no COT data" in the config so
the agent doesn't waste time trying to fetch them; they can still be listed
in the UI as price-only reference if you add the optional price overlay.

### Equity Indices & Volatility (TFF report)
- E-mini / Micro E-mini S&P 500 (ES / MES)
- E-mini / Micro E-mini Nasdaq 100 (NQ / MNQ)
- E-mini / Micro E-mini Dow Jones 30 (YM / MYM)
- E-mini / Micro E-mini Russell 2000 (RTY / M2K)
- VIX Futures / Mini VIX Futures (CBOE)
- ⚠️ Not COT-reportable (non-US exchange): Nikkei 225, Euro STOXX 50, FTSE 100, MSCI EM/EAFE, Hang Seng, Nifty 50

### Energy & Environmental (Legacy report)
- WTI Crude Oil (CL)
- Brent Crude Oil (BZ, ICE US — **is** reportable on CFTC via ICE Futures U.S.)
- RBOB Gasoline (RB)
- Heating Oil (HO)
- Natural Gas — Henry Hub (NG)
- ⚠️ Not COT-reportable: Low Sulphur Gasoil, Dutch TTF, Electricity/Power (PJM/ERCOT/MISO), Coal (API2/API4), EUA/CCA carbon allowances, RINs

### Metals (Legacy report)
- Gold (GC / MGC)
- Silver (SI)
- Platinum (PL)
- Palladium (PA)
- Copper (HG)
- ⚠️ Not COT-reportable (LME): Aluminum, Zinc, Lead, Nickel, Tin, Iron Ore
- ⚠️ Not COT-reportable (new/thin CFTC coverage — verify): Lithium, Cobalt

### Agriculture & Livestock (Legacy report)
- Corn (ZC)
- Soybeans (ZS), Soybean Meal (ZM), Soybean Oil (ZL)
- Wheat — Chicago SRW (ZW), Kansas City HRW (KE)
- Rough Rice (ZR), Oats (ZO)
- Sugar #11 (SB)
- Coffee C (KC)
- Cocoa (CC)
- Cotton #2 (CT)
- Frozen Concentrated Orange Juice (OJ)
- Lumber (LBR)
- Live Cattle (LE), Feeder Cattle (GF), Lean Hogs (HE)
- Class III & Class IV Milk, Cash-Settled Butter & Cheese

### FX (TFF report)
- Euro FX (6E)
- British Pound (6B)
- Japanese Yen (6J)
- Australian Dollar (6A)
- Canadian Dollar (6C)
- Swiss Franc (6S)
- New Zealand Dollar (6N)
- U.S. Dollar Index (DX)
- Mexican Peso (6M)
- Brazilian Real (6L)
- South African Rand (6Z)

### Digital Assets (TFF report — CME regulated)
- Bitcoin Futures (BTC) & Micro Bitcoin (MBT)
- Ether Futures (ETH) & Micro Ether (MET)
- Micro XRP Futures

### Rates (optional, TFF report)
- 2Y, 5Y, 10Y Treasury futures
- Fed Funds futures

---

Maintain this as a config dict mapping display name → `cftc_contract_market_code`
+ report type (legacy vs TFF) + `cot_available: bool`. Items flagged
non-reportable above should still get a config entry (with `cot_available:
False`) so the UI can show them grayed out / price-only rather than silently
omitting them — useful since you'll likely want to expand coverage later if
CFTC adds a contract.

---

## 4. Data Model / Processing

For each instrument, from raw weekly rows compute:

- **Net position** per category = Long − Short (e.g., `noncomm_positions_long_all - noncomm_positions_short_all`)
- **Net position as % of open interest** (normalizes across time — more useful than raw contracts for spotting extremes)
- **Week-over-week change** in net position (flow, not just level)
- **Z-score / percentile rank** of current net position vs trailing 1yr, 3yr, 5yr — this is what flags "extreme" positioning
- Store commercials, large specs, small specs (legacy) OR dealer/asset mgr/leveraged funds/other/nonreportable (TFF) as separate series

**Storage:** Pull full history once (CFTC has data back to 1986 legacy / 2010ish TFF), cache locally as Parquet/SQLite (one table per instrument or one long table with instrument column). On each run, fetch only rows newer than last stored `report_date` and append — avoids re-pulling full history every time.

---

## 5. Dashboard Layout (Streamlit)

**Sidebar controls:**
- Asset class filter (Metals / Energy / Ag / FX / Indices)
- Instrument selector (single or multi-select for comparison)
- Report type toggle (Futures Only vs Combined) where applicable
- Date range slider (e.g., last 1/3/5/10 yr / all history)
- Toggle: raw contracts vs % of open interest vs z-score view

**Main panel per instrument:**
1. **Header row**: current net positioning for each category, WoW change (colored arrows), extremity badge (e.g., "Large Specs: 92nd percentile — near historical high")
2. **Main line chart**: net position over time, one line per category (Commercial / Large Spec / Small Spec, or Dealer/AM/LevFund/Other for TFF), price overlay of the underlying futures on secondary y-axis (optional, needs a price data source — see note below)
3. **Secondary chart**: open interest over time (context for whether positioning changes are meaningful vs. low-liquidity noise)
4. **Extremes table**: current z-score/percentile per category, sortable

**Overview/scanner page** (across all instruments):
- Table: every instrument, current net position, WoW change, percentile rank — sortable/filterable, so user can scan for "who's most stretched" in one view across the full universe. This is likely the most-used page.

---

## 6. Price Overlay (optional but valuable)
COT alone shows positioning; overlaying price shows whether positioning is diverging from price (a classic reversal signal). Needs a separate free price feed — `yfinance` works for most futures/FX/index proxies. Flag this as Phase 2 if it adds complexity.

---

## 7. Update / Scheduling
- Streamlit app itself: on load, check latest stored `report_date` vs latest available on CFTC; if new week exists, fetch delta and refresh cache.
- Optional: separate scheduled job (cron / GitHub Actions) that runs Fridays after 3:30pm ET to pre-populate cache so the app loads fast without waiting on API calls.

---

## 8. Suggested Build Phases for the Coding Agent
1. **Phase 1 — Data layer**: instrument config, Socrata fetch functions (legacy + TFF), local cache (SQLite/Parquet), computed metrics (net position, % OI, z-score).
2. **Phase 2 — Single-instrument view**: sidebar selector + main line chart + extremes table for one instrument at a time.
3. **Phase 3 — Overview/scanner table** across full universe.
4. **Phase 4 — Multi-instrument comparison** (overlay 2-3 instruments' net positioning on one chart).
5. **Phase 5 (optional)** — price overlay via yfinance, scheduled auto-refresh, alerts (e.g., notify when any instrument crosses 90th/10th percentile).

---

## 9. Tech Stack Summary
- **Frontend/app**: Streamlit
- **Data fetch**: `requests` or `sodapy` (Socrata Python client) against CFTC API
- **Storage**: SQLite or Parquet files, local
- **Processing**: pandas
- **Charts**: Plotly (interactive, zoomable — better than matplotlib for this use case) or Streamlit-native `st.line_chart` for quick version
- **Optional price data**: yfinance
