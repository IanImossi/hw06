"""
HW6 Part B - Reconcile the Power BI DAX measure library to independent pandas calculations.

Run from the hw06 folder (or anywhere):
    python scripts/01_reconcile_measures.py

Inputs
    Wildcat Capital Clean/*.csv     the clean CSVs (pandas side, computed from scratch)
    reports/powerbi_values.csv      measure, slice, value exported from Power BI DAX query view
Outputs
    reports/pandas_values.csv           every pandas value (written even before Power BI numbers exist)
    reports/measure_reconciliation.csv  measure, slice, powerbi_value, pandas_value, abs_diff, match

Nothing here reads from Power BI except reports/powerbi_values.csv, and that file is only
used for the comparison step. Each pandas function re-creates the DAX filter context by hand:
  * a date window (the dim_date rows left visible by the slice), and
  * an optional client-tier filter (dim_client -> fact tables via client_id).
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "Wildcat Capital Clean"
REPORTS = ROOT / "reports"

CURRENCY_TOL = 0.01
RATIO_TOL = 0.0001

# Measure -> kind. "currency" uses the 0.01 tolerance, "ratio" 0.0001, "text" exact match.
# Fee Yield (bps) is a ratio expressed in basis points; it is compared at the ratio tolerance.
MEASURE_KIND = {
    "AUM (naive SUM)": "currency",
    "Total Fees": "currency",
    "Net Flows": "currency",
    "Ending AUM": "currency",
    "Ending Clients": "currency",  # a count; 0.01 tolerance means it must match exactly
    "Avg AUM per Client": "currency",
    "Ending AUM LY": "currency",
    "AUM YoY %": "ratio",
    "Ending AUM PM": "currency",
    "AUM MoM %": "ratio",
    "Avg Monthly AUM": "currency",
    "Fee Yield (bps)": "ratio",
    "Organic Growth Rate": "ratio",
    "AUM-Weighted Alpha": "ratio",
    "Alpha Signal": "text",
    "Top 10 Client Share": "ratio",
}


# --------------------------------------------------------------------------------------
# Load
# --------------------------------------------------------------------------------------
def load():
    snap = pd.read_csv(DATA / "fact_portfolio_snapshot.csv", parse_dates=["snapshot_date"])
    fees = pd.read_csv(DATA / "fact_fees.csv", parse_dates=["fee_date"])
    txn = pd.read_csv(DATA / "fact_transactions.csv", parse_dates=["txn_date"])
    client = pd.read_csv(DATA / "dim_client.csv")
    date = pd.read_csv(DATA / "dim_date.csv", parse_dates=["date"])

    tier = client.set_index("client_id")["client_tier"]
    for df in (snap, fees, txn):
        # The model filters facts by tier through fact[client_id] -> dim_client[client_id].
        df["client_tier"] = df["client_id"].map(tier)
    return snap, fees, txn, client, date


SNAP, FEES, TXN, CLIENT, DATE = load()
CAL_MIN, CAL_MAX = DATE["date"].min(), DATE["date"].max()


# --------------------------------------------------------------------------------------
# Filter context
# --------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Ctx:
    """The rows of dim_date and dim_client a DAX slice leaves visible."""

    start: pd.Timestamp = CAL_MIN
    end: pd.Timestamp = CAL_MAX
    tier: str | None = None

    def clip(self) -> "Ctx":
        # Shifted windows only keep dates that exist in dim_date (as DAX time intelligence does).
        return Ctx(max(self.start, CAL_MIN), min(self.end, CAL_MAX), self.tier)

    def same_period_last_year(self) -> "Ctx":
        return Ctx(self.start - pd.DateOffset(years=1), self.end - pd.DateOffset(years=1), self.tier).clip()

    def previous_month(self) -> "Ctx":
        # DATEADD(dim_date[date], -1, MONTH); month-end dates map to the shorter month's end.
        return Ctx(self.start - pd.DateOffset(months=1), self.end - pd.DateOffset(months=1), self.tier).clip()


def rows(df: pd.DataFrame, date_col: str, ctx: Ctx) -> pd.DataFrame:
    m = df[date_col].between(ctx.start, ctx.end)
    if ctx.tier is not None:
        m &= df["client_tier"] == ctx.tier
    return df[m]


def last_snapshot(s: pd.DataFrame) -> pd.DataFrame:
    """LASTNONBLANK(dim_date[date], COUNTROWS(snapshot)): rows on the latest date that has data."""
    if s.empty:
        return s
    return s[s["snapshot_date"] == s["snapshot_date"].max()]


def sum_or_blank(series: pd.Series) -> float:
    """DAX SUM over no rows is BLANK, not 0. Return NaN (our BLANK) for empty input."""
    return series.sum() if len(series) else np.nan


def divide(n, d):
    """DAX DIVIDE without an alternate result: blank (NaN) when the denominator is blank or 0."""
    if d is None or pd.isna(d) or d == 0 or n is None or pd.isna(n):
        return np.nan
    return n / d


# --------------------------------------------------------------------------------------
# Measures (pandas twins of the DAX in powerbi/measures.md)
# --------------------------------------------------------------------------------------
def aum_naive(ctx):
    return sum_or_blank(rows(SNAP, "snapshot_date", ctx)["aum"])


def total_fees(ctx):
    return sum_or_blank(rows(FEES, "fee_date", ctx)["amount"])


def net_flows(ctx):
    t = rows(TXN, "txn_date", ctx)
    dep = sum_or_blank(t.loc[t.txn_type == "Deposit", "amount"])
    wd = sum_or_blank(t.loc[t.txn_type == "Withdrawal", "amount"])
    if pd.isna(dep) and pd.isna(wd):
        return np.nan  # BLANK - BLANK = BLANK
    return (0 if pd.isna(dep) else dep) - (0 if pd.isna(wd) else wd)  # BLANK acts as 0 in arithmetic


def ending_aum(ctx):
    s = last_snapshot(rows(SNAP, "snapshot_date", ctx))
    return s["aum"].sum() if not s.empty else np.nan


def ending_clients(ctx):
    s = last_snapshot(rows(SNAP, "snapshot_date", ctx))
    return s["client_id"].nunique() if not s.empty else np.nan


def avg_aum_per_client(ctx):
    return divide(ending_aum(ctx), ending_clients(ctx))


def ending_aum_ly(ctx):
    return ending_aum(ctx.same_period_last_year())


def aum_yoy(ctx):
    ly = ending_aum_ly(ctx)
    return divide(ending_aum(ctx) - ly, ly)


def ending_aum_pm(ctx):
    return ending_aum(ctx.previous_month())


def aum_mom(ctx):
    pm = ending_aum_pm(ctx)
    return divide(ending_aum(ctx) - pm, pm)


def avg_monthly_aum(ctx):
    s = rows(SNAP, "snapshot_date", ctx)
    return divide(sum_or_blank(s["aum"]), s["snapshot_date"].nunique())


def fee_yield_bps(ctx):
    s = rows(SNAP, "snapshot_date", ctx)
    return divide(total_fees(ctx) * 12 * 10000, sum_or_blank(s["aum"]))


def organic_growth(ctx):
    return divide(net_flows(ctx), ending_aum_ly(ctx))


def weighted_alpha(ctx, include_suspect=False):
    s = last_snapshot(rows(SNAP, "snapshot_date", ctx))  # last date is found BEFORE excluding suspects
    if not include_suspect:
        s = s[s["is_return_suspect"] == 0]  # same test as DAX [is_return_suspect] = 0
    if s.empty:
        return np.nan
    return divide((s["aum"] * s["active_alpha_ytd"]).sum(), s["aum"].sum())


def alpha_signal(ctx):
    a = weighted_alpha(ctx)
    if pd.isna(a):
        return ""
    if a >= 0.02:
        return "Outperforming"
    if a <= -0.02:
        return "Lagging"
    return "In line"


def client_ending_aum(ctx) -> pd.Series:
    """[Ending AUM] evaluated per dim_client[client_id] (context transition inside TOPN):
    each client's balance at that client's own last snapshot inside the window."""
    s = rows(SNAP, "snapshot_date", ctx)
    last = s.groupby("client_id")["snapshot_date"].transform("max")
    return s[s["snapshot_date"] == last].groupby("client_id")["aum"].sum()


def top10_share(ctx):
    # VALUES(dim_client[client_id]) = dim_client rows left by the tier filter (dates do not filter dim_client).
    clients = CLIENT if ctx.tier is None else CLIENT[CLIENT.client_tier == ctx.tier]
    per_client = client_ending_aum(ctx).reindex(clients["client_id"]).dropna()
    if per_client.empty:
        return np.nan
    # TOPN(10, ..., DESC) keeps ties at the 10th value, so take every client >= the 10th largest.
    cutoff = per_client.sort_values(ascending=False).iloc[min(9, len(per_client) - 1)]
    top_ids = per_client[per_client >= cutoff].index
    # CALCULATE([Ending AUM], Top10): last date that has data for the top-10 set, summed at that date.
    s = rows(SNAP, "snapshot_date", ctx)
    top = last_snapshot(s[s["client_id"].isin(top_ids)])
    return divide(top["aum"].sum(), ending_aum(ctx))


MEASURES = {
    "AUM (naive SUM)": aum_naive,
    "Total Fees": total_fees,
    "Net Flows": net_flows,
    "Ending AUM": ending_aum,
    "Ending Clients": ending_clients,
    "Avg AUM per Client": avg_aum_per_client,
    "Ending AUM LY": ending_aum_ly,
    "AUM YoY %": aum_yoy,
    "Ending AUM PM": ending_aum_pm,
    "AUM MoM %": aum_mom,
    "Avg Monthly AUM": avg_monthly_aum,
    "Fee Yield (bps)": fee_yield_bps,
    "Organic Growth Rate": organic_growth,
    "AUM-Weighted Alpha": weighted_alpha,
    "Alpha Signal": alpha_signal,
    "Top 10 Client Share": top10_share,
}


# --------------------------------------------------------------------------------------
# Slices required by the assignment
# --------------------------------------------------------------------------------------
def year_ctx(y, tier=None):
    return Ctx(pd.Timestamp(y, 1, 1), pd.Timestamp(y, 12, 31), tier)


BY_YEAR = ["Ending AUM", "Ending AUM LY", "AUM YoY %", "Avg Monthly AUM", "Fee Yield (bps)",
           "Organic Growth Rate", "AUM-Weighted Alpha", "Alpha Signal", "AUM (naive SUM)"]
BY_TIER_2024 = ["Ending AUM", "Avg AUM per Client", "Ending AUM LY", "AUM YoY %", "Fee Yield (bps)",
                "Organic Growth Rate", "AUM-Weighted Alpha", "Alpha Signal", "Top 10 Client Share"]
DEC_2024 = ["Ending AUM", "Ending AUM PM", "AUM MoM %"]


def slices():
    yield "Grand Total", Ctx(), list(MEASURES)
    for y in sorted(DATE["year"].unique()):
        yield f"Year {y}", year_ctx(y), BY_YEAR
    for t in sorted(CLIENT["client_tier"].unique()):
        yield f"2024 Tier {t}", year_ctx(2024, t), BY_TIER_2024
    yield "Dec 2024", Ctx(pd.Timestamp(2024, 12, 1), pd.Timestamp(2024, 12, 31)), DEC_2024


def pandas_values() -> pd.DataFrame:
    out = []
    for label, ctx, names in slices():
        for name in names:
            out.append({"measure": name, "slice": label, "value": MEASURES[name](ctx)})
    return pd.DataFrame(out)


# --------------------------------------------------------------------------------------
# Compare
# --------------------------------------------------------------------------------------
def to_number(v):
    """Parse a Power BI value. Handles $, thousands commas, %, and accounting negatives like ($1,234.00).
    Raises ValueError for anything else; compare() reports that row as a mismatch instead of crashing."""
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return np.nan
    s = str(v).strip().replace(",", "").replace("$", "").replace("\u2212", "-")
    if s == "":
        return np.nan
    negative = s.startswith("(") and s.endswith(")")
    if negative:
        s = s[1:-1].strip()
    pct = s.endswith("%")
    if pct:
        s = s[:-1].strip()
    x = float(s)
    if pct:
        x /= 100
    return -x if negative else x


def compare(pbi: pd.DataFrame, pdv: pd.DataFrame) -> pd.DataFrame:
    pbi = pbi.copy()
    pbi["measure"] = pbi["measure"].str.strip()
    pbi["slice"] = pbi["slice"].astype(str).str.strip()
    df = pdv.rename(columns={"value": "pandas_value"}).merge(
        pbi.rename(columns={"value": "powerbi_value"}), on=["measure", "slice"], how="outer", indicator="side"
    )
    recs = []
    for r in df.itertuples(index=False):
        kind = MEASURE_KIND.get(r.measure, "currency")
        pv, qv = r.powerbi_value, r.pandas_value
        if r.side != "both":  # row exists on one side only
            recs.append((r.measure, r.slice, pv, qv, np.nan, False))
            continue
        if kind == "text":
            a = "" if pd.isna(pv) else str(pv).strip()
            b = "" if pd.isna(qv) else str(qv).strip()
            recs.append((r.measure, r.slice, a, b, np.nan, a == b))
            continue
        try:
            a, b = to_number(pv), to_number(qv)
        except ValueError:  # unparseable Power BI value: flag it, keep going
            recs.append((r.measure, r.slice, pv, qv, np.nan, False))
            continue
        if np.isnan(a) and np.isnan(b):  # both blank, e.g. YoY in 2020
            recs.append((r.measure, r.slice, a, b, 0.0, True))
            continue
        diff = abs(a - b)
        tol = CURRENCY_TOL if kind == "currency" else RATIO_TOL
        recs.append((r.measure, r.slice, a, b, diff, bool(diff <= tol)))
    out = pd.DataFrame(recs, columns=["measure", "slice", "powerbi_value", "pandas_value", "abs_diff", "match"])
    return out


def main():
    REPORTS.mkdir(exist_ok=True)
    pdv = pandas_values()
    pdv.to_csv(REPORTS / "pandas_values.csv", index=False)
    print(f"pandas: {len(pdv)} values -> reports/pandas_values.csv")

    pbi_path = REPORTS / "powerbi_values.csv"
    if not pbi_path.exists():
        sys.exit("reports/powerbi_values.csv not found. Export it from DAX query view "
                 "(powerbi/export_queries.dax), then run this script again.")
    # sep=None sniffs commas or tabs (a grid pasted from DAX query view is tab-separated);
    # headers like "[measure]" are normalised to "measure".
    pbi = pd.read_csv(pbi_path, sep=None, engine="python", dtype=str, keep_default_na=False, encoding="utf-8-sig")
    pbi.columns = [c.strip().strip("\ufeff").strip("[]").lower() for c in pbi.columns]
    missing = {"measure", "slice", "value"} - set(pbi.columns)
    if missing:
        sys.exit(f"reports/powerbi_values.csv is missing columns: {sorted(missing)}")
    pbi = pbi[pbi["measure"].str.strip().str.strip("[]").str.lower() != "measure"]  # drop header rows pasted again
    pbi = pbi[["measure", "slice", "value"]]
    pbi["measure"], pbi["slice"] = pbi["measure"].str.strip(), pbi["slice"].str.strip()
    dupes = pbi[pbi.duplicated(["measure", "slice"], keep=False)]
    if not dupes.empty:  # a pasted-twice row would otherwise be counted as two matches
        sys.exit("reports/powerbi_values.csv has duplicate measure/slice rows:\n" + dupes.to_string(index=False))
    rec = compare(pbi, pdv)
    rec.to_csv(REPORTS / "measure_reconciliation.csv", index=False)

    n, ok = len(rec), int(rec["match"].sum())
    print(f"reconciliation: {n} rows, {ok} match, {n - ok} mismatch -> reports/measure_reconciliation.csv")
    if ok < n:
        print(rec[~rec["match"]].to_string(index=False))
        sys.exit(1)


if __name__ == "__main__":
    main()
