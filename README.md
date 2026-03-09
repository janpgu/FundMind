# FundMind

Downloads fund documents from [fundinfo.com](https://www.fundinfo.com) for a list of ISINs and tracks what was downloaded in an Excel file.

## What it does

Given a list of fund ISINs in `funds.xlsx`, the script:

1. Queries the fundinfo.com API for each ISIN to discover all available documents
2. Downloads every document type available (prospectus, monthly report, KIID, etc.)
3. Picks the best language variant per document (EN > DE > FR > IT > ES)
4. Skips files that already exist locally (safe to re-run)
5. Updates `funds.xlsx` with a column per document type showing the downloaded filename

## Project structure

```
FundMind/
├── funds.xlsx                          # Input: ISINs to process; Output: download status columns
├── fund_mind.py                        # Main script
└── fund_document_library/              # Downloaded PDFs (created automatically)
    └── {ISIN}/
        └── {ISIN}_{Type}_{Lang}_{Date}.pdf
```

## funds.xlsx format

The spreadsheet must have at minimum these columns:

| IDINSTRUMENT | DESCRIPTION |
|---|---|
| CH0002788708 | UBS Asia Equity Fund USD P |
| ... | ... |

After running, metadata and document columns are added:

| IDINSTRUMENT | DESCRIPTION | Legal Form | TER Excluding Performance Fee | EPT Valuation Frequency | EPT Investment Objective | ManCo | Fund Domicile Alpha-2 | Fund Launch Date | Fund Currency | Prospectus | Annual Report | ... |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| CH0002788708 | UBS Asia Equity Fund USD P | SICAV | 1.44 | Daily | ... | UBS Fund Management | CH | 1988-11-28 | USD | CH0002788708_PR_EN_2025-10-13.pdf | CH0002788708_AR_EN_2025-10-31.pdf | ... |

Empty cells mean the data was not available from fundinfo.com for that fund.

## Metadata fields

These columns are populated from the fundinfo.com `fund/Data` endpoint:

| Column | Field code | Description |
|---|---|---|
| Legal Form | OFST160100 | Legal structure of the fund (e.g. SICAV, FCP) |
| TER Excluding Performance Fee | OFST452100 | Total expense ratio excluding performance fee |
| EPT Valuation Frequency | OFEP010100 | How often the fund is valued (e.g. Daily) |
| EPT Investment Objective | OFEP040400 | Investment objective as per the EPT template |
| ManCo | OFST001020 | Management company name |
| Fund Domicile Alpha-2 | OFST010010 | Country of domicile (ISO 3166-1 alpha-2, e.g. LU, IE, CH) |
| Fund Launch Date | OFST010240 | Date the fund was launched |
| Fund Currency | OFST010410 | Base currency of the fund (e.g. USD, EUR, CHF) |

## Document types

| Code | Column label | Description |
|---|---|---|
| AR | Annual Report | Annual report |
| ESC | ESG Scorecard | ESG scorecard |
| KFS | KFS | Key facts sheet |
| KIID | KIID | Key investor information document |
| KMS | KMS | Key information document (Switzerland) |
| KPP | KPP | Key information document (PRIIPs, Switzerland) |
| LM | Legal Message | Legal / regulatory message |
| MR | Monthly Report | Monthly factsheet |
| PR | Prospectus | Full prospectus |
| PRP | PRIIPs | PRIIPs KID |
| SAR | Semi-Annual Report | Semi-annual report |
| SUP | Supplement | Fund supplement |

Not all document types are available for every fund — it depends on what fundinfo.com has indexed.

## File naming

Downloaded files follow the pattern:

```
{ISIN}_{DocType}_{Language}_{Date}.pdf
```

Example: `fund_document_library/CH0002788708/CH0002788708_PR_EN_2025-10-13.pdf`

## Setup

Requires Python 3.12+. Create the conda environment from the provided file:

```bash
conda env create -f fundmind-environment.yml
conda activate fundmind
```

> **Note:** If you see an `openpyxl` import error after a fresh environment setup, try reinstalling numpy:
> ```
> pip install --force-reinstall numpy
> ```
> This fixes a DLL conflict that can occur with certain conda numpy builds.

## Usage

```bash
conda activate fundmind
python fund_mind.py
```

Run from the project directory (where `funds.xlsx` lives).

## Testing

```bash
conda activate fundmind
python -m pytest tests/ -v
```

Run from the project directory (where `funds.xlsx` lives). The `fund_document_library/` folder is created automatically.

### Re-running

The script is idempotent. Files that already exist in `fund_document_library/` are skipped and still recorded in the Excel output. You can safely add new ISINs to `funds.xlsx` and re-run — existing downloads are not touched.

### Output

Log messages (with timestamps and level) go to stderr. The human-readable summary goes to stdout:

```
2026-03-08 23:02:33 | INFO | Loaded 1 fund(s) from funds.xlsx
2026-03-08 23:02:33 | INFO | Processing | ISIN=CH0002788708 | Name=UBS Asia Equity Fund USD P
2026-03-08 23:02:35 | INFO | [PR] Downloading | lang=EN | date=2025-10-13 | file=CH0002788708_PR_EN_2025-10-13.pdf
...

============================================================
Summary:
  [OK] CH0002788708: downloaded=['AR', 'ESC', 'KMS', 'KPP', 'LM', 'MR', 'PR', 'PRP', 'SAR'] errors=[]
```

## Configuration

All tuneable settings live in the `Config` dataclass at the top of the script. The defaults work out of the box but can be adjusted:

| Field | Default | Description |
|---|---|---|
| `excel_file` | `funds.xlsx` | Path to the input/output spreadsheet |
| `output_dir` | `fund_document_library` | Root folder for downloaded PDFs |
| `fundinfo_profile` | `CH-prof` | Investor profile sent to fundinfo.com (drives both the API URL and the `DU` cookie) |
| `lang_pref` | `EN, DE, FR, IT, ES` | Language preference order |
| `max_concurrency` | `5` | Max number of funds processed in parallel |
| `request_timeout` | `30` | HTTP timeout in seconds |
| `retry_count` | `3` | Number of download attempts before giving up |
| `polite_delay_seconds` | `0.3` | Delay between document downloads for a single fund |

To change a setting, edit the `Config` dataclass defaults, or instantiate it with overrides if calling `run_pipeline` from another script:

```python
from fund_mind import Config, run_pipeline
import asyncio

config = Config(fundinfo_profile="DE-retail", max_concurrency=2)
results = asyncio.run(run_pipeline(config))
```

## How fundinfo.com access works

The script uses the fundinfo.com public API without requiring an account or API key. Two cookies are set to bypass the investor profile disclaimer:

- `DU=CH-prof` — sets the investor profile to Switzerland / Professional (avoids the country selector popup)
- `PrivacyPolicy=true` — dismisses the cookie consent banner

Two API endpoints are used:

**Document discovery:**
```
GET https://www.fundinfo.com/en/CH-prof/LandingPage/Data?skip=0&query={ISIN}
```
Returns a JSON response containing all available documents in `Data[0].D`, organised by document type code. Each entry includes the download URL, language, date, and an `Active` boolean flag.

**Fund metadata:**
```
GET https://www.fundinfo.com/en/CH-prof/fund/Data?OFST020000={ISIN}
```
Returns fund-level metadata fields in `Data.S`, keyed by EPT/OFST field codes (legal form, fees, domicile, currency, etc.).

### Language selection

For each document type, the script:
1. Filters to active documents (falls back to inactive if none active)
2. Sorts by date descending (most recent first)
3. Picks the first match in language preference order: EN → DE → FR → IT → ES
4. Falls back to whatever language is available if none of the preferred languages exist
