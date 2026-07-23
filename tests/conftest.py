"""Make the app's `src/` modules importable in tests.

The app runs with `streamlit run src/app.py`, which puts `src/` on the path.
Tests replicate that so `from analyzer import ReviewAnalyzer` works.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
