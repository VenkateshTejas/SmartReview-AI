import pandas as pd
import numpy as np
from datetime import datetime

class SimpleAnalyzer:
    """Business-focused analyzer for actionable insights"""
    
    def analyze_text(self, df, text_column):
        """Analyze text and identify business priorities"""
        if text_column not in df.columns:
            return None
        
        analysis = {
            'total_reviews': len(df),
            'avg_length': df[text_column].str.len().mean(),
            'shortest_review': df[text_column].str.len().min(),
            'longest_review': df[text_column].str.len().max(),
            'empty_reviews': df[text_column].isna().sum()
        }
        
        # Keywords for different business aspects
        positive_words = ['good', 'great', 'excellent', 'amazing', 'love', 'perfect', 'best', 'awesome', 'fantastic', 'wonderful', 'recommend']
        negative_words = ['bad', 'terrible', 'awful', 'horrible', 'worst', 'hate', 'poor', 'disappointing', 'waste', 'broken', 'never', 'don\'t']
        
        # Issue categories that businesses care about
        issue_keywords = {
            'Quality Issues': ['broken', 'defective', 'poor quality', 'cheap', 'flimsy', 'fell apart', 'stopped working'],
            'Shipping Problems': ['late', 'delayed', 'shipping', 'delivery', 'never arrived', 'damaged box', 'slow'],
            'Customer Service': ['rude', 'unhelpful', 'no response', 'poor service', 'customer service', 'support'],
            'Wrong Product': ['wrong', 'different', 'not as described', 'not what I ordered', 'mistake'],
            'Value/Pricing': ['expensive', 'overpriced', 'not worth', 'waste of money', 'rip off'],
            'Sizing Issues': ['too small', 'too large', 'doesn\'t fit', 'size', 'bigger', 'smaller']
        }
        
        # Urgent keywords that need immediate attention
        urgent_keywords = ['refund', 'return', 'lawsuit', 'dangerous', 'injured', 'sick', 'hospital', 'fire', 'burn', 'cut']
        
        sentiments = []
        issues_found = []
        urgent_reviews = []
        review_priorities = []
        
        for idx, text in enumerate(df[text_column].fillna('')):
            text_lower = str(text).lower()
            
            # Sentiment analysis
            pos_count = sum(word in text_lower for word in positive_words)
            neg_count = sum(word in text_lower for word in negative_words)
            
            if pos_count > neg_count:
                sentiments.append('Positive')
                priority_score = 0
            elif neg_count > pos_count:
                sentiments.append('Negative')
                priority_score = 50
            else:
                sentiments.append('Neutral')
                priority_score = 25
            
            # Check for issues
            review_issues = []
            for issue_type, keywords in issue_keywords.items():
                if any(keyword in text_lower for keyword in keywords):
                    review_issues.append(issue_type)
                    priority_score += 20
            
            issues_found.append(review_issues)
            
            # Check for urgent keywords
            is_urgent = any(word in text_lower for word in urgent_keywords)
            if is_urgent:
                urgent_reviews.append(idx)
                priority_score += 30
            
            # Add rating to priority if available
            if 'rating' in df.columns:
                rating_value = df.iloc[idx].get('rating', 3)
                if rating_value <= 2:
                    priority_score += 20
                elif rating_value == 3:
                    priority_score += 10
            
            review_priorities.append(min(priority_score, 100))
        
        analysis['sentiments'] = sentiments
        analysis['positive_count'] = sentiments.count('Positive')
        analysis['negative_count'] = sentiments.count('Negative')
        analysis['neutral_count'] = sentiments.count('Neutral')
        analysis['issues_found'] = issues_found
        analysis['urgent_indices'] = urgent_reviews
        analysis['priority_scores'] = review_priorities
        
        # Calculate issue summary
        issue_summary = {}
        for issues_list in issues_found:
            for issue in issues_list:
                issue_summary[issue] = issue_summary.get(issue, 0) + 1
        analysis['issue_summary'] = issue_summary
        
        return analysis
    
    def get_actionable_insights(self, df, analysis_results, text_column):
        """Generate specific action items for business owners"""
        if not analysis_results:
            return None
        
        insights = {
            'urgent_actions': [],
            'improvement_areas': [],
            'positive_highlights': [],
            'recommendations': []
        }
        
        # Identify urgent actions
        if analysis_results['urgent_indices']:
            insights['urgent_actions'].append({
                'action': 'IMMEDIATE ATTENTION REQUIRED',
                'count': len(analysis_results['urgent_indices']),
                'description': f"{len(analysis_results['urgent_indices'])} reviews mention refunds, returns, or safety issues"
            })
        
        # Identify top problems
        if analysis_results['issue_summary']:
            sorted_issues = sorted(analysis_results['issue_summary'].items(), key=lambda x: x[1], reverse=True)
            for issue, count in sorted_issues[:3]:
                percentage = (count / analysis_results['total_reviews']) * 100
                insights['improvement_areas'].append({
                    'issue': issue,
                    'impact': f"{count} reviews ({percentage:.1f}%)",
                    'action': self.get_action_for_issue(issue)
                })
        
        # Calculate response recommendations
        negative_pct = (analysis_results['negative_count'] / analysis_results['total_reviews']) * 100
        if negative_pct > 30:
            insights['recommendations'].append("🚨 High negative sentiment - Consider product quality review")
        if 'Quality Issues' in analysis_results['issue_summary']:
            insights['recommendations'].append("🔧 Multiple quality complaints - Check with manufacturing/suppliers")
        if 'Shipping Problems' in analysis_results['issue_summary']:
            insights['recommendations'].append("📦 Shipping issues detected - Review logistics partner performance")
        
        return insights
    
    def get_action_for_issue(self, issue_type):
        """Get specific action for each issue type"""
        actions = {
            'Quality Issues': "Review manufacturing QC process and supplier standards",
            'Shipping Problems': "Contact logistics partner and review packaging",
            'Customer Service': "Schedule team training and review response templates",
            'Wrong Product': "Audit fulfillment process and product listings",
            'Value/Pricing': "Analyze competitor pricing and value proposition",
            'Sizing Issues': "Update size charts and product descriptions"
        }
        return actions.get(issue_type, "Investigate and create action plan")
    
    def get_priority_reviews(self, df, analysis_results, text_column, top_n=10):
        """Get reviews that need immediate attention"""
        if not analysis_results or 'priority_scores' not in analysis_results:
            return pd.DataFrame()
        
        # Add priority scores to dataframe
        priority_df = df.copy()
        priority_df['priority_score'] = analysis_results['priority_scores']
        priority_df['sentiment'] = analysis_results['sentiments']
        priority_df['issues'] = [', '.join(issues) if issues else 'None' for issues in analysis_results['issues_found']]
        
        # Sort by priority
        priority_df = priority_df.sort_values('priority_score', ascending=False)
        
        return priority_df.head(top_n)
    
    def get_word_frequency(self, df, text_column, top_n=10):
        """Get most common words"""
        if text_column not in df.columns:
            return []
        
        all_words = []
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'from', 'is', 'was', 'are', 'were', 'i', 'it', 'this', 'that'}
        
        for text in df[text_column].fillna(''):
            words = str(text).lower().split()
            words = [w.strip('.,!?";') for w in words if len(w) > 3 and w not in stop_words]
            all_words.extend(words)
        
        word_freq = pd.Series(all_words).value_counts().head(top_n)
        return word_freq.to_dict()
    
    def export_analysis(self, df, analysis_results):
        """Prepare data for export"""
        export_data = df.copy()
        
        if analysis_results:
            if 'sentiments' in analysis_results:
                export_data['predicted_sentiment'] = analysis_results['sentiments']
            if 'priority_scores' in analysis_results:
                export_data['priority_score'] = analysis_results['priority_scores']
            if 'issues_found' in analysis_results:
                export_data['issues_detected'] = [', '.join(issues) if issues else 'None' for issues in analysis_results['issues_found']]
        
        export_data['analysis_date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        return export_data