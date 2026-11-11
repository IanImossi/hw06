"""
HW6 Part C - pandas evidence for the design questions in powerbi/measures.md.

Run from the hw06 folder:
    python scripts/02_part_c_evidence.py

Reuses the measure functions in 01_reconcile_measures.py so every number here is computed
with exactly the same filter-context logic that was reconciled against Power BI.
"""

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("rec", HERE / "01_reconcile_measures.py")
m = importlib.util.module_from_spec(spec)
sys.modules["rec"] = m  # dataclasses need the module registered
spec.loader.exec_module(m)

S, F = m.SNAP, m.FEES
ALL = m.Ctx()
Y24 = m.year_ctx(2024)


def money(x):
    return f"${x:,.2f}"


print("=" * 70)
print("(a) Ending AUM vs SUMX ( VALUES ( dim_client[client_id] ), [Ending AUM] )")
print("=" * 70)
ending = m.ending_aum(ALL)
per_client = m.client_ending_aum(ALL)  # each client's balance at that client's own last snapshot
sumx = per_client.sum()
last_date = S.groupby("client_id")["snapshot_date"].max()
departed = last_date[last_date < S["snapshot_date"].max()]
print("Ending AUM               ", money(ending))
print("SUMX over clients        ", money(sumx))
print("Difference               ", money(sumx - ending))
print("Clients whose last snapshot is before Dec 2024:", len(departed))
print("  by year of last snapshot:", departed.dt.year.value_counts().sort_index().to_dict())
print("  sum of their last balances:", money(per_client[departed.index].sum()))

print()
print("=" * 70)
print("(b) 2024 Fee Yield vs Effective Fee Rate")
print("=" * 70)
f24 = m.rows(F, "fee_date", Y24)
s24 = m.rows(S, "snapshot_date", Y24)
fees = f24["amount"].sum()
print("2024 fees                 ", money(fees))
print("Sum aum_basis (fact_fees) ", money(f24["aum_basis"].sum()),
      f"-> Effective Fee Rate {fees * 12e4 / f24['aum_basis'].sum():.2f} bps")
print("Sum aum (snapshot)        ", money(s24["aum"].sum()),
      f"-> Fee Yield {m.fee_yield_bps(Y24):.2f} bps")
print("Fee rows per client-month (max):", f24.groupby(["client_id", "fee_date"]).size().max())

joined = s24.merge(f24[["client_id", "fee_date", "aum_basis", "amount"]],
                   left_on=["client_id", "snapshot_date"], right_on=["client_id", "fee_date"], how="left")
billed = joined[joined["amount"].notna()]
unbilled = joined[joined["amount"].isna()]
print("Max |aum_basis - aum| where a fee row exists:", (billed["aum_basis"] - billed["aum"]).abs().max())
print(f"Snapshot client-months: {len(joined):,}; with no fee row: {len(unbilled):,} "
      f"({len(unbilled) / len(joined):.1%}) holding {money(unbilled['aum'].sum())}")

all_join = S.merge(F[["client_id", "fee_date", "amount"]], left_on=["client_id", "snapshot_date"],
                   right_on=["client_id", "fee_date"], how="left")
all_join["no_fee"] = all_join["amount"].isna()
print("Share of client-months with no fee row, by year:")
print(all_join.groupby(all_join["snapshot_date"].dt.year)["no_fee"].mean().round(4).to_string())
print("2024 share by tier:")
print(all_join[all_join["snapshot_date"].dt.year == 2024].groupby("client_tier")["no_fee"].mean().round(4).to_string())
print("Clients missing at least one 2024 fee month:", unbilled["client_id"].nunique())
fees_wo_snapshot = F.merge(S[["client_id", "snapshot_date"]], left_on=["client_id", "fee_date"],
                           right_on=["client_id", "snapshot_date"], how="left")["snapshot_date"].isna().sum()
print("Fee rows with no matching snapshot:", fees_wo_snapshot)
gap_bps = fees * 12e4 / f24["aum_basis"].sum() - m.fee_yield_bps(Y24)
print(f"Revenue gap = {gap_bps:.2f} bps x Avg Monthly AUM {money(m.avg_monthly_aum(Y24))} "
      f"= {money(gap_bps / 1e4 * m.avg_monthly_aum(Y24))}")

print()
print("=" * 70)
print("(c) AUM-Weighted Alpha: last snapshot, suspects")
print("=" * 70)
last = m.last_snapshot(S)
clean, suspect = last[last["is_return_suspect"] == 0], last[last["is_return_suspect"] == 1]
print(f"Rows at last snapshot {last['snapshot_date'].max().date()}: {len(last)}; suspect: {len(suspect)}")
print(f"Suspect alpha range {suspect['active_alpha_ytd'].min():.2%} to {suspect['active_alpha_ytd'].max():.2%}, "
      f"mean {suspect['active_alpha_ytd'].mean():.2%}, AUM {money(suspect['aum'].sum())}")
print(f"Clean alpha range   {clean['active_alpha_ytd'].min():.2%} to {clean['active_alpha_ytd'].max():.2%}")
print(f"AUM-weighted, suspects excluded : {m.weighted_alpha(ALL):.4%}")
print(f"Simple mean, same rows          : {clean['active_alpha_ytd'].mean():.4%}")
print(f"AUM-weighted, suspects included : {m.weighted_alpha(ALL, include_suspect=True):.4%}")
print(f"Simple mean, suspects included  : {last['active_alpha_ytd'].mean():.4%}")
clean = clean.assign(size_quintile=pd.qcut(clean["aum"], 5, labels=[1, 2, 3, 4, 5]))
print("Simple mean alpha by AUM quintile (1 = smallest):")
print(clean.groupby("size_quintile", observed=True)["active_alpha_ytd"].mean().map("{:.2%}".format).to_string())
print("Retail: simple mean "
      f"{clean.loc[clean.client_tier == 'Retail', 'active_alpha_ytd'].mean():.2%} vs weighted "
      f"{m.weighted_alpha(m.Ctx(tier='Retail')):.2%}")
y = S[(S["snapshot_date"].dt.year == 2024) & (S["is_return_suspect"] == 0)]
by_month = (y.assign(w=y["aum"] * y["active_alpha_ytd"]).groupby("month")[["w", "aum"]].sum()
            .pipe(lambda g: g["w"] / g["aum"]))
print("2024 AUM-weighted YTD alpha by month:", by_month.map("{:.2%}".format).to_dict())

print()
print("=" * 70)
print("(d) Organic Growth vs AUM YoY by tier, 2024")
print("=" * 70)
out = []
for t in ["Retail", "HNW", "UHNW", None]:
    c = m.year_ctx(2024, t)
    e, ly, nf = m.ending_aum(c), m.ending_aum_ly(c), m.net_flows(c)
    out.append({"tier": t or "Firm", "net_flows": nf, "ending_aum_ly": ly, "ending_aum": e,
                "organic_%": nf / ly * 100, "yoy_%": (e - ly) / ly * 100, "growth_not_from_flows": e - ly - nf,
                "share_of_net_flows_%": np.nan, "share_of_ending_aum_%": np.nan,
                "fee_yield_bps": m.fee_yield_bps(c)})
d = pd.DataFrame(out).set_index("tier")
d["share_of_net_flows_%"] = d["net_flows"] / d.loc["Firm", "net_flows"] * 100
d["share_of_ending_aum_%"] = d["ending_aum"] / d.loc["Firm", "ending_aum"] * 100
pd.set_option("display.width", 200)
print(d.round(2).to_string())
