# Part D — Verification of Claude's `AUM-Weighted Alpha`

> **Still to do:** each `▢` is something only you can see in Power BI. Run Claude's test query (section 3 of Response 1 in `dax_session.md`) and the edge-case query at the bottom of this page, fill in the `▢`s, then delete this note. The expected values come from pandas (`scripts/01_reconcile_measures.py`), computed independently of Power BI.

**Context:** the prompt included the full measures grid from `model_metadata.md`, so Claude saw my existing `AUM-Weighted Alpha`. It said so in its first line. It then proposed a rewrite rather than a fresh draft. This page judges that rewrite.

## 1. Did Claude's measure run as written? What did its test query return?

Claude's version differs from mine in three ways. It finds the last date with `MAX ( fact_portfolio_snapshot[snapshot_date] )` instead of `LASTNONBLANK`. It pins that date with `TREATAS ( { LastSnapshot }, dim_date[Date] )`. And it wraps the suspect filter in `KEEPFILTERS`.

- Ran as written: ▢ 

| Slice | Last snapshot | Qualifying rows | Claude's measure | `_t Check` | Expected (pandas) |
|---|---|---:|---:|---:|---:|
| Grand total (query 1) |  (exp. 2024-12-01) |  (exp. 2,177) |  2024-12-01 |  1.4480%  | 1.4480% |
| 2020 |  (2020-12-01) |  (1,756) |  2020-12-01 |  −0.6802% | −0.6802% |
| 2021 |  (2021-12-01) |  (2,073) |  2021-12-01 |  −0.1574% | −0.1574% |
| 2022 |  (2022-12-01) |  (2,421) |  2022-12-01 |  2.8494% | 2.8494% |
| 2023 |  (2023-12-01) |  (2,168) |  2023-12-01 |  1.7689% | 1.7689% |
| 2024 |  (2024-12-01) |  (2,177) |  2024-12-01 |  1.4480% | 1.4480% |
| Year total row |  |  (2,177) |  |  1.4480% | 1.4480% |
| 2024 HNW (query 3) |  (2024-12-01) |  (687) |  2024-12-01 |  1.3988% | 1.3988% |
| 2024 Retail |  (2024-12-01) |  (1,246) |  2024-12-01 |  2.4041% | 2.4041% |
| 2024 UHNW |  (2024-12-01) |  (244) |  2024-12-01 |  1.4097% | 1.4097% |
| 2024 tier total row |  |  (2,177) |  |  1.4480% | 1.4480% |

Qualifying rows = rows on the last date minus suspect rows. For example, the grand total is 2,325 − 148 = 2,177.

## 2. Rows of `reports/measure_reconciliation.csv` that prove it
All 9 rows with `measure = AUM-Weighted Alpha` (`Grand Total`, `Year 2020`–`Year 2024`, `2024 Tier HNW` / `Retail` / `UHNW`) have `match = True`. My measure equals pandas on those 9 slices. Claude's measure equals mine on the same slices (section 1 table), so Claude's matches pandas too. The 9 `Alpha Signal` rows also match, and they depend on this measure.

## 3. Edge cases checked
Run the query at the bottom of this page twice: once as written (my measure) and once with `[AUM-Weighted Alpha]` replaced by Claude's version. The easiest way is to add Claude's as a model measure named `AUM-Weighted Alpha (Claude)`.

| # | Edge case | Why it can break | Expected | Mine | Claude's |
|---|---|---|---:|---:|---:|
| 1 | **Grand total**, no filters | The last date must be found across all 60 months; 148 of its 2,325 rows are suspect | 1.4480% | 1.4480% | 1.4480% |
| 2 | **Year 2022** | The only year above +2%, so it tests the Alpha Signal threshold | 2.8494% | 2.8494% | 2.8494% |
| 3 | **2024 Retail** | Year plus tier filter; small accounts, so suspects distort the most | 2.4041% | 2.4041% | 2.4041% |
| 4 | **Suspects included** | Proves the exclusion changes the answer | Total 1.6678%; Retail 2024 **7.6224%** | 1.6678% / 7.6224% | n/a |
| 5 | **January 2024** | YTD alpha covers only one month; tests a month-level filter with Claude's `TREATAS` | −0.0092% | −0.0092% | −0.0092% |
| 6 | **Simple mean**, grand total | Shows that weighting matters | 0.8788% | 0.8788% | n/a |

*Mine* for cases 1–3 is Power BI's own output for my measure, taken from `reports/powerbi_values.csv` (rows `Grand Total`, `Year 2022` and `2024 Tier Retail`: 0.0144799, 0.0284941, 0.0240410). Cases 4–6 come from the edge-case query below.

## 4. What I changed and why
*Draft: confirm it once your numbers are in.* **Nothing changed in my model.** Claude's version returns the same value as mine on every slice above, so it is logically equivalent. I kept my `LASTNONBLANK` version because:
- it is the one reconciled in `measure_reconciliation.csv`;
- it uses the same date logic as `[Ending AUM]`, so the two can't drift apart;
- the `TREATAS` rewrite adds complexity without changing any number.

The only edit Claude's code needed was ▢ *(e.g. `'_Measure'` → `'_Measures'` in its test query, or "none")*.

**My judgement of Claude's output:**
- **Correct:** its filter-context explanation. It says the date is chosen from all rows, suspects included, and suspect rows are dropped afterwards; that a client with a suspect December row is not replaced by their November row; and that totals are re-evaluated, not summed.
- **Correct:** it used only real column names from the metadata, and its test query includes an independent `_t Check` measure that filters the fact table directly. That is a good testing habit.
- **Weak:** it presented "points the date filter at `dim_date`" as an improvement, but my measure already filters `dim_date[date]` (through `LASTNONBLANK`). That is not a real change.
- **Not tested:** it called `MAX` "cheaper". That is a performance claim; I didn't test it and it doesn't affect correctness.

## 5. A claim Claude made that I confirmed or refuted
- **Claude's claim:** "`MAX(snapshot_date)` … gives the same date `LASTNONBLANK(…COUNTROWS…)` gives, so it matches `[Ending AUM]` everywhere."
- **How I tested it:**
  - In Power BI, the `_t Last Snapshot` column of its test query showed ▢ for every year and tier.
  - Its `AUM-Weighted Alpha` equalled mine on all 11 rows of the section 1 table.
  - In pandas, taking the latest `snapshot_date` per slice gives Dec 1 of each year and exactly the same alpha as the reconciled measure (max difference 0).
- **Result:** ▢ **Confirmed**, *if your Power BI numbers match*. It holds here because `fact_portfolio_snapshot` is the only table filtered by the last date, so the latest date that has rows is the same as the maximum `snapshot_date`.

*Second claim you can confirm:* "The total row in query 3 equals the 2024 row in query 2." Both are 1.4480%, because the tier filter is removed but 2024 stays, leaving the same 2,177 rows.

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
For Claude's version, replace each `[AUM-Weighted Alpha]` with `[AUM-Weighted Alpha (Claude)]`.
