"""Review analysis engine for SmartReview-AI.

Turns raw product reviews into sentiment, issue categories, priority scores and
actionable business insights.

Sentiment uses VADER (purpose-built for short, informal review text: it handles
negation, intensifiers, capitalisation and punctuation emphasis). It falls back
to TextBlob and finally to a tiny built-in lexicon so the app never crashes if a
dependency is missing.
"""

import pandas as pd
from datetime import datetime

# --- Sentiment backend selection (done once at import) -----------------------
_VADER = None
_BACKEND = "lexicon"
try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    _VADER = SentimentIntensityAnalyzer()
    _BACKEND = "vader"
except Exception:  # pragma: no cover - dependency fallback
    try:
        from textblob import TextBlob
        _BACKEND = "textblob"
    except Exception:  # pragma: no cover - last-resort fallback
        _BACKEND = "lexicon"

# Sentiment thresholds tuned per backend (compound/polarity in [-1, 1]).
_THRESHOLDS = {"vader": 0.05, "textblob": 0.10, "lexicon": 0.0}

# Minimal fallback lexicon (only used if neither VADER nor TextBlob is present).
_POS_WORDS = {"good", "great", "excellent", "amazing", "love", "perfect", "best",
              "happy", "outstanding", "recommend", "fast", "quality", "works"}
_NEG_WORDS = {"bad", "poor", "broke", "broken", "defective", "waste", "cheap",
              "terrible", "awful", "refund", "disappointed", "wrong", "damaged",
              "rude", "overpriced", "dangerous", "never"}


class ReviewAnalyzer:
    """Sentiment + issue + priority analysis for a table of reviews."""

    # Issue category -> keywords that signal it, plus its priority weight.
    ISSUE_RULES = {
        "Safety Concern": (
            ["dangerous", "unsafe", "hazard", "caught fire", "got hurt",
             "injured", "recall", "harmful", "toxic"], 40),
        "Quality Issues": (
            ["broke", "broken", "defective", "stopped working", "not working",
             "poor quality", "cheaply made", "cheap materials", "fell apart",
             "malfunction", "faulty", "flimsy"], 20),
        "Wrong Product": (
            ["wrong item", "wrong product", "not what i ordered",
             "not as described", "false advertising", "not as advertised"], 20),
        "Shipping Problems": (
            ["never arrived", "didn't arrive", "lost package",
             "damaged in shipping", "damaged during shipping",
             "package was damaged", "delayed", "late delivery",
             "still waiting", "never shipped"], 20),
        "Customer Service": (
            ["rude", "unhelpful", "poor service", "no response", "no reply",
             "ignored", "terrible service"], 15),
        "Sizing Issues": (
            ["too small", "too big", "too large", "doesn't fit", "does not fit",
             "size chart", "wrong size", "runs small", "runs large"], 10),
        "Value/Pricing": (
            ["overpriced", "not worth", "waste of money", "too expensive",
             "rip off", "ripoff"], 10),
    }

    # Phrases that mean "a human needs to respond today".
    URGENT_KEYWORDS = ["refund", "return it", "returning", "lawsuit",
                       "legal action", "sue", "dangerous", "unsafe",
                       "injured", "got hurt", "recall", "hazard"]

    def __init__(self):
        self.backend = _BACKEND
        self.pos_threshold = _THRESHOLDS[_BACKEND]
        self.neg_threshold = -_THRESHOLDS[_BACKEND]

    # --- Sentiment -----------------------------------------------------------
    def _raw_score(self, text):
        """Return a sentiment score in [-1, 1] using the active backend."""
        text = str(text)
        if self.backend == "vader":
            return _VADER.polarity_scores(text)["compound"]
        if self.backend == "textblob":
            return TextBlob(text).sentiment.polarity
        words = text.lower().split()
        pos = sum(w.strip(".,!?") in _POS_WORDS for w in words)
        neg = sum(w.strip(".,!?") in _NEG_WORDS for w in words)
        total = pos + neg
        return 0.0 if total == 0 else (pos - neg) / total

    def _label(self, score):
        """Map a score to (label, confidence)."""
        if score >= self.pos_threshold:
            label = "Positive"
        elif score <= self.neg_threshold:
            label = "Negative"
        else:
            label = "Neutral"
        confidence = round(min(0.5 + abs(score) / 2, 0.99), 2)
        return label, confidence

    def analyze_sentiment(self, text):
        """Sentiment of a single piece of text -> (label, confidence, score)."""
        score = self._raw_score(text)
        label, confidence = self._label(score)
        return label, confidence, score

    # --- Main analysis -------------------------------------------------------
    def analyze_text(self, df, text_column):
        """Analyze every review and return a results dict."""
        if text_column not in df.columns:
            return None

        lengths = df[text_column].astype(str).str.len()
        analysis = {
            "backend": self.backend,
            "total_reviews": len(df),
            "avg_length": lengths.mean(),
            "shortest_review": lengths.min(),
            "longest_review": lengths.max(),
            "empty_reviews": int(df[text_column].isna().sum()),
        }

        sentiments, issues_found, urgent_reviews, review_priorities = [], [], [], []

        for idx, row in df.iterrows():
            text = str(row[text_column])
            text_lower = text.lower()

            # Sentiment from text, blended with the star rating when available so
            # a 1-star "it's fine" still reads as dissatisfied.
            text_score = self._raw_score(text)
            score = text_score
            rating = row.get("rating") if "rating" in row else None
            if rating is not None and pd.notna(rating):
                rating_score = (float(rating) - 3) / 2.0  # 1->-1 ... 5->+1
                score = 0.65 * text_score + 0.35 * rating_score
            sentiment, _ = self._label(score)
            sentiments.append(sentiment)

            # Base priority from sentiment.
            priority_score = 50 if sentiment == "Negative" else (
                25 if sentiment == "Neutral" else 0)

            # Detect issues and add their weights.
            review_issues = []
            for issue, (keywords, weight) in self.ISSUE_RULES.items():
                if any(kw in text_lower for kw in keywords):
                    review_issues.append(issue)
                    priority_score += weight
            issues_found.append(review_issues)

            # Urgent escalation.
            if any(kw in text_lower for kw in self.URGENT_KEYWORDS):
                urgent_reviews.append(idx)
                priority_score += 30

            # Low ratings raise priority further.
            if rating is not None and pd.notna(rating):
                if float(rating) <= 2:
                    priority_score += 20
                elif float(rating) == 3:
                    priority_score += 10

            review_priorities.append(min(priority_score, 100))

        analysis["sentiments"] = sentiments
        analysis["positive_count"] = sentiments.count("Positive")
        analysis["negative_count"] = sentiments.count("Negative")
        analysis["neutral_count"] = sentiments.count("Neutral")
        analysis["issues_found"] = issues_found
        analysis["urgent_indices"] = urgent_reviews
        analysis["priority_scores"] = review_priorities

        issue_summary = {}
        for issues_list in issues_found:
            for issue in issues_list:
                issue_summary[issue] = issue_summary.get(issue, 0) + 1
        # Keep the summary ordered most-common first.
        analysis["issue_summary"] = dict(
            sorted(issue_summary.items(), key=lambda kv: kv[1], reverse=True))

        return analysis

    # --- Supporting analytics ------------------------------------------------
    def get_word_frequency(self, df, text_column, top_n=10):
        """Most common meaningful words across all reviews."""
        if text_column not in df.columns:
            return {}

        stop_words = {
            "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
            "of", "with", "by", "from", "is", "was", "are", "were", "be", "been",
            "have", "has", "had", "do", "does", "did", "will", "would", "could",
            "should", "may", "might", "must", "can", "this", "that", "these",
            "those", "i", "you", "he", "she", "it", "we", "they", "them", "their",
            "what", "which", "who", "when", "where", "why", "how", "all", "each",
            "every", "both", "few", "more", "most", "other", "some", "such",
            "only", "own", "same", "so", "than", "too", "very", "just", "your",
            "my", "product", "item", "one", "get", "got", "also", "even", "still",
        }

        all_words = []
        for text in df[text_column].fillna(""):
            for w in str(text).lower().split():
                w = w.strip('.,!?";:()[]{}\'"-')
                if len(w) > 3 and w not in stop_words:
                    all_words.append(w)

        if all_words:
            return pd.Series(all_words).value_counts().head(top_n).to_dict()
        return {}

    def get_actionable_insights(self, df, analysis_results, text_column):
        """Generate business insights from the analysis results."""
        if not analysis_results:
            return None

        insights = {"urgent_actions": [], "improvement_areas": [],
                    "recommendations": []}
        total = analysis_results["total_reviews"] or 1

        if analysis_results["urgent_indices"]:
            count = len(analysis_results["urgent_indices"])
            insights["urgent_actions"].append({
                "action": "IMMEDIATE ATTENTION REQUIRED",
                "count": count,
                "description": f"{count} reviews need immediate response",
            })

        for issue, count in list(analysis_results.get("issue_summary", {}).items())[:3]:
            percentage = (count / total) * 100
            insights["improvement_areas"].append({
                "issue": issue,
                "impact": f"{count} reviews ({percentage:.1f}%)",
                "action": self.get_action_for_issue(issue),
            })

        summary = analysis_results.get("issue_summary", {})
        negative_pct = (analysis_results["negative_count"] / total) * 100
        if negative_pct > 30:
            insights["recommendations"].append(
                "High negative sentiment — review product/service quality")
        if "Safety Concern" in summary:
            insights["recommendations"].append(
                "Safety complaints reported — escalate to compliance immediately")
        if "Quality Issues" in summary:
            insights["recommendations"].append(
                "Multiple quality complaints — check manufacturing")
        if "Shipping Problems" in summary:
            insights["recommendations"].append(
                "Shipping issues detected — review logistics")
        if "Sizing Issues" in summary:
            insights["recommendations"].append(
                "Sizing complaints — update size charts and product descriptions")

        return insights

    def get_action_for_issue(self, issue_type):
        """Recommended action for each issue category."""
        actions = {
            "Safety Concern": "Escalate to compliance/legal and consider product recall",
            "Quality Issues": "Review manufacturing QC process and supplier standards",
            "Shipping Problems": "Contact logistics partner and review packaging",
            "Customer Service": "Schedule team training and review response protocols",
            "Wrong Product": "Audit fulfillment process and product listings",
            "Value/Pricing": "Analyze competitor pricing and value proposition",
            "Sizing Issues": "Update size charts and product descriptions",
        }
        return actions.get(issue_type, "Investigate and create action plan")

    # --- Response drafting ---------------------------------------------------
    # Suggested reply templates keyed by issue category (most severe first).
    RESPONSE_TEMPLATES = {
        "Safety Concern": (
            "Hi {name}, thank you for flagging this — safety is our top priority "
            "and we're treating your report with urgency. Please stop using the "
            "{product} immediately. We're issuing a full refund now and escalating "
            "this to our product-safety team, who will follow up with you directly."),
        "Quality Issues": (
            "Hi {name}, I'm sorry the {product} didn't hold up — that's not the "
            "standard we aim for. We'd like to make it right with a free replacement "
            "or a full refund, whichever you prefer. I've also shared your feedback "
            "with our quality team."),
        "Wrong Product": (
            "Hi {name}, apologies for the mix-up with your order. We'll ship the "
            "correct {product} right away at no cost and email you a prepaid return "
            "label for the item you received. Thank you for your patience."),
        "Shipping Problems": (
            "Hi {name}, I'm sorry about the delivery trouble with your {product}. "
            "We're tracking down your package and will reship or refund it today, "
            "plus cover any shipping charges. Thank you for letting us know."),
        "Customer Service": (
            "Hi {name}, I'm sorry about the experience you had with our support "
            "team — that's not how we want to treat customers. I've escalated this "
            "to a manager who will reach out personally to make it right."),
        "Sizing Issues": (
            "Hi {name}, sorry the {product} didn't fit as expected. We'll happily "
            "send a free exchange in the correct size and I've flagged our size "
            "guide for review so this is clearer for the next customer."),
        "Value/Pricing": (
            "Hi {name}, thank you for the honest feedback on pricing. We're always "
            "reviewing our value against the market — I'd like to offer you a "
            "discount on your next order as a thank-you for giving us a try."),
    }

    def draft_response(self, sentiment, issues=None, rating=None, product=None,
                       name="there"):
        """Draft a suggested reply to a review (template-based, no external API)."""
        product = product or "product"
        issues = issues or []

        # Prioritise the most severe detected issue.
        for issue in self.ISSUE_RULES:  # dict is ordered most-severe first
            if issue in issues:
                return self.RESPONSE_TEMPLATES[issue].format(name=name, product=product)

        if sentiment == "Positive":
            return (f"Hi {name}, thank you so much for the kind words — we're "
                    f"thrilled you're happy with the {product}! Reviews like yours "
                    "make our day. We'd love to see you again soon.")
        if sentiment == "Negative":
            return (f"Hi {name}, I'm sorry the {product} didn't meet your "
                    "expectations. We'd really like to understand what went wrong "
                    "and make it right — please reply here and we'll help right away.")
        return (f"Hi {name}, thanks for taking the time to review the {product}. "
                "We'd love to know what would have made this a 5-star experience — "
                "your feedback helps us improve.")

    def get_priority_reviews(self, df, analysis_results, text_column, top_n=10):
        """Return the highest-priority reviews for triage."""
        if not analysis_results or "priority_scores" not in analysis_results:
            return pd.DataFrame()

        priority_df = df.copy()
        priority_df["priority_score"] = analysis_results["priority_scores"]
        priority_df["sentiment"] = analysis_results["sentiments"]
        priority_df["issues"] = [", ".join(issues) if issues else "None"
                                 for issues in analysis_results["issues_found"]]

        return priority_df.sort_values("priority_score", ascending=False).head(top_n)

    def export_analysis(self, df, analysis_results):
        """Attach analysis columns to the data for export."""
        export_data = df.copy()

        if analysis_results:
            export_data["predicted_sentiment"] = analysis_results["sentiments"]
            export_data["priority_score"] = analysis_results["priority_scores"]
            export_data["issues_detected"] = [
                ", ".join(issues) if issues else "None"
                for issues in analysis_results["issues_found"]]

        export_data["analysis_date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return export_data


# Backwards-compatible aliases (older code imported FinalAnalyzer/SimpleAnalyzer).
FinalAnalyzer = ReviewAnalyzer
SimpleAnalyzer = ReviewAnalyzer
