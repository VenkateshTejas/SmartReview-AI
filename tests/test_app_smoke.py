"""Smoke tests: render every nav section (and every table filter) headlessly.

These catch the "app works on the Dashboard but crashes on another tab" class
of bug — e.g. a NameError that only fires when you open Export — before it
reaches the live site. Uses Streamlit's native AppTest harness.
"""
import os

from streamlit.testing.v1 import AppTest

APP = os.path.join(os.path.dirname(__file__), "..", "src", "app.py")

SECTIONS = ["Welcome", "Dashboard", "Priority & Replies",
            "Insights & Actions", "Analysis Details", "Export"]

# Every value the table filter can take, including the ones set by the
# chart drill-downs (sentiment chips -> "Neutral", issue bar -> "Quality Issues").
FILTERS = ["All", "Positive", "Negative", "Neutral", "With issues",
           "Urgent", "Quality Issues"]


def test_every_nav_section_renders():
    """Each nav section must render on the sample data without raising."""
    at = AppTest.from_file(APP, default_timeout=60).run()
    assert not at.exception, f"Welcome raised: {at.exception}"
    for section in SECTIONS[1:]:
        at.session_state["nav"] = section
        at.run()
        assert not at.exception, f"{section} raised: {at.exception}"


def test_detail_filters_do_not_crash():
    """Every Analysis Details filter (incl. chart drill-down values) renders."""
    at = AppTest.from_file(APP, default_timeout=60).run()
    for flt in FILTERS:
        at.session_state["nav"] = "Analysis Details"
        at.session_state["detail_filter"] = flt
        at.run()
        assert not at.exception, f"detail_filter={flt!r} raised: {at.exception}"
