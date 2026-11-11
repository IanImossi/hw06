# HW6 — DAX Measure Library: AUM & Performance

Wildcat Capital measure library in Power BI, reconciled to pandas, with design questions and one Claude-assisted measure.

**Result:** 91 Power BI values reconciled to pandas: **91 match**. The largest difference is $0.0001 (from Excel's 15-digit precision); the tolerances are 0.01 for currency and 0.0001 for ratios.

## Structure

```
hw06/
├── README.md
├── HW06_DAX_Measure_Library.md        assignment directions
├── powerbi_dax_guide.md               DAX patterns and export guide
├── Wildcat_Star_Model.pbix            posted starting model
├── Wildcat Capital Clean/             the 8 clean CSVs (pandas side)
├── powerbi/
│   ├── hw06.pbix                      model + _Measures table + "Measures" report page
│   ├── measures.md                    Part A documentation + Part C answers
│   ├── export_queries.dax             DAX queries that produce reports/powerbi_values.csv
│   └── Measures.png                   screenshot of the report page
├── scripts/
│   ├── 01_reconcile_measures.py       Part B: pandas twins of every measure + comparison
│   └── 02_part_c_evidence.py          Part C: pandas evidence for questions (a)–(d)
├── reports/
│   ├── powerbi_values.csv             Power BI values (measure, slice, value)
│   ├── pandas_values.csv              pandas values, written by the script
│   └── measure_reconciliation.csv     measure, slice, powerbi_value, pandas_value, abs_diff, match
└── claude/
    ├── model_metadata.md              INFO.VIEW export (columns, relationships, measures)
    ├── dax_session.md                 prompt + Claude Desktop's full response (measure 9)
    └── verification.md                how Claude's AUM-Weighted Alpha was verified
```

## How to run

Requires Python 3 with `pandas` and `numpy` (`pip install pandas numpy`). Run from the `hw06` folder:

```bash
python scripts/01_reconcile_measures.py   # writes reports/pandas_values.csv and reports/measure_reconciliation.csv
python scripts/02_part_c_evidence.py      # prints the numbers used in the Part C answers
```

To regenerate `reports/powerbi_values.csv`: open `powerbi/hw06.pbix`, run queries 1–6 from `powerbi/export_queries.dax` in **DAX query view**, and paste the result grids into the CSV (`measure, slice, value`). The script accepts comma- or tab-separated files and skips repeated header rows.

**Slices covered (91 rows):**
- every measure at the **Grand Total** (16)
- measures 1, 4, 6–10 and `AUM (naive SUM)` **by year**, 2020–2024 (45)
- measures 1, 3, 4, 7–11 **by client tier for 2024** (27)
- measure 5 for **December 2024** (3)

`AUM (naive SUM)` matches its pandas twin (`.sum()` of `aum`) at $566.7B: both tools make the same mistake.

## Claude Code review of `01_reconcile_measures.py`

I asked Claude Code to review the script before committing. None of its findings changed a current result, but they would cause false mismatches, crashes or hidden errors on different input. After the fixes, I re-ran the script: the pandas values are identical and all 91 rows still match.

| # | Claude Code flagged | Why it matters | What I did |
|---|---|---|---|
| 1 | **Empty slices give 0 in pandas but BLANK in DAX.** `SUM` over no rows is BLANK in DAX, and BLANK − BLANK is still BLANK, but pandas `.sum()` returns 0. This affects `total_fees`, `net_flows` and `aum_naive` (L126–136), and `fee_yield_bps` returns 0 where DAX returns blank. | Any slice with no fees or no transactions would show up as a false mismatch. No current slice is empty. | **Fixed.** Added `sum_or_blank()`, used by `aum_naive`, `total_fees`, `net_flows`, `avg_monthly_aum` and `fee_yield_bps`. `net_flows` returns blank only when deposits and withdrawals are both blank, as in DAX. Tested: an empty 2019 window now returns blank for all five. |
| 2 | **`to_number` crashes on formatted values.** It strips `$` and `,` but not `%`, and doesn't handle accounting negatives like `($1,234.00)` (L282–288). | A re-export containing `19.58%` would raise a `ValueError` and stop the whole run, instead of reporting a mismatch. | **Fixed.** `to_number` now handles `%` (÷ 100), `($1,234.00)`, `$`, commas and the Unicode minus sign. Anything else is caught, and that row is reported as `match = False` instead of stopping the run. Tested with `19.58%`, `($1,234.00)` and `abc`. |
| 3 | **Duplicate Power BI rows aren't caught.** If a measure/slice pair is pasted twice, the outer merge (L295) creates two rows, and both can match. | The "91 match" count could be inflated without any warning. | **Fixed.** The script now exits with an error listing any duplicate measure/slice rows. Tested by pasting one row twice. |
| 4 | **`is_return_suspect != 1` isn't exactly the DAX `= 0`** (L188). A NaN flag passes the pandas filter but fails the DAX one. | No effect today, because the column has no NaNs, but `== 0` mirrors the DAX exactly at no cost. | **Fixed.** Changed to `is_return_suspect == 0`. |
| 5 | **The Fee Yield tolerance is very tight.** It's compared at `RATIO_TOL = 0.0001` on a value of about 43 bps, a relative precision of about 2e-6. | It passes because Power BI exports full precision, but a value rounded to the displayed format (`43.15`) would fail. | **Kept on purpose.** The assignment sets 0.0001 for ratios, and my values come from DAX query view at full precision, so the strict tolerance proves an exact match rather than a rounded one. |
| 6 | **Importing the script loads every CSV.** `load()` runs at import time (L75), and `Ctx`'s defaults depend on it; `02_part_c_evidence.py` relies on this side effect. | Fine for a homework pipeline, but a hidden cost if the code is reused. | **Left as is.** Loading once at import keeps both scripts on the same data and logic; it is documented here for anyone reusing the code. |

## Mismatches and fixes

1. **"Dec 2024" turned into a date (Power BI side, labels only).** I first collected the DAX query results in Excel (`powerbi_values.xlsx`). Excel auto-converted the slice label `Dec 2024` into the date 12/1/2024, so those 3 rows could not join to the pandas rows. The numbers were right; the label was wrong. **Fix:** saved the file as CSV with the text label `Dec 2024` restored. Excel also cut values to 15 significant digits, which explains the largest `abs_diff` of $0.0001, still well inside tolerance.
2. **2024 tier table showed all-years values (report page).** The tier table on the first version of the **Measures** page had no visual-level filter. Its Fee Yield and Organic Growth Rate therefore didn't match the 2024 pandas values: for example, HNW Fee Yield was 61.68 bps instead of 61.39, and HNW Organic Growth was 4.19% instead of 1.18%. Ending AUM looked right only because the last snapshot is December 2024 either way. The Power BI side was wrong. **Fix:** added the visual-level filter `dim_date[year]` = 2024. The exported reconciliation values were unaffected, because `export_queries.dax` applies the 2024 filter itself.

## Notes

- **Tools:**
  - Claude drafted the DAX documentation and the scripts.
  - I ran the scripts in VS Code.
  - Claude Code reviewed the reconciliation script (see above).
  - The Part D measure was drafted in a separate Claude Desktop session (`claude/dax_session.md`).
- **Model file:** `powerbi/hw06.pbix` is about 21 MB, under GitHub's 100 MB limit.
- **Part D:** the prompt included the full measures grid from the metadata export, so Claude saw my existing `AUM-Weighted Alpha` and reviewed it rather than drafting from scratch. This is disclosed and judged in `claude/verification.md`.
