import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from datetime import datetime
from final_analyzer import FinalAnalyzer as SimpleAnalyzer

st.set_page_config(page_title="SmartReview-AI", page_icon="📊", layout="wide")

# Initialize session state
if 'df' not in st.session_state:
    st.session_state.df = None
if 'analysis_results' not in st.session_state:
    st.session_state.analysis_results = None
if 'insights' not in st.session_state:
    st.session_state.insights = None
if 'priority_reviews' not in st.session_state:
    st.session_state.priority_reviews = pd.DataFrame()
if 'word_freq' not in st.session_state:
    st.session_state.word_freq = {}
if 'col_info' not in st.session_state:
    st.session_state.col_info = None

# Custom CSS for better UI
st.markdown("""
<style>
    .urgent-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #fee;
        border-left: 4px solid #f44336;
        margin: 1rem 0;
    }
    .success-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #efe;
        border-left: 4px solid #4caf50;
        margin: 1rem 0;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        padding-left: 20px;
        padding-right: 20px;
    }
</style>
""", unsafe_allow_html=True)

st.title("🤖 SmartReview-AI Business Intelligence")
st.markdown("**Transform customer feedback into actionable business decisions**")

# Function to generate sample data
def generate_sample_data():
    np.random.seed(42)
    sample_reviews = [
        "Excellent product! Highly recommend to everyone. Fast shipping too!",
        "Product broke after 2 days. Poor quality. Want a refund immediately.",
        "Good value for money, happy with purchase.",
        "Wrong item delivered. This is not what I ordered. Very disappointed.",
        "Amazing quality! Exceeded my expectations. Will buy again.",
        "Customer service was rude and unhelpful. Product is okay though.",
        "Perfect! Exactly what I needed. Great quality.",
        "Waste of money. Cheap materials. Do not buy this product.",
        "Decent product for the price. Shipping was delayed by a week.",
        "Outstanding quality and fast shipping! Love it!",
        "Defective product. Stopped working after one week. Need refund.",
        "Too small, doesn't fit. Size chart is wrong.",
        "Overpriced for what you get. Not worth the money.",
        "Item never arrived. Still waiting after 3 weeks.",
        "Dangerous product! My child got hurt. This should be recalled.",
        "Great product but package was damaged during shipping.",
        "Not as described on website. False advertising.",
        "Excellent customer service! Product works perfectly.",
        "Cheaply made. Fell apart immediately. Total waste.",
        "Five stars! Best purchase I've made this year!"
    ]
    
    data = {
        'review_text': np.random.choice(sample_reviews, 100),
        'rating': np.random.choice([1, 2, 3, 4, 5], 100, p=[0.15, 0.15, 0.2, 0.25, 0.25]),
        'product': np.random.choice(['Laptop Stand', 'Phone Case', 'Wireless Headphones', 'Tablet Cover', 'USB Cable'], 100),
        'date': pd.date_range('2024-01-01', periods=100),
        'customer_id': [f'CUST{i:04d}' for i in range(100)]
    }
    return pd.DataFrame(data)

# Function to detect review columns
def analyze_columns(df):
    """Detect what columns are available in the dataframe"""
    column_info = {
        'total_columns': len(df.columns),
        'columns': df.columns.tolist(),
        'has_rating': False,
        'has_text': False,
        'text_column': None,
        'rating_column': None,
        'numeric_columns': [],
        'text_columns': []
    }
    
    # Check for rating columns
    rating_keywords = ['rating', 'score', 'stars', 'rate', 'review_rating']
    for col in df.columns:
        if any(keyword in col.lower() for keyword in rating_keywords):
            column_info['has_rating'] = True
            column_info['rating_column'] = col
            break
    
    # Check for text columns
    text_keywords = ['review', 'text', 'comment', 'feedback', 'description', 'content']
    for col in df.columns:
        if any(keyword in col.lower() for keyword in text_keywords):
            column_info['has_text'] = True
            column_info['text_column'] = col
            break
    
    # Find numeric and text columns
    for col in df.columns:
        if df[col].dtype in ['int64', 'float64']:
            column_info['numeric_columns'].append(col)
        elif df[col].dtype == 'object':
            column_info['text_columns'].append(col)
    
    return column_info

# Function to perform analysis
def perform_analysis(df, col_info):
    """Perform analysis and store in session state"""
    analyzer = SimpleAnalyzer()
    
    if col_info['has_text']:
        with st.spinner("🔄 Analyzing reviews for business insights..."):
            st.session_state.analysis_results = analyzer.analyze_text(df, col_info['text_column'])
            st.session_state.word_freq = analyzer.get_word_frequency(df, col_info['text_column'])
            st.session_state.insights = analyzer.get_actionable_insights(
                df, st.session_state.analysis_results, col_info['text_column']
            )
            st.session_state.priority_reviews = analyzer.get_priority_reviews(
                df, st.session_state.analysis_results, col_info['text_column']
            )

# Sidebar for upload
with st.sidebar:
    st.header("📤 Data Upload")
    
    # Option to use sample data or upload
    data_source = st.radio("Choose data source:", ["Upload CSV", "Use Sample Data"])
    
    if data_source == "Upload CSV":
        uploaded_file = st.file_uploader("Upload CSV", type="csv")
        if uploaded_file:
            new_df = pd.read_csv(uploaded_file)
            # Only update if it's a new file
            if st.session_state.df is None or not new_df.equals(st.session_state.df):
                st.session_state.df = new_df
                st.session_state.col_info = analyze_columns(new_df)
                perform_analysis(st.session_state.df, st.session_state.col_info)
            st.success(f"✅ Loaded {len(st.session_state.df)} rows")
    else:
        if st.button("🎲 Generate Sample Data"):
            st.session_state.df = generate_sample_data()
            st.session_state.col_info = analyze_columns(st.session_state.df)
            perform_analysis(st.session_state.df, st.session_state.col_info)
            st.success("✅ Sample data with business scenarios generated!")
    
    if st.session_state.df is not None:
        st.divider()
        st.markdown("### 📊 Quick Stats")
        st.metric("Total Reviews", len(st.session_state.df))
        if 'rating' in st.session_state.df.columns:
            avg_rating = st.session_state.df['rating'].mean()
            st.metric("Average Rating", f"{avg_rating:.2f} ⭐")

# Main area - use session state data
if st.session_state.df is not None:
    df = st.session_state.df
    col_info = st.session_state.col_info
    analysis_results = st.session_state.analysis_results
    insights = st.session_state.insights
    priority_reviews = st.session_state.priority_reviews
    word_freq = st.session_state.word_freq
    
    # Create tabs for different business functions
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🎯 Business Dashboard",
        "🚨 Priority Reviews",
        "💡 Insights & Actions",
        "📊 Analysis Details",
        "💾 Export Results"
    ])
    
    with tab1:
        st.header("Business Overview Dashboard")
        
        # Alert box for urgent items
        if analysis_results and analysis_results['urgent_indices']:
            st.error(f"⚠️ **URGENT**: {len(analysis_results['urgent_indices'])} reviews need immediate attention!")
        
        # Key metrics
        col1, col2, col3, col4 = st.columns(4)
        
        if analysis_results:
            with col1:
                st.metric(
                    "Sentiment Score",
                    f"{(analysis_results['positive_count']/len(df)*100):.1f}%",
                    delta=f"{analysis_results['positive_count']} positive",
                    delta_color="normal"
                )
            with col2:
                st.metric(
                    "Issues Detected",
                    len([i for i in analysis_results['issues_found'] if i]),
                    delta=f"in {len([i for i in analysis_results['issues_found'] if i])} reviews",
                    delta_color="inverse"
                )
            with col3:
                urgent_count = len(analysis_results['urgent_indices'])
                st.metric(
                    "Urgent Reviews",
                    urgent_count,
                    delta="Need response today" if urgent_count > 0 else "All clear",
                    delta_color="inverse"
                )
            with col4:
                response_needed = len([i for i in analysis_results['priority_scores'] if i > 50])
                st.metric(
                    "Response Needed",
                    response_needed,
                    delta=f"{(response_needed/len(df)*100):.1f}% of reviews",
                    delta_color="inverse"
                )
        
        # Charts
        if analysis_results:
            col1, col2 = st.columns(2)
            
            with col1:
                # Issue breakdown
                if analysis_results['issue_summary']:
                    issue_df = pd.DataFrame(
                        list(analysis_results['issue_summary'].items()),
                        columns=['Issue Type', 'Count']
                    )
                    fig = px.bar(
                        issue_df,
                        x='Count',
                        y='Issue Type',
                        orientation='h',
                        title="Issues Requiring Attention",
                        color='Count',
                        color_continuous_scale='Reds'
                    )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No specific issues detected")
            
            with col2:
                # Sentiment pie chart
                sentiment_data = pd.DataFrame({
                    'Sentiment': ['Positive', 'Negative', 'Neutral'],
                    'Count': [
                        analysis_results['positive_count'],
                        analysis_results['negative_count'],
                        analysis_results['neutral_count']
                    ]
                })
                fig = px.pie(
                    sentiment_data,
                    values='Count',
                    names='Sentiment',
                    title="Customer Sentiment",
                    color_discrete_map={
                        'Positive': '#4CAF50',
                        'Negative': '#F44336',
                        'Neutral': '#FFC107'
                    }
                )
                st.plotly_chart(fig, use_container_width=True)
    
    with tab2:
        st.header("🚨 Reviews Requiring Immediate Attention")
        
        if not priority_reviews.empty:
            st.warning(f"Found {len(priority_reviews)} high-priority reviews that need your attention:")
            
            # Filter options
            col1, col2 = st.columns([2, 1])
            with col1:
                issue_filter = st.multiselect(
                    "Filter by issue type:",
                    options=['All'] + list(analysis_results['issue_summary'].keys()) if analysis_results else [],
                    default=['All']
                )
            with col2:
                show_urgent_only = st.checkbox("Show only urgent reviews", value=False, key="urgent_filter")
            
            # Filter priority reviews based on selections
            filtered_reviews = priority_reviews.copy()
            
            if show_urgent_only and analysis_results:
                # Get indices of urgent reviews
                urgent_indices = analysis_results['urgent_indices']
                # Filter to show only urgent reviews
                filtered_reviews = filtered_reviews[filtered_reviews.index.isin(urgent_indices)]
            
            if 'All' not in issue_filter and len(issue_filter) > 0:
                # Filter by selected issues
                filtered_reviews = filtered_reviews[
                    filtered_reviews['issues'].apply(
                        lambda x: any(issue in x for issue in issue_filter)
                    )
                ]
            
            # Display filtered priority reviews
            if not filtered_reviews.empty:
                for idx, row in filtered_reviews.iterrows():
                    priority = row['priority_score']
                    
                    # Color code based on priority
                    if priority >= 80:
                        container = st.error
                        icon = "🔴"
                    elif priority >= 60:
                        container = st.warning
                        icon = "🟡"
                    else:
                        container = st.info
                        icon = "🟢"
                    
                    with container(f"{icon} Priority Score: {priority}/100"):
                        col1, col2 = st.columns([3, 1])
                        
                        with col1:
                            st.write(f"**Customer:** {row.get('customer_id', 'Unknown')}")
                            if 'product' in row:
                                st.write(f"**Product:** {row['product']}")
                            if 'rating' in row:
                                st.write(f"**Rating:** {'⭐' * int(row['rating'])}")
                            st.write(f"**Issues:** {row['issues']}")
                            st.write(f"**Review:** {row[col_info['text_column']]}")
                        
                        with col2:
                            st.write(f"**Sentiment:** {row['sentiment']}")
                            st.write(f"**Date:** {row.get('date', 'Unknown')}")
                            if st.button(f"Mark as Resolved", key=f"resolve_{idx}"):
                                st.success("✓ Marked as resolved")
            else:
                st.info("No reviews match the selected filters")
        else:
            st.info("No priority reviews found")
    
    with tab3:
        st.header("💡 Actionable Business Insights")
        
        if insights:
            # Urgent Actions
            if insights['urgent_actions']:
                st.error("🚨 **URGENT ACTIONS REQUIRED**")
                for action in insights['urgent_actions']:
                    st.write(f"- {action['description']}")
                    st.write(f"  **Action:** {action['action']}")
            
            # Improvement Areas
            if insights['improvement_areas']:
                st.subheader("📈 Top Improvement Areas")
                for area in insights['improvement_areas']:
                    with st.expander(f"{area['issue']} - Affecting {area['impact']}"):
                        st.write(f"**Recommended Action:** {area['action']}")
                        st.write("**Steps to take:**")
                        st.write("1. Review all affected products")
                        st.write("2. Contact relevant department")
                        st.write("3. Implement corrective measures")
                        st.write("4. Follow up with affected customers")
            
            # Recommendations
            if insights['recommendations']:
                st.subheader("💡 Strategic Recommendations")
                for rec in insights['recommendations']:
                    st.info(rec)
            
            # Action Plan Generator
            st.subheader("📋 Generated Action Plan")
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**Immediate (Today):**")
                st.write("☐ Respond to urgent reviews")
                st.write("☐ Contact customers with safety concerns")
                st.write("☐ Review refund requests")
            
            with col2:
                st.write("**This Week:**")
                st.write("☐ Address quality control issues")
                st.write("☐ Review shipping partner performance")
                st.write("☐ Update product descriptions")
    
    with tab4:
        st.header("📊 Detailed Analysis")
        
        if analysis_results:
            # Word frequency
            if word_freq:
                st.subheader("Most Frequently Mentioned Words")
                word_df = pd.DataFrame(list(word_freq.items()), columns=['Word', 'Frequency'])
                fig = px.treemap(
                    word_df,
                    path=['Word'],
                    values='Frequency',
                    title="Word Cloud (Size = Frequency)"
                )
                st.plotly_chart(fig, use_container_width=True)
            
            # Time trend if date column exists
            if 'date' in df.columns and analysis_results:
                st.subheader("Sentiment Trend Over Time")
                trend_df = df.copy()
                trend_df['sentiment'] = analysis_results['sentiments']
                trend_df['date'] = pd.to_datetime(trend_df['date'])
                
                daily_sentiment = trend_df.groupby(['date', 'sentiment']).size().reset_index(name='count')
                fig = px.line(
                    daily_sentiment,
                    x='date',
                    y='count',
                    color='sentiment',
                    title="Sentiment Trends",
                    color_discrete_map={
                        'Positive': '#4CAF50',
                        'Negative': '#F44336',
                        'Neutral': '#FFC107'
                    }
                )
                st.plotly_chart(fig, use_container_width=True)
            
            # Full data view
            st.subheader("All Reviews with Analysis")
            display_df = df.copy()
            display_df['Sentiment'] = analysis_results['sentiments']
            display_df['Priority'] = analysis_results['priority_scores']
            display_df['Issues'] = [', '.join(i) if i else 'None' for i in analysis_results['issues_found']]
            
            st.dataframe(
                display_df.sort_values('Priority', ascending=False),
                use_container_width=True,
                height=400
            )
    
    with tab5:
        st.header("💾 Export Analysis Results")
        
        if analysis_results:
            # Re-initialize analyzer for export
            analyzer = SimpleAnalyzer()
            export_df = analyzer.export_analysis(df, analysis_results)
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                csv = export_df.to_csv(index=False)
                st.download_button(
                    label="📥 Download Full Analysis (CSV)",
                    data=csv,
                    file_name=f"review_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
            
            with col2:
                # Priority reviews only
                if not priority_reviews.empty:
                    priority_csv = priority_reviews.to_csv(index=False)
                    st.download_button(
                        label="🚨 Download Priority Reviews",
                        data=priority_csv,
                        file_name=f"priority_reviews_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv"
                    )
            
            with col3:
                # Summary report
                if insights:
                    summary = f"""
SMARTREVIEW-AI BUSINESS REPORT
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}

EXECUTIVE SUMMARY
Total Reviews Analyzed: {len(df)}
Positive Sentiment: {analysis_results['positive_count']} ({(analysis_results['positive_count']/len(df)*100):.1f}%)
Negative Sentiment: {analysis_results['negative_count']} ({(analysis_results['negative_count']/len(df)*100):.1f}%)
Urgent Reviews: {len(analysis_results['urgent_indices'])}

TOP ISSUES:
{chr(10).join([f"- {issue}: {count} occurrences" for issue, count in list(analysis_results['issue_summary'].items())[:5]])}

RECOMMENDATIONS:
{chr(10).join([f"- {rec}" for rec in insights['recommendations']])}

ACTION ITEMS:
1. Respond to {len(analysis_results['urgent_indices'])} urgent reviews immediately
2. Address top issue: {list(analysis_results['issue_summary'].keys())[0] if analysis_results['issue_summary'] else 'None'}
3. Follow up with {analysis_results['negative_count']} dissatisfied customers
                    """
                    st.download_button(
                        label="📊 Download Executive Summary",
                        data=summary,
                        file_name=f"executive_summary_{datetime.now().strftime('%Y%m%d')}.txt",
                        mime="text/plain"
                    )
            
            st.success("✅ Reports ready for download!")
else:
    st.info("👈 Please upload a CSV file or generate sample data to begin analysis")

# Footer
st.divider()
st.markdown("""
    <div style='text-align: center; color: #888; padding: 20px;'>
        SmartReview-AI v2.0 | Business Intelligence Edition | Built with Streamlit
    </div>
""", unsafe_allow_html=True)