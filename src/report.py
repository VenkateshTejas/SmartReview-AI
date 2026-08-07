"""PDF report generation for SmartReview-AI.

Turns the analysis into a polished, executive-ready document: headline metrics,
sentiment + trend charts, issues rolled up with recommended actions, a
per-product breakdown, strategic recommendations, an action plan, and a
priority response queue with ready-to-send draft replies. Charts are rendered
with matplotlib (no headless-browser dependency) and laid out with ReportLab so
it all works on Streamlit Community Cloud.
"""
import io
from datetime import datetime

import matplotlib
matplotlib.use("Agg")  # headless backend for server-side rendering
import matplotlib.pyplot as plt
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (HRFlowable, Image, KeepTogether, PageBreak,
                                Paragraph, SimpleDocTemplate, Spacer, Table,
                                TableStyle)

# --- Palette (mirrors the app's "Refined light" identity) --------------------
INK = colors.HexColor("#0F172A")
MUTED = colors.HexColor("#64748B")
ACCENT = colors.HexColor("#4F46E5")
ACCENT_SOFT = colors.HexColor("#EEF2FF")
BORDER = colors.HexColor("#E2E8F0")
CARD = colors.HexColor("#F8FAFC")
POS = colors.HexColor("#10B981")
NEG = colors.HexColor("#EF4444")
NEU = colors.HexColor("#F59E0B")
_POS, _NEG, _NEU = "#10B981", "#EF4444", "#F59E0B"

PAGE_W, PAGE_H = LETTER
MARGIN = 0.7 * inch
CONTENT_W = PAGE_W - 2 * MARGIN


# --- Text styles -------------------------------------------------------------
def _styles():
    ss = getSampleStyleSheet()
    s = {}
    s["h1"] = ParagraphStyle("h1", parent=ss["Title"], fontName="Helvetica-Bold",
                             fontSize=24, textColor=INK, leading=27, spaceAfter=2)
    s["sub"] = ParagraphStyle("sub", fontName="Helvetica", fontSize=10.5,
                              textColor=MUTED, leading=15)
    s["h2"] = ParagraphStyle("h2", fontName="Helvetica-Bold", fontSize=14,
                             textColor=INK, leading=17, spaceBefore=16,
                             spaceAfter=6)
    s["body"] = ParagraphStyle("body", fontName="Helvetica", fontSize=10,
                               textColor=INK, leading=15)
    s["muted"] = ParagraphStyle("muted", fontName="Helvetica", fontSize=8.5,
                                textColor=MUTED, leading=12)
    s["cardnum"] = ParagraphStyle("cardnum", fontName="Helvetica-Bold",
                                  fontSize=19, textColor=INK, leading=21)
    s["cardlbl"] = ParagraphStyle("cardlbl", fontName="Helvetica", fontSize=7.5,
                                  textColor=MUTED, leading=10)
    s["cardsub"] = ParagraphStyle("cardsub", fontName="Helvetica", fontSize=8,
                                  textColor=MUTED, leading=10)
    s["th"] = ParagraphStyle("th", fontName="Helvetica-Bold", fontSize=9,
                             textColor=colors.white, leading=12)
    s["td"] = ParagraphStyle("td", fontName="Helvetica", fontSize=9,
                             textColor=INK, leading=13)
    s["quote"] = ParagraphStyle("quote", fontName="Helvetica-Oblique",
                                fontSize=9, textColor=colors.HexColor("#334155"),
                                leading=13, leftIndent=6)
    s["reply"] = ParagraphStyle("reply", fontName="Helvetica", fontSize=9,
                                textColor=INK, leading=13, leftIndent=6)
    s["replylbl"] = ParagraphStyle("replylbl", fontName="Helvetica-Bold",
                                   fontSize=8, textColor=ACCENT, leading=11)
    return s


# --- matplotlib helpers ------------------------------------------------------
def _mpl_base():
    plt.rcParams.update({
        "font.size": 9, "text.color": "#334155",
        "axes.edgecolor": "#CBD5E1", "axes.labelcolor": "#64748B",
        "xtick.color": "#64748B", "ytick.color": "#64748B",
        "axes.titlecolor": "#0F172A", "svg.fonttype": "none",
    })


def _fig_to_image(fig, width):
    """Serialise a matplotlib figure to a width-fitted ReportLab Image."""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=170, bbox_inches="tight",
                transparent=True)
    plt.close(fig)
    buf.seek(0)
    img = Image(buf)
    img.drawWidth = width
    img.drawHeight = width * img.imageHeight / img.imageWidth
    return img


def _donut_chart(pos, neg, neu, width):
    _mpl_base()
    data = [(pos, "Positive", _POS), (neg, "Negative", _NEG),
            (neu, "Neutral", _NEU)]
    data = [d for d in data if d[0] > 0]
    total = pos + neg + neu or 1
    fig, ax = plt.subplots(figsize=(3.6, 3.0))
    ax.pie([d[0] for d in data], colors=[d[2] for d in data], startangle=90,
           counterclock=False,
           wedgeprops=dict(width=0.42, edgecolor="white", linewidth=2.5))
    ax.text(0, 0.12, f"{total:,}", ha="center", va="center",
            fontsize=17, fontweight="bold", color="#0F172A")
    ax.text(0, -0.16, "reviews", ha="center", va="center",
            fontsize=8.5, color="#64748B")
    ax.legend([f"{d[1]}  {d[0]/total*100:.0f}%" for d in data],
              loc="center left", bbox_to_anchor=(1.0, 0.5), frameon=False,
              fontsize=9, handlelength=1.1)
    ax.set(aspect="equal")
    return _fig_to_image(fig, width)


def _issues_chart(issue_summary, width):
    _mpl_base()
    items = list(issue_summary.items())[:8][::-1]  # ascending for barh
    labels = [k for k, _ in items]
    vals = [v for _, v in items]
    fig, ax = plt.subplots(figsize=(6.6, 0.42 * len(items) + 0.7))
    ax.barh(range(len(items)), vals, color="#818CF8", height=0.62,
            edgecolor="#4F46E5", linewidth=0.6)
    ax.set_yticks(range(len(items)))
    ax.set_yticklabels(labels, fontsize=9, color="#0F172A")
    for i, v in enumerate(vals):
        ax.text(v + max(vals) * 0.01, i, str(v), va="center", fontsize=8.5,
                color="#475569")
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.tick_params(axis="both", length=0)
    ax.set_xlabel("reviews mentioning issue", fontsize=8)
    ax.margins(x=0.08, y=0.05)
    return _fig_to_image(fig, width)


def _trend_chart(df, sentiments, date_col, width):
    """Weekly sentiment volume; returns None if dates aren't usable."""
    try:
        t = df[[date_col]].copy()
        t["sentiment"] = sentiments
        t[date_col] = pd.to_datetime(t[date_col], errors="coerce")
        t = t.dropna(subset=[date_col])
        if t.empty:
            return None
        daily = (t.groupby([pd.Grouper(key=date_col, freq="W"), "sentiment"])
                 .size().reset_index(name="count"))
        if daily.empty:
            return None
        _mpl_base()
        fig, ax = plt.subplots(figsize=(6.6, 2.4))
        for name, col in (("Positive", _POS), ("Negative", _NEG),
                          ("Neutral", _NEU)):
            sub = daily[daily["sentiment"] == name]
            if not sub.empty:
                ax.plot(sub[date_col], sub["count"], marker="o", markersize=3.5,
                        linewidth=2, color=col, label=name)
        ax.spines[["top", "right"]].set_visible(False)
        ax.tick_params(axis="both", length=0, labelsize=8)
        ax.grid(axis="y", color="#EEF2F7", linewidth=1)
        ax.set_ylabel("reviews / week", fontsize=8)
        ax.legend(frameon=False, fontsize=8, ncol=3, loc="upper center",
                  bbox_to_anchor=(0.5, 1.18))
        fig.autofmt_xdate(rotation=0, ha="center")
        return _fig_to_image(fig, width)
    except Exception:
        return None


# --- Flowable builders -------------------------------------------------------
def _rule(color=BORDER, w=0.8, space=6):
    return HRFlowable(width="100%", thickness=w, color=color,
                      spaceBefore=space, spaceAfter=space)


def _kpi_cards(cards, s):
    """A responsive row of stat 'cards' rendered as a bordered table."""
    cell_data = []
    for label, value, sub, accent in cards:
        inner = [
            [Paragraph(label.upper(), s["cardlbl"])],
            [Paragraph(str(value), ParagraphStyle(
                "cn", parent=s["cardnum"],
                textColor=accent or INK))],
            [Paragraph(sub, s["cardsub"])],
        ]
        t = Table(inner, colWidths=[CONTENT_W / len(cards) - 8])
        t.setStyle(TableStyle([
            ("TOPPADDING", (0, 0), (-1, -1), 1),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ]))
        cell_data.append(t)
    outer = Table([cell_data], colWidths=[CONTENT_W / len(cards)] * len(cards))
    outer.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), CARD),
        ("BOX", (0, 0), (-1, -1), 0.8, BORDER),
        ("LINEAFTER", (0, 0), (-2, -1), 0.8, BORDER),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
    ]))
    return outer


def _table(header, rows, col_widths, s, align_right=None):
    align_right = align_right or []
    data = [[Paragraph(h, s["th"]) for h in header]]
    for r in rows:
        data.append([c if isinstance(c, Paragraph)
                     else Paragraph(str(c), s["td"]) for c in r])
    t = Table(data, colWidths=col_widths, repeatRows=1)
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), ACCENT),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEBELOW", (0, 0), (-1, -2), 0.5, BORDER),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, CARD]),
        ("BOX", (0, 0), (-1, -1), 0.8, BORDER),
    ]
    for c in align_right:
        style.append(("ALIGN", (c, 1), (c, -1), "RIGHT"))
    t.setStyle(TableStyle(style))
    return t


def _reply_card(rank, score, sentiment, meta, review, reply, s):
    scolor = {"Positive": _POS, "Negative": _NEG, "Neutral": _NEU}.get(
        sentiment, "#64748B")
    head = Table([[
        Paragraph(f'<font color="#4F46E5"><b>#{rank}</b></font> &nbsp; '
                  f'Priority {score}/100 &nbsp;·&nbsp; '
                  f'<font color="{scolor}"><b>{sentiment}</b></font>',
                  s["td"]),
        Paragraph(meta, ParagraphStyle("m", parent=s["muted"], alignment=2)),
    ]], colWidths=[CONTENT_W * 0.55 - 20, CONTENT_W * 0.45 - 20])
    head.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0),
                              ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                              ("TOPPADDING", (0, 0), (-1, -1), 0),
                              ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                              ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
    inner = [
        [head],
        [Paragraph(f"&ldquo;{review}&rdquo;", s["quote"])],
        [Paragraph("SUGGESTED REPLY", s["replylbl"])],
        [Paragraph(reply, s["reply"])],
    ]
    box = Table(inner, colWidths=[CONTENT_W - 20])
    box.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.white),
        ("BOX", (0, 0), (-1, -1), 0.8, BORDER),
        ("LINEBELOW", (0, 0), (0, 0), 0.6, BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("BACKGROUND", (0, 2), (0, 3), ACCENT_SOFT),
    ]))
    return KeepTogether([box, Spacer(1, 8)])


# --- Page furniture ----------------------------------------------------------
def _page_decoration(canvas, doc):
    canvas.saveState()
    # header band accent
    canvas.setFillColor(ACCENT)
    canvas.rect(0, PAGE_H - 6, PAGE_W, 6, stroke=0, fill=1)
    # footer
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(MUTED)
    canvas.drawString(MARGIN, 0.42 * inch,
                      "SmartReview-AI · Customer Review Intelligence")
    canvas.drawRightString(PAGE_W - MARGIN, 0.42 * inch,
                           f"Page {doc.page}")
    canvas.setStrokeColor(BORDER)
    canvas.setLineWidth(0.5)
    canvas.line(MARGIN, 0.58 * inch, PAGE_W - MARGIN, 0.58 * inch)
    canvas.restoreState()


def _clip(text, n):
    text = " ".join(str(text).split())
    return text if len(text) <= n else text[:n - 1].rstrip() + "…"


# --- Main entry point --------------------------------------------------------
def build_pdf(*, df, analysis_results, insights, priority_reviews, word_freq,
              text_col, rating_col, backend, draft_response, action_for_issue,
              product_col=None, date_col=None, max_replies=6):
    """Build the executive PDF and return it as bytes."""
    s = _styles()
    total = analysis_results["total_reviews"] or 1
    pos = analysis_results["positive_count"]
    neg = analysis_results["negative_count"]
    neu = analysis_results["neutral_count"]
    pos_pct, neg_pct = pos / total * 100, neg / total * 100
    net = pos_pct - neg_pct
    urgent = len(analysis_results["urgent_indices"])
    resp_needed = len([x for x in analysis_results["priority_scores"] if x > 50])
    issue_summary = analysis_results.get("issue_summary", {})
    sentiments = analysis_results["sentiments"]
    avg_rating = None
    if rating_col and rating_col in df.columns \
            and pd.api.types.is_numeric_dtype(df[rating_col]):
        avg_rating = df[rating_col].mean()

    story = []

    # ---- Title block --------------------------------------------------------
    story.append(Paragraph("Customer Review Intelligence Report", s["h1"]))
    story.append(Paragraph(
        f"Generated {datetime.now():%B %d, %Y · %H:%M} &nbsp;·&nbsp; "
        f"{total:,} reviews analysed &nbsp;·&nbsp; "
        f"Sentiment engine: {backend.upper()}", s["sub"]))
    story.append(Spacer(1, 4))
    story.append(_rule(ACCENT, 1.4, space=8))

    # ---- Executive summary --------------------------------------------------
    top_issue, top_issue_ct = (next(iter(issue_summary.items()))
                               if issue_summary else (None, 0))
    health = ("healthy" if net >= 25 else
              "mixed" if net >= 0 else "under pressure")
    narrative = (
        f"Across <b>{total:,}</b> reviews, customer sentiment is "
        f"<b>{health}</b>, with a net sentiment of <b>{net:+.0f}</b> "
        f"({pos_pct:.0f}% positive vs. {neg_pct:.0f}% negative). ")
    if urgent:
        narrative += (f"<b>{urgent}</b> reviews are flagged urgent and "
                      f"<b>{resp_needed}</b> warrant a response. ")
    if top_issue:
        narrative += (f"The most common issue is <b>{top_issue}</b>, cited in "
                      f"{top_issue_ct} reviews "
                      f"({top_issue_ct / total * 100:.0f}%).")
    story.append(Paragraph("Executive summary", s["h2"]))
    story.append(Paragraph(narrative, s["body"]))
    story.append(Spacer(1, 10))

    cards = [
        ("Total reviews", f"{total:,}", "in this analysis", INK),
        ("Net sentiment", f"{net:+.0f}", "positive − negative %",
         POS if net >= 0 else NEG),
        ("Positive", f"{pos_pct:.0f}%", f"{pos:,} reviews", POS),
        ("Negative", f"{neg_pct:.0f}%", f"{neg:,} reviews", NEG),
    ]
    if avg_rating is not None:
        cards.append(("Avg. rating", f"{avg_rating:.2f}", "out of 5", ACCENT))
    else:
        cards.append(("Urgent", f"{urgent:,}", "need response today", NEU))
    story.append(_kpi_cards(cards, s))

    # ---- Sentiment + trend --------------------------------------------------
    story.append(Paragraph("Sentiment overview", s["h2"]))
    story.append(_donut_chart(pos, neg, neu, CONTENT_W * 0.62))

    trend = _trend_chart(df, sentiments, date_col, CONTENT_W) if date_col \
        else None
    if trend is not None:
        story.append(KeepTogether([
            Paragraph("Sentiment trend over time", s["h2"]),
            trend,
            Paragraph(
                "Weekly review volume by sentiment — watch for rising "
                "negatives before they show up in churn.", s["muted"]),
        ]))

    # ---- Issues + recommended actions ---------------------------------------
    if issue_summary:
        story.append(KeepTogether([
            Paragraph("Top issues &amp; recommended actions", s["h2"]),
            Paragraph(
                "Recurring problems rolled up across all reviews, most "
                "frequent first, each with a recommended next step.",
                s["muted"]),
            Spacer(1, 6),
            _issues_chart(issue_summary, CONTENT_W),
        ]))
        story.append(Spacer(1, 8))
        rows = []
        for issue, ct in list(issue_summary.items())[:8]:
            rows.append([
                Paragraph(f"<b>{issue}</b>", s["td"]),
                f"{ct}",
                f"{ct / total * 100:.0f}%",
                Paragraph(action_for_issue(issue), s["td"]),
            ])
        story.append(_table(
            ["Issue", "Count", "Share", "Recommended action"], rows,
            [1.5 * inch, 0.75 * inch, 0.7 * inch, CONTENT_W - 2.95 * inch], s,
            align_right=[1, 2]))

    # ---- Per-product breakdown (segmentation) -------------------------------
    prod_rows = _product_rows(df, sentiments, analysis_results, product_col,
                              rating_col, s)
    if prod_rows:
        story.append(KeepTogether([
            Paragraph("Sentiment by product", s["h2"]),
            Paragraph(
                "Where negative sentiment concentrates — the products to "
                "prioritise (sorted by negative share).", s["muted"]),
            Spacer(1, 6),
            _table(
                ["Product", "Reviews", "Negative", "Avg. rating", "Top issue"],
                prod_rows,
                [CONTENT_W - 4.15 * inch, 0.8 * inch, 0.9 * inch, 0.95 * inch,
                 1.5 * inch], s, align_right=[1, 2, 3]),
        ]))

    # ---- Most mentioned words -----------------------------------------------
    if word_freq:
        words = list(word_freq.items())[:15]
        chips = ",  ".join(f"{w} ({c})" for w, c in words)
        story.append(Paragraph("Most mentioned words", s["h2"]))
        story.append(Paragraph(chips, s["body"]))

    # ---- Recommendations + action plan --------------------------------------
    if insights and insights.get("recommendations"):
        story.append(Paragraph("Strategic recommendations", s["h2"]))
        for rec in insights["recommendations"]:
            story.append(Paragraph(f"•&nbsp; {rec}", s["body"]))
            story.append(Spacer(1, 2))

    story.append(Paragraph("Suggested action plan", s["h2"]))
    plan = Table([[
        _plan_cell("TODAY", ["Respond to urgent reviews",
                             "Handle safety &amp; refund requests",
                             "Reply to 1-star reviews"], s),
        _plan_cell("THIS WEEK", ["Address the top quality issues",
                                 "Review shipping performance",
                                 "Update product descriptions"], s),
    ]], colWidths=[CONTENT_W / 2] * 2)
    plan.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                              ("LEFTPADDING", (0, 0), (0, 0), 0),
                              ("RIGHTPADDING", (0, 0), (0, 0), 10),
                              ("LEFTPADDING", (1, 0), (1, 0), 10)]))
    story.append(plan)

    # ---- Priority response queue --------------------------------------------
    if priority_reviews is not None and not priority_reviews.empty:
        story.append(PageBreak())
        story.append(Paragraph("Priority response queue", s["h2"]))
        story.append(Paragraph(
            f"The {min(max_replies, len(priority_reviews))} highest-priority "
            "reviews, each with a ready-to-send draft reply to edit and send.",
            s["muted"]))
        story.append(Spacer(1, 8))
        for rank, (_, row) in enumerate(
                priority_reviews.head(max_replies).iterrows(), start=1):
            meta_bits = []
            if product_col and product_col in row and pd.notna(row[product_col]):
                meta_bits.append(str(row[product_col]))
            if rating_col and rating_col in row and pd.notna(row[rating_col]):
                try:
                    meta_bits.append("★" * int(row[rating_col]))
                except (ValueError, TypeError):
                    pass
            if str(row.get("issues", "")).strip():
                meta_bits.append(str(row["issues"]))
            reply = draft_response(
                sentiment=row["sentiment"],
                issues=[i.strip() for i in str(row.get("issues", "")).split(",")],
                rating=row.get(rating_col) if rating_col else None,
                product=row.get(product_col) if product_col else None)
            story.append(_reply_card(
                rank, int(row["priority_score"]), row["sentiment"],
                " · ".join(meta_bits), _clip(row[text_col], 260),
                _clip(reply, 500), s))

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=LETTER, leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=0.7 * inch, bottomMargin=0.75 * inch,
        title="SmartReview-AI — Customer Review Intelligence Report",
        author="SmartReview-AI")
    doc.build(story, onFirstPage=_page_decoration, onLaterPages=_page_decoration)
    buf.seek(0)
    return buf.getvalue()


def _plan_cell(title, items, s):
    inner = [[Paragraph(title, s["replylbl"])]]
    for it in items:
        inner.append([Paragraph(f"•&nbsp; {it}", s["td"])])
    t = Table(inner, colWidths=[CONTENT_W / 2 - 10])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), CARD),
        ("BOX", (0, 0), (-1, -1), 0.8, BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
    ]))
    return t


def _product_rows(df, sentiments, analysis_results, product_col, rating_col, s):
    """Per-product roll-up: volume, negative share, avg rating, top issue."""
    if not product_col or product_col not in df.columns:
        return None
    work = pd.DataFrame({
        "product": df[product_col].astype(str).values,
        "sentiment": sentiments,
        "issues": [", ".join(i) if i else "" for i in
                   analysis_results["issues_found"]],
    })
    if rating_col and rating_col in df.columns \
            and pd.api.types.is_numeric_dtype(df[rating_col]):
        work["rating"] = df[rating_col].values
    rows = []
    for prod, g in work.groupby("product"):
        n = len(g)
        neg_share = (g["sentiment"] == "Negative").mean() * 100
        avg = f"{g['rating'].mean():.2f}" if "rating" in g else "—"
        issue_ct = {}
        for cell in g["issues"]:
            for iss in [x.strip() for x in cell.split(",") if x.strip()]:
                issue_ct[iss] = issue_ct.get(iss, 0) + 1
        top_issue = max(issue_ct, key=issue_ct.get) if issue_ct else "—"
        rows.append((prod, n, neg_share, avg, top_issue))
    rows.sort(key=lambda r: r[2], reverse=True)  # worst negatives first
    out = []
    for prod, n, neg_share, avg, top_issue in rows[:8]:
        out.append([
            Paragraph(f"<b>{prod}</b>", s["td"]),
            f"{n}",
            Paragraph(f'<font color="{_NEG if neg_share >= 25 else "#475569"}">'
                      f'{neg_share:.0f}%</font>', s["td"]),
            avg,
            Paragraph(top_issue, s["td"]),
        ])
    return out
