# License Plate Activation and Cancellation Report

Automated analytics pipeline for daily monitoring of vehicle plate activations and cancellations across multiple insurance brands in a fleet-protection operation.

---

## Project Overview

This project delivers **operational intelligence on plate lifecycle events**—activations, full set cancellations, partial benefit cancellations, and finalized contracts—for four commercial brands: **Segtruck**, **Stcoop**, **Viavante**, and **Tag**.

**Objectives**

- Consolidate plate-level data from AWS Athena (silver-layer insurance schemas) into a single, auditable reporting base.
- Produce daily executive summaries segmented by company and cancellation type.
- Distribute results automatically to stakeholders via Excel, visual snapshots, and team channels.

**Business problem**

Commercial and operations teams need a reliable, same-day view of how many plates were activated versus cancelled, broken down by brand and cancellation category (full set vs. benefit-only). Manual extraction from operational systems was slow, error-prone, and inconsistent across weekends. This solution standardizes definitions, deduplicates records at chassis level, and automates the full report cycle—including distribution—so leadership can react quickly to portfolio movement.

---

## Technologies Used

| Area | Tools |
|------|--------|
| **Language & analytics** | Python, Pandas |
| **Query layer** | SQL (Presto/Athena dialect), AWS Athena |
| **Cloud & data lake** | AWS Wrangler, Amazon S3 (Parquet bronze layer), boto3 |
| **Local / exploratory querying** | DuckDB, Jupyter Notebook |
| **Reporting & delivery** | Microsoft Excel (openpyxl), Html2Image, Power BI, SharePoint (OneDrive) |
| **Automation** | Scheduled Python ETL, desktop automation (PyAutoGUI) for messaging |

---

## Key Libraries

| Library | Role in the project |
|---------|---------------------|
| **pandas** | Merging cancellation bases, date filtering, deduplication, commercial categorization, delinquency flags, and KPI aggregation |
| **awswrangler** | Executing SQL files against Athena and loading results into DataFrames |
| **openpyxl** | Populating multi-sheet Excel templates (detail tabs + summary dashboard) |
| **html2image** | Rendering HTML summary tables as PNG for quick visual distribution |
| **pyautogui** | Automating WhatsApp delivery of the daily snapshot (optional end-to-end step) |
| **duckdb** + **boto3** | Prototype/local pipelines reading Parquet from S3 when Athena is not used (notebooks and backup scripts) |
| **datetime** | Business calendar logic (e.g., Monday reports covering Friday–Sunday) |

---

## Data Processing & SQL Logic

### Main queries (`sql/`)

Three production SQL assets drive the pipeline:

1. **`all_boards_ATIVOS.sql`** — Active plates with valid plate/chassis, active set status (`iss.id = 7`), and benefit status **ATIVO**.
2. **`all_boards_CANCELAMENTOS_INTEGRAIS.sql`** — Full set cancellations: `date_cancellation` populated, set status excluding **ATIVO** and **RENOVACAO**.
3. **`all_boards_CANCELAMENTOS_PARCIAIS.sql`** — Benefit-level cancellations: status **CANCELADO**, **FINALIZADO**, or **NAO RENOVADO**, with benefit update date from 2025 onward.

Each query **UNIONs the same logical model across four schemas** (`silver`, `stcoop`, `viavante`, `tag`), tagging records with a company dimension.

### Joins & grain

- Core path: `insurance_registration` → `insurance_reg_set` → `insurance_reg_set_coverage` → vehicle/trailer entities.
- Enrichment: customer and unit (`catalogo`, `representante`), consultant (`vendedor`), benefit catalog (`benefits`, `category`, `price_list_benefits`), support user.
- **Grain**: one row per chassis after `ROW_NUMBER() ... PARTITION BY chassi ORDER BY data_registro DESC` and `rn = 1` (most recent registration wins).

### Python-side business rules

- **Partial vs. integral**: Partial cancellations are unioned with integral; chassis still active in the ativos base are removed from partials (handles renewals in another set).
- **Commercial channel**: Units matching franchise keywords are classified as *Unidades/Franquias* vs. *Parceiros/Corretores/FTR*.
- **Delinquency**: Cross-reference with a 45+ day overdue invoice query; flags cancelled sets linked to delinquent portfolios (with test/association exclusions).
- **Period logic**: Weekdays report prior day; **Mondays aggregate Friday–Sunday** for activations and cancellations.

---

## Analysis & Notebook Logic

### Production path — `python/ETL_ativ_cancel.py`

An 8-step class-based ETL (`ETL_relat_ativ_cancel`):

1. **Extract** — Athena reads for ativos, integral and partial cancellations.
2. **Transform cancellations** — Concatenate, dedupe by chassis, normalize dates and categories.
3. **Enrich** — Apply 45+ delinquency flag.
4. **Calculate metrics** — Counts by company: activations, partial cancellations, integral cancelled vs. finalized.
5. **Fill Excel** — Sheets: `ATIVOS`, `CANCELAMENTOS`, `CANCELAMENTOS ONTEM`, historical `BASE`, summary `RELATORIO`.
6. **Generate image** — HTML table → PNG executive summary.
7. **Distribute** — Optional WhatsApp automation with period message.
8. **Archive** — Versioned file in `history/` and sync to SharePoint.

### Notebooks — `notebooks/`, `notes/`, `bkp/`

- **`ETL_ativ_cancel.ipynb`**: Interactive version of the same workflow used to design and validate transformations before production scripting.
- **`s3_base.ipynb`** (and related `bkp/s3_base_*.py`): Builds in-memory DuckDB views over S3 Parquet landing zones to test SQL locally against bronze data.
- **Power BI** (`reports/`): Dashboards for broader plate analysis, activation relationship views, and cancellation-focused reporting.

---

## Key Highlights

- **Multi-brand data model** — Single reporting contract across four Athena schemas with consistent joins and status rules.
- **Chassis-level deduplication** — SQL `ROW_NUMBER` plus Pandas `drop_duplicates` to avoid double-counting renewals and duplicate sets.
- **Cancellation taxonomy** — Separates integral set events (cancelled vs. finalized) from partial benefit cancellations for accurate KPI interpretation.
- **Weekend-aware scheduling** — Monday batch automatically rolls up three days without manual date adjustment.
- **End-to-end automation** — From lake query to Excel, visual summary, team notification, and cloud folder sync in one run.
- **Analytical rigor** — Delinquency cross-check and active-set exclusion reduce false cancellation signals in operational metrics.

---

## Project Structure

```
relatorio_ativacoes_cancelamentos/
├── python/ETL_ativ_cancel.py    # Production ETL (entry point)
├── sql/                         # Athena SQL (ativos, cancelamentos)
├── notebooks/                   # Jupyter prototypes
├── reports/                     # Power BI dashboards (.pbix)
├── template/                    # Excel report template (gitignored)
├── history/                     # Dated report outputs (gitignored)
├── img/                         # Generated summary images (gitignored)
├── notes/                       # S3 / DuckDB exploration
└── bkp/                         # Legacy scripts, SQL variants, backups
```

---

## Running the Pipeline

```bash
python python/ETL_ativ_cancel.py
```

**Prerequisites**: AWS credentials with Athena access to the `silver` database, local paths configured in `ETL_relat_ativ_cancel.PATHS`, and the Excel template present under `template/`.

> Sensitive outputs (`.xlsx`, `.png`) and credentials are excluded via `.gitignore`.
