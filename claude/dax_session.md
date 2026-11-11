# Claude Desktop DAX session — Measure 9: `AUM-Weighted Alpha`

Workflow: **Draft → Test → Debug → Review** (Week 10).

> **How to fill this in:** start a **new** Claude Desktop chat. Copy Prompt 1 (everything inside the fence; the metadata grids are already in it) and send it. Paste Claude's **complete, unedited** reply under "Response 1". If you ask follow-ups (debugging an error, questioning a claim), add them as Prompt 2 / Response 2, and so on. Don't tidy up Claude's answers: the grade rests on judging what it actually produced.

---

## Prompt 1 — Draft

```text
I'm building a DAX measure in Power BI Desktop for a wealth-management star schema. Please
write ONE measure, explain its filter context, and give me a DAX query I can run in DAX query
view to test it.

## Measure to write
Name: AUM-Weighted Alpha
Business definition: active_alpha_ytd weighted by aum, at the last snapshot in the current
filter, excluding rows where is_return_suspect = 1.
  - Result = SUM(aum × active_alpha_ytd) ÷ SUM(aum) over the qualifying rows.
  - It must work in a card (no filters), in a table by dim_date[year], and in a table by
    dim_client[client_tier] filtered to 2024.
  - Return BLANK when there are no qualifying rows. Store it in the _Measures table.

## What the metadata cannot tell you
- fact_portfolio_snapshot grain: ONE ROW PER CLIENT PER MONTH. snapshot_date is always the
  1st of the month (60 dates, 2020-01-01 to 2024-12-01). There is no row on month-end dates,
  so LASTDATE / ENDOFMONTH / CLOSINGBALANCE* would return a date with no data.
- aum is a BALANCE (semi-additive): it must not be summed across dates.
- active_alpha_ytd is a YEAR-TO-DATE rate (non-additive): January covers 1 month, December
  covers 12, so only the last snapshot of the period is the full-period value.
- is_return_suspect is an integer flag (0/1); 1 = corrupt return data.
- dim_date is marked as the date table and relates to fact_portfolio_snapshot[snapshot_date].
  All relationships are many-to-one, single direction.
- Measures live in the table named _Measure (being renamed to _Measures).
- Existing measure you can reuse or mirror:
    Ending AUM =
    CALCULATE ( SUM ( fact_portfolio_snapshot[aum] ),
        LASTNONBLANK ( dim_date[date], CALCULATE ( COUNTROWS ( fact_portfolio_snapshot ) ) ) )

## Model metadata (exported with INFO.VIEW queries)
### Columns
[Table]	[Column]	[DataType]	[DAX formula]	[IsHidden]
DateTableTemplate_b50879b8-a09d-4fd7-b9a6-7a34995295aa	Date	Date		true
DateTableTemplate_b50879b8-a09d-4fd7-b9a6-7a34995295aa	Day	Integer	DAY([Date])	true
DateTableTemplate_b50879b8-a09d-4fd7-b9a6-7a34995295aa	Quarter	Text	"Qtr " & [QuarterNo]	true
DateTableTemplate_b50879b8-a09d-4fd7-b9a6-7a34995295aa	QuarterNo	Integer	INT(([MonthNo] + 2) / 3)	true
DateTableTemplate_b50879b8-a09d-4fd7-b9a6-7a34995295aa	Month	Text	FORMAT([Date], "MMMM")	true
DateTableTemplate_b50879b8-a09d-4fd7-b9a6-7a34995295aa	MonthNo	Integer	MONTH([Date])	true
DateTableTemplate_b50879b8-a09d-4fd7-b9a6-7a34995295aa	Year	Integer	YEAR([Date])	true
dim_advisor	years_experience	Integer		false
dim_advisor	certifications	Text		false
dim_advisor	advisor_id	Integer		false
dim_advisor	first_name	Text		false
dim_advisor	last_name	Text		false
dim_advisor	region	Text		false
dim_advisor	aum_target_mm	Integer		false
dim_benchmark	ticker_proxy	Text		false
dim_benchmark	asset_class	Text		false
dim_benchmark	name	Text		false
dim_benchmark	benchmark_id	Integer		false
dim_client	client_since	Date		false
dim_client	first_name	Text		false
dim_client	primary_account_type	Text		false
dim_client	client_tier	Text		false
dim_client	risk_profile	Text		false
dim_client	zip_code	Text		false
dim_client	state	Text		false
dim_client	city	Text		false
dim_client	age	Integer		false
dim_client	last_name	Text		false
dim_client	initial_aum	Number		false
dim_client	client_id	Integer		false
dim_client	is_active	True/False		false
dim_client	advisor_id	Integer		false
dim_date	is_quarter_end	Integer		false
dim_date	is_year_end	Integer		false
dim_date	is_trading_day	Integer		false
dim_date	Year	Integer		false
dim_date	Date	Date		false
dim_date	date_id	Integer		false
dim_date	Month	Integer		false
dim_date	Quarter	Integer		false
dim_date	month_name	Text		false
dim_date	week_of_year	Integer		false
dim_date	day_of_week	Text		false
dim_date	is_month_end	Integer		false
dim_security	expense_ratio_bps	Integer		false
dim_security	security_id	Integer		false
dim_security	ticker	Text		false
dim_security	name	Text		false
dim_security	asset_class	Text		false
dim_security	sector	Text		false
dim_security	benchmark_id	Integer		false
dim_security	is_etf	True/False		false
fact_fees	fee_date	Date		false
fact_fees	fee_type	Text		false
fact_fees	aum_basis	Number		false
fact_fees	bps_charged	Number		false
fact_fees	amount	Number		false
fact_fees	fee_id	Integer		false
fact_fees	client_id	Integer		false
fact_fees	advisor_id	Integer		false
fact_portfolio_snapshot	Year	Integer		false
fact_portfolio_snapshot	snapshot_date	Date		false
fact_portfolio_snapshot	benchmark_id	Integer		false
fact_portfolio_snapshot	advisor_id	Integer		false
fact_portfolio_snapshot	client_id	Integer		false
fact_portfolio_snapshot	snapshot_id	Integer		false
fact_portfolio_snapshot	benchmark_return_ytd	Number		false
fact_portfolio_snapshot	is_return_suspect	Integer		false
fact_portfolio_snapshot	account_type	Text		false
fact_portfolio_snapshot	cash_pct	Number		false
fact_portfolio_snapshot	active_alpha_ytd	Number		false
fact_portfolio_snapshot	return_ytd	Number		false
fact_portfolio_snapshot	aum	Number		false
fact_portfolio_snapshot	Month	Integer		false
fact_transactions	security_id	Integer		false
fact_transactions	shares	Number		false
fact_transactions	is_post_departure_txn	Integer		false
fact_transactions	txn_type	Text		false
fact_transactions	txn_date	Date		false
fact_transactions	price	Number		false
fact_transactions	txn_id	Integer		false
fact_transactions	advisor_id	Integer		false
fact_transactions	client_id	Integer		false
fact_transactions	amount	Number		false
LocalDateTable_30b0d5f8-768e-4d2a-9562-888fa2f9b2e7	Month	Text	FORMAT([Date], "MMMM")	true
LocalDateTable_30b0d5f8-768e-4d2a-9562-888fa2f9b2e7	Date	Date		true
LocalDateTable_30b0d5f8-768e-4d2a-9562-888fa2f9b2e7	Year	Integer	YEAR([Date])	true
LocalDateTable_30b0d5f8-768e-4d2a-9562-888fa2f9b2e7	MonthNo	Integer	MONTH([Date])	true
LocalDateTable_30b0d5f8-768e-4d2a-9562-888fa2f9b2e7	QuarterNo	Integer	INT(([MonthNo] + 2) / 3)	true
LocalDateTable_30b0d5f8-768e-4d2a-9562-888fa2f9b2e7	Quarter	Text	"Qtr " & [QuarterNo]	true
LocalDateTable_30b0d5f8-768e-4d2a-9562-888fa2f9b2e7	Day	Integer	DAY([Date])	true
LocalDateTable_976ce71a-eea0-49bb-b089-dd421adaa4b8	Day	Integer	DAY([Date])	true
LocalDateTable_976ce71a-eea0-49bb-b089-dd421adaa4b8	Quarter	Text	"Qtr " & [QuarterNo]	true
LocalDateTable_976ce71a-eea0-49bb-b089-dd421adaa4b8	QuarterNo	Integer	INT(([MonthNo] + 2) / 3)	true
LocalDateTable_976ce71a-eea0-49bb-b089-dd421adaa4b8	Month	Text	FORMAT([Date], "MMMM")	true
LocalDateTable_976ce71a-eea0-49bb-b089-dd421adaa4b8	MonthNo	Integer	MONTH([Date])	true
LocalDateTable_976ce71a-eea0-49bb-b089-dd421adaa4b8	Year	Integer	YEAR([Date])	true
LocalDateTable_976ce71a-eea0-49bb-b089-dd421adaa4b8	Date	Date		true

### Relationships
[ID]	[Name]	[Relationship]	[Model]	[IsActive]	[CrossFilteringBehavior]	[RelyOnReferentialIntegrity]	[FromTable]	[FromColumn]	[FromCardinality]	[ToTable]	[ToColumn]	[ToCardinality]	[State]	[SecurityFilteringBehavior]
2450	AutoDetected_47d2c78f-3915-4351-b30d-fc5f654a65f4	'fact_transactions'[advisor_id] *[<-]1 'dim_advisor'[advisor_id]	deff81d0-ce52-458c-8c79-b690b2a55bd7	true	OneDirection	false	fact_transactions	advisor_id	Many	dim_advisor	advisor_id	One	Ready	Single
3424	AutoDetected_080dc0c9-a847-4102-8fe6-5527ad4e80b2	'fact_transactions'[client_id] *[<-]1 'dim_client'[client_id]	deff81d0-ce52-458c-8c79-b690b2a55bd7	true	OneDirection	false	fact_transactions	client_id	Many	dim_client	client_id	One	Ready	Single
4453	AutoDetected_2f815d05-ddf4-42b9-bf11-303f56a168d6	'fact_transactions'[security_id] *[<-]1 'dim_security'[security_id]	deff81d0-ce52-458c-8c79-b690b2a55bd7	true	OneDirection	false	fact_transactions	security_id	Many	dim_security	security_id	One	Ready	Single
4712	6deec966-5197-f019-8717-87cd3326e62d	'fact_transactions'[txn_date] *[<-]1 'dim_date'[date]	deff81d0-ce52-458c-8c79-b690b2a55bd7	true	OneDirection	false	fact_transactions	txn_date	Many	dim_date	date	One	Ready	Single
2451	AutoDetected_515f758c-a4c4-4e3e-8414-fe1239270ac5	'fact_portfolio_snapshot'[advisor_id] *[<-]1 'dim_advisor'[advisor_id]	deff81d0-ce52-458c-8c79-b690b2a55bd7	true	OneDirection	false	fact_portfolio_snapshot	advisor_id	Many	dim_advisor	advisor_id	One	Ready	Single
2639	AutoDetected_27290db9-48a2-4230-a18e-ac5fca16ab64	'fact_portfolio_snapshot'[benchmark_id] *[<-]1 'dim_benchmark'[benchmark_id]	deff81d0-ce52-458c-8c79-b690b2a55bd7	true	OneDirection	false	fact_portfolio_snapshot	benchmark_id	Many	dim_benchmark	benchmark_id	One	Ready	Single
3425	AutoDetected_8da07bbb-379a-44b4-8620-2cb9df480b79	'fact_portfolio_snapshot'[client_id] *[<-]1 'dim_client'[client_id]	deff81d0-ce52-458c-8c79-b690b2a55bd7	true	OneDirection	false	fact_portfolio_snapshot	client_id	Many	dim_client	client_id	One	Ready	Single
4695	aa81e5e4-13d7-2473-c80b-1050d4fb268e	'fact_portfolio_snapshot'[snapshot_date] *[<-]1 'dim_date'[date]	deff81d0-ce52-458c-8c79-b690b2a55bd7	true	OneDirection	false	fact_portfolio_snapshot	snapshot_date	Many	dim_date	date	One	Ready	Single
2452	AutoDetected_13cb45f8-9f1d-42c6-9326-a4402ef86ceb	'fact_fees'[advisor_id] *[<-]1 'dim_advisor'[advisor_id]	deff81d0-ce52-458c-8c79-b690b2a55bd7	true	OneDirection	false	fact_fees	advisor_id	Many	dim_advisor	advisor_id	One	Ready	Single
3426	AutoDetected_6b7ee019-ebcc-4ab0-a5f6-23016186f549	'fact_fees'[client_id] *[<-]1 'dim_client'[client_id]	deff81d0-ce52-458c-8c79-b690b2a55bd7	true	OneDirection	false	fact_fees	client_id	Many	dim_client	client_id	One	Ready	Single
4678	fbd94a81-c893-0c31-c79a-9a0f84f664a0	'fact_fees'[fee_date] *[<-]1 'dim_date'[date]	deff81d0-ce52-458c-8c79-b690b2a55bd7	true	OneDirection	false	fact_fees	fee_date	Many	dim_date	date	One	Ready	Single
2662	371030ed-f05a-47f6-a233-06998810b983	'dim_client'[client_since] *[<-]1 'LocalDateTable_976ce71a-eea0-49bb-b089-dd421adaa4b8'[Date]	deff81d0-ce52-458c-8c79-b690b2a55bd7	true	OneDirection	false	dim_client	client_since	Many	LocalDateTable_976ce71a-eea0-49bb-b089-dd421adaa4b8	date	One	Ready	Single
3498	4ef23535-e977-479b-98bc-f80d9c25c9a5	'dim_date'[date] *[<-]1 'LocalDateTable_30b0d5f8-768e-4d2a-9562-888fa2f9b2e7'[Date]	deff81d0-ce52-458c-8c79-b690b2a55bd7	true	OneDirection	false	dim_date	date	Many	LocalDateTable_30b0d5f8-768e-4d2a-9562-888fa2f9b2e7	date	One	Ready	Single
4454	AutoDetected_031cb484-3962-4004-9c23-08d705a8563e	'dim_security'[benchmark_id] *[<-]1 'dim_benchmark'[benchmark_id]	deff81d0-ce52-458c-8c79-b690b2a55bd7	true	OneDirection	false	dim_security	benchmark_id	Many	dim_benchmark	benchmark_id	One	Ready	Single

### Measures
[Table]	[Measure]	[DAX formula]	[FormatString]	[State]
_Measure	Total Fees	SUM(fact_fees[amount])		Valid
_Measure	Net Flows	CALCULATE ( SUM ( fact_transactions[amount] ), fact_transactions[txn_type] = "Deposit" ) - CALCULATE(SUM( fact_transactions[amount]), fact_transactions[txn_type] = "Withdrawal")		Valid
_Measure	AUM (naive SUM)	SUM ( fact_portfolio_snapshot[aum] )		Valid
_Measure	Ending AUM	
CALCULATE (
    SUM ( fact_portfolio_snapshot[aum] ),
    LASTNONBLANK ( dim_date[date], CALCULATE ( COUNTROWS ( fact_portfolio_snapshot ) ) )
)		Valid
_Measure	Ending Clients	
CALCULATE (
    DISTINCTCOUNT ( fact_portfolio_snapshot[client_id] ),
    LASTNONBLANK ( dim_date[date], CALCULATE ( COUNTROWS ( fact_portfolio_snapshot ) ) )
)
		Valid
_Measure	Avg AUM per Client	DIVIDE ( [Ending AUM], [Ending Clients] )		Valid
_Measure	Ending AUM LY	CALCULATE ( [Ending AUM], SAMEPERIODLASTYEAR ( dim_date[date] ) )		Valid
_Measure	AUM YoY %	DIVIDE ( [Ending AUM] - [Ending AUM LY], [Ending AUM LY] )		Valid
_Measure	Ending AUM PM	CALCULATE ( [Ending AUM], DATEADD ( dim_date[date], -1, MONTH ) )		Valid
_Measure	AUM MoM %	DIVIDE ( [Ending AUM] - [Ending AUM PM], [Ending AUM PM] )
		Valid
_Measure	Avg Monthly AUM	
DIVIDE (
    SUM ( fact_portfolio_snapshot[aum] ),
    DISTINCTCOUNT ( fact_portfolio_snapshot[snapshot_date] )
)
		Valid
_Measure	Fee Yield (bps)	
DIVIDE ( [Total Fees] * 12 * 10000, SUM ( fact_portfolio_snapshot[aum] ) )
		Valid
_Measure	Organic Growth Rate	DIVIDE ( [Net Flows], [Ending AUM LY] )
		Valid
_Measure	AUM-Weighted Alpha	
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
		Valid
_Measure	Alpha Signal	
VAR a = [AUM-Weighted Alpha]
RETURN
    SWITCH (TRUE (), ISBLANK ( a ), BLANK (),
        a >= 0.02, "Outperforming",
        a <= -0.02, "Lagging",
        "In line")
		Valid
_Measure	Top 10 Client Share	
VAR Top10 =
    TOPN ( 10, VALUES ( dim_client[client_id] ), [Ending AUM], DESC )
RETURN
    DIVIDE ( CALCULATE ( [Ending AUM], Top10 ), [Ending AUM] )
		Valid

## Please return
1. The measure DAX, using only tables and columns that appear in the metadata above.
2. A short explanation of its filter context: how the "last snapshot" is found in each of the
   three visuals above, in what order the suspect filter and the date filter apply, and what
   happens at the grand total.
3. One DAX test query (EVALUATE ...) that returns the measure at the grand total, by
   dim_date[year], and by dim_client[client_tier] for 2024.
4. Any assumption you had to make.
```

## Response 1

```text
Below are the measure, its filter context in each of your three visuals, a test query and my assumptions.

One thing to know first: your metadata already has an `AUM-Weighted Alpha` measure in `_Measure`, and its logic is basically correct. The version below keeps that logic and makes three small changes:
- It uses `MAX` to find the last date instead of `LASTNONBLANK`. It picks the same date and is cheaper.
- It points the date filter at `dim_date`.
- It wraps the suspect filter in `KEEPFILTERS`.

## 1. Measure

```dax
AUM-Weighted Alpha =
VAR LastSnapshot =
    MAX ( fact_portfolio_snapshot[snapshot_date] )    -- last 1st-of-month with rows in the current filter
RETURN
    CALCULATE (
        DIVIDE (
            SUMX (
                fact_portfolio_snapshot,
                fact_portfolio_snapshot[aum] * fact_portfolio_snapshot[active_alpha_ytd]
            ),
            SUM ( fact_portfolio_snapshot[aum] )
        ),
        TREATAS ( { LastSnapshot }, dim_date[Date] ),
        KEEPFILTERS ( fact_portfolio_snapshot[is_return_suspect] = 0 )
    )
```

- **Home table:** `_Measure`. When you rename that table to `_Measures`, the measure moves with it.
- **Format string:** `0.00%`.
- **Why it's safe for these columns:**
  - It never adds `aum` or `active_alpha_ytd` across dates: only one snapshot date is ever in scope.
  - It never uses `LASTDATE`, `ENDOFMONTH` or `CLOSINGBALANCE*`, so it can't land on a month-end date that has no rows.
- **BLANK when nothing qualifies:** if there are no rows, `LastSnapshot` is blank, `TREATAS` matches nothing and `DIVIDE` returns BLANK. The same happens if every row on that date is suspect.

## 2. Filter context

**How the last snapshot is found.** `MAX(snapshot_date)` runs in the visual's full filter context, so you get the latest date that actually has fact rows for that cell. That's the same date `LASTNONBLANK(…COUNTROWS…)` gives, so it matches `[Ending AUM]` everywhere. `TREATAS` then pins `dim_date[Date]` to that one day. It only replaces filters on that column, so filters like Year stay in place, and they don't conflict because the date already sits inside them.

| Visual | Filter context | Last snapshot used |
|---|---|---|
| Card | none | 2024-12-01, all non-suspect rows on that date |
| Table by `dim_date[Year]` | Year = Y | Y-12-01, or the latest month with data if the year is partial. Each year shows its full-year YTD alpha. |
| Table by `dim_client[client_tier]`, 2024 | Year = 2024 and tier = T | The latest 2024 date with rows for tier T. Normally Dec 1; earlier only if no client in that tier has a December row. |

**Order of the suspect and date filters.** Inside `CALCULATE`, the two filter arguments don't apply one after the other. Both are built from the outer context and then intersected. The order that matters is that `LastSnapshot` is calculated before the suspect filter exists. So:
1. The date is chosen from all rows, suspect ones included.
2. Then the suspect rows on that date are dropped.

A client whose December row is suspect is left out. Their November row isn't used in its place, because a November YTD number isn't a full-year value. If every row on the last date is suspect, the result is BLANK rather than an older month's number. `KEEPFILTERS` means a slicer set to `is_return_suspect = 1` also gives BLANK, instead of being silently overridden.

**Grand total.**
- **By year:** the total row has no year filter, so it shows the 2024-12-01 value, which equals the card. It is not a sum or average of the yearly rows. That's correct, because YTD rates can't be added up.
- **By tier, 2024:** the tier filter is removed and 2024 stays, so the total is the AUM-weighted alpha across all tiers on 2024-12-01. When every tier row uses Dec 1, it equals the AUM-weighted blend of the rows.

## 3. Test query (DAX query view)

```dax
DEFINE
    MEASURE '_Measure'[AUM-Weighted Alpha] =
        VAR LastSnapshot = MAX ( fact_portfolio_snapshot[snapshot_date] )
        RETURN
            CALCULATE (
                DIVIDE (
                    SUMX ( fact_portfolio_snapshot,
                        fact_portfolio_snapshot[aum] * fact_portfolio_snapshot[active_alpha_ytd] ),
                    SUM ( fact_portfolio_snapshot[aum] )
                ),
                TREATAS ( { LastSnapshot }, dim_date[Date] ),
                KEEPFILTERS ( fact_portfolio_snapshot[is_return_suspect] = 0 )
            )
    MEASURE '_Measure'[_t Last Snapshot] =
        MAX ( fact_portfolio_snapshot[snapshot_date] )
    MEASURE '_Measure'[_t Qualifying Rows] =
        VAR d = MAX ( fact_portfolio_snapshot[snapshot_date] )
        RETURN
            CALCULATE ( COUNTROWS ( fact_portfolio_snapshot ),
                TREATAS ( { d }, dim_date[Date] ),
                KEEPFILTERS ( fact_portfolio_snapshot[is_return_suspect] = 0 ) )
    -- Independent cross-check: filters the fact directly, no TREATAS
    MEASURE '_Measure'[_t Check] =
        VAR d = MAX ( fact_portfolio_snapshot[snapshot_date] )
        VAR q =
            FILTER ( fact_portfolio_snapshot,
                fact_portfolio_snapshot[snapshot_date] = d
                    && fact_portfolio_snapshot[is_return_suspect] = 0 )
        RETURN
            DIVIDE ( SUMX ( q, fact_portfolio_snapshot[aum] * fact_portfolio_snapshot[active_alpha_ytd] ),
                     SUMX ( q, fact_portfolio_snapshot[aum] ) )

-- 1) Grand total (card)
EVALUATE
ROW (
    "Last snapshot", [_t Last Snapshot],
    "Qualifying rows", [_t Qualifying Rows],
    "AUM-Weighted Alpha", [AUM-Weighted Alpha],
    "Check", [_t Check]
)

-- 2) By year, with total row
EVALUATE
SUMMARIZECOLUMNS (
    ROLLUPADDISSUBTOTAL ( dim_date[Year], "Is Total" ),
    "Last snapshot", [_t Last Snapshot],
    "Qualifying rows", [_t Qualifying Rows],
    "AUM-Weighted Alpha", [AUM-Weighted Alpha],
    "Check", [_t Check]
)
ORDER BY [Is Total], dim_date[Year]

-- 3) By client tier, 2024, with total row
EVALUATE
SUMMARIZECOLUMNS (
    ROLLUPADDISSUBTOTAL ( dim_client[client_tier], "Is Total" ),
    TREATAS ( { 2024 }, dim_date[Year] ),
    "Last snapshot", [_t Last Snapshot],
    "Qualifying rows", [_t Qualifying Rows],
    "AUM-Weighted Alpha", [AUM-Weighted Alpha],
    "Check", [_t Check]
)
ORDER BY [Is Total], dim_client[client_tier]
```

**What to expect:**
- `AUM-Weighted Alpha` and `Check` match on every row.
- The total row in query 2 equals the result of query 1.
- In query 2, each year's last snapshot is Dec 1 of that year.
- The total row in query 3 equals the 2024 row in query 2.

The `DEFINE MEASURE` only applies to this query, so nothing changes in the model until you use the "Update model" option.

## 4. Assumptions

- **Home table:** `_Measure` (it exists today); the planned rename carries the measure along.
- **Which "last snapshot":** it's the last snapshot of any rows, not the last snapshot of non-suspect rows. If you want the latter, change the VAR to `CALCULATE ( MAX ( fact_portfolio_snapshot[snapshot_date] ), fact_portfolio_snapshot[is_return_suspect] = 0 )`.
- **Who's included:** clients with a row on the last snapshot date. Clients who left earlier drop out, the same as `[Ending AUM]`.
- **Units:** `active_alpha_ytd` is stored as a decimal (0.012 = 1.2%), hence the `0.00%` format. If it's in bps, change the format.
- **Blank alpha:** I assumed no rows have `aum` but a blank `active_alpha_ytd`. Such rows would sit in the denominator as zeros and pull the result toward 0. If they exist, add `NOT ISBLANK ( fact_portfolio_snapshot[active_alpha_ytd] )` as another filter.
- **Blank flag:** a blank `is_return_suspect` counts as 0 (qualifying), because in DAX `BLANK() = 0` is true. Use `== 0` if blanks should be excluded.
- **Date table:** visuals use `dim_date[Year]` and `dim_date[Date]` (`dim_date[date]` in the relationships is the same column; DAX names aren't case-sensitive). The `LocalDateTable` hanging off `dim_date[date]` suggests Auto date/time is still on. Make sure visuals use `dim_date[Year]`, not the auto date hierarchy.
```

---

## Prompt 2 — Test / Debug *(only if needed: e.g. an error message, a wrong number, or a claim you want Claude to justify)*

```text
PASTE YOUR FOLLOW-UP HERE
```

## Response 2

```text
PASTE CLAUDE'S RESPONSE HERE
```
