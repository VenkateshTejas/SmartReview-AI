"""Tests for the review analysis engine (src/analyzer.py)."""
import pandas as pd
import pytest

from analyzer import ReviewAnalyzer, FinalAnalyzer, SimpleAnalyzer

TEXT_COL = "review_text"

# One review that should trigger each issue category.
ISSUE_EXAMPLES = {
    "Quality Issues": "It broke after two days. Poor quality, very disappointing.",
    "Shipping Problems": "The package never arrived. Still waiting weeks later.",
    "Customer Service": "Support was rude and unhelpful when I asked for help.",
    "Value/Pricing": "Overpriced and not worth the money at all.",
    "Sizing Issues": "Too small, doesn't fit, and the size chart is wrong.",
    "Wrong Product": "Wrong item delivered. This is not what I ordered.",
    "Safety Concern": "Dangerous product, my child got hurt. Should be recalled.",
}


@pytest.fixture
def analyzer():
    return ReviewAnalyzer()


def _df(reviews, ratings=None):
    data = {TEXT_COL: list(reviews)}
    if ratings is not None:
        data["rating"] = list(ratings)
    return pd.DataFrame(data)


# --- Backend & aliases -------------------------------------------------------
def test_backend_is_known(analyzer):
    assert analyzer.backend in {"vader", "textblob", "lexicon"}


def test_backwards_compatible_aliases():
    # Old code imported these names; they must still resolve to the engine.
    assert FinalAnalyzer is ReviewAnalyzer
    assert SimpleAnalyzer is ReviewAnalyzer


# --- Sentiment ---------------------------------------------------------------
def test_clear_negative_sentiment(analyzer):
    label, conf, score = analyzer.analyze_sentiment(
        "This is terrible. It broke immediately and the quality is awful.")
    assert label == "Negative"
    assert score < 0
    assert 0.5 <= conf <= 0.99


def test_clear_positive_sentiment(analyzer):
    label, _, score = analyzer.analyze_sentiment(
        "Absolutely love it! Works perfectly and I highly recommend it.")
    assert label == "Positive"
    assert score > 0


@pytest.mark.skipif(ReviewAnalyzer().backend != "vader",
                    reason="rating-blend direction is clearest with VADER scoring")
def test_rating_blends_into_sentiment(analyzer):
    # Near-neutral text: the star rating should tip the label.
    neutral = "The package contained the product I ordered."
    res = analyzer.analyze_text(_df([neutral, neutral], ratings=[1, 5]), TEXT_COL)
    assert res["sentiments"][0] == "Negative"   # 1-star tips negative
    assert res["sentiments"][1] == "Positive"   # 5-star tips positive


# --- Issue detection ---------------------------------------------------------
@pytest.mark.parametrize("category,text", list(ISSUE_EXAMPLES.items()))
def test_each_issue_category_is_detected(analyzer, category, text):
    res = analyzer.analyze_text(_df([text]), TEXT_COL)
    assert category in res["issues_found"][0]


def test_clean_positive_review_has_no_issues(analyzer):
    res = analyzer.analyze_text(_df(["Great product, fast shipping, love it!"]), TEXT_COL)
    assert res["issues_found"][0] == []


def test_issue_summary_counts(analyzer):
    reviews = ["It broke, poor quality.", "Defective, stopped working."]
    res = analyzer.analyze_text(_df(reviews), TEXT_COL)
    assert res["issue_summary"].get("Quality Issues") == 2


# --- Urgency & priority ------------------------------------------------------
def test_urgent_keywords_flagged(analyzer):
    reviews = ["Great, no problems here.", "I want a refund immediately."]
    res = analyzer.analyze_text(_df(reviews), TEXT_COL)
    assert 0 not in res["urgent_indices"]
    assert 1 in res["urgent_indices"]


def test_priority_orders_severe_above_happy(analyzer):
    happy = "Fantastic, works perfectly, five stars!"
    severe = "Dangerous product, my child got hurt, I want a refund. Recall this!"
    res = analyzer.analyze_text(_df([happy, severe], ratings=[5, 1]), TEXT_COL)
    assert res["priority_scores"][1] > res["priority_scores"][0]
    assert res["priority_scores"][1] >= 90   # safety + urgent + 1-star
    assert res["priority_scores"][0] <= 20


def test_priority_capped_at_100(analyzer):
    res = analyzer.analyze_text(
        _df(["Dangerous, injured, defective, wrong item, refund, recall!"],
            ratings=[1]), TEXT_COL)
    assert res["priority_scores"][0] <= 100


# --- Result shape ------------------------------------------------------------
def test_analysis_has_all_keys_app_depends_on(analyzer):
    res = analyzer.analyze_text(_df(["Good product."]), TEXT_COL)
    required = {"backend", "total_reviews", "sentiments", "positive_count",
                "negative_count", "neutral_count", "issues_found",
                "urgent_indices", "priority_scores", "issue_summary"}
    assert required <= set(res)
    n = res["total_reviews"]
    assert len(res["sentiments"]) == n
    assert len(res["issues_found"]) == n
    assert len(res["priority_scores"]) == n
    assert (res["positive_count"] + res["negative_count"]
            + res["neutral_count"]) == n


def test_missing_column_returns_none(analyzer):
    assert analyzer.analyze_text(_df(["hi"]), "does_not_exist") is None


def test_empty_dataframe_does_not_crash(analyzer):
    res = analyzer.analyze_text(_df([]), TEXT_COL)
    assert res["total_reviews"] == 0
    assert res["sentiments"] == []
    assert res["issue_summary"] == {}


# --- Word frequency ----------------------------------------------------------
def test_word_frequency_skips_stopwords_and_short_words(analyzer):
    freq = analyzer.get_word_frequency(
        _df(["the battery battery life is good good good"]), TEXT_COL)
    assert "the" not in freq          # stopword
    assert "is" not in freq           # short/stopword
    assert freq.get("good") == 3
    assert freq.get("battery") == 2


# --- Insights ----------------------------------------------------------------
def test_insights_surface_top_issues_and_recommendations(analyzer):
    reviews = ["Broke, poor quality."] * 4 + ["Love it!"]
    res = analyzer.analyze_text(_df(reviews), TEXT_COL)
    insights = analyzer.get_actionable_insights(_df(reviews), res, TEXT_COL)
    assert insights["improvement_areas"]
    assert insights["improvement_areas"][0]["issue"] == "Quality Issues"
    assert any("quality" in r.lower() for r in insights["recommendations"])


def test_get_action_for_issue_covers_all_categories(analyzer):
    for category in ISSUE_EXAMPLES:
        assert analyzer.get_action_for_issue(category)          # non-empty
    assert analyzer.get_action_for_issue("Nonexistent Issue")   # has a default


# --- Reply drafting ----------------------------------------------------------
def test_draft_response_is_issue_aware(analyzer):
    safety = analyzer.draft_response("Negative", ["Safety Concern"], 1, "Heater").lower()
    assert "safety" in safety or "refund" in safety
    shipping = analyzer.draft_response("Negative", ["Shipping Problems"], 2, "Mat").lower()
    assert "deliver" in shipping or "reship" in shipping or "shipping" in shipping


def test_draft_response_positive_and_neutral(analyzer):
    assert "thank" in analyzer.draft_response("Positive", [], 5).lower()
    assert "5-star" in analyzer.draft_response("Neutral", [], 3).lower()


def test_draft_response_prioritises_most_severe_issue(analyzer):
    # Safety outranks Value/Pricing when both are present.
    draft = analyzer.draft_response("Negative", ["Value/Pricing", "Safety Concern"], 1)
    assert "safety" in draft.lower()


# --- Priority reviews & export -----------------------------------------------
def test_priority_reviews_sorted_descending(analyzer):
    reviews = ["Love it!", "Dangerous, refund now!", "It's okay."]
    res = analyzer.analyze_text(_df(reviews, ratings=[5, 1, 3]), TEXT_COL)
    pr = analyzer.get_priority_reviews(_df(reviews, ratings=[5, 1, 3]), res, TEXT_COL)
    scores = pr["priority_score"].tolist()
    assert scores == sorted(scores, reverse=True)
    assert {"priority_score", "sentiment", "issues"} <= set(pr.columns)


def test_export_adds_analysis_columns(analyzer):
    df = _df(["Broke, poor quality.", "Great!"])
    res = analyzer.analyze_text(df, TEXT_COL)
    export = analyzer.export_analysis(df, res)
    for col in ("predicted_sentiment", "priority_score", "issues_detected",
                "analysis_date"):
        assert col in export.columns
    assert len(export) == len(df)
