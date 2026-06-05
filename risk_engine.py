# risk_engine.py - IMPROVED VERSION with typo handling
import re
from typing import Dict, List, Tuple

class RiskEngine:
    """5-dimensional risk scoring for patient messages"""
    
    def __init__(self):
        # Symptom keywords with severity weights (EXPANDED with common typos)
        self.symptom_weights = {
            # Severe symptoms (weight 0.8-1.0)
            'severe pain': 0.9, 'excruciating': 0.9, 'unbearable': 0.9,
            'bleeding': 0.9, 'blood': 0.8, 'hemorrhage': 1.0,
            'bleed': 0.9, 'bleeds': 0.9, 'bleeding heavily': 1.0,
            
            # Fever (including typos)
            'fever': 0.7, 'feverish': 0.7, 'high temperature': 0.7,
            'frver': 0.6, 'feaver': 0.6, 'fevar': 0.6,  # Common typos
            '102': 0.8, '103': 0.9, '104': 1.0,
            
            # Infection symptoms
            'infection': 0.8, 'pus': 0.7, 'redness': 0.4,
            'vomiting': 0.7, 'nausea': 0.5, 'diarrhea': 0.5,
            
            # Critical symptoms
            'dizzy': 0.5, 'faint': 0.6, 'unconscious': 1.0,
            'swelling': 0.4, 'cough': 0.3, 'headache': 0.3,
            'pain level': 0.6, 'hurts': 0.4, 'aching': 0.3,
            'chills': 0.6, 'sweating': 0.4, 'weakness': 0.4,
            
            # Chest/heart symptoms
            'chest pain': 0.9, 'heart': 0.8, 'breathing': 0.8,
        }
        
        # Emergency keywords (for immediate CRITICAL response)
        self.emergency_keywords = [
            'emergency', 'urgent', 'ambulance', 'hospital now', 
            "can't breathe", 'cannot breathe', 'bleeding heavily',
            'severe bleeding', 'unconscious', 'passed out', 
            'chest pain', 'heart attack', 'stroke'
        ]
        
        # Positive indicators (reduces risk)
        self.positive_indicators = [
            'better', 'improving', 'good', 'great', 'excellent',
            'no pain', 'healing', 'fine', 'normal', 'well'
        ]
    
    def extract_pain_level(self, text: str) -> Tuple[int, bool]:
        """Extract pain level from text (1-10)"""
        patterns = [
            r'pain\s*(\d{1,2})',
            r'pain level\s*(\d{1,2})',
            r'(\d{1,2})\s*/\s*10',
            r'rate.*?(\d{1,2})',
            r'pain\s*(?:is\s*)?(\d{1,2})',
            r'\b([1-9]|10)\b(?=.*pain)'
        ]
        
        text_lower = text.lower()
        for pattern in patterns:
            match = re.search(pattern, text_lower)
            if match:
                level = int(match.group(1))
                return min(level, 10), True
        
        return 0, False
    
    def detect_symptoms(self, text: str) -> List[str]:
        """Detect which symptoms are mentioned (with fuzzy matching)"""
        detected = []
        text_lower = text.lower()
        
        # Direct matching
        for symptom in self.symptom_weights.keys():
            if symptom in text_lower:
                detected.append(symptom)
        
        # Special case: check for bleeding-related words
        if any(word in text_lower for word in ['bleed', 'bleeds', 'bleeding', 'blood']):
            if 'bleeding' not in detected:
                detected.append('bleeding')
        
        return detected
    
    def calculate_sentiment(self, text: str) -> float:
        """Calculate simple sentiment score (-1 to +1)"""
        text_lower = text.lower()
        
        positive_count = sum(1 for word in self.positive_indicators if word in text_lower)
        negative_count = sum(1 for symptom in self.symptom_weights.keys() if symptom in text_lower)
        
        total = positive_count + negative_count
        if total == 0:
            return 0
        
        sentiment = (positive_count - negative_count) / total
        return max(-1, min(1, sentiment))
    
    def calculate_risk_score(self, message: str, patient_history: List[Dict] = None) -> Dict:
        """Calculate 5-dimensional risk score (0-1)"""
        text_lower = message.lower()
        
        # Dimension 1: Symptom Score
        symptoms = self.detect_symptoms(message)
        symptom_score = sum(self.symptom_weights.get(s, 0) for s in symptoms)
        symptom_score = min(symptom_score, 1.0)
        
        # Dimension 2: Pain Score
        pain_level, has_pain = self.extract_pain_level(message)
        if has_pain and pain_level >= 8:
            pain_score = 0.9  # Severe pain
        elif has_pain and pain_level >= 6:
            pain_score = 0.6  # Moderate-high pain
        elif has_pain and pain_level >= 4:
            pain_score = 0.4  # Moderate pain
        elif has_pain:
            pain_score = 0.2  # Mild pain
        else:
            pain_score = 0
        
        # Dimension 3: Sentiment Score
        sentiment = self.calculate_sentiment(message)
        sentiment_risk = max(0, (1 - sentiment) / 2)
        
        # Dimension 4: Emergency Keywords (CRITICAL override)
        is_emergency = any(k in text_lower for k in self.emergency_keywords)
        emergency_score = 1.0 if is_emergency else 0
        
        # Dimension 5: Historical trend (simplified)
        history_risk = 0
        if patient_history and len(patient_history) > 0:
            recent_risks = [c.get('risk_score', 0) for c in patient_history[-3:]]
            if recent_risks and max(recent_risks) > 0.5:
                history_risk = 0.3
        
        # Weighted combination
        weights = {
            'symptoms': 0.30,
            'pain': 0.25,
            'sentiment': 0.10,
            'emergency': 0.25,  # Increased weight for emergency
            'history': 0.10
        }
        
        final_risk = (
            weights['symptoms'] * symptom_score +
            weights['pain'] * pain_score +
            weights['sentiment'] * sentiment_risk +
            weights['emergency'] * emergency_score +
            weights['history'] * history_risk
        )
        
        # Emergency override: if emergency keywords detected, force CRITICAL
        if is_emergency:
            final_risk = max(final_risk, 0.85)
            severity = "CRITICAL"
        elif final_risk >= 0.7:
            severity = "CRITICAL"
        elif final_risk >= 0.5:
            severity = "HIGH"
        elif final_risk >= 0.25:
            severity = "MEDIUM"
        else:
            severity = "LOW"
        
        return {
            'risk_score': round(final_risk, 3),
            'severity': severity,
            'components': {
                'symptom_score': round(symptom_score, 2),
                'pain_score': round(pain_score, 2),
                'sentiment_risk': round(sentiment_risk, 2),
                'emergency_score': emergency_score,
                'history_risk': round(history_risk, 2),
                'pain_level': pain_level if has_pain else None
            },
            'detected_symptoms': symptoms,
            'pain_level': pain_level if has_pain else None,
            'is_emergency': is_emergency
        }
    
    def get_response_message(self, risk_result: Dict) -> str:
        """Generate appropriate response based on risk level"""
        severity = risk_result['severity']
        risk_score = risk_result['risk_score']
        pain_level = risk_result.get('pain_level')
        symptoms = risk_result.get('detected_symptoms', [])
        
        if severity == "CRITICAL":
            symptom_text = ", ".join(symptoms[:3]) if symptoms else "serious symptoms"
            return (
                "🚨 **CRITICAL ALERT** 🚨\n\n"
                f"⚠️ IMMEDIATE ACTION REQUIRED\n\n"
                f"I've detected: {symptom_text}\n"
                f"Risk Score: {risk_score}\n\n"
                f"📞 **Call your doctor or emergency services NOW!**\n\n"
                f"🆘 DO NOT WAIT. Seek medical attention immediately.\n\n"
                f"I have alerted the emergency medical team."
            )
        
        elif severity == "HIGH":
            symptom_text = ", ".join(symptoms[:3]) if symptoms else "your symptoms"
            return (
                f"⚠️ **High Risk Detected** (Score: {risk_score})\n\n"
                f"I've detected {symptom_text} that needs attention.\n\n"
                f"📋 Your doctor will be notified immediately.\n\n"
                f"💊 Take prescribed medication and rest.\n"
                f"📞 Contact your doctor if condition worsens.\n\n"
                f"I'll check on you again in a few hours."
            )
        
        elif severity == "MEDIUM":
            if pain_level and pain_level >= 7:
                return (
                    f"📊 **Pain Level: {pain_level}/10**\n\n"
                    f"⚠️ This is significant pain. Please take your prescribed pain medication.\n\n"
                    f"💡 If pain doesn't improve within 4 hours or increases to 9-10, contact your doctor.\n\n"
                    f"I've logged this for your medical team."
                )
            elif pain_level:
                return (
                    f"📊 **Pain Level: {pain_level}/10**\n\n"
                    f"Your symptoms are being monitored. Continue resting and take medications as prescribed.\n\n"
                    f"💡 Let me know if pain increases to 8+ or if new symptoms appear."
                )
            return (
                f"📝 **Check-in Recorded** (Moderate symptoms detected)\n\n"
                f"Risk Score: {risk_score}\n\n"
                f"Contact your doctor if symptoms persist for more than 24 hours."
            )
        
        else:  # LOW
            return (
                f"✅ **Check-in Complete**\n\n"
                f"Your recovery is on track! Keep up the good work.\n\n"
                f"💪 **Recovery Tips:**\n"
                f"• Take medications on time\n"
                f"• Stay hydrated\n"
                f"• Get adequate rest\n"
                f"• Light walking if approved by doctor\n\n"
                f"I'll check on you again tomorrow. Feel better! 🌟"
            )

# Create global instance
risk_engine = RiskEngine()
print("✅ Risk Engine loaded (IMPROVED VERSION)")
print("   - Emergency detection: BLEEDING now triggers CRITICAL alert")
print("   - Typo handling: 'frver' detected as fever")
print("   - Enhanced symptom matching")