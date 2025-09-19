import pandas as pd
import numpy as np
from datetime import datetime

# Try to import VADER, fall back if not available
try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    HAS_VADER = True
except ImportError:
    HAS_VADER = False

class BetterAnalyzer:
    """Better sentiment analyzer with VADER or improved keywords"""
    
    def __init__(self):
        if HAS_VADER:
            self.vader = SentimentIntensityAnalyzer()
        else:
            self.vader = None
    
    def analyze_sentiment(self, text):
        """Analyze sentiment with VADER or fallback"""
        if self.vader:
            scores = self.vader.polarity_scores(text)
            if scores['compound'] >= 0.05:
                return 'Positive', abs(scores['compound'])
            elif scores['compound'] <= -0.05:
                return 'Negative', abs(scores['compound'])
            else:
                return 'Neutral', 0.5
        else:
            # Fallback to improved keyword analysis
            return self.analyze_sentiment_keywords(text)
    
    def analyze_sentiment_keywords(self, text):
        """Better keyword-based sentiment"""
        text_lower = str(text).lower()
        
        # Positive indicators
        pos_score = 0
        if any(word in text_lower for word in ['great', 'excellent', 'love', 'perfect', 'amazing', 'best']):
            pos_score += 2
        if any(word in text_lower for word in ['good', 'nice', 'helpful', 'easy', 'works', 'recommend']):
            pos_score += 1
        if len(text) > 200 and 'features' in text_lower:  # Long descriptive reviews
            pos_score += 1
        
        # Negative indicators - ONLY real problems
        neg_score = 0
        if any(word in text_lower for word in ['broke', 'defective', 'terrible', 'waste', 'horrible']):
            neg_score += 2
        if any(word in text_lower for word in ['disappointed', 'poor', 'bad', 'returned']):
            neg_score += 1
        
        if pos_score > neg_score:
            return 'Positive', 0.7
        elif neg_score > pos_score:
            return 'Negative', 0.7
        else:
            return 'Neutral', 0.5
    
    def analyze_text(self, df, text_column):
        """Main analysis method - required by app.py"""
        if text_column not in df.columns:
            return None
        
        analysis = {
            'total_reviews': len(df),
            'avg_length': df[text_column].str.len().mean(),
            'shortest_review': df[text_column].str.len().min(),
            'longest_review': df[text_column].str.len().max(),
            'empty_reviews': df[text_column].isna().sum(),
            'method': 'VADER' if self.vader else 'Improved Keywords'
        }
        
        sentiments = []
        issues_found = []
        urgent_reviews = []
        review_priorities = []
        
        for idx, row in df.iterrows():
            text = str(row[text_column])
            text_lower = text.lower()
            
            # Get sentiment
            sentiment, confidence = self.analyze_sentiment(text)
            sentiments.append(sentiment)
            
            # Priority scoring
            priority_score = 0
            if sentiment == 'Negative':
                priority_score = 50
            elif sentiment == 'Neutral':
                priority_score = 25
            
            # Detect REAL issues only
            review_issues = []
            
            # Only flag actual quality problems
            if any(word in text_lower for word in ['broke', 'broken', 'defective', 'stopped working']):
                review_issues.append('Quality Issues')
                priority_score += 20
            
            # Only flag actual wrong products
            if any(phrase in text_lower for phrase in ['wrong item', 'not what i ordered', 'different product than']):
                review_issues.append('Wrong Product')
                priority_score += 20
            
            # Only flag real shipping problems
            if any(phrase in text_lower for phrase in ['never arrived', 'lost package', 'damaged in shipping']):
                review_issues.append('Shipping Problems')
                priority_score += 20
            
            if any(phrase in text_lower for phrase in ['rude', 'unhelpful', 'poor service']):
                review_issues.append('Customer Service')
                priority_score += 15
            
            issues_found.append(review_issues)
            
            # Check for urgent keywords
            if any(word in text_lower for word in ['refund', 'return', 'lawyer', 'dangerous']):
                urgent_reviews.append(idx)
                priority_score += 30
            
            # Rating influence
            if 'rating' in row:
                if row['rating'] <= 2:
                    priority_score += 20
            
            review_priorities.append(min(priority_score, 100))
        
        analysis['sentiments'] = sentiments
        analysis['positive_count'] = sentiments.count('Positive')
        analysis['negative_count'] = sentiments.count('Negative')
        analysis['neutral_count'] = sentiments.count('Neutral')
        analysis['issues_found'] = issues_found
        analysis['urgent_indices'] = urgent_reviews
        analysis['priority_scores'] = review_priorities
        
        # Issue summary
        issue_summary = {}
        for issues_list in issues_found:
            for issue in issues_list:
                issue_summary[issue] = issue_summary.get(issue, 0) + 1
        analysis['issue_summary'] = issue_summary
        
        return analysis
    
    def get_word_frequency(self, df, text_column, top_n=10):
        """Get most common words - required by app.py"""
        if text_column not in df.columns:
            return {}
        
        all_words = []
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 
                     'of', 'with', 'by', 'from', 'is', 'was', 'are', 'were', 'it', 'this', 
                     'that', 'these', 'they', 'them', 'your', 'you', 'can', 'will'}
        
        for text in df[text_column].fillna(''):
            words = str(text).lower().split()
            words = [w.strip('.,!?";:()[]{}') for w in words 
                    if len(w) > 3 and w.lower() not in stop_words]
            all_words.extend(words)
        
        if all_words:
            word_freq = pd.Series(all_words).value_counts().head(top_n)
            return word_freq.to_dict()
        return {}
    
    def get_actionable_insights(self, df, analysis_results, text_column):
        """Generate business insights - required by app.py"""
        if not analysis_results:
            return None
        
        insights = {
            'urgent_actions': [],
            'improvement_areas': [],
            'recommendations': []
        }
        
        # Urgent actions
        if analysis_results['urgent_indices']:
            insights['urgent_actions'].append({
                'action': 'IMMEDIATE ATTENTION REQUIRED',
                'count': len(analysis_results['urgent_indices']),
                'description': f"{len(analysis_results['urgent_indices'])} reviews need immediate response"
            })
        
        # Top issues
        if analysis_results.get('issue_summary'):
            sorted_issues = sorted(analysis_results['issue_summary'].items(), 
                                 key=lambda x: x[1], reverse=True)
            for issue, count in sorted_issues[:3]:
                percentage = (count / analysis_results['total_reviews']) * 100
                insights['improvement_areas'].append({
                    'issue': issue,
                    'impact': f"{count} reviews ({percentage:.1f}%)",
                    'action': self.get_action_for_issue(issue)
                })
        
        # Recommendations
        negative_pct = (analysis_results['negative_count'] / analysis_results['total_reviews']) * 100
        if negative_pct > 30:
            insights['recommendations'].append("🚨 High negative sentiment - Review product quality")
        if 'Quality Issues' in analysis_results.get('issue_summary', {}):
            insights['recommendations'].append("🔧 Quality issues detected - Check manufacturing")
        
        return insights
    
    def get_action_for_issue(self, issue_type):
        """Get specific action for each issue"""
        actions = {
            'Quality Issues': "Review manufacturing QC process and supplier quality",
            'Shipping Problems': "Contact logistics partner and review packaging",
            'Customer Service': "Schedule team training and review protocols",
            'Wrong Product': "Audit fulfillment process and product listings",
            'Value/Pricing': "Analyze competitor pricing and value proposition"
        }
        return actions.get(issue_type, "Investigate and create action plan")
    
    def get_priority_reviews(self, df, analysis_results, text_column, top_n=10):
        """Get priority reviews - required by app.py"""
        if not analysis_results or 'priority_scores' not in analysis_results:
            return pd.DataFrame()
        
        priority_df = df.copy()
        priority_df['priority_score'] = analysis_results['priority_scores']
        priority_df['sentiment'] = analysis_results['sentiments']
        priority_df['issues'] = [', '.join(issues) if issues else 'None' 
                                 for issues in analysis_results['issues_found']]
        
        return priority_df.sort_values('priority_score', ascending=False).head(top_n)
    
    def export_analysis(self, df, analysis_results):
        """Export analysis - required by app.py"""
        export_data = df.copy()
        
        if analysis_results:
            export_data['sentiment'] = analysis_results['sentiments']
            export_data['priority_score'] = analysis_results['priority_scores']
            export_data['issues'] = [', '.join(i) if i else 'None' 
                                    for i in analysis_results['issues_found']]
        
        export_data['analysis_date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        return export_data