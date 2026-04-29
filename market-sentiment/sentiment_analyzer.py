#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Vietnam Alpha Suite -- VN-Index Market Sentiment Analyzer
----------------------------------------------------------
Multi-source scraper with Vietnamese NLP scoring and
Bloomberg-style terminal output.

Requirements:
    pip install requests beautifulsoup4 rich
"""

from __future__ import annotations

import sys
import time
import unicodedata
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

import requests
from bs4 import BeautifulSoup
from rich import box
from rich.align import Align
from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
)
from rich.table import Table
from rich.text import Text

# ── Configuration ─────────────────────────────────────────────────────────────

TIMEOUT        = 12     # HTTP timeout per request (seconds)
MAX_HEADLINES  = 25     # cap per source
REQUEST_DELAY  = 0.9    # politeness gap between requests (seconds)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept":          "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection":      "keep-alive",
}

# ── Vietnamese Sentiment Lexicon ───────────────────────────────────────────────
# Longer compound phrases are matched first (greedy) to prevent double-counting.
# Weights: 3 = strong signal  |  2 = moderate  |  1 = weak hint

POSITIVE_KEYWORDS: dict[str, int] = {
    # -- Strong (3) --
    "but pha":             3,   # breakthrough (ASCII fallback key, matched on NFC text)
    "but pha":             3,
    "bứt phá":             3,
    "đột phá":             3,
    "kỷ lục mới":          3,
    "kỷ lục":              3,
    "tăng vọt":            3,
    "tăng mạnh":           3,
    "bùng nổ":             3,
    "đỉnh cao nhất":       3,
    "đỉnh cao":            3,
    "hưng phấn":           3,
    # -- Moderate (2) --
    "tăng trưởng mạnh":    2,
    "tăng trưởng":         2,
    "hồi phục mạnh":       2,
    "hồi phục":            2,
    "phục hồi":            2,
    "khởi sắc":            2,
    "tích cực":            2,
    "sinh lời":            2,
    "vượt trội":           2,
    "vượt kỳ vọng":        2,
    "dòng tiền đổ vào":    2,
    "thị trường xanh":     2,
    "tăng điểm":           2,
    "lợi nhuận tăng":      2,
    "lợi nhuận":           2,
    "cơ hội":              2,
    "tăng":                2,
    "vượt":                2,
    # -- Weak (1) --
    "ổn định":             1,
    "khả quan":            1,
    "triển vọng":          1,
    "tốt":                 1,
    "mạnh":                1,
    "cao":                 1,
    "lên":                 1,
    "xanh":                1,
    "tiến":                1,
}

NEGATIVE_KEYWORDS: dict[str, int] = {
    # -- Strong (3) --
    "lao dốc":             3,
    "sụt giảm mạnh":       3,
    "sụt giảm":            3,
    "thua lỗ nặng":        3,
    "thua lỗ":             3,
    "giảm sâu":            3,
    "bán tháo":            3,
    "nguy cơ vỡ nợ":       3,
    "nguy cơ":             3,
    "suy thoái":           3,
    "đổ vỡ":               3,
    # -- Moderate (2) --
    "giảm mạnh":           2,
    "rủi ro lớn":          2,
    "rủi ro":              2,
    "áp lực bán":          2,
    "áp lực":              2,
    "lo ngại":             2,
    "tiêu cực":            2,
    "điều chỉnh mạnh":     2,
    "điều chỉnh":          2,
    "thị trường đỏ":       2,
    "mất điểm":            2,
    "giảm điểm":           2,
    "bất ổn":              2,
    "cảnh báo":            2,
    "giảm":                2,
    "sụt":                 2,
    "xuống":               2,
    "mất":                 2,
    # -- Weak (1) --
    "khó khăn":            1,
    "thấp":                1,
    "thua":                1,
    "đỏ":                  1,
    "chậm lại":            1,
}

# ── News Sources ───────────────────────────────────────────────────────────────

SOURCES: list[dict] = [
    {
        "name":  "CafeF",
        "emoji": "CF",
        "url":   "https://cafef.vn/thi-truong-chung-khoan.chn",
        "selectors": [
            "h3.title a",
            ".box-category-item h3 a",
            ".box-category-middle-content h2 a",
            "h2.title a",
            ".sapo a",
            "article h2 a",
            "h3 a",
        ],
    },
    {
        "name":  "Vietstock",
        "emoji": "VS",
        "url":   "https://vietstock.vn/chung-khoan/",
        "selectors": [
            ".article-title a",
            ".news-list .title a",
            "h3.title a",
            ".item-news h3 a",
            ".newstitle a",
            ".list-news h3 a",
            "h2 a",
            "h3 a",
        ],
    },
    {
        "name":  "VnExpress",
        "emoji": "VE",
        "url":   "https://vnexpress.net/kinh-doanh/chung-khoan",
        "selectors": [
            "h3.title-news a",
            ".title-news a",
            ".item-news h3 a",
            "h2.title-news a",
            ".description a",
            "h3 a",
        ],
    },
]

# ── Offline mock data (used ONLY when ALL live sources fail) ──────────────────

MOCK_HEADLINES: list[tuple[str, str]] = [
    ("CafeF",     "VN-Index tăng mạnh 18 điểm, bứt phá vùng kháng cự 1,260"),
    ("CafeF",     "Cổ phiếu bluechip khởi sắc, thị trường hồi phục mạnh sau chuỗi giảm"),
    ("CafeF",     "Khối ngoại bán tháo mạnh, áp lực lên nhóm cổ phiếu vốn hóa lớn"),
    ("Vietstock", "VN-Index điều chỉnh nhẹ trước áp lực chốt lời cuối phiên"),
    ("Vietstock", "Lợi nhuận quý I của VNM tăng trưởng 12%, vượt kỳ vọng thị trường"),
    ("Vietstock", "Rủi ro lạm phát toàn cầu gây cảnh báo cho nhà đầu tư Việt Nam"),
    ("VnExpress", "VN-Index tăng điểm nhờ dòng tiền đổ vào cổ phiếu bất động sản"),
    ("VnExpress", "Cảnh báo: nhiều cổ phiếu mid-cap tiêu cực, lo ngại rủi ro thanh khoản"),
    ("VnExpress", "Kỷ lục mới: giá trị giao dịch toàn thị trường đạt 28,000 tỷ đồng"),
    ("CafeF",     "VIC tăng vọt 4.5%, dẫn dắt nhóm cổ phiếu bất động sản bùng nổ"),
    ("Vietstock", "TCB và VCB sụt giảm mạnh do lo ngại nợ xấu tăng cao"),
    ("VnExpress", "Triển vọng thị trường 2026: tích cực nhờ dòng vốn FDI tăng trưởng"),
]

# ── Data Model ─────────────────────────────────────────────────────────────────

@dataclass
class Headline:
    source:      str
    text:        str
    pos_score:   int = 0
    neg_score:   int = 0
    matched_pos: list[str] = field(default_factory=list)
    matched_neg: list[str] = field(default_factory=list)
    is_mock:     bool = False

    @property
    def net_score(self) -> int:
        return self.pos_score - self.neg_score

    @property
    def sentiment(self) -> str:
        n = self.net_score
        if   n >=  3: return "BULLISH"
        elif n >=  1: return "WEAK BULL"
        elif n <= -3: return "BEARISH"
        elif n <= -1: return "WEAK BEAR"
        return "NEUTRAL"

# ── NLP Engine ────────────────────────────────────────────────────────────────

def normalize(text: str) -> str:
    """Unicode-NFC normalise and lowercase for consistent Vietnamese matching."""
    return unicodedata.normalize("NFC", text).lower().strip()


def score_headline(text: str) -> tuple[int, int, list[str], list[str]]:
    """
    Score a Vietnamese headline against the weighted sentiment lexicon.

    Longer compound phrases are consumed first so sub-words inside a phrase
    (e.g. 'tăng' inside 'tăng mạnh') are not double-counted.
    Returns (pos_score, neg_score, matched_pos_keywords, matched_neg_keywords).
    """
    pos_score, neg_score = 0, 0
    matched_pos: list[str] = []
    matched_neg: list[str] = []

    working = normalize(text)
    for kw, weight in sorted(POSITIVE_KEYWORDS.items(), key=lambda x: -len(x[0])):
        if kw in working:
            pos_score += weight
            matched_pos.append(kw)
            working = working.replace(kw, " " * len(kw), 1)

    working = normalize(text)
    for kw, weight in sorted(NEGATIVE_KEYWORDS.items(), key=lambda x: -len(x[0])):
        if kw in working:
            neg_score += weight
            matched_neg.append(kw)
            working = working.replace(kw, " " * len(kw), 1)

    return pos_score, neg_score, matched_pos, matched_neg

# ── Scraping ───────────────────────────────────────────────────────────────────

def fetch_page(url: str) -> Optional[BeautifulSoup]:
    """Fetch URL and return BeautifulSoup, or None on any network/HTTP failure."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        resp.raise_for_status()
        resp.encoding = resp.apparent_encoding or "utf-8"
        return BeautifulSoup(resp.text, "html.parser")
    except (
        requests.exceptions.Timeout,
        requests.exceptions.ConnectionError,
        requests.exceptions.HTTPError,
        requests.exceptions.RequestException,
    ):
        return None
    except Exception:
        return None


def scrape_source(src: dict) -> tuple[list[str], str]:
    """
    Try each CSS selector in priority order; stop once we find 5+ results.
    Falls back to a broad <h2>/<h3> scan if all selectors miss.
    Returns (raw_text_list, human_readable_status).
    """
    soup = fetch_page(src["url"])
    if soup is None:
        return [], "OFFLINE"

    headlines: list[str] = []
    for selector in src["selectors"]:
        for el in soup.select(selector):
            raw = " ".join(el.get_text(separator=" ", strip=True).split())
            if len(raw) >= 15 and raw not in headlines:
                headlines.append(raw)
        if len(headlines) >= 5:
            break

    if not headlines:
        for tag in soup.find_all(["h2", "h3"], limit=40):
            raw = " ".join(tag.get_text(separator=" ", strip=True).split())
            if len(raw) >= 15 and raw not in headlines:
                headlines.append(raw)

    headlines = headlines[:MAX_HEADLINES]
    status = f"{len(headlines)} headlines" if headlines else "NO RESULTS"
    return headlines, status

# ── Analytics ─────────────────────────────────────────────────────────────────

def calculate_alpha_confidence(headlines: list[Headline]) -> dict:
    """
    Alpha Confidence Score = (total positive weight / total weight) * 100.
    Defaults to 50.0 when no keywords were matched (pure neutral corpus).
    """
    if not headlines:
        return {"score": 50.0, "signal": "NEUTRAL",
                "bullish": 0, "bearish": 0, "neutral": 0, "total": 0,
                "total_pos": 0, "total_neg": 0}

    total_pos = sum(h.pos_score for h in headlines)
    total_neg = sum(h.neg_score for h in headlines)
    total_w   = total_pos + total_neg
    score     = (total_pos / total_w * 100) if total_w else 50.0

    bullish = sum(1 for h in headlines if "BULL" in h.sentiment)
    bearish = sum(1 for h in headlines if "BEAR" in h.sentiment)
    neutral = sum(1 for h in headlines if h.sentiment == "NEUTRAL")

    if   score >= 72: signal = "STRONG BUY"
    elif score >= 58: signal = "CAUTIOUSLY BULLISH"
    elif score >= 42: signal = "NEUTRAL -- HOLD"
    elif score >= 28: signal = "CAUTIOUSLY BEARISH"
    else:             signal = "STRONG SELL"

    return {"score": score, "signal": signal,
            "bullish": bullish, "bearish": bearish,
            "neutral": neutral, "total": len(headlines),
            "total_pos": total_pos, "total_neg": total_neg}


def top_keywords(headlines: list[Headline], kind: str = "pos", n: int = 4) -> list[str]:
    c: Counter = Counter()
    for h in headlines:
        c.update(h.matched_pos if kind == "pos" else h.matched_neg)
    return [kw for kw, _ in c.most_common(n)]

# ── Terminal Rendering ─────────────────────────────────────────────────────────

console = Console()

_SENT_STYLES: dict[str, tuple[str, str]] = {
    "BULLISH":   ("bright_green", "[bold bright_green] BULLISH  [/bold bright_green]"),
    "WEAK BULL": ("green",        "[bold green] WEAK BULL[/bold green]"),
    "NEUTRAL":   ("yellow",       "[bold yellow] NEUTRAL  [/bold yellow]"),
    "WEAK BEAR": ("red",          "[bold red] WEAK BEAR[/bold red]"),
    "BEARISH":   ("bright_red",   "[bold bright_red] BEARISH  [/bold bright_red]"),
}


def _tier_color(score: float) -> str:
    if   score >= 72: return "bright_green"
    elif score >= 58: return "green"
    elif score >= 42: return "yellow"
    elif score >= 28: return "red"
    else:             return "bright_red"


def render_header() -> None:
    console.print()
    banner = Text()
    banner.append("  VIETNAM ALPHA SUITE  ", style="bold black on bright_white")
    banner.append("  VN-INDEX SENTIMENT ANALYZER  ", style="bold white on red")
    console.print(Align.center(banner))
    ts = datetime.now().strftime("%Y-%m-%d  %H:%M:%S  ICT")
    console.print(Align.center(
        Text(f"{ts}  |  Vietnamese NLP Engine v2.0", style="dim")
    ))
    console.print()


def make_bar(score: float, width: int = 34) -> str:
    filled = max(0, min(width, int(score / 100 * width)))
    color  = _tier_color(score)
    bar    = f"[bold {color}]{'█' * filled}[/bold {color}]"
    bar   += f"[dim]{'░' * (width - filled)}[/dim]"
    bar   += f"  [bold {color}]{score:5.1f}%[/bold {color}]"
    return bar


def render_headlines_table(headlines: list[Headline]) -> None:
    if not headlines:
        console.print("[dim italic]  No headlines collected.[/dim italic]\n")
        return

    table = Table(
        title="[bold cyan]VN-INDEX MARKET HEADLINES[/bold cyan]",
        title_justify="left",
        box=box.SIMPLE_HEAVY,
        header_style="bold cyan",
        border_style="bright_black",
        show_lines=False,
        expand=True,
        pad_edge=True,
        padding=(0, 1),
    )
    table.add_column("#",      style="dim",        width=4,  justify="right", no_wrap=True)
    table.add_column("SOURCE", style="bold white", width=12, no_wrap=True)
    table.add_column("HEADLINE",                   ratio=1)
    table.add_column("SIGNAL",                     width=12, justify="center", no_wrap=True)
    table.add_column("SCORE",                      width=7,  justify="right",  no_wrap=True)

    for i, h in enumerate(headlines, 1):
        color, badge = _SENT_STYLES.get(h.sentiment, ("white", h.sentiment))
        text         = (h.text[:110] + "...") if len(h.text) > 110 else h.text
        sign         = "+" if h.net_score > 0 else ""
        score_markup = f"[bold {color}]{sign}{h.net_score}[/bold {color}]"
        mock_tag     = " [dim](mock)[/dim]" if h.is_mock else ""

        table.add_row(
            str(i),
            f"[bold]{h.source}[/bold]{mock_tag}",
            f"[{color}]{text}[/{color}]" if h.sentiment != "NEUTRAL" else text,
            badge,
            score_markup,
        )

    console.print(table)


def render_summary(stats: dict, headlines: list[Headline]) -> None:
    score  = stats["score"]
    color  = _tier_color(score)
    signal = stats["signal"]

    top_pos = top_keywords(headlines, "pos")
    top_neg = top_keywords(headlines, "neg")
    pos_str = "  ".join(
        f"[bright_green]+{k}[/bright_green]" for k in top_pos
    ) or "[dim]none detected[/dim]"
    neg_str = "  ".join(
        f"[bright_red]-{k}[/bright_red]" for k in top_neg
    ) or "[dim]none detected[/dim]"

    body = "\n".join([
        "",
        f"  [bold {color}]ALPHA CONFIDENCE SCORE[/bold {color}]",
        "",
        f"  [dim]Score [/dim] {make_bar(score)}",
        f"  [dim]Signal[/dim] [bold {color}]{signal}[/bold {color}]",
        "",
        (
            f"  [dim]Bullish[/dim] [bright_green]{stats['bullish']:>3}[/bright_green]"
            f"   [dim]Bearish[/dim] [bright_red]{stats['bearish']:>3}[/bright_red]"
            f"   [dim]Neutral[/dim] [yellow]{stats['neutral']:>3}[/yellow]"
            f"   [dim]Total[/dim] [white]{stats['total']:>3}[/white]"
        ),
        (
            f"  [dim]Pos weight[/dim] [bright_green]{stats['total_pos']}[/bright_green]"
            f"   [dim]Neg weight[/dim] [bright_red]{stats['total_neg']}[/bright_red]"
        ),
        "",
        f"  [dim]Top positive signals:[/dim]  {pos_str}",
        f"  [dim]Top negative signals:[/dim]  {neg_str}",
        "",
    ])

    console.print(
        Panel(
            body,
            title=f"[bold {color}]  ALPHA CONFIDENCE REPORT  [/bold {color}]",
            border_style=color,
            padding=(0, 0),
        )
    )
    console.print()

# ── Orchestrator ───────────────────────────────────────────────────────────────

def run() -> None:
    render_header()

    all_headlines: list[Headline] = []
    source_log: list[tuple[str, str, bool]] = []

    with Progress(
        SpinnerColumn(spinner_name="dots2", style="bold cyan"),
        TextColumn("[bold white]{task.description:<36}"),
        BarColumn(bar_width=30, style="cyan", complete_style="bright_cyan"),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        console=console,
        transient=False,
    ) as progress:

        for src in SOURCES:
            task = progress.add_task(
                f"  Scraping {src['name']}...", total=100
            )
            progress.update(task, advance=15)

            raw_texts, status = scrape_source(src)
            ok = bool(raw_texts)

            progress.update(task, advance=50)
            time.sleep(REQUEST_DELAY)

            for text in raw_texts:
                pos, neg, mpos, mneg = score_headline(text)
                all_headlines.append(
                    Headline(
                        source=src["name"], text=text,
                        pos_score=pos, neg_score=neg,
                        matched_pos=mpos, matched_neg=mneg,
                    )
                )

            status_markup = (
                f"[bright_green]{status}[/bright_green]"
                if ok else f"[bright_red]{status}[/bright_red]"
            )
            tick = "OK " if ok else "ERR"
            progress.update(
                task,
                completed=100,
                description=f"  [{tick}] {src['name']:<12} {status}",
            )
            source_log.append((src["name"], status, ok))

    console.print()
    for name, status, ok in source_log:
        icon  = "[bright_green]v[/bright_green]" if ok else "[bright_red]x[/bright_red]"
        note  = (
            f"[bright_green]{status}[/bright_green]"
            if ok else f"[bright_red]{status}[/bright_red]"
        )
        console.print(f"  {icon}  [bold]{name:<12}[/bold]  {note}")
    console.print()

    # Activate offline mock mode only if every live source returned nothing
    if not all_headlines:
        console.print(
            Panel(
                "[yellow]All live sources are unreachable.[/yellow]\n"
                "[dim]Running on built-in mock data for demonstration.\n"
                "Check your internet connection or review source URLs.[/dim]",
                title="[yellow]  OFFLINE MODE  [/yellow]",
                border_style="yellow",
                padding=(0, 2),
            )
        )
        console.print()
        for src_name, text in MOCK_HEADLINES:
            pos, neg, mpos, mneg = score_headline(text)
            all_headlines.append(
                Headline(
                    source=src_name, text=text,
                    pos_score=pos, neg_score=neg,
                    matched_pos=mpos, matched_neg=mneg,
                    is_mock=True,
                )
            )

    render_headlines_table(all_headlines)
    console.print()
    render_summary(calculate_alpha_confidence(all_headlines), all_headlines)


if __name__ == "__main__":
    try:
        run()
    except KeyboardInterrupt:
        console.print("\n[dim]  Interrupted.[/dim]\n")
        sys.exit(0)
