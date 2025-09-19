import pandas as pd
import numpy as np
from datetime import datetime
from textblob import TextBlob

class FinalAnalyzer:
    """Sentiment analyzer using TextBlob - works well for product reviews"""
    
    def __init__(self):
        print("Analyzer initialized with TextBlob sentiment analysis")
    
    def analyze_sentiment(self, text):
        """Analyze sentiment using TextBlob"""
        try:
            blob = TextBlob(str(text))
            polarity = blob.sentiment.polarity  # -1 to 1
            subjectivity = blob.sentiment.subjectivity  # 0 to 1
            
            # Adjust thresholds for product reviews
            if polarity > 0.1:
                confidence = min(0.6 + abs(polarity) * 0.3, 0.95)
                return 'Positive', confidence
            elif polarity < -0.1:
                confidence = min(0.6 + abs(polarity) * 0.3, 0.95)
                return 'Negative', confidence
            else:
                return 'Neutral', 0.5
        except:
            return 'Neutral', 0.5
    
    def analyze_text(self, df, text_column):
        """Main analysis method"""
        if text_column not in df.columns:
            return None
        
        analysis = {
            'total_reviews': len(df),
            'avg_length': df[text_column].str.len().mean(),
            'shortest_review': df[text_column].str.len().min(),
            'longest_review': df[text_column].str.len().max(),
            'empty_reviews': df[text_column].isna().sum()
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
            
            # Calculate priority
            priority_score = 0
            if sentiment == 'Negative':
                priority_score = 50
            elif sentiment == 'Neutral':
                priority_score = 25
            
            # Detect issues
            review_issues = []
            
            # Quality issues
            if any(word in text_lower for word in ['broke', 'broken', 'defective', 'stopped working', 'poor quality']):
                review_issues.append('Quality Issues')
                priority_score += 20
            
            # Shipping problems
            if any(phrase in text_lower for phrase in ['never arrived', 'lost package', 'damaged in shipping', 'wrong item']):
                review_issues.append('Shipping Problems')
                priority_score += 20
            
            # Customer service
            if any(phrase in text_lower for phrase in ['poor service', 'rude', 'unhelpful', 'no response']):
                review_issues.append('Customer Service')
                priority_score += 15
            
            # Value/Pricing
            if any(phrase in text_lower for phrase in ['overpriced', 'not worth', 'waste of money', 'too expensive']):
                review_issues.append('Value/Pricing')
                priority_score += 10
            
            issues_found.append(review_issues)
            
            # Check for urgent keywords
            if any(word in text_lower for word in ['refund', 'return', 'lawsuit', 'dangerous', 'injured']):
                urgent_reviews.append(idx)
                priority_score += 30
            
            # Factor in rating if available
            if 'rating' in row:
                rating = row.get('rating', 3)
                if rating <= 2:
                    priority_score += 20
                elif rating == 3:
                    priority_score += 10
            
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
        """Get most common words from reviews"""
        if text_column not in df.columns:
            return {}
        
        all_words = []
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'is', 'was', 'are', 'were', 'be', 'been',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
            'should', 'may', 'might', 'must', 'can', 'this', 'that', 'these',
            'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'them', 'their',
            'what', 'which', 'who', 'when', 'where', 'why', 'how', 'all', 'each',
            'every', 'both', 'few', 'more', 'most', 'other', 'some', 'such', 'only',
            'own', 'same', 'so', 'than', 'too', 'very', 'just', 'your', 'my'
        }
        
        for text in df[text_column].fillna(''):
            words = str(text).lower().split()
            words = [w.strip('.,!?";:()[]{}\'"-') for w in words 
                    if len(w) > 3 and w.strip('.,!?";:()[]{}\'"-').lower() not in stop_words]
            all_words.extend(words)
        
        if all_words:
            word_freq = pd.Series(all_words).value_counts().head(top_n)
            return word_freq.to_dict()
        return {}
    
    def get_actionable_insights(self, df, analysis_results, text_column):
        """Generate business insights"""
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
        
        # Recommendations based on sentiment
        negative_pct = (analysis_results['negative_count'] / analysis_results['total_reviews']) * 100
        if negative_pct > 30:
            insights['recommendations'].append("🚨 High negative sentiment - Review product/service quality")
        if 'Quality Issues' in analysis_results.get('issue_summary', {}):
            insights['recommendations'].append("🔧 Multiple quality complaints - Check manufacturing")
        if 'Shipping Problems' in analysis_results.get('issue_summary', {}):
            insights['recommendations'].append("📦 Shipping issues detected - Review logistics")
        
        return insights
    
    def get_action_for_issue(self, issue_type):
        """Get specific action for each issue type"""
        actions = {
            'Quality Issues': "Review manufacturing QC process and supplier standards",
            'Shipping Problems': "Contact logistics partner and review packaging",
            'Customer Service': "Schedule team training and review response protocols",
            'Wrong Product': "Audit fulfillment process and product listings",
            'Value/Pricing': "Analyze competitor pricing and value proposition",
            'Sizing Issues': "Update size charts and product descriptions"
        }
        return actions.get(issue_type, "Investigate and create action plan")
    
    def get_priority_reviews(self, df, analysis_results, text_column, top_n=10):
        """Get high-priority reviews"""
        if not analysis_results or 'priority_scores' not in analysis_results:
            return pd.DataFrame()
        
        priority_df = df.copy()
        priority_df['priority_score'] = analysis_results['priority_scores']
        priority_df['sentiment'] = analysis_results['sentiments']
        priority_df['issues'] = [', '.join(issues) if issues else 'None' 
                                 for issues in analysis_results['issues_found']]
        
        return priority_df.sort_values('priority_score', ascending=False).head(top_n)
    
    def export_analysis(self, df, analysis_results):
        """Prepare data for export"""
        export_data = df.copy()
        
        if analysis_results:
            export_data['predicted_sentiment'] = analysis_results['sentiments']
            export_data['priority_score'] = analysis_results['priority_scores']
            export_data['issues_detected'] = [', '.join(issues) if issues else 'None' 
                                             for issues in analysis_results['issues_found']]
        
        export_data['analysis_date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        return export_data