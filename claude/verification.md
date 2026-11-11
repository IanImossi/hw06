# Part D — Verification of Claude's `AUM-Weighted Alpha`

**Context:** my prompt included the full measures grid from `model_metadata.md`, so Claude saw my existing `AUM-Weighted Alpha` and said so in its first line. Instead of drafting from scratch, it proposed a rewrite. This page judges that rewrite.

## 1. Did Claude's measure run as written? What did its test query return?

Claude's version differs from mine in three ways:
- it finds the last date with `MAX ( fact_portfolio_snapshot[snapshot_date] )` instead of `LASTNONBLANK`;
- it pins that date with `TREATAS ( { LastSnapshot }, dim_date[Date] )`;
- it wraps the suspect filter in `KEEPFILTERS`.

**Ran as written: yes.** I made no edits. The table was still named `_Measure` when I ran it, so Claude's `DEFINE MEASURE '_Measure'[…]` lines worked as given.

Its test query returned:

| Slice | Last snapshot | Claude's `AUM-Weighted Alpha` | Expected (pandas) |
|---|---|---:|---:|
| Grand total (query 1) | 2024-12-01 | 1.4480% | 1.4480% |
| 2020 | 2020-12-01 | −0.6802% | −0.6802% |
| 2021 | 2021-12-01 | −0.1574% | −0.1574% |
| 2022 | 2022-12-01 | 2.8494% | 2.8494% |
| 2023 | 2023-12-01 | 1.7689% | 1.7689% |
| 2024 | 2024-12-01 | 1.4480% | 1.4480% |
| Year total row | — | 1.4480% | 1.4480% |
| 2024 HNW (query 3) | 2024-12-01 | 1.3988% | 1.3988% |
| 2024 Retail | 2024-12-01 | 2.4041% | 2.4041% |
| 2024 UHNW | 2024-12-01 | 1.4097% | 1.4097% |
| 2024 tier total row | — | 1.4480% | 1.4480% |

Every value equals pandas to 4 decimal places. The last snapshot is always the 1st of December, never a month-end date with no rows.

## 2. Rows of `reports/measure_reconciliation.csv` that prove it
All 9 rows with `measure = AUM-Weighted Alpha` (`Grand Total`, `Year 2020`–`Year 2024`, `2024 Tier HNW` / `Retail` / `UHNW`) have `match = True`, with an `abs_diff` of 0 or less than 1e-12. That proves my measure equals pandas. Claude's measure returned the same values on the same slices (section 1), so it matches too. The 9 `Alpha Signal` rows also match, and they depend on this measure.

## 3. Edge cases checked
I ran the query at the bottom of this page twice: once with my measure and once with Claude's.

| # | Edge case | Why it can break | Expected | Mine | Claude's |
|---|---|---|---:|---:|---:|
| 1 | **Grand total**, no filters | The last date must be found across all 60 months; 148 of its 2,325 rows are suspect | 1.4480% | 1.4480% | 1.4480% |
| 2 | **Year 2022** | The only year above +2%, so it tests the Alpha Signal threshold | 2.8494% | 2.8494% | 2.8494% |
| 3 | **2024 Retail** | Year plus tier filter; small accounts, so suspects distort the most | 2.4041% | 2.4041% | 2.4041% |
| 4 | **Suspects included** | Proves the exclusion changes the answer | Total 1.6678%; Retail 2024 7.6224% | 1.6678% / 7.6224% | n/a |
| 5 | **January 2024** | YTD alpha covers only one month; tests a month-level filter with Claude's `TREATAS` | −0.0092% | −0.0092% | −0.0092% |
| 6 | **Simple mean**, grand total | Shows that weighting matters | 0.8788% | 0.8788% | n/a |

*Mine* for cases 1–3 also appears in my Power BI export, `reports/powerbi_values.csv` (rows `Grand Total`, `Year 2022`, `2024 Tier Retail`: 0.0144799, 0.0284941, 0.0240410).

**What the edge cases show:**
- Excluding suspects matters. They pull the firm-wide figure from 1.45% up to 1.67%, and Retail from 2.40% up to 7.62%, because Retail accounts are small and the bad returns aren't diluted.
- AUM weighting matters. A simple mean (0.88%) lets the many small, underperforming accounts drag the result down.

## 4. What I changed and why
**Nothing changed in my model.** Claude's version returns the same value as mine on every slice and edge case above, so it is logically equivalent. I kept my `LASTNONBLANK` version because:
- it is the one reconciled in `measure_reconciliation.csv`;
- it uses the same date logic as `[Ending AUM]`, so the two can't drift apart;
- the `TREATAS` rewrite adds complexity without changing any number.

Claude's code needed no edits to run.

**My judgement of Claude's output:**
- **Correct:** its filter-context explanation. It says the date is chosen from all rows, suspects included, and suspect rows are dropped afterwards; that a client with a suspect December row is not replaced by their November row; and that totals are re-evaluated, not summed.
- **Correct:** it used only real column names from the metadata, and its test query includes an independent `_t Check` measure that filters the fact table directly. That is a good testing habit.
- **Weak:** it presented "points the date filter at `dim_date`" as an improvement, but my measure already filters `dim_date[date]` (through `LASTNONBLANK`). That is not a real change.
- **Not tested:** it called `MAX` "cheaper". That is a performance claim; I didn't test it and it doesn't affect correctness.

## 5. A claim Claude made that I confirmed or refuted
- **Claude's claim:** "`MAX(snapshot_date)` … gives the same date `LASTNONBLANK(…COUNTROWS…)` gives, so it matches `[Ending AUM]` everywhere."
- **How I tested it:**
  - In Power BI, the `Last snapshot` column of its test query showed the 1st of December of each year (2020-12-01 to 2024-12-01), and 2024-12-01 for every 2024 tier. These are the same dates `LASTNONBLANK` picks for `[Ending AUM]`.
  - Its `AUM-Weighted Alpha` equalled mine on every slice in section 1 and every edge case in section 3.
  - In pandas, taking the latest `snapshot_date` per slice gives the same dates and exactly the same alpha as the reconciled measure (max difference 0).
- **Result: Confirmed.** It holds here because `fact_portfolio_snapshot` is the only table filtered by the last date, so the latest date that has rows is the same as the maximum `snapshot_date`.

A second claim, also confirmed: "The total row in query 3 equals the 2024 row in query 2." Both show 1.4480%, because the tier filter is removed but 2024 stays, leaving the same 2,177 rows.

---

### Edge-case test query (DAX query view)
```DAX
EVALUATE
VAR WeightedIncl =
    // same as the measure, but without the suspect filter
    CALCULATE (
        DIVIDE (
            SUMX ( fact_portfolio_snapshot, fact_portfolio_snapshot[aum] * fact_portfolio_snapshot[active_alpha_ytd] ),
            SUM ( fact_portfolio_snapshot[aum] )
        ),
        LASTNONBLANK ( dim_date[date], CALCULATE ( COUNTROWS ( fact_portfolio_snapshot ) ) )
    )
RETURN
    ROW (
        "1 Grand total", [AUM-Weighted Alpha],
        "2 Year 2022", CALCULATE ( [AUM-Weighted Alpha], dim_date[year] = 2022 ),
        "3 Retail 2024", CALCULATE ( [AUM-Weighted Alpha], dim_date[year] = 2024, dim_client[client_tier] = "Retail" ),
        "4a Incl suspects, total", WeightedIncl,
        "4b Incl suspects, Retail 2024",
            CALCULATE (
                CALCULATE (
                    DIVIDE (
                        SUMX ( fact_portfolio_snapshot, fact_portfolio_snapshot[aum] * fact_portfolio_snapshot[active_alpha_ytd] ),
                        SUM ( fact_portfolio_snapshot[aum] )
                    ),
                    LASTNONBLANK ( dim_date[date], CALCULATE ( COUNTROWS ( fact_portfolio_snapshot ) ) )
                ),
                dim_date[year] = 2024,
                dim_client[client_tier] = "Retail"
            ),
        "5 Jan 2024", CALCULATE ( [AUM-Weighted Alpha], dim_date[year] = 2024, dim_date[month] = 1 ),
        "6 Simple mean, total",
            CALCULATE (
                AVERAGE ( fact_portfolio_snapshot[active_alpha_ytd] ),
                LASTNONBLANK ( dim_date[date], CALCULATE ( COUNTROWS ( fact_portfolio_snapshot ) ) ),
                fact_portfolio_snapshot[is_return_suspect] = 0
            )
    )
```
For Claude's version I replaced each `[AUM-Weighted Alpha]` with `[AUM-Weighted Alpha (Claude)]`, a temporary copy of Claude's measure that I deleted afterwards.
