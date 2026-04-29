#!/usr/bin/env python3
"""
Vietnam Alpha Suite -- Ronin Network Tokenomics Visualizer
Generates ronin_economics_2026.png

Requirements:
    pip install requests matplotlib numpy
"""

import calendar
import sys
from datetime import date
from typing import Optional

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from matplotlib.gridspec import GridSpec
from matplotlib.lines import Line2D
import numpy as np
import requests

# ── Ronin Brand Palette ───────────────────────────────────────────────────────

BG_DARK    = "#0D111C"   # deep navy (Ronin website bg)
BG_PANEL   = "#131928"   # card background
GRID_COLOR = "#1E2840"   # subtle grid lines
RON_BLUE   = "#1652F0"   # Ronin primary blue
RON_CYAN   = "#3D7BFF"   # lighter accent
OLD_CHAIN  = "#FF6B81"   # old sidechain (warm red)
BURN_RED   = "#FF4757"   # burn / bearish
MINT_GREEN = "#2ED573"   # mint / bullish
GOLD       = "#FFA502"   # highlight / current value
TEXT_WHITE = "#E8EAED"
TEXT_DIM   = "#8B97B0"

# ── Constants ─────────────────────────────────────────────────────────────────

RON_MAX_SUPPLY     = 1_000_000_000
OLD_INFLATION_RATE = 0.20    # 20 % annual   -- old Ronin sidechain
NEW_INFLATION_RATE = 0.005   # 0.5 % annual  -- new Layer 2
BURN_RATE_ANNUAL   = 0.003   # 0.3 % annual burn from on-chain fees
COINGECKO_URL      = "https://api.coingecko.com/api/v3/coins/ronin"
OUTPUT_FILE        = "ronin_economics_2026.png"

# ── Mock data (active if CoinGecko is unreachable) ────────────────────────────

_MOCK = {
    "price_usd":          1.34,
    "circulating_supply": 388_500_000,
    "max_supply":         RON_MAX_SUPPLY,
    "market_cap_usd":     520_390_000,
    "volume_24h":         14_200_000,
    "price_change_24h":   3.2,
    "source":             "mock data",
}

# ── Data Fetching ─────────────────────────────────────────────────────────────

def fetch_ron_data() -> dict:
    """
    Pull live RON data from CoinGecko's free API.
    Falls back to mock data if the request fails for any reason.
    """
    try:
        resp = requests.get(
            COINGECKO_URL,
            params={"localization": "false", "tickers": "false",
                    "community_data": "false", "developer_data": "false"},
            timeout=10,
        )
        resp.raise_for_status()
        md = resp.json()["market_data"]
        return {
            "price_usd":          md["current_price"]["usd"],
            "circulating_supply": md["circulating_supply"] or _MOCK["circulating_supply"],
            "max_supply":         RON_MAX_SUPPLY,
            "market_cap_usd":     md["market_cap"]["usd"],
            "volume_24h":         md["total_volume"]["usd"],
            "price_change_24h":   md["price_change_percentage_24h"] or 0.0,
            "source":             "CoinGecko",
        }
    except Exception as exc:
        print(f"[!] CoinGecko unavailable ({exc}). Using mock data.")
        return _MOCK


# ── 2026 Migration Economics Engine ──────────────────────────────────────────

def compute_scenarios(data: dict) -> dict:
    """
    Projects RON circulating supply over 12 months under two regimes:

      Old Sidechain  -- 20 % annual inflation, compounded monthly.
      New Layer 2    -- 0.5 % annual inflation minus 0.3 % fee-burn, net ~0.2 %.

    Returns all arrays needed by the chart builder.
    """
    s0      = data["circulating_supply"]
    months  = np.arange(1, 13)

    # Monthly compounding rates
    r_old   = OLD_INFLATION_RATE / 12
    r_new   = (NEW_INFLATION_RATE - BURN_RATE_ANNUAL) / 12   # net after burn

    old_supply = np.minimum(s0 * (1 + r_old) ** months, RON_MAX_SUPPLY)
    new_supply = np.clip(s0 * (1 + r_new) ** months, s0, RON_MAX_SUPPLY)

    # Daily rates based on current circulating supply
    daily_mint_old = s0 * OLD_INFLATION_RATE / 365
    daily_mint_new = s0 * NEW_INFLATION_RATE / 365
    daily_burn     = s0 * BURN_RATE_ANNUAL   / 365

    return {
        "months":         months,
        "old_supply":     old_supply,
        "new_supply":     new_supply,
        "daily_mint_old": daily_mint_old,
        "daily_mint_new": daily_mint_new,
        "daily_burn":     daily_burn,
        "saved_12m":      float(old_supply[-1] - new_supply[-1]),
    }


# ── Helpers ───────────────────────────────────────────────────────────────────

def month_labels(n: int = 12) -> list[str]:
    today = date.today()
    out   = []
    for i in range(1, n + 1):
        m = (today.month - 1 + i) % 12 + 1
        y = today.year + (today.month - 1 + i) // 12
        out.append(f"{calendar.month_abbr[m]}\n'{str(y)[2:]}")
    return out


def _style_ax(ax) -> None:
    """Apply shared dark-panel styling to an axes."""
    ax.set_facecolor(BG_PANEL)
    ax.grid(color=GRID_COLOR, linewidth=0.55, alpha=0.8)
    ax.tick_params(colors=TEXT_DIM, labelsize=9)
    for spine in ax.spines.values():
        spine.set_edgecolor(GRID_COLOR)


# ── Chart Builder ─────────────────────────────────────────────────────────────

def build_chart(data: dict, sc: dict) -> plt.Figure:
    plt.style.use("dark_background")

    fig = plt.figure(figsize=(16, 11), facecolor=BG_DARK)
    gs  = GridSpec(
        2, 2, figure=fig,
        height_ratios=[3, 2],
        hspace=0.44, wspace=0.30,
        top=0.87, bottom=0.07, left=0.07, right=0.95,
    )

    ax_sup  = fig.add_subplot(gs[0, :])
    ax_burn = fig.add_subplot(gs[1, 0])
    ax_inf  = fig.add_subplot(gs[1, 1])

    for ax in (ax_sup, ax_burn, ax_inf):
        _style_ax(ax)

    x      = sc["months"]
    xlabs  = month_labels()
    old_m  = sc["old_supply"] / 1e6
    new_m  = sc["new_supply"] / 1e6
    circ_m = data["circulating_supply"] / 1e6

    # ── Chart 1: 12-Month Supply Projection (full-width, dual y-axis) ────────
    ax_sup_r = ax_sup.twinx()
    ax_sup_r.tick_params(colors=TEXT_DIM, labelsize=9)
    ax_sup_r.spines["right"].set_edgecolor(GRID_COLOR)
    for s in ("left", "top", "bottom"):
        ax_sup_r.spines[s].set_visible(False)
    ax_sup_r.grid(False)

    # Savings zone fill
    ax_sup.fill_between(x, new_m, old_m,
                        alpha=0.10, color=MINT_GREEN, zorder=1,
                        label="_nolegend_")

    # Old sidechain trajectory
    ax_sup.plot(x, old_m,
                color=OLD_CHAIN, linewidth=2.5, linestyle="--",
                marker="o", markersize=5,
                markerfacecolor=BG_DARK, markeredgewidth=1.8,
                label=f"Old Sidechain  ({OLD_INFLATION_RATE*100:.0f}% annual inflation)",
                zorder=3)

    # New L2 trajectory
    ax_sup.plot(x, new_m,
                color=RON_BLUE, linewidth=2.8,
                marker="o", markersize=5,
                markerfacecolor=BG_DARK, markeredgewidth=1.8,
                label=f"New Layer 2  (<{NEW_INFLATION_RATE*100:.1f}% net inflation after burns)",
                zorder=3)

    # Current supply reference
    ax_sup.axhline(circ_m, color=GOLD, linewidth=1.1, linestyle=":", alpha=0.75)
    ax_sup.text(0.5, circ_m + (old_m.max() - circ_m) * 0.04,
                f"Current: {circ_m:.1f}M RON",
                color=GOLD, fontsize=8.5, ha="center", transform=ax_sup.get_yaxis_transform())

    # Max supply cap
    ax_sup.axhline(1000, color=TEXT_DIM, linewidth=0.7, linestyle=":", alpha=0.35)
    ax_sup.text(0.99, 999.5, "Max 1,000M",
                color=TEXT_DIM, fontsize=7.5, ha="right", va="top",
                transform=ax_sup.get_yaxis_transform(), alpha=0.6)

    # Savings callout annotation
    mid_x = 6
    mid_y = (old_m[5] + new_m[5]) / 2
    ax_sup.annotate(
        f"+{sc['saved_12m']/1e6:.1f}M RON\nsaved vs old chain",
        xy=(mid_x, mid_y), xycoords="data",
        color=MINT_GREEN, fontsize=9, ha="center", va="center",
        bbox=dict(boxstyle="round,pad=0.35", facecolor=BG_DARK,
                  edgecolor=MINT_GREEN, alpha=0.90, linewidth=1.2),
    )

    # Sync right y-axis to % of max supply
    lo, hi = old_m.min() * 0.9985, old_m.max() * 1.004
    ax_sup.set_ylim(lo, hi)
    ax_sup_r.set_ylim(lo / 10, hi / 10)   # divide by 10 because axis is in M and max is 1000M
    ax_sup_r.set_ylabel("% of Max Supply (1B RON)", color=TEXT_DIM, fontsize=10)
    ax_sup_r.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.2f%%"))

    ax_sup.set_xticks(x)
    ax_sup.set_xticklabels(xlabs, fontsize=8.5, color=TEXT_DIM)
    ax_sup.set_ylabel("Circulating Supply (M RON)", color=TEXT_DIM, fontsize=10)
    ax_sup.set_title("12-Month RON Supply Projection  —  Old Sidechain vs New Layer 2",
                     color=TEXT_WHITE, fontsize=13, fontweight="bold", pad=10)
    ax_sup.yaxis.set_major_formatter(
        mticker.FuncFormatter(lambda v, _: f"{v:.0f}M"))
    ax_sup.legend(loc="upper left", facecolor=BG_PANEL,
                  edgecolor=GRID_COLOR, fontsize=9.5, labelcolor=TEXT_WHITE,
                  framealpha=0.9)

    # ── Chart 2: Daily Burn vs Mint Rates (bar chart) ────────────────────────
    bar_labels = ["Old Chain\nMint / day", "New L2\nMint / day", "Fee Burn\n/ day"]
    bar_vals   = [sc["daily_mint_old"] / 1e3,
                  sc["daily_mint_new"] / 1e3,
                  sc["daily_burn"]     / 1e3]
    bar_colors = [OLD_CHAIN, RON_BLUE, BURN_RED]
    x_pos      = np.arange(3)

    bars = ax_burn.bar(x_pos, bar_vals, width=0.48,
                       color=bar_colors, edgecolor=BG_DARK, linewidth=0.8, zorder=2)

    for bar, val in zip(bars, bar_vals):
        ax_burn.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + max(bar_vals) * 0.025,
            f"{val:.1f}K\nRON",
            ha="center", va="bottom", fontsize=8.5,
            color=TEXT_WHITE, fontweight="bold",
        )

    # Mint-to-burn ratio callout
    ratio = sc["daily_mint_old"] / max(sc["daily_burn"], 1)
    ax_burn.annotate(
        f"Old chain mints {ratio:.0f}x\nmore than it burns",
        xy=(0.5, 0.93), xycoords="axes fraction",
        ha="center", va="top", fontsize=8.5, color=GOLD,
        bbox=dict(boxstyle="round,pad=0.3", facecolor=BG_DARK,
                  edgecolor=GOLD, alpha=0.85, linewidth=1.1),
    )

    ax_burn.set_xticks(x_pos)
    ax_burn.set_xticklabels(bar_labels, fontsize=9, color=TEXT_DIM)
    ax_burn.set_ylabel("Daily Volume (K RON)", color=TEXT_DIM, fontsize=10)
    ax_burn.set_title("Daily Mint vs Burn Rate", color=TEXT_WHITE,
                      fontsize=11, fontweight="bold")
    ax_burn.yaxis.set_major_formatter(
        mticker.FuncFormatter(lambda v, _: f"{v:.0f}K"))

    # ── Chart 3: Inflation Rate Comparison (horizontal bars) ────────────────
    inf_labels = [f"Old Sidechain\n(Pre-2026)", f"New Layer 2\n(2026+)"]
    inf_rates  = [OLD_INFLATION_RATE * 100, NEW_INFLATION_RATE * 100]
    y_pos      = np.arange(2)

    h_bars = ax_inf.barh(y_pos, inf_rates, height=0.38,
                          color=[OLD_CHAIN, RON_BLUE],
                          edgecolor=BG_DARK, linewidth=0.8, zorder=2)

    for bar, rate in zip(h_bars, inf_rates):
        ax_inf.text(
            rate + max(inf_rates) * 0.015,
            bar.get_y() + bar.get_height() / 2,
            f"{rate:.1f}%",
            va="center", ha="left",
            color=TEXT_WHITE, fontweight="bold", fontsize=12,
        )

    reduction = (1 - NEW_INFLATION_RATE / OLD_INFLATION_RATE) * 100
    ax_inf.annotate(
        f"   -{reduction:.0f}% inflation\n   reduction",
        xy=(NEW_INFLATION_RATE * 100, 0.48),
        xytext=(5, 0.48),
        ha="left", va="center", fontsize=9.5,
        color=MINT_GREEN, fontweight="bold",
        arrowprops=dict(arrowstyle="->", color=MINT_GREEN, lw=1.4),
    )

    ax_inf.set_yticks(y_pos)
    ax_inf.set_yticklabels(inf_labels, fontsize=9.5, color=TEXT_DIM)
    ax_inf.set_xlabel("Annual Inflation Rate (%)", color=TEXT_DIM, fontsize=10)
    ax_inf.set_title("2026 Migration: Inflation Impact",
                     color=TEXT_WHITE, fontsize=11, fontweight="bold")
    ax_inf.xaxis.set_major_formatter(mticker.FormatStrFormatter("%.0f%%"))
    ax_inf.set_xlim(0, max(inf_rates) * 1.25)

    # ── Figure Header ─────────────────────────────────────────────────────────
    price   = data["price_usd"]
    circ    = data["circulating_supply"]
    mcap    = data["market_cap_usd"]
    vol     = data["volume_24h"]
    chg     = data["price_change_24h"]
    util    = circ / RON_MAX_SUPPLY * 100
    src     = data["source"]

    chg_col  = MINT_GREEN if chg >= 0 else BURN_RED
    chg_sign = "+" if chg >= 0 else ""

    # Title block
    fig.text(0.07,  0.955, "RONIN", fontsize=20, fontweight="bold",
             color=RON_BLUE, va="center")
    fig.text(0.145, 0.956, "(RON)", fontsize=11, color=TEXT_DIM, va="center")
    fig.text(0.195, 0.956, "TOKENOMICS DASHBOARD  ·  2026 MIGRATION ANALYSIS",
             fontsize=11, fontweight="bold", color=TEXT_WHITE, va="center")

    # KPI strip
    kpis = [
        ("PRICE",    f"${price:,.3f}",                   TEXT_WHITE),
        ("24H CHG",  f"{chg_sign}{chg:.1f}%",            chg_col),
        ("CIRC SUP", f"{circ/1e6:.1f}M",                  TEXT_WHITE),
        ("MARKET CAP", f"${mcap/1e6:.0f}M",              TEXT_WHITE),
        ("24H VOL",  f"${vol/1e6:.1f}M",                  TEXT_DIM),
        ("MAX SUP",  "1,000M RON",                        TEXT_DIM),
        ("UTILISED", f"{util:.1f}%",                      RON_CYAN),
        ("SOURCE",   src,                                 TEXT_DIM),
    ]
    kx = 0.355
    for label, val, col in kpis:
        fig.text(kx, 0.963, label, fontsize=7,   color=TEXT_DIM,   va="center", fontweight="bold")
        fig.text(kx, 0.948, val,   fontsize=9.5, color=col,        va="center", fontweight="bold")
        kx += 0.082

    # Separator line
    fig.add_artist(
        Line2D([0.05, 0.95], [0.932, 0.932],
               transform=fig.transFigure,
               color=RON_BLUE, linewidth=0.9, alpha=0.55)
    )

    # Footer
    today_str = date.today().strftime("%Y-%m-%d")
    fig.text(
        0.5, 0.015,
        f"Vietnam Alpha Suite  |  Ronin Tokenomics  |  "
        f"Generated {today_str}  |  Data: {src}  |  Not financial advice",
        ha="center", fontsize=7.5, color=TEXT_DIM, alpha=0.65,
    )

    return fig


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    sep = "-" * 52
    print(f"\n  VIETNAM ALPHA SUITE -- Ronin Tokenomics Visualizer")
    print(f"  {sep}")

    print("  [1/3] Fetching RON market data ...")
    data = fetch_ron_data()
    print(f"        Price    : ${data['price_usd']:.3f}")
    print(f"        Supply   : {data['circulating_supply']/1e6:.2f}M RON")
    print(f"        Mkt Cap  : ${data['market_cap_usd']/1e6:.1f}M")
    print(f"        Source   : {data['source']}")

    print("  [2/3] Computing 2026 migration scenarios ...")
    sc = compute_scenarios(data)
    print(f"        Old chain 12m supply : {sc['old_supply'][-1]/1e6:.2f}M RON")
    print(f"        New L2    12m supply : {sc['new_supply'][-1]/1e6:.2f}M RON")
    print(f"        RON saved from burn  : {sc['saved_12m']/1e6:.2f}M "
          f"({sc['saved_12m']/data['circulating_supply']*100:.1f}% of circ supply)")
    print(f"        Old daily mint       : {sc['daily_mint_old']/1e3:.1f}K RON/day")
    print(f"        New daily mint       : {sc['daily_mint_new']/1e3:.1f}K RON/day")
    print(f"        Daily fee burn       : {sc['daily_burn']/1e3:.1f}K RON/day")

    print("  [3/3] Rendering chart ...")
    fig = build_chart(data, sc)
    fig.savefig(OUTPUT_FILE, dpi=180, bbox_inches="tight", facecolor=BG_DARK)
    plt.close(fig)
    print(f"        Saved -> {OUTPUT_FILE}")

    print(f"\n  Done. Open {OUTPUT_FILE} to view the dashboard.")
    print(f"  {sep}\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n  Interrupted.\n")
        sys.exit(0)
