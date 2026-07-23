import io
import os
from datetime import datetime

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

from analyzer import ReviewAnalyzer

st.set_page_config(page_title="SmartReview-AI", page_icon="🤖", layout="wide")

# --- Config ------------------------------------------------------------------
SAMPLE_CSV = os.path.join(os.path.dirname(__file__), "..", "data", "sample",
                          "sample_reviews.csv")
MAX_ROWS = 5000  # cap analysed rows so the hosted demo stays snappy

# Dark-tuned semantic palette (lighter shades read better on a dark canvas).
SENTIMENT_COLORS = {"Positive": "#34D399", "Negative": "#F87171",
                    "Neutral": "#FBBF24"}
ACCENT = "#6366F1"
MUTED = "#94A3B8"

analyzer = ReviewAnalyzer()

# --- Styling: "Refined dark" -------------------------------------------------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@500;600&display=swap');

    :root {
        --surface:#141A24; --surface-2:#0D121B; --border:rgba(255,255,255,.08);
        --muted:#94A3B8; --accent:#6366F1; --text:#E5E7EB;
    }
    html, body, .stApp, [data-testid="stAppViewContainer"],
    [data-testid="stSidebar"] { font-family:'Inter', sans-serif; }

    /* ambient depth: subtle indigo + cyan glows on the dark canvas */
    .stApp {
        background-image:
            radial-gradient(900px 520px at 12% -8%, rgba(99,102,241,.14), transparent 60%),
            radial-gradient(760px 520px at 100% -6%, rgba(34,211,238,.08), transparent 55%);
        background-attachment:fixed;
    }

    @keyframes fadeUp { from{opacity:0;transform:translateY(10px);} to{opacity:1;transform:none;} }
    @keyframes shimmer { to { background-position:200% center; } }
    @keyframes pulse { 0%,100%{box-shadow:0 0 0 0 rgba(52,211,153,.45);} 50%{box-shadow:0 0 0 7px rgba(52,211,153,0);} }
    @keyframes grow { from{transform:scaleY(0);} to{transform:scaleY(1);} }

    /* strip default Streamlit chrome for a cleaner product surface */
    [data-testid="stHeader"] { background:transparent; }
    [data-testid="stToolbar"], [data-testid="stDecoration"],
    #MainMenu, footer { display:none !important; }

    .block-container { padding-top:2rem; padding-bottom:4rem; max-width:1200px; }

    /* hero */
    .hero { margin:0 0 1.75rem; animation:fadeUp .5s ease both; }
    .hero-badge {
        display:inline-flex; align-items:center; gap:.5rem; font-size:.78rem;
        font-weight:500; color:var(--muted); border:1px solid var(--border);
        padding:.3rem .75rem; border-radius:999px; margin-bottom:1.1rem;
        letter-spacing:.02em; background:rgba(255,255,255,.02);
    }
    .hero-badge::before {
        content:""; width:7px; height:7px; border-radius:50%; background:#34D399;
        animation:pulse 2.4s ease-in-out infinite;
    }
    .hero-title { display:flex; align-items:center; gap:.85rem; }
    .hero-mark { flex:none; }
    .hero-mark rect { transform-box:fill-box; transform-origin:bottom;
        animation:grow .6s cubic-bezier(.2,.8,.2,1) both; }
    .hero-mark rect:nth-of-type(2){ animation-delay:.08s; }
    .hero-mark rect:nth-of-type(3){ animation-delay:.16s; }
    .hero h1 {
        margin:0; font-size:2.6rem; font-weight:700; letter-spacing:-.03em; line-height:1.05;
        background:linear-gradient(92deg,#A5B4FC 0%,#818CF8 35%,#22D3EE 70%,#A5B4FC 100%);
        background-size:200% auto; -webkit-background-clip:text; background-clip:text;
        color:transparent; animation:shimmer 7s linear infinite;
    }
    .hero p { margin:.6rem 0 0; color:var(--muted); font-size:1.08rem; max-width:640px; }

    /* metric cards + hover lift */
    [data-testid="stMetric"] {
        background:var(--surface); border:1px solid var(--border);
        border-radius:14px; padding:1.1rem 1.25rem; animation:fadeUp .5s ease both;
        transition:transform .18s ease, border-color .18s ease, box-shadow .18s ease;
    }
    [data-testid="stMetric"]:hover {
        transform:translateY(-3px); border-color:rgba(99,102,241,.55);
        box-shadow:0 10px 30px rgba(0,0,0,.35), 0 0 0 1px rgba(99,102,241,.18);
    }
    [data-testid="stMetricLabel"] p { color:var(--muted); font-size:.82rem;
        font-weight:500; letter-spacing:.02em; text-transform:uppercase; }
    [data-testid="stMetricValue"] {
        font-family:'JetBrains Mono', monospace; font-weight:600;
        letter-spacing:-.02em; color:var(--text);
    }

    /* tabs */
    .stTabs [data-baseweb="tab-list"] { gap:2px; border-bottom:1px solid var(--border); }
    .stTabs [data-baseweb="tab"] { height:44px; padding:0 16px; color:var(--muted);
        transition:color .15s ease; }
    .stTabs [data-baseweb="tab"]:hover { color:var(--text); }
    .stTabs [aria-selected="true"] { color:var(--text); }
    .stTabs [data-baseweb="tab-highlight"] { background:var(--accent); }

    /* headings */
    h1,h2,h3,h4 { letter-spacing:-.01em; }

    /* empty state */
    .empty-card {
        background:var(--surface); border:1px solid var(--border);
        border-radius:16px; padding:1.75rem 2rem; animation:fadeUp .5s ease both;
    }
    .empty-card h3 { margin-top:0; }

    /* expanders, inputs, buttons + hover */
    [data-testid="stExpander"] { border:1px solid var(--border);
        border-radius:12px; background:var(--surface);
        transition:border-color .18s ease; }
    [data-testid="stExpander"]:hover { border-color:rgba(99,102,241,.4); }
    .stButton>button, .stDownloadButton>button {
        border-radius:10px; border:1px solid var(--border); font-weight:500;
        transition:transform .15s ease, border-color .15s ease, box-shadow .15s ease;
    }
    .stButton>button:hover, .stDownloadButton>button:hover {
        transform:translateY(-1px); border-color:rgba(99,102,241,.6);
        box-shadow:0 6px 18px rgba(99,102,241,.15);
    }
    [data-baseweb="select"]>div, .stTextArea textarea, .stTextInput input {
        border-radius:10px !important;
    }

    /* sidebar */
    [data-testid="stSidebar"] { background:var(--surface-2);
        border-right:1px solid var(--border); }

    .draft-label { font-weight:600; color:#A5B4FC; margin-bottom:.3rem;
        font-size:.9rem; }
    blockquote { border-left:3px solid var(--accent); color:var(--muted); }

    /* clickable KPI tiles: real buttons styled to look like metric cards */
    [class*="st-key-kpitile_"] button {
        display:flex; flex-direction:column; align-items:flex-start;
        gap:.2rem; text-align:left; background:var(--surface);
        border:1px solid var(--border); border-radius:14px;
        padding:1.05rem 1.2rem; min-height:118px;
        transition:transform .18s ease, border-color .18s ease, box-shadow .18s ease;
    }
    [class*="st-key-kpitile_"] button:hover {
        transform:translateY(-3px); border-color:rgba(99,102,241,.55);
        box-shadow:0 10px 30px rgba(0,0,0,.35), 0 0 0 1px rgba(99,102,241,.18);
    }
    [class*="st-key-kpitile_"] button [data-testid="stMarkdownContainer"] { width:100%; }
    [class*="st-key-kpitile_"] button p { margin:0; text-align:left; }
    [class*="st-key-kpitile_"] button p:nth-of-type(1) {
        color:var(--muted); font-size:.75rem; font-weight:600;
        letter-spacing:.05em; text-transform:uppercase;
    }
    [class*="st-key-kpitile_"] button p:nth-of-type(2) {
        font-family:'JetBrains Mono', monospace; font-size:2rem; font-weight:700;
        line-height:1.15; color:var(--text);
    }
    [class*="st-key-kpitile_"] button p:nth-of-type(3) {
        color:var(--muted); font-size:.8rem; margin-top:.15rem;
    }

    @media (prefers-reduced-motion: reduce) {
        *, *::before, *::after { animation:none !important; transition:none !important; }
    }
</style>
""", unsafe_allow_html=True)


def style_fig(fig, show_legend=True):
    """Apply the dark theme to a Plotly figure so charts match the app."""
    has_title = bool(fig.layout.title.text)  # avoid rendering a stray "undefined"
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", color=MUTED, size=13),
        margin=dict(l=0, r=10, t=44 if has_title else 8, b=0),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color=MUTED), title_text=""),
        showlegend=show_legend,
        xaxis=dict(gridcolor="rgba(255,255,255,.06)",
                   zerolinecolor="rgba(255,255,255,.08)", linecolor="rgba(255,255,255,.08)"),
        yaxis=dict(gridcolor="rgba(255,255,255,.06)",
                   zerolinecolor="rgba(255,255,255,.08)", linecolor="rgba(255,255,255,.08)"),
    )
    if has_title:
        fig.update_layout(title_font=dict(color="#E5E7EB", size=15))
    return fig


def open_detail(category):
    """Tile click -> jump to Analysis Details with the table pre-filtered."""
    st.session_state.nav = "Analysis Details"
    st.session_state.detail_filter = category


def _set(state_key, value):
    st.session_state[state_key] = value


# --- Data loading ------------------------------------------------------------
@st.cache_data(show_spinner=False)
def load_sample_data():
    """Load the bundled realistic demo dataset (with a synthetic fallback)."""
    try:
        return pd.read_csv(SAMPLE_CSV)
    except Exception:
        rng = np.random.default_rng(42)
        base = [
            "Excellent product, highly recommend! Fast shipping too.",
            "Broke after two days. Poor quality, want a refund.",
            "Good value for money, happy with the purchase.",
            "Wrong item delivered, not what I ordered at all.",
            "Customer service was rude and unhelpful.",
            "Too small, doesn't fit. The size chart is wrong.",
            "Item never arrived, still waiting after three weeks.",
            "Overpriced for what you get, waste of money.",
        ]
        return pd.DataFrame({
            "review_text": rng.choice(base, 100),
            "rating": rng.choice([1, 2, 3, 4, 5], 100, p=[.15, .15, .2, .25, .25]),
            "product": rng.choice(["Headphones", "Cable", "Bottle", "Chair"], 100),
            "date": pd.date_range("2025-01-01", periods=100).astype(str),
        })


def read_csv_robust(uploaded_file):
    """Read an uploaded CSV, tolerating encoding and malformed-row problems."""
    warnings = []
    raw = uploaded_file.getvalue()
    df, last_err = None, None
    for enc in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            df = pd.read_csv(io.BytesIO(raw), encoding=enc)
            if enc != "utf-8":
                warnings.append(f"File wasn't UTF-8 — read it as {enc}.")
            break
        except UnicodeDecodeError:
            continue
        except Exception as e:  # parser error -> retry leniently
            last_err = e
            try:
                df = pd.read_csv(io.BytesIO(raw), encoding=enc, engine="python",
                                 on_bad_lines="skip")
                warnings.append("Some malformed rows were skipped during import.")
                break
            except Exception as e2:
                last_err = e2
                continue
    if df is None:
        return None, [f"Couldn't parse this CSV ({last_err})."]

    df.columns = [str(c).strip() for c in df.columns]
    df = df.dropna(how="all").reset_index(drop=True)
    if df.empty:
        return None, ["This file has no usable rows."]
    return df, warnings


def analyze_columns(df):
    """Detect the review-text and rating columns (with a length-based fallback)."""
    text_cols = [c for c in df.columns if df[c].dtype == object]
    info = {"text_column": None, "rating_column": None, "text_columns": text_cols}

    for col in df.columns:
        if any(k in col.lower() for k in ["rating", "score", "stars", "rate"]):
            info["rating_column"] = col
            break

    def avg_len(c):
        return df[c].astype(str).str.len().mean()

    # Prefer text columns whose name signals review content, but skip id-like
    # columns and, among matches, pick the one with the longest average text.
    text_keywords = ["review", "text", "comment", "feedback", "description",
                     "content", "body", "message"]
    candidates = [c for c in text_cols
                  if any(k in c.lower() for k in text_keywords)
                  and not c.lower().endswith("_id") and c.lower() != "id"]
    if candidates:
        info["text_column"] = max(candidates, key=avg_len)
    elif text_cols:  # fallback: the longest free-text column
        best = max(text_cols, key=avg_len)
        if avg_len(best) >= 15:
            info["text_column"] = best
    return info


@st.cache_data(show_spinner=False)
def analyze(df, text_col):
    """Run the full analysis pipeline (cached on the data + chosen column)."""
    results = analyzer.analyze_text(df, text_col)
    word_freq = analyzer.get_word_frequency(df, text_col)
    insights = analyzer.get_actionable_insights(df, results, text_col)
    priority = analyzer.get_priority_reviews(df, results, text_col, top_n=25)
    return results, word_freq, insights, priority


# --- Sidebar: data source ----------------------------------------------------
with st.sidebar:
    st.header("Data")
    source = st.radio("Data source", ["Use sample data", "Upload CSV"])

    df = None
    if source == "Upload CSV":
        uploaded = st.file_uploader("Reviews CSV", type=["csv"])
        if uploaded is not None:
            df, warns = read_csv_robust(uploaded)
            if df is None:
                for w in warns:
                    st.error(w)
            else:
                st.success(f"Loaded {len(df):,} rows")
                for w in warns:
                    st.warning(w)
        else:
            st.caption("CSV with a review-text column (a rating column helps too).")
    else:
        df = load_sample_data()
        st.success(f"{len(df):,} realistic demo reviews loaded")

    text_col = None
    if df is not None:
        col_info = analyze_columns(df)
        st.divider()
        st.markdown("### Columns")
        options = col_info["text_columns"] or list(df.columns)
        default = col_info["text_column"] or options[0]
        text_col = st.selectbox(
            "Review text column", options,
            index=options.index(default) if default in options else 0,
            help="Auto-detected — change it if we picked the wrong column.")

        st.divider()
        st.markdown("### Quick stats")
        st.metric("Total reviews", f"{len(df):,}")
        rating_col = col_info["rating_column"]
        if rating_col and pd.api.types.is_numeric_dtype(df[rating_col]):
            st.metric("Average rating", f"{df[rating_col].mean():.2f} / 5")
        st.caption(f"Sentiment engine: {analyzer.backend.upper()}")


# --- Hero --------------------------------------------------------------------
st.markdown("""
<div class="hero">
  <div class="hero-badge">Business Intelligence</div>
  <div class="hero-title">
    <svg class="hero-mark" width="38" height="38" viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg">
      <defs><linearGradient id="mark" x1="0" y1="0" x2="1" y2="1">
        <stop offset="0" stop-color="#818CF8"/><stop offset="1" stop-color="#22D3EE"/>
      </linearGradient></defs>
      <rect x="4" y="22" width="8" height="14" rx="2.5" fill="url(#mark)"/>
      <rect x="16" y="13" width="8" height="23" rx="2.5" fill="url(#mark)"/>
      <rect x="28" y="5" width="8" height="31" rx="2.5" fill="url(#mark)"/>
    </svg>
    <h1>SmartReview-AI</h1>
  </div>
  <p>Customer feedback → decisions. Sentiment, recurring issues, and a ranked
     action queue with a suggested reply for every review.</p>
</div>
""", unsafe_allow_html=True)

if df is None or not text_col:
    st.markdown("""
    <div class="empty-card">
      <h3>Get started in 5 seconds</h3>
      <ol>
        <li>Keep <b>“Use sample data”</b> selected in the sidebar to explore a
            realistic dataset, or</li>
        <li>Switch to <b>“Upload CSV”</b> and drop in your own reviews export.</li>
      </ol>
      <p>Your file just needs a column of review text; a <code>rating</code>
         column (1–5) makes the analysis sharper.</p>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# --- Analyse (cap very large files for speed) --------------------------------
if len(df) > MAX_ROWS:
    st.info(f"Large file — analysing a random sample of {MAX_ROWS:,} of "
            f"{len(df):,} reviews to keep things fast.")
    df = df.sample(MAX_ROWS, random_state=0).sort_index().reset_index(drop=True)

with st.spinner("Analysing reviews…"):
    analysis_results, word_freq, insights, priority_reviews = analyze(df, text_col)

total = analysis_results["total_reviews"]
rating_col = analyze_columns(df)["rating_column"]

NAV = ["Dashboard", "Priority & Replies", "Insights & Actions",
       "Analysis Details", "Export"]
st.session_state.setdefault("nav", "Dashboard")
for _c, _name in zip(st.columns(len(NAV)), NAV):
    _c.button(_name, key=f"navbtn_{_name}", on_click=_set, args=("nav", _name),
              use_container_width=True,
              type="primary" if st.session_state.nav == _name else "secondary")
nav = st.session_state.nav

# --- Dashboard ---------------------------------------------------------------
if nav == "Dashboard":
    st.subheader("Business overview")

    urgent_count = len(analysis_results["urgent_indices"])
    if urgent_count:
        st.error(f"**URGENT** — {urgent_count} reviews need a response today.")

    pos_pct = analysis_results["positive_count"] / total * 100
    neg_pct = analysis_results["negative_count"] / total * 100
    issues_ct = len([i for i in analysis_results["issues_found"] if i])
    resp_needed = len([s for s in analysis_results["priority_scores"] if s > 50])

    st.caption("Click a tile to open its reviews in Analysis Details.")
    tiles = [
        ("positive", "Positive", analysis_results["positive_count"], f"{pos_pct:.0f}%"),
        ("negative", "Negative", analysis_results["negative_count"], f"{neg_pct:.0f}%"),
        ("issues", "With issues", issues_ct, f"{issues_ct / total * 100:.0f}%"),
        ("urgent", "Urgent", urgent_count, f"{resp_needed} to reply"),
    ]
    for col, (slug, label, value, sub) in zip(st.columns(4), tiles):
        with col:
            st.button(f"{label}\n\n{value}\n\n{sub}", key=f"kpitile_{slug}",
                      on_click=open_detail, args=(label,),
                      use_container_width=True)

    col1, col2 = st.columns(2)
    with col1:
        if analysis_results["issue_summary"]:
            issue_df = pd.DataFrame(analysis_results["issue_summary"].items(),
                                    columns=["Issue Type", "Count"])
            fig = px.bar(issue_df, x="Count", y="Issue Type", orientation="h",
                         title="Issues requiring attention", color="Count",
                         color_continuous_scale=["#7F1D1D", "#F87171"])
            fig.update_layout(yaxis={"categoryorder": "total ascending"},
                              coloraxis_showscale=False)
            fig.update_traces(marker_line_width=0)
            st.plotly_chart(style_fig(fig, show_legend=False),
                            use_container_width=True)
        else:
            st.info("No specific issues detected.")
    with col2:
        sentiment_df = pd.DataFrame({
            "Sentiment": ["Positive", "Negative", "Neutral"],
            "Count": [analysis_results["positive_count"],
                      analysis_results["negative_count"],
                      analysis_results["neutral_count"]],
        })
        fig = px.pie(sentiment_df, values="Count", names="Sentiment", hole=0.55,
                     title="Customer sentiment", color="Sentiment",
                     color_discrete_map=SENTIMENT_COLORS)
        fig.update_traces(marker=dict(line=dict(color="#0B0F17", width=3)),
                          textfont=dict(family="Inter", color="#0B0F17", size=13))
        st.plotly_chart(style_fig(fig), use_container_width=True)

# --- Priority queue + suggested replies --------------------------------------
if nav == "Priority & Replies":
    st.subheader("Reviews to action first")
    st.caption("Ranked by priority score. Each has an editable, suggested reply.")

    if priority_reviews.empty:
        st.info("No priority reviews found.")
    else:
        f1, f2 = st.columns([3, 1])
        with f1:
            issue_opts = ["All"] + list(analysis_results["issue_summary"].keys())
            issue_filter = st.multiselect("Filter by issue", issue_opts,
                                          default=["All"])
        with f2:
            urgent_only = st.checkbox("Urgent only")

        view = priority_reviews.copy()
        if urgent_only:
            view = view[view.index.isin(analysis_results["urgent_indices"])]
        if "All" not in issue_filter and issue_filter:
            view = view[view["issues"].apply(
                lambda x: any(i in x for i in issue_filter))]

        if view.empty:
            st.info("No reviews match the selected filters.")
        for idx, row in view.head(20).iterrows():
            score = int(row["priority_score"])
            text = str(row[text_col])
            title = f"{score}/100 · {row['sentiment']} · {text[:70]}…"
            with st.expander(title):
                meta = []
                if "product" in row:
                    meta.append(f"**Product:** {row['product']}")
                if rating_col and rating_col in row and pd.notna(row[rating_col]):
                    try:
                        meta.append("**Rating:** " + "⭐" * int(row[rating_col]))
                    except (ValueError, TypeError):
                        pass
                meta.append(f"**Issues:** {row['issues']}")
                st.markdown("  ·  ".join(meta))
                st.markdown(f"> {text}")

                draft = analyzer.draft_response(
                    sentiment=row["sentiment"],
                    issues=[i.strip() for i in str(row["issues"]).split(",")],
                    rating=row.get(rating_col) if rating_col else None,
                    product=row.get("product"))
                st.markdown('<div class="draft-label">Suggested reply '
                            '(edit before sending)</div>', unsafe_allow_html=True)
                st.text_area("draft", value=draft, height=110,
                             key=f"draft_{idx}", label_visibility="collapsed")

# --- Insights ----------------------------------------------------------------
if nav == "Insights & Actions":
    st.subheader("Actionable insights")
    if insights and insights["urgent_actions"]:
        st.error("**Urgent actions required**")
        for a in insights["urgent_actions"]:
            st.write(f"- {a['description']}")

    if insights and insights["improvement_areas"]:
        st.markdown("#### Top improvement areas")
        for area in insights["improvement_areas"]:
            with st.expander(f"{area['issue']} — affecting {area['impact']}"):
                st.write(f"**Recommended action:** {area['action']}")
                st.write("1. Review affected products\n"
                         "2. Loop in the relevant team\n"
                         "3. Implement a fix\n"
                         "4. Follow up with affected customers")

    if insights and insights["recommendations"]:
        st.markdown("#### Strategic recommendations")
        for rec in insights["recommendations"]:
            st.info(rec)

    st.markdown("#### Suggested action plan")
    c1, c2 = st.columns(2)
    c1.markdown("**Today**\n\n- Respond to urgent reviews\n"
                "- Handle safety & refund requests\n- Reply to 1-star reviews")
    c2.markdown("**This week**\n\n- Address top quality issues\n"
                "- Review shipping performance\n- Update product descriptions")

# --- Analysis details --------------------------------------------------------
if nav == "Analysis Details":
    st.subheader("Detailed analysis")
    if word_freq:
        st.markdown("#### Most mentioned words")
        word_df = pd.DataFrame(word_freq.items(), columns=["Word", "Frequency"])
        fig = px.treemap(word_df, path=["Word"], values="Frequency",
                         color="Frequency",
                         color_continuous_scale=["#1E293B", "#6366F1"])
        fig.update_traces(marker=dict(cornerradius=6,
                                      line=dict(color="#0B0F17", width=2)),
                          textfont=dict(family="Inter", color="#E5E7EB", size=14))
        fig.update_layout(coloraxis_showscale=False)
        st.plotly_chart(style_fig(fig, show_legend=False),
                        use_container_width=True)

    date_col = next((c for c in df.columns if "date" in c.lower()), None)
    if date_col:
        try:
            trend = df.copy()
            trend["sentiment"] = analysis_results["sentiments"]
            trend[date_col] = pd.to_datetime(trend[date_col], errors="coerce")
            trend = trend.dropna(subset=[date_col])
            daily = (trend.groupby([pd.Grouper(key=date_col, freq="W"), "sentiment"])
                     .size().reset_index(name="count"))
            if not daily.empty:
                st.markdown("#### Sentiment trend over time")
                fig = px.line(daily, x=date_col, y="count", color="sentiment",
                              color_discrete_map=SENTIMENT_COLORS, markers=True)
                fig.update_traces(line=dict(width=2.5))
                st.plotly_chart(style_fig(fig), use_container_width=True)
        except Exception:
            pass

    st.markdown("#### All reviews with analysis")
    detail_opts = ["All", "Positive", "Negative", "With issues", "Urgent"]
    st.session_state.setdefault("detail_filter", "All")
    for _c, _name in zip(st.columns(len(detail_opts)), detail_opts):
        _c.button(_name, key=f"dfbtn_{_name}", on_click=_set,
                  args=("detail_filter", _name), use_container_width=True,
                  type="primary" if st.session_state.detail_filter == _name else "secondary")
    flt = st.session_state.detail_filter

    display_df = df.copy()
    display_df["Sentiment"] = analysis_results["sentiments"]
    display_df["Priority"] = analysis_results["priority_scores"]
    display_df["Issues"] = [", ".join(i) if i else "None"
                            for i in analysis_results["issues_found"]]
    if flt == "Positive":
        display_df = display_df[display_df["Sentiment"] == "Positive"]
    elif flt == "Negative":
        display_df = display_df[display_df["Sentiment"] == "Negative"]
    elif flt == "With issues":
        display_df = display_df[display_df["Issues"] != "None"]
    elif flt == "Urgent":
        display_df = display_df[display_df.index.isin(analysis_results["urgent_indices"])]

    suffix = "" if flt == "All" else f" · {flt}"
    st.caption(f"Showing {len(display_df):,} of {total:,} reviews{suffix}")
    st.dataframe(display_df.sort_values("Priority", ascending=False),
                 use_container_width=True, height=420)

# --- Export ------------------------------------------------------------------
if nav == "Export":
    st.subheader("Export results")
    export_df = analyzer.export_analysis(df, analysis_results)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    c1, c2, c3 = st.columns(3)
    c1.download_button("Download full analysis (CSV)", export_df.to_csv(index=False),
                       f"review_analysis_{stamp}.csv", "text/csv",
                       use_container_width=True)
    if not priority_reviews.empty:
        c2.download_button("Download priority reviews (CSV)",
                           priority_reviews.to_csv(index=False),
                           f"priority_reviews_{stamp}.csv", "text/csv",
                           use_container_width=True)

    top_issues = "\n".join(f"- {k}: {v} occurrences"
                           for k, v in list(analysis_results["issue_summary"].items())[:5])
    recs = "\n".join(f"- {r}" for r in (insights["recommendations"] if insights else []))
    summary = f"""SMARTREVIEW-AI BUSINESS REPORT
Generated: {datetime.now():%Y-%m-%d %H:%M}

EXECUTIVE SUMMARY
Total reviews analysed: {total}
Positive: {analysis_results['positive_count']} ({pos_pct:.1f}%)
Negative: {analysis_results['negative_count']} ({neg_pct:.1f}%)
Urgent reviews: {len(analysis_results['urgent_indices'])}

TOP ISSUES
{top_issues or '- None detected'}

RECOMMENDATIONS
{recs or '- None'}
"""
    c3.download_button("Download executive summary (TXT)", summary,
                       f"executive_summary_{stamp}.txt", "text/plain",
                       use_container_width=True)
    st.success("Reports ready to download.")

st.divider()
st.caption("SmartReview-AI · Business Intelligence Edition · Built with Streamlit "
           f"& {analyzer.backend.upper()} sentiment analysis")
