# 🤖 SmartReview-AI

[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.49-red.svg)](https://streamlit.io/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/Status-In%20Development-orange.svg)](https://github.com/VenkateshTejas/smartreview-ai)

A review-analysis platform that turns customer feedback into prioritized, actionable insights — sentiment, recurring issues, and a triage queue with suggested replies.

## 🎯 Executive Summary

SmartReview-AI helps e-commerce teams keep up with customer feedback. Instead of reading reviews one by one, it classifies sentiment, detects recurring issues (quality, shipping, sizing, safety, pricing, and more), and surfaces the reviews that need a response first — each with a suggested reply. It's built as a product-management + engineering portfolio project; the `docs/` folder holds the PRD, personas, and research behind it.

## 📊 The Problem

For a store with a steady stream of reviews, keeping up by hand doesn't scale:

- Reading and triaging every review manually gets slower as volume grows.
- Recurring problems (a sizing issue, a bad shipping lane, a quality defect) are easy to miss when feedback is scattered across hundreds of reviews.
- Reviews that need a fast response — refunds, safety complaints — can sit unanswered.
- There's rarely a single view of *what* customers are unhappy about and *which* reviews to act on first.

SmartReview-AI focuses on that last mile: turning a pile of reviews into a ranked, categorized to-do list.

## 💡 The Solution

SmartReview-AI provides:
- ⚡ Real-time sentiment analysis (positive/negative/neutral)
- 🎯 Automatic issue detection and categorization
- 📈 Predictive alerts for emerging problems
- 🔥 Priority-based response recommendations
- 📊 Competitive intelligence tracking

## ✨ Key Features

### Available Now (MVP)
- ✅ Bulk review processing (thousands of reviews in seconds)
- ✅ Sentiment classification with VADER (tuned for short review text)
- ✅ Automatic issue detection (quality, shipping, sizing, safety, pricing & more)
- ✅ Priority scoring to triage the reviews that matter most
- ✅ **Suggested reply templates** tailored to each review's detected issue
- ✅ Trend & word-frequency visualization dashboard
- ✅ Robust CSV upload (handles odd encodings & malformed rows) + a bundled demo dataset
- ✅ CSV / executive-summary export

### Coming Soon
- 🔄 Real-time review monitoring
- 🌍 Multi-language support
- 📱 Mobile application
- 🔗 E-commerce platform integrations

## 🛠️ Technology Stack

| Component | Technology |
|-----------|-----------|
| **Language** | Python 3.12 |
| **Sentiment / NLP** | VADER (`vaderSentiment`), with a TextBlob fallback |
| **Data Processing** | Pandas, NumPy |
| **Web Framework** | Streamlit |
| **Visualization** | Plotly |
| **Cloud** | Streamlit Cloud |
| **Version Control** | Git/GitHub |

## 📁 Project Structure
```
smartreview-ai/
│
├── 📂 src/                   # Application code
│   ├── app.py               # Streamlit UI: dashboard, priority queue, insights, export
│   └── analyzer.py          # ReviewAnalyzer: sentiment, issue detection, priority scoring
│
├── 📊 data/                  # sample / uploads / exports (CSV files gitignored)
│
├── 📚 docs/                  # Product-management documentation
│   ├── week-1/              # Discovery: charter, personas, user stories, research
│   └── week-2/              # Design: PRD, architecture, WBS, timeline, metrics
│
├── 📝 .gitignore
├── 📖 README.md
└── 📦 requirements.txt
```

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- 2GB free disk space
- Internet connection for downloading ML models

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/VenkateshTejas/smartreview-ai.git
cd smartreview-ai

Set up virtual environment

bashpython3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

Install dependencies

bashpip install -r requirements.txt

Download sample data

bash# Option 1: Use Kaggle CLI
kaggle datasets download -d kritanjalijain/amazon-reviews

# Option 2: Download manually from:
# https://www.kaggle.com/datasets/kritanjalijain/amazon-reviews
# Place in data/ directory

Run the application

```bash
streamlit run src/app.py
```

Open browser
Navigate to http://localhost:8501

### ☁️ Deploy for free

- **Streamlit Community Cloud** — main file `src/app.py`, branch `main`.
- **Render** — a [`render.yaml`](render.yaml) blueprint is included. In the Render
  dashboard choose **New → Blueprint** and pick this repo; it builds on the free
  tier. (Free services sleep after ~15 min idle and cold-start on the next visit.)

📈 Usage Guide

Upload Data: Click "Browse files" to upload your CSV
Select Analysis Type: Choose between Quick Analysis or Deep Insights
Configure Settings: Adjust confidence thresholds if needed
Run Analysis: Click "Analyze Reviews"
Export Results: Download insights as CSV or PDF

Input Format
CSV file with columns:

review_text: The review content
rating: Numerical rating (optional)
product_id: Product identifier (optional)

📊 Intended Impact

> ⚠️ This is a portfolio project, not a deployed commercial product. The framing below describes the value it's *designed* to deliver — these are not measured results or real customer outcomes.

The goal is to shrink the gap between "a customer left feedback" and "someone acted on it":

- **Less manual triage** — sentiment, issue category, and priority are computed for every review, so a person works from a ranked shortlist instead of reading everything.
- **Faster response to what matters** — urgent reviews (refund, safety, wrong item) float to the top, each with a ready-to-edit reply.
- **Recurring-issue visibility** — the dashboard shows which categories (quality, shipping, sizing, …) drive negative sentiment, so fixes target the biggest sources rather than one-off complaints.

Actual time or cost savings would depend entirely on a store's review volume and existing workflow.

🎯 Target Users
Primary Users

Small Business Owners: Shopify/Amazon sellers with 100-1,000 products
E-commerce Managers: Managing 500+ reviews monthly
Customer Service Teams: Handling multi-channel feedback

Use Cases

Product quality monitoring
Customer satisfaction tracking
Competitive analysis
Brand reputation management
Product development insights

🗓️ Development Timeline
✅ Week 1: Discovery & Planning (Complete)

Market research and competitive analysis
User personas and journey mapping
Technical requirements gathering
Development environment setup

🔄 Week 2: Design & Architecture (In Progress)

System architecture design
Data flow diagrams
API specifications
UI/UX wireframes

📅 Week 3: Development & Testing (Upcoming)

Core AI implementation
Dashboard development
Integration testing
Performance optimization

📅 Week 4: Deployment & Polish (Upcoming)

Cloud deployment
Documentation completion
Demo video creation
Launch preparation

🧪 Testing

A pytest suite covers the analyzer — sentiment labelling, issue detection across all categories, priority scoring, reply drafting, and edge cases (empty/missing columns).

```bash
pip install -r requirements-dev.txt
pytest
```

📖 Documentation

Project Charter
User Stories
Technical Architecture
API Documentation
Deployment Guide

🤝 Contributing
This is a portfolio project demonstrating PM and technical skills. For questions or suggestions:

Open an issue for bugs or features
Contact via GitHub for collaboration
Fork for your own implementation

📜 License
MIT License - see LICENSE file for details.
👨‍💻 Author
Tejas Venkatesh

Role: Product Manager / Developer
GitHub: @VenkateshTejas
Project Duration: 4 weeks (December 2024)

🙏 Acknowledgments

Data Source: Kaggle Amazon Reviews Dataset
ML Models: Hugging Face Transformers Community
Framework: Streamlit Open Source Project
Icons: Font Awesome

📊 Project Status
Week 1: ████████████████████ 100% Complete
Week 2: ████░░░░░░░░░░░░░░░░ 20% In Progress
Week 3: ░░░░░░░░░░░░░░░░░░░░ 0% Planned
Week 4: ░░░░░░░░░░░░░░░░░░░░ 0% Planned

Overall: ████████░░░░░░░░░░░░ 35% Complete
🔗 Links

Live Demo (Coming Week 4)
Video Walkthrough (Coming Week 4)
Case Study (Coming Week 4)
