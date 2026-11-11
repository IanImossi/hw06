# Part D — Verification of Claude's `AUM-Weighted Alpha`

> **How to fill this in:** every `▢` is something only you can observe, in Claude Desktop, Power BI or VS Code. The expected values were computed independently in pandas (`scripts/01_reconcile_measures.py`, `scripts/02_part_c_evidence.py`). Replace each `▢` with what you saw, delete this note and the "how to" lines, and keep it to about one page.

## 1. Did Claude's measure run as written?
- Ran without edits: ▢ *(yes / no; if no, quote the error message)*
- Claude's test query returned:

| Slice | Claude's test query | Expected (pandas) |
|---|---:|---:|
| Grand total | ▢ | 1.4480% |
| Year 2020 | ▢ | −0.6802% |
| Year 2021 | ▢ | −0.1574% |
| Year 2022 | ▢ | 2.8494% |
| Year 2023 | ▢ | 1.7689% |
| Year 2024 | ▢ | 1.4480% |
| 2024 HNW | ▢ | 1.3988% |
| 2024 Retail | ▢ | 2.4041% |
| 2024 UHNW | ▢ | 1.4097% |

## 2. Rows of `reports/measure_reconciliation.csv` that prove it
The 9 rows with `measure = AUM-Weighted Alpha` (`Grand Total`, `Year 2020`–`Year 2024`, `2024 Tier HNW` / `Retail` / `UHNW`) all have `match = True`, with an `abs_diff` of at most ▢. The 9 `Alpha Signal` rows also match, and they depend on this measure.

*How to check: open the CSV and filter `measure` to `AUM-Weighted Alpha`.*

## 3. Edge cases checked
Run the query at the bottom of this page in DAX query view and fill in the "Power BI" column.

| # | Edge case | Why it can break | Expected | Power BI |
|---|---|---|---:|---:|
| 1 | **Grand total** (no filters) | The last date must be found across all 60 months (2024-12-01); 148 of its 2,325 rows are suspect | 1.4480% | ▢ |
| 2 | **Year 2022** | The only year above the +2% threshold, so it tests the boundary used by Alpha Signal; 79 suspect rows | 2.8494% (Outperforming) | ▢ |
| 3 | **2024 tier table** | Tier filter plus year filter; Retail is where suspects matter most because accounts are small | Retail 2.4041% | ▢ |
| 4 | **Suspects included** (the measure without the filter) | Proves the exclusion actually changes the answer | Total 1.6678%; Retail 2024 **7.6224%** | ▢ / ▢ |
| 5 | **January 2024** | YTD alpha covers only one month here | −0.0092% | ▢ |
| 6 | **Simple mean** at grand total (wrong weighting, for contrast) | Shows the weighting matters | 0.8788% | ▢ |

## 4. What I changed and why
▢ *Either: "Nothing. Claude's measure matched on every slice and edge case above." Or: describe each change, e.g. Claude used LASTDATE, used a column that doesn't exist, applied the suspect filter before finding the last date, or used ALL(). Say how you noticed: an error, a wrong number, or a mismatch in the reconciliation.*

**My judgement of Claude's output:** ▢ *(2–3 sentences: was the filter-context explanation correct? Did it use only real column names from the metadata? Was its test query useful?)*

## 5. A claim Claude made that I confirmed or refuted
- **Claude's claim (quote it):** ▢
- **How I tested it:** ▢ *(e.g. edge case 4 or 5 above, or a pandas line)*
- **Result:** ▢ **Confirmed / Refuted**, because ▢

*Good claims to test, if Claude makes them:*
- *"Excluding suspects changes the result." Edge case 4: 1.67% → 1.45% overall, and 7.62% → 2.40% for Retail. Confirmed if Claude said so.*
- *"Without the last-date filter, the measure would average YTD values across months." Weighting every 2024 month gives 0.3225% instead of 1.4480%, so the claim is confirmed.*
- *"The last date is found before / after the suspect filter." Both orders give the same date here, because every month has non-suspect rows. If Claude says the order changes the result for this data, that's refuted.*

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
