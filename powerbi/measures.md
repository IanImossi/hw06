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

Every number below is reproduced by `python scripts/02_part_c_evidence.py`, which reuses the pandas measure logic that matched Power BI on all 91 rows of `reports/measure_reconciliation.csv`.

### (a) Ending AUM vs `SUMX ( VALUES ( dim_client[client_id] ), [Ending AUM] )`

| | Value |
|---|---:|
| `Ending AUM` (no filters) | **$12,729,572,078.86** |
| `SUMX` over clients | **$13,149,297,713.80** |
| Difference | **$419,725,634.94** |

`Ending AUM` finds **one** last date for the whole filter (2024-12-01) and sums the 2,325 clients present on it. The SUMX version iterates every client, and context transition makes `[Ending AUM]` find **each client's own** last date. For the 175 clients who left the firm (last snapshot in 2022 for 13 of them, in 2023 for 162), that is their final balance before departure. Those stale balances add up to exactly **$419,725,634.94**, the whole gap. Money that has already walked out the door is counted as if it were still here.

Power BI agrees: query 7 in `powerbi/export_queries.dax` returns both values side by side.

**`Ending AUM` answers "How much do we manage today?"** The SUMX number is "the last-known balance of everyone who has ever been a client," which is not a balance at any single point in time.

### (b) Why 2024 Fee Yield (43.15 bps) < ICE 9 Effective Fee Rate (45.53 bps)

Both use the same numerator, 2024 fees of **$48,714,005.93**. The denominators differ:

| 2024 | Denominator | bps |
|---|---:|---:|
| Effective Fee Rate = fees × 12 × 10,000 ÷ Σ `fact_fees[aum_basis]` | $128,385,303,527.10 | 45.53 |
| Fee Yield = fees × 12 × 10,000 ÷ Σ `fact_portfolio_snapshot[aum]` | $135,459,843,783.73 | 43.15 |

Pandas evidence (joining the two facts on `client_id` + month):
- `fact_fees` has exactly **one row per billed client-month** (26,216 rows in 2024), and where a fee row exists, `aum_basis` equals the snapshot `aum` **to the cent** (max difference 0.00).
- But the snapshot has **27,900** client-months in 2024. **1,684 (6.0%) have no fee row**, holding **$7,074,540,256.63** of AUM. That is exactly the denominator gap (135.46B − 128.39B).
- The gaps are scattered, not structural: 5–6% of client-months in every year 2020–2024, every tier (Retail 6.3%, HNW 5.7%, UHNW 5.4%), and 1,082 different clients each missing 1–5 months. There are no fee rows without a snapshot.

**Data limitation:** `fact_fees` is **incomplete**. It does not record a fee for every client-month that holds assets, and nothing in the data says whether those months were waived, unbilled, or simply missing from the billing extract. Effective Fee Rate only measures the price on *billed* assets. Fee Yield measures revenue on *all* assets, so it is lower by the share of AUM that generated no recorded fee. The 2.4 bps difference on 2024's $11.29B average book is about **$2.7M** of revenue, either never billed or not captured in the data.

### (c) AUM-Weighted Alpha: last snapshot only, and excluding suspects

**Why the last snapshot only:** `active_alpha_ytd` is **year-to-date**. January's value covers one month and December's covers twelve, so mixing months blends returns over different horizons. On top of that, `aum` is a balance, so weighting across 12 months would count each client's dollars 12 times. The 2024 weighted alpha builds from −0.01% in January to +1.45% in December. Only the last snapshot gives the full-period answer, weighted by the balance on the same date.

**Why exclude `is_return_suspect = 1`:** at 2024-12-01, 148 of 2,325 rows are flagged. Their `active_alpha_ytd` runs from −121% to **+7,134%** (mean +231.6%), which are data errors, not real performance. The 2,177 clean rows range from −50% to +50%.

| Grand total (last snapshot, 2024-12-01) | Value |
|---|---:|
| AUM-weighted, suspects **excluded** (the measure) | **1.45%** |
| Simple mean, same 2,177 rows | **0.88%** |
| AUM-weighted, suspects **included** | **1.67%** |
| *(for reference) simple mean, suspects included* | *15.56%* |

The simple mean is lower because it gives the smallest account the same vote as the $82M largest one, and the smallest accounts did worst. The bottom fifth of accounts by size averaged −4.4% alpha, while the other four fifths averaged +1.3% to +3.3%. In Retail the gap is widest: a simple mean of 0.53% against an AUM-weighted 2.40%. AUM weighting answers the question that matters for the firm: how did the *dollars* we manage do? Suspect rows hold only $15.5M of AUM, so weighting already dampens them (+0.22 pts). In a simple mean they would blow the result up roughly 18×. Excluding them protects both versions.

### (d) Organic Growth Rate by tier, 2024

| 2024 tier | Net Flows | Ending AUM LY | **Organic Growth** | **AUM YoY %** | Growth not from flows |
|---|---:|---:|---:|---:|---:|
| Retail | $44.2M | $447.8M | **9.87%** | 19.13% | $41.5M |
| HNW | $25.2M | $2,130.2M | **1.18%** | 19.64% | $393.1M |
| UHNW | $8.1M | $8,067.0M | **0.10%** | 19.59% | $1,572.5M |
| Firm | $77.5M | $10,645.0M | **0.73%** | 19.58% | $2,007.1M |

**What it says:** every tier grew about 19–20%, but almost none of it was new money. Firm-wide, net flows explain 0.73 points of the 19.58-point growth; the rest, about $2.0B, came from somewhere other than deposits and withdrawals, mostly market returns. Retail is the only tier where clients are meaningfully adding money (9.9% of its base), and it supplied 57% of the firm's net new dollars while holding 4% of its AUM. UHNW, which is 76% of AUM, grew $1.58B almost entirely from markets. Wildcat's book is growing *with the market*, not by winning wallet share at the top end.

**What it does not tell you:**
- It does not *prove* the remainder is investment performance. AUM YoY − Organic is a residual that also includes dividends, fees debited, and the balances of clients who left.
- Which flows came from new clients versus existing ones, or how many clients were added or lost.
- Whether the growth is profitable. Retail flows look strong, but Retail AUM is small, and on its own the rate says nothing about revenue. (Fee yield differs by tier: Retail 82.8 bps, UHNW 36.1 bps.)
- Size: a rate on a small base looks large. Retail's 9.87% is $44M, while UHNW's 0.10% is $8M on an $8B base.
- Tier is the client's *current* tier in `dim_client` (a static attribute), so clients who moved tiers during the year are not tracked.
