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
SENTIMENT_COLORS = {"Positive": "#16a34a", "Negative": "#dc2626",
                    "Neutral": "#f59e0b"}

analyzer = ReviewAnalyzer()

# --- Styling -----------------------------------------------------------------
st.markdown("""
<style>
    .hero {
        background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
        padding: 1.6rem 2rem; border-radius: 16px; margin-bottom: 1.2rem;
        color: white;
    }
    .hero h1 { margin: 0; font-size: 2.1rem; color: white; }
    .hero p { margin: .35rem 0 0; opacity: .9; font-size: 1.02rem; }
    [data-testid="stMetric"] {
        background: rgba(128,128,128,0.06);
        border: 1px solid rgba(128,128,128,0.18);
        border-radius: 12px; padding: 1rem 1.1rem;
    }
    .empty-card {
        border: 1px solid rgba(128,128,128,0.2); border-radius: 14px;
        padding: 1.5rem 1.8rem; background: rgba(128,128,128,0.05);
    }
    .empty-card h3 { margin-top: 0; }
    .stTabs [data-baseweb="tab-list"] { gap: 6px; }
    .stTabs [data-baseweb="tab"] { height: 46px; padding: 0 18px; }
    .draft-label { font-weight: 600; color: #4f46e5; margin-bottom: .2rem; }
</style>
""", unsafe_allow_html=True)


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
    st.header("📤 Data")
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
                st.success(f"✅ Loaded {len(df):,} rows")
                for w in warns:
                    st.warning(w)
        else:
            st.caption("CSV with a review-text column (a rating column helps too).")
    else:
        df = load_sample_data()
        st.success(f"✅ {len(df):,} realistic demo reviews loaded")

    text_col = None
    if df is not None:
        col_info = analyze_columns(df)
        st.divider()
        st.markdown("### 🧭 Columns")
        options = col_info["text_columns"] or list(df.columns)
        default = col_info["text_column"] or options[0]
        text_col = st.selectbox(
            "Review text column", options,
            index=options.index(default) if default in options else 0,
            help="Auto-detected — change it if we picked the wrong column.")

        st.divider()
        st.markdown("### 📊 Quick stats")
        st.metric("Total reviews", f"{len(df):,}")
        rating_col = col_info["rating_column"]
        if rating_col and pd.api.types.is_numeric_dtype(df[rating_col]):
            st.metric("Average rating", f"{df[rating_col].mean():.2f} ⭐")
        st.caption(f"Sentiment engine: {analyzer.backend.upper()}")


# --- Hero --------------------------------------------------------------------
st.markdown("""
<div class="hero">
  <h1>🤖 SmartReview-AI</h1>
  <p>Turn thousands of customer reviews into decisions — sentiment, issues,
     priorities and ready-to-send replies.</p>
</div>
""", unsafe_allow_html=True)

if df is None or not text_col:
    st.markdown("""
    <div class="empty-card">
      <h3>👋 Get started in 5 seconds</h3>
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

with st.spinner("🔄 Analysing reviews…"):
    analysis_results, word_freq, insights, priority_reviews = analyze(df, text_col)

total = analysis_results["total_reviews"]
rating_col = analyze_columns(df)["rating_column"]

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🎯 Dashboard", "🚨 Priority & Replies", "💡 Insights & Actions",
    "📊 Analysis Details", "💾 Export",
])

# --- Tab 1: Dashboard --------------------------------------------------------
with tab1:
    st.subheader("Business overview")

    urgent_count = len(analysis_results["urgent_indices"])
    if urgent_count:
        st.error(f"⚠️ **URGENT:** {urgent_count} reviews need a response today.")

    c1, c2, c3, c4 = st.columns(4)
    pos_pct = analysis_results["positive_count"] / total * 100
    neg_pct = analysis_results["negative_count"] / total * 100
    issues_ct = len([i for i in analysis_results["issues_found"] if i])
    resp_needed = len([s for s in analysis_results["priority_scores"] if s > 50])
    c1.metric("😊 Positive", analysis_results["positive_count"],
              f"{pos_pct:.0f}%", delta_color="off")
    c2.metric("😞 Negative", analysis_results["negative_count"],
              f"{neg_pct:.0f}%", delta_color="off")
    c3.metric("⚠️ With issues", issues_ct,
              f"{issues_ct / total * 100:.0f}%", delta_color="off")
    c4.metric("🚨 Urgent", urgent_count,
              f"{resp_needed} need a reply", delta_color="off")

    col1, col2 = st.columns(2)
    with col1:
        if analysis_results["issue_summary"]:
            issue_df = pd.DataFrame(analysis_results["issue_summary"].items(),
                                    columns=["Issue Type", "Count"])
            fig = px.bar(issue_df, x="Count", y="Issue Type", orientation="h",
                         title="Issues requiring attention", color="Count",
                         color_continuous_scale="Reds")
            fig.update_layout(yaxis={"categoryorder": "total ascending"},
                              margin=dict(l=0, r=0, t=40, b=0))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No specific issues detected. 🎉")
    with col2:
        sentiment_df = pd.DataFrame({
            "Sentiment": ["Positive", "Negative", "Neutral"],
            "Count": [analysis_results["positive_count"],
                      analysis_results["negative_count"],
                      analysis_results["neutral_count"]],
        })
        fig = px.pie(sentiment_df, values="Count", names="Sentiment", hole=0.45,
                     title="Customer sentiment", color="Sentiment",
                     color_discrete_map=SENTIMENT_COLORS)
        fig.update_layout(margin=dict(l=0, r=0, t=40, b=0))
        st.plotly_chart(fig, use_container_width=True)

# --- Tab 2: Priority queue + AI replies --------------------------------------
with tab2:
    st.subheader("🚨 Reviews to action first")
    st.caption("Ranked by priority score. Each has an editable, AI-drafted reply.")

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
            icon = "🔴" if score >= 80 else ("🟡" if score >= 50 else "🟢")
            text = str(row[text_col])
            title = f"{icon} {score}/100 · {row['sentiment']} · {text[:70]}…"
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
                st.markdown('<div class="draft-label">✍️ Suggested reply '
                            '(edit before sending)</div>', unsafe_allow_html=True)
                st.text_area("draft", value=draft, height=110,
                             key=f"draft_{idx}", label_visibility="collapsed")

# --- Tab 3: Insights ---------------------------------------------------------
with tab3:
    st.subheader("💡 Actionable insights")
    if insights and insights["urgent_actions"]:
        st.error("🚨 **Urgent actions required**")
        for a in insights["urgent_actions"]:
            st.write(f"- {a['description']}")

    if insights and insights["improvement_areas"]:
        st.markdown("#### 📈 Top improvement areas")
        for area in insights["improvement_areas"]:
            with st.expander(f"{area['issue']} — affecting {area['impact']}"):
                st.write(f"**Recommended action:** {area['action']}")
                st.write("1. Review affected products\n"
                         "2. Loop in the relevant team\n"
                         "3. Implement a fix\n"
                         "4. Follow up with affected customers")

    if insights and insights["recommendations"]:
        st.markdown("#### 🧭 Strategic recommendations")
        for rec in insights["recommendations"]:
            st.info(rec)

    st.markdown("#### 📋 Suggested action plan")
    c1, c2 = st.columns(2)
    c1.markdown("**Today**\n\n- Respond to urgent reviews\n"
                "- Handle safety & refund requests\n- Reply to 1-star reviews")
    c2.markdown("**This week**\n\n- Address top quality issues\n"
                "- Review shipping performance\n- Update product descriptions")

# --- Tab 4: Analysis details -------------------------------------------------
with tab4:
    st.subheader("📊 Detailed analysis")
    if word_freq:
        st.markdown("#### Most mentioned words")
        word_df = pd.DataFrame(word_freq.items(), columns=["Word", "Frequency"])
        fig = px.treemap(word_df, path=["Word"], values="Frequency")
        fig.update_layout(margin=dict(l=0, r=0, t=10, b=0))
        st.plotly_chart(fig, use_container_width=True)

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
                fig.update_layout(margin=dict(l=0, r=0, t=10, b=0))
                st.plotly_chart(fig, use_container_width=True)
        except Exception:
            pass

    st.markdown("#### All reviews with analysis")
    display_df = df.copy()
    display_df["Sentiment"] = analysis_results["sentiments"]
    display_df["Priority"] = analysis_results["priority_scores"]
    display_df["Issues"] = [", ".join(i) if i else "None"
                            for i in analysis_results["issues_found"]]
    st.dataframe(display_df.sort_values("Priority", ascending=False),
                 use_container_width=True, height=420)

# --- Tab 5: Export -----------------------------------------------------------
with tab5:
    st.subheader("💾 Export results")
    export_df = analyzer.export_analysis(df, analysis_results)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    c1, c2, c3 = st.columns(3)
    c1.download_button("📥 Full analysis (CSV)", export_df.to_csv(index=False),
                       f"review_analysis_{stamp}.csv", "text/csv",
                       use_container_width=True)
    if not priority_reviews.empty:
        c2.download_button("🚨 Priority reviews (CSV)",
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
    c3.download_button("📊 Executive summary (TXT)", summary,
                       f"executive_summary_{stamp}.txt", "text/plain",
                       use_container_width=True)
    st.success("✅ Reports ready to download.")

st.divider()
st.caption("SmartReview-AI · Business Intelligence Edition · Built with Streamlit "
           f"& {analyzer.backend.upper()} sentiment analysis")
