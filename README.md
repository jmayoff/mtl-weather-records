# Montréal Weather Records Dashboard

A static dashboard hosted on **GitHub Pages** that shows all-time record high and low temperatures for any calendar date in Montréal, sourced from Environment and Climate Change Canada (ECCC) open data.

## Live demo

`https://YOUR_USERNAME.github.io/mtl-weather-records/`

---

## How it works

```
ECCC bulk CSV API
    ↓ (GitHub Actions, daily cron)
scripts/fetch_records.py
    ↓
data/records.json      ← record high/low per MM-DD
data/stations.json     ← station metadata
    ↓
index.html             ← pure-JS dashboard, no server needed
```

The Python script fetches daily climate data from all known Montréal-area ECCC stations, scans every available year for each station, and computes the all-time record high and low for each calendar day. Results are committed back to the repo as JSON files. The dashboard reads those JSON files — no backend required, no CORS issues.

### Stations covered

| Station | ID | Years |
|---|---|---|
| Montréal/P.E. Trudeau Intl A | 5415 | 1941–2013 |
| Montréal/P.E. Trudeau Intl A | 10761 | 2013–present |
| Montréal McGill | 7024 | 1871–1993 |
| Montréal (UQAM) | 30165 | 1993–2019 |
| Montréal McTavish | 48374 | 2002–present |
| Montréal Ville-Marie | 5417 | 1941–1980 |
| Montréal St-Hubert A | 5424 | 1928–2019 |
| Montréal St-Hubert A | 51157 | 2013–present |

---

## Setup (5 minutes)

### 1. Fork / create the repo

```bash
git clone https://github.com/YOUR_USERNAME/mtl-weather-records
cd mtl-weather-records
```

### 2. Enable GitHub Pages

- Go to **Settings → Pages**
- Source: **Deploy from a branch** → `main` / `/ (root)`

### 3. Run the data fetch (first time)

Either trigger the workflow manually:

- Go to **Actions → Fetch ECCC Records → Run workflow**

Or run locally:

```bash
python scripts/fetch_records.py
git add data/
git commit -m "initial data fetch"
git push
```

> ⚠️ The first fetch takes **~30–60 minutes** because it downloads ~150 years × 8 stations of data. Subsequent daily runs only refresh the current year (fast).

### 4. Done

Visit `https://YOUR_USERNAME.github.io/mtl-weather-records/`

---

## Updating the station list

Edit the `STATIONS` list in `scripts/fetch_records.py`. Each station needs:

```python
{"id": 12345, "name": "Station Name", "start": 1970, "end": None}
```

Set `"end": None` to mean "current year."

You can find station IDs at [climate.weather.gc.ca](https://climate.weather.gc.ca/historical_data/search_historic_data_e.html).

---

## Data licence

Data © Environment and Climate Change Canada, used under the [Open Government Licence – Canada](https://open.canada.ca/en/open-government-licence-canada).
