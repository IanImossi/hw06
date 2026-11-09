# HW6 Measure Library — Wildcat Capital AUM & Performance

All measures live in the `_Measures` table of `powerbi/hw06.pbix`. Model facts the measures rely on:

- `fact_portfolio_snapshot` grain: **one row per client per month**; `snapshot_date` is the 1st of the month (60 dates, 2020-01-01 → 2024-12-01). `aum` is a **balance** (semi-additive); `active_alpha_ytd` is a **year-to-date rate** (non-additive).
- `fact_fees` grain: one row per billed client-month (fee date on the 1st). `fact_transactions` grain: one row per transaction (any day).
- All facts relate many-to-one, single direction, to `dim_date[date]` and `dim_client[client_id]`; `dim_date` is marked as the date table.

Additivity patterns used below: **SUM** (additive), **Last balance** (semi-additive: value at the last date with data), **Recompute-and-weight** (non-additive: rebuild the ratio from additive parts).

---

## Part A — Measures

### Base measures (from the ICEs)
```DAX
Total Fees = SUM ( fact_fees[amount] )
```
```DAX
Net Flows =
CALCULATE ( SUM ( fact_transactions[amount] ), fact_transactions[txn_type] = "Deposit" )
    - CALCULATE ( SUM ( fact_transactions[amount] ), fact_transactions[txn_type] = "Withdrawal" )
```
Format: `$#,0.00`. Pattern: **SUM**. Fees and net flows are flows, so they add across any slice.

### 0. AUM (naive SUM) — ⚠️ WRONG ON PURPOSE, never put on a report
```DAX
AUM (naive SUM) = SUM ( fact_portfolio_snapshot[aum] )
```
Format: `$#,0.00`. Pattern: SUM applied to a balance — **the trap**. With no filter it returns **$566.7B**, 44.5× the real $12.73B, because it adds the same dollars once for every month they sat in the account. Kept only to prove that pandas `.sum()` makes the identical mistake.

### 1. Ending AUM
```DAX
Ending AUM =
CALCULATE (
    SUM ( fact_portfolio_snapshot[aum] ),
    LASTNONBLANK ( dim_date[date], CALCULATE ( COUNTROWS ( fact_portfolio_snapshot ) ) )
)
```
Format: `$#,0.00`. Pattern: **Last balance**. LASTNONBLANK finds the latest date in the current filter that actually has snapshot rows (needed because snapshots sit on the 1st, so LASTDATE would land on an empty month-end). *Meaning:* how much Wildcat manages at the end of the period you are looking at.

### 2. Ending Clients
```DAX
Ending Clients =
CALCULATE (
    DISTINCTCOUNT ( fact_portfolio_snapshot[client_id] ),
    LASTNONBLANK ( dim_date[date], CALCULATE ( COUNTROWS ( fact_portfolio_snapshot ) ) )
)
```
Format: `#,0`. Pattern: **Last balance** (a headcount is a stock, not a flow). *Meaning:* how many clients hold an account with us at the end of the period.

### 3. Avg AUM per Client
```DAX
Avg AUM per Client = DIVIDE ( [Ending AUM], [Ending Clients] )
```
Format: `$#,0.00`. Pattern: **Recompute-and-weight** (ratio of two last-balance measures, never an average of averages). *Meaning:* the typical relationship size, which tells a manager whether growth is coming from bigger or more clients.

### 4. Ending AUM LY and AUM YoY %
```DAX
Ending AUM LY = CALCULATE ( [Ending AUM], SAMEPERIODLASTYEAR ( dim_date[date] ) )
```
```DAX
AUM YoY % = DIVIDE ( [Ending AUM] - [Ending AUM LY], [Ending AUM LY] )
```
Formats: `$#,0.00` and `0.00%`. Pattern: **Last balance** shifted one year, then **Recompute** for the growth rate. LASTNONBLANK runs inside the shifted dates, so 2024 compares Dec-2024 to Dec-2023. No alternate result in DIVIDE, so 2020 (no prior year) shows blank instead of a fake 0%. *Meaning:* how much bigger the book is than a year ago, from all causes (markets plus flows).

### 5. Ending AUM PM and AUM MoM %
```DAX
Ending AUM PM = CALCULATE ( [Ending AUM], DATEADD ( dim_date[date], -1, MONTH ) )
```
```DAX
AUM MoM % = DIVIDE ( [Ending AUM] - [Ending AUM PM], [Ending AUM PM] )
```
Formats: `$#,0.00` and `0.00%`. Pattern: **Last balance** shifted one month, then **Recompute**. *Meaning:* month-over-month change in the book; December 2024 grew 4.25% over November.

### 6. Avg Monthly AUM
```DAX
Avg Monthly AUM =
DIVIDE (
    SUM ( fact_portfolio_snapshot[aum] ),
    DISTINCTCOUNT ( fact_portfolio_snapshot[snapshot_date] )
)
```
Format: `$#,0.00`. Pattern: **Recompute-and-weight** (Σ balance ÷ number of months = time-weighted average balance). *Meaning:* the average size of the book over the period, the right base for revenue that accrues all year.

### 7. Fee Yield (bps)
```DAX
Fee Yield (bps) =
DIVIDE ( [Total Fees] * 12 * 10000, SUM ( fact_portfolio_snapshot[aum] ) )
```
Format: `0.00`. Pattern: **Recompute-and-weight** across **two fact tables** — the numerator comes from `fact_fees`, the denominator from `fact_portfolio_snapshot`, and both are filtered by the shared `dim_date` and `dim_client`. Σ aum over n months ÷ 12 is the average annual base, so fees × 12 ÷ Σ aum annualizes correctly. *Meaning:* how many basis points of revenue Wildcat earns per dollar it manages.

### 8. Organic Growth Rate
```DAX
Organic Growth Rate = DIVIDE ( [Net Flows], [Ending AUM LY] )
```
Format: `0.00%`. Pattern: **Recompute** (additive flow ÷ last balance). *Meaning:* how much of the book's growth came from clients adding new money rather than from markets.

### 9. AUM-Weighted Alpha
```DAX
AUM-Weighted Alpha =
VAR LastSnapshot =
    LASTNONBLANK ( dim_date[date], CALCULATE ( COUNTROWS ( fact_portfolio_snapshot ) ) )
RETURN
    CALCULATE (
        DIVIDE (
            SUMX (
                fact_portfolio_snapshot,
                fact_portfolio_snapshot[aum] * fact_portfolio_snapshot[active_alpha_ytd]
            ),
            SUM ( fact_portfolio_snapshot[aum] )
        ),
        LastSnapshot,
        fact_portfolio_snapshot[is_return_suspect] = 0
    )
```
Format: `0.00%`. Pattern: **Recompute-and-weight** at the **last snapshot**. The last date is found from all rows first, then suspect rows are dropped. *Meaning:* how far, dollar for dollar, client portfolios beat or trailed their benchmarks year-to-date.

### 10. Alpha Signal
```DAX
Alpha Signal =
VAR a = [AUM-Weighted Alpha]
RETURN
    SWITCH (
        TRUE (),
        ISBLANK ( a ), BLANK (),
        a >= 0.02, "Outperforming",
        a <= -0.02, "Lagging",
        "In line"
    )
```
Format: text. Pattern: inherits **Recompute-and-weight** from measure 9 (a label on a non-additive rate; never aggregated itself). *Meaning:* a one-word verdict a manager can scan: 2022 was the only "Outperforming" year firm-wide.

### 11. Top 10 Client Share
```DAX
Top 10 Client Share =
VAR Top10 =
    TOPN ( 10, VALUES ( dim_client[client_id] ), [Ending AUM], DESC )
RETURN
    DIVIDE ( CALCULATE ( [Ending AUM], Top10 ), [Ending AUM] )
```
Format: `0.00%`. Pattern: **Last balance**, ranked, then **Recompute** as a share. `VALUES` (not `ALL`) keeps only the clients in the current filter, so in a tier row it ranks that tier's clients and the share can never exceed 100%. *Meaning:* concentration risk — how much of the book walks out the door if the ten biggest relationships leave.

---

## Part C — Design questions

*(to be added)*
