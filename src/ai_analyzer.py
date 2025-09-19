import pandas as pd
import numpy as np
from datetime import datetime

try:
    from transformers import pipeline
    HAS_AI = True
except ImportError:
    HAS_AI = False
    print("AI models not available, using fallback analysis")

class AIAnalyzer:
    """AI-powered analyzer with fallback to keyword-based"""
    
    def __init__(self):
        self.analyzer = None
        self.classifier = None
        
        if HAS_AI:
            try:
                print("Loading AI models... (this may take a minute the first time)")
                self.analyzer = pipeline(
                    "sentiment-analysis",
                    model="nlptown/bert-base-multilingual-uncased-sentiment",
                    device=-1
                )
                print("✅ AI models loaded successfully!")
            except Exception as e:
                print(f"Could not load AI models: {e}")
                print("Using keyword-based fallback")
        else:
            print("Using keyword-based analysis (install transformers for AI)")
    
    def analyze_sentiment_ai(self, text):
        """Use AI for sentiment analysis"""
        if self.analyzer:
            try:
                text = text[:512]
                result = self.analyzer(text)[0]
                label = result['label']
                score = result['score']
                
                if '5' in label or '4' in label:
                    return 'Positive', score
                elif '1' in label or '2' in label:
                    return 'Negative', score
                else:
                    return 'Neutral', score
            except:
                return self.analyze_sentiment_keywords(text)
        else:
            return self.analyze_sentiment_keywords(text)
    
    def analyze_sentiment_keywords(self, text):
        """Fallback keyword-based sentiment"""
        text_lower = str(text).lower()
        
        strong_positive = ['excellent', 'amazing', 'fantastic', 'love', 'perfect', 'best', 
                          'outstanding', 'wonderful', 'great', 'awesome', 'recommend']
        positive = ['good', 'nice', 'helpful', 'useful', 'reliable', 'powerful', 'easy',
                   'satisfied', 'happy', 'pleased', 'works well', 'sturdy']
        
        strong_negative = ['terrible', 'horrible', 'awful', 'hate', 'worst', 'useless',
                          'waste', 'garbage', 'broke', 'defective', 'disappointed']
        negative = ['bad', 'poor', 'cheap', 'slow', 'difficult', 'problem', 'issue',
                   'not worth', 'wouldn\'t recommend', 'returned']
        
        pos_score = 0
        neg_score = 0
        
        for word in strong_positive:
            if word in text_lower:
                pos_score += 2
        for word in positive:
            if word in text_lower:
                pos_score += 1
        
        for word in strong_negative:
            if word in text_lower:
                neg_score += 2
        for word in negative:
            if word in text_lower:
                neg_score += 1
        
        negation_phrases = ['not bad', 'not terrible', 'no problems', 'no issues']
        for phrase in negation_phrases:
            if phrase in text_lower:
                pos_score += 1
        
        if pos_score > neg_score:
            confidence = min(pos_score / (pos_score + neg_score + 1), 0.99)
            return 'Positive', confidence
        elif neg_score > pos_score:
            confidence = min(neg_score / (pos_score + neg_score + 1), 0.99)
            return 'Negative', confidence
        else:
            return 'Neutral', 0.5
    
    def get_word_frequency(self, df, text_column, top_n=10):
        """Get most common words from reviews"""
        if text_column not in df.columns:
            return {}
        
        all_words = []
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 
                     'of', 'with', 'by', 'from', 'is', 'was', 'are', 'were', 'i', 'it', 
                     'this', 'that', 'you', 'your', 'can', 'not', 'don\'t', 'let', 'plus',
                     'they', 'them', 'their', 'what', 'which', 'who', 'when', 'where',
                     'why', 'how', 'all', 'would', 'there', 'been', 'will', 'more',
                     'very', 'most', 'other', 'into', 'just', 'only', 'such', 'than'}
        
        for text in df[text_column].fillna(''):
            words = str(text).lower().split()
            words = [w.strip('.,!?";:()[]{}\'"-') for w in words 
                    if len(w) > 3 and w.strip('.,!?";:()[]{}\'"-').lower() not in stop_words]
            all_words.extend(words)
        
        if all_words:
            word_freq = pd.Series(all_words).value_counts().head(top_n)
            return word_freq.to_dict()
        return {}
    
    def analyze_text(self, df, text_column, use_ai=True):
        """Analyze text with AI or fallback"""
        if text_column not in df.columns:
            return None
        
        analysis = {
            'total_reviews': len(df),
            'avg_length': df[text_column].str.len().mean(),
            'shortest_review': df[text_column].str.len().min(),
            'longest_review': df[text_column].str.len().max(),
            'empty_reviews': df[text_column].isna().sum(),
            'method': 'AI-Powered' if (use_ai and self.analyzer) else 'Keyword-Based'
        }
        
        issue_keywords = {
            'Quality Issues': ['broken', 'defective', 'poor quality', 'cheap', 'flimsy'],
            'Shipping Problems': ['late', 'delayed', 'shipping', 'delivery', 'damaged box'],
            'Customer Service': ['rude', 'unhelpful', 'no response', 'poor service'],
            'Wrong Product': ['wrong', 'different', 'not as described', 'mistake'],
            'Value/Pricing': ['expensive', 'overpriced', 'not worth', 'waste of money'],
        }
        
        urgent_keywords = ['refund', 'return', 'dangerous', 'injured', 'safety']
        
        sentiments = []
        confidences = []
        issues_found = []
        urgent_reviews = []
        review_priorities = []
        
        for idx, row in df.iterrows():
            text = str(row[text_column])
            text_lower = text.lower()
            
            if use_ai and self.analyzer:
                sentiment, confidence = self.analyze_sentiment_ai(text)
            else:
                sentiment, confidence = self.analyze_sentiment_keywords(text)
            
            sentiments.append(sentiment)
            confidences.append(confidence)
            
            if sentiment == 'Negative':
                priority_score = 50
            elif sentiment == 'Neutral':
                priority_score = 25
            else:
                priority_score = 0
            
            review_issues = []
            for issue_type, keywords in issue_keywords.items():
                if any(keyword in text_lower for keyword in keywords):
                    review_issues.append(issue_type)
                    priority_score += 20
            
            issues_found.append(review_issues)
            
            is_urgent = any(word in text_lower for word in urgent_keywords)
            if is_urgent:
                urgent_reviews.append(idx)
                priority_score += 30
            
            if 'rating' in row:
                rating_value = row.get('rating', 3)
                if rating_value <= 2:
                    priority_score += 20
            
            review_priorities.append(min(priority_score, 100))
        
        analysis['sentiments'] = sentiments
        analysis['confidences'] = confidences
        analysis['avg_confidence'] = np.mean(confidences)
        analysis['positive_count'] = sentiments.count('Positive')
        analysis['negative_count'] = sentiments.count('Negative')
        analysis['neutral_count'] = sentiments.count('Neutral')
        analysis['issues_found'] = issues_found
        analysis['urgent_indices'] = urgent_reviews
        analysis['priority_scores'] = review_priorities
        
        issue_summary = {}
        for issues_list in issues_found:
            for issue in issues_list:
                issue_summary[issue] = issue_summary.get(issue, 0) + 1
        analysis['issue_summary'] = issue_summary
        
        return analysis
    
    def get_actionable_insights(self, df, analysis_results, text_column):
        """Generate specific action items"""
        if not analysis_results:
            return None
        
        insights = {
            'urgent_actions': [],
            'improvement_areas': [],
            'recommendations': [],
            'confidence_level': analysis_results.get('avg_confidence', 0)
        }
        
        if analysis_results.get('avg_confidence', 0) < 0.6:
            insights['recommendations'].append(
                "⚠️ Low confidence scores - consider manual review"
            )
        
        if analysis_results['urgent_indices']:
            insights['urgent_actions'].append({
                'action': 'IMMEDIATE ATTENTION REQUIRED',
                'count': len(analysis_results['urgent_indices']),
                'description': f"{len(analysis_results['urgent_indices'])} reviews need immediate attention"
            })
        
        if analysis_results['issue_summary']:
            sorted_issues = sorted(analysis_results['issue_summary'].items(), 
                                 key=lambda x: x[1], reverse=True)
            for issue, count in sorted_issues[:3]:
                percentage = (count / analysis_results['total_reviews']) * 100
                insights['improvement_areas'].append({
                    'issue': issue,
                    'impact': f"{count} reviews ({percentage:.1f}%)",
                    'action': self.get_action_for_issue(issue)
                })
        
        negative_pct = (analysis_results['negative_count'] / analysis_results['total_reviews']) * 100
        if negative_pct > 30:
            insights['recommendations'].append("🚨 High negative sentiment - Review product quality")
        if 'Quality Issues' in analysis_results.get('issue_summary', {}):
            insights['recommendations'].append("🔧 Quality complaints detected - Check manufacturing")
        if 'Shipping Problems' in analysis_results.get('issue_summary', {}):
            insights['recommendations'].append("📦 Shipping issues - Review logistics")
        
        return insights
    
    def get_action_for_issue(self, issue_type):
        """Get specific action for each issue"""
        actions = {
            'Quality Issues': "Review manufacturing QC process",
            'Shipping Problems': "Contact logistics partner",
            'Customer Service': "Schedule team training",
            'Wrong Product': "Audit fulfillment process",
            'Value/Pricing': "Analyze competitor pricing"
        }
        return actions.get(issue_type, "Investigate and create action plan")
    
    def get_priority_reviews(self, df, analysis_results, text_column, top_n=10):
        """Get priority reviews"""
        if not analysis_results or 'priority_scores' not in analysis_results:
            return pd.DataFrame()
        
        priority_df = df.copy()
        priority_df['priority_score'] = analysis_results['priority_scores']
        priority_df['sentiment'] = analysis_results['sentiments']
        priority_df['confidence'] = analysis_results.get('confidences', [0.5] * len(df))
        priority_df['issues'] = [', '.join(issues) if issues else 'None' 
                                 for issues in analysis_results['issues_found']]
        
        return priority_df.sort_values('priority_score', ascending=False).head(top_n)
    
    def export_analysis(self, df, analysis_results):
        """Export analysis results"""
        export_data = df.copy()
        
        if analysis_results:
            export_data['sentiment'] = analysis_results['sentiments']
            export_data['confidence'] = analysis_results.get('confidences', [0] * len(df))
            export_data['priority_score'] = analysis_results['priority_scores']
            export_data['issues'] = [', '.join(i) if i else 'None' 
                                    for i in analysis_results['issues_found']]
            export_data['analysis_method'] = analysis_results.get('method', 'Unknown')
        
        export_data['analysis_date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        return export_data