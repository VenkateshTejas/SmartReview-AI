import pandas as pd
import numpy as np
from datetime import datetime
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import warnings
warnings.filterwarnings('ignore')

class ProfessionalAnalyzer:
    """Production-grade sentiment analyzer using state-of-the-art models"""
    
    def __init__(self, model_name="cardiffnlp/twitter-roberta-base-sentiment-latest"):
        """
        Initialize with a proven sentiment analysis model.
        Alternative models you can try:
        - "nlptown/bert-base-multilingual-uncased-sentiment" (5-star ratings)
        - "distilbert-base-uncased-finetuned-sst-2-english" (simpler, faster)
        - "cardiffnlp/twitter-roberta-base-sentiment-latest" (robust, handles many cases)
        """
        print(f"Loading professional AI model: {model_name}")
        print("This may take a minute on first run...")
        
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.model = AutoModelForSequenceClassification.from_pretrained(model_name)
            self.model.eval()  # Set to evaluation mode
            
            # Map model outputs to our sentiment labels
            if "nlptown" in model_name:
                # This model outputs star ratings 1-5
                self.label_mapping = {
                    0: 'Negative',  # 1 star
                    1: 'Negative',  # 2 stars
                    2: 'Neutral',   # 3 stars
                    3: 'Positive',  # 4 stars
                    4: 'Positive'   # 5 stars
                }
            elif "cardiffnlp" in model_name:
                # This model outputs negative/neutral/positive
                self.label_mapping = {
                    0: 'Negative',
                    1: 'Neutral',
                    2: 'Positive'
                }
            else:
                # Default binary classification
                self.label_mapping = {
                    0: 'Negative',
                    1: 'Positive'
                }
            
            print("✅ AI model loaded successfully!")
            self.model_loaded = True
            
        except Exception as e:
            print(f"Error loading model: {e}")
            print("Falling back to rule-based analysis")
            self.model_loaded = False
    
    def analyze_sentiment_with_ai(self, text):
        """Use transformer model for accurate sentiment analysis"""
        if not self.model_loaded:
            return self.fallback_analysis(text)
        
        try:
            # Truncate text to model's max length (usually 512 tokens)
            text = text[:1500]  # Rough character limit
            
            # Tokenize
            inputs = self.tokenizer(
                text, 
                return_tensors="pt",
                truncation=True,
                padding=True,
                max_length=512
            )
            
            # Get prediction
            with torch.no_grad():
                outputs = self.model(**inputs)
                predictions = torch.nn.functional.softmax(outputs.logits, dim=-1)
                predicted_class = torch.argmax(predictions, dim=-1).item()
                confidence = predictions[0][predicted_class].item()
            
            # Map to our sentiment labels
            sentiment = self.label_mapping.get(predicted_class, 'Neutral')
            
            return sentiment, confidence
            
        except Exception as e:
            print(f"Error in AI analysis: {e}")
            return self.fallback_analysis(text)
    
    def fallback_analysis(self, text):
        """Simple fallback if AI model fails"""
        text_lower = text.lower()
        
        # Clear negative indicators
        if any(word in text_lower for word in [
            'terrible', 'horrible', 'awful', 'worst', 'broken',
            'defective', 'disappointed', 'waste of money', 'do not buy'
        ]):
            return 'Negative', 0.7
        
        # Clear positive indicators
        if any(word in text_lower for word in [
            'excellent', 'amazing', 'perfect', 'love', 'best',
            'highly recommend', 'fantastic', 'outstanding'
        ]):
            return 'Positive', 0.7
        
        # Default to neutral for ambiguous cases
        return 'Neutral', 0.5
    
    def detect_issues(self, text):
        """Detect specific business-relevant issues in reviews"""
        text_lower = text.lower()
        issues = []
        
        # Define issue patterns with high precision
        issue_patterns = {
            'Quality Issues': [
                'broke', 'broken', 'defective', 'stopped working',
                'fell apart', 'poor quality', 'cheap quality',
                'doesn\'t work', 'malfunction'
            ],
            'Shipping Problems': [
                'never arrived', 'never received', 'lost package',
                'damaged in shipping', 'wrong address', 'delayed shipping',
                'still waiting', 'hasn\'t arrived'
            ],
            'Wrong Product': [
                'wrong item', 'wrong product', 'not what i ordered',
                'different than described', 'not as advertised',
                'sent the wrong', 'incorrect item'
            ],
            'Customer Service': [
                'rude customer service', 'unhelpful support',
                'no response from seller', 'ignored my emails',
                'terrible service', 'poor communication'
            ],
            'Safety Concerns': [
                'dangerous', 'unsafe', 'hazard', 'injury',
                'caught fire', 'electric shock', 'toxic'
            ]
        }
        
        for issue_type, patterns in issue_patterns.items():
            if any(pattern in text_lower for pattern in patterns):
                issues.append(issue_type)
        
        return issues
    
    def analyze_text(self, df, text_column):
        """Main analysis method for the dataframe"""
        if text_column not in df.columns:
            return None
        
        print(f"Analyzing {len(df)} reviews with AI...")
        
        analysis = {
            'total_reviews': len(df),
            'avg_length': df[text_column].str.len().mean(),
            'shortest_review': df[text_column].str.len().min(),
            'longest_review': df[text_column].str.len().max(),
            'empty_reviews': df[text_column].isna().sum(),
            'method': 'Transformer AI Model' if self.model_loaded else 'Rule-Based'
        }
        
        sentiments = []
        confidences = []
        issues_found = []
        urgent_reviews = []
        review_priorities = []
        
        # Process each review
        for idx, row in df.iterrows():
            text = str(row[text_column])
            
            # Get AI sentiment
            sentiment, confidence = self.analyze_sentiment_with_ai(text)
            sentiments.append(sentiment)
            confidences.append(confidence)
            
            # Detect issues
            issues = self.detect_issues(text)
            issues_found.append(issues)
            
            # Calculate priority score
            priority = 0
            
            # Sentiment-based priority
            if sentiment == 'Negative':
                priority = 50
            elif sentiment == 'Neutral':
                priority = 20
            
            # Issue-based priority
            if 'Safety Concerns' in issues:
                priority += 50  # Highest priority
                urgent_reviews.append(idx)
            elif 'Quality Issues' in issues:
                priority += 30
            elif issues:  # Any other issues
                priority += 20
            
            # Check for urgent keywords
            urgent_keywords = ['refund', 'return', 'lawyer', 'sue', 'legal action']
            if any(word in text.lower() for word in urgent_keywords):
                urgent_reviews.append(idx) if idx not in urgent_reviews else None
                priority += 25
            
            # Factor in rating if available
            if 'rating' in row and pd.notna(row['rating']):
                if row['rating'] <= 2:
                    priority += 15
                elif row['rating'] <= 3:
                    priority += 5
            
            review_priorities.append(min(priority, 100))
        
        # Compile results
        analysis['sentiments'] = sentiments
        analysis['confidences'] = confidences
        analysis['avg_confidence'] = np.mean(confidences) if confidences else 0
        analysis['positive_count'] = sentiments.count('Positive')
        analysis['negative_count'] = sentiments.count('Negative')
        analysis['neutral_count'] = sentiments.count('Neutral')
        analysis['issues_found'] = issues_found
        analysis['urgent_indices'] = list(set(urgent_reviews))
        analysis['priority_scores'] = review_priorities
        
        # Issue summary
        issue_summary = {}
        for issues_list in issues_found:
            for issue in issues_list:
                issue_summary[issue] = issue_summary.get(issue, 0) + 1
        analysis['issue_summary'] = issue_summary
        
        print(f"✅ Analysis complete: {analysis['positive_count']} positive, "
              f"{analysis['negative_count']} negative, {analysis['neutral_count']} neutral")
        
        return analysis
    
    def get_word_frequency(self, df, text_column, top_n=15):
        """Extract meaningful keywords from reviews"""
        if text_column not in df.columns:
            return {}
        
        # More comprehensive stop words
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'is', 'was', 'are', 'were', 'been', 'be',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
            'should', 'may', 'might', 'must', 'can', 'could', 'this', 'that',
            'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'them',
            'their', 'what', 'which', 'who', 'when', 'where', 'why', 'how',
            'all', 'each', 'every', 'both', 'few', 'more', 'most', 'other',
            'some', 'such', 'only', 'own', 'same', 'so', 'than', 'too', 'very',
            'just', 'my', 'your', 'his', 'her', 'its', 'our', 'their'
        }
        
        all_words = []
        for text in df[text_column].fillna(''):
            # Better word extraction
            words = text.lower().split()
            words = [
                word.strip('.,!?";:()[]{}\'"-–—') 
                for word in words
            ]
            # Filter meaningful words
            meaningful_words = [
                word for word in words
                if len(word) > 3 
                and word not in stop_words
                and word.isalpha()  # Only alphabetic words
            ]
            all_words.extend(meaningful_words)
        
        if all_words:
            word_freq = pd.Series(all_words).value_counts().head(top_n)
            return word_freq.to_dict()
        return {}
    
    def get_actionable_insights(self, df, analysis_results, text_column):
        """Generate actionable business insights"""
        if not analysis_results:
            return None
        
        insights = {
            'urgent_actions': [],
            'improvement_areas': [],
            'recommendations': [],
            'positive_highlights': []
        }
        
        total = analysis_results['total_reviews']
        
        # Urgent actions
        if analysis_results['urgent_indices']:
            insights['urgent_actions'].append({
                'action': '🚨 IMMEDIATE RESPONSE REQUIRED',
                'count': len(analysis_results['urgent_indices']),
                'description': f"{len(analysis_results['urgent_indices'])} reviews require urgent attention"
            })
        
        # Safety concerns get top priority
        if 'Safety Concerns' in analysis_results.get('issue_summary', {}):
            count = analysis_results['issue_summary']['Safety Concerns']
            insights['urgent_actions'].append({
                'action': '⚠️ SAFETY ISSUE DETECTED',
                'count': count,
                'description': f"{count} reviews mention safety concerns - investigate immediately"
            })
        
        # Improvement areas
        if analysis_results.get('issue_summary'):
            sorted_issues = sorted(
                analysis_results['issue_summary'].items(),
                key=lambda x: x[1],
                reverse=True
            )
            for issue, count in sorted_issues[:3]:
                percentage = (count / total) * 100
                insights['improvement_areas'].append({
                    'issue': issue,
                    'impact': f"{count} reviews ({percentage:.1f}%)",
                    'action': self.get_action_for_issue(issue)
                })
        
        # Sentiment-based recommendations
        neg_pct = (analysis_results['negative_count'] / total) * 100
        pos_pct = (analysis_results['positive_count'] / total) * 100
        
        if neg_pct > 40:
            insights['recommendations'].append(
                "🔴 Critical: Over 40% negative sentiment - immediate action required"
            )
        elif neg_pct > 25:
            insights['recommendations'].append(
                "🟡 Warning: High negative sentiment detected - review product quality"
            )
        
        if pos_pct > 70:
            insights['positive_highlights'].append(
                "🟢 Strong positive sentiment - leverage for marketing"
            )
        
        # Confidence check
        avg_confidence = analysis_results.get('avg_confidence', 0)
        if avg_confidence < 0.6:
            insights['recommendations'].append(
                "📊 Low confidence scores - consider manual review for accuracy"
            )
        
        return insights
    
    def get_action_for_issue(self, issue_type):
        """Map issues to specific business actions"""
        actions = {
            'Safety Concerns': "URGENT: Investigate safety reports, consider recall if necessary",
            'Quality Issues': "Review manufacturing QC, contact suppliers, implement quality checks",
            'Shipping Problems': "Audit logistics partner, review packaging, track shipping metrics",
            'Wrong Product': "Audit fulfillment process, update product listings, train warehouse staff",
            'Customer Service': "Review support tickets, conduct team training, update response templates",
            'Value/Pricing': "Analyze competitor pricing, review value proposition, consider adjustments"
        }
        return actions.get(issue_type, "Investigate and develop action plan")
    
    def get_priority_reviews(self, df, analysis_results, text_column, top_n=10):
        """Get reviews requiring immediate attention"""
        if not analysis_results or 'priority_scores' not in analysis_results:
            return pd.DataFrame()
        
        priority_df = df.copy()
        priority_df['priority_score'] = analysis_results['priority_scores']
        priority_df['sentiment'] = analysis_results['sentiments']
        priority_df['confidence'] = analysis_results['confidences']
        priority_df['issues'] = [
            ', '.join(issues) if issues else 'None'
            for issues in analysis_results['issues_found']
        ]
        
        return priority_df.sort_values('priority_score', ascending=False).head(top_n)
    
    def export_analysis(self, df, analysis_results):
        """Prepare data for export with all analysis details"""
        export_data = df.copy()
        
        if analysis_results:
            export_data['sentiment'] = analysis_results['sentiments']
            export_data['confidence_score'] = analysis_results['confidences']
            export_data['priority_score'] = analysis_results['priority_scores']
            export_data['issues_detected'] = [
                ', '.join(issues) if issues else 'None'
                for issues in analysis_results['issues_found']
            ]
            export_data['requires_response'] = [
                idx in analysis_results['urgent_indices']
                for idx in range(len(df))
            ]
        
        export_data['analysis_date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        export_data['analysis_method'] = analysis_results.get('method', 'Unknown')
        
        return export_data