# database.py
import os
from supabase import create_client, Client
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

class Database:
    def __init__(self):
        self.supabase: Client = create_client(
            os.getenv('SUPABASE_URL'),
            os.getenv('SUPABASE_KEY')
        )
    
    def register_patient(self, chat_id: int, name: str, phone: str = None):
        """Register a new patient"""
        # Check if already exists
        existing = self.supabase.table('patients').select('*').eq('telegram_chat_id', chat_id).execute()
        
        if existing.data:
            return existing.data[0]
        
        # Insert new patient (mock surgery date - 3 days ago for demo)
        from datetime import datetime, timedelta
        surgery_date = (datetime.now() - timedelta(days=3)).date()
        
        data = {
            'telegram_chat_id': chat_id,
            'name': name,
            'phone': phone or f"+91{chat_id}"[-10:],
            'surgery_type': 'General Surgery',
            'surgery_date': surgery_date.isoformat(),
            'status': 'ACTIVE'
        }
        
        result = self.supabase.table('patients').insert(data).execute()
        return result.data[0]
    
    def save_checkin(self, patient_id: str, message: str, risk_score: float = None, symptoms: list = None):
        """Save patient check-in"""
        data = {
            'patient_id': patient_id,
            'message': message,
            'risk_score': risk_score,
            'symptoms_detected': symptoms or []
        }
        result = self.supabase.table('checkins').insert(data).execute()
        return result.data[0]
    
    def get_patient_by_chat_id(self, chat_id: int):
        """Get patient by Telegram chat ID"""
        result = self.supabase.table('patients').select('*').eq('telegram_chat_id', chat_id).execute()
        return result.data[0] if result.data else None
    
    def create_alert(self, patient_id: str, severity: str, reason: str):
        """Create an alert for doctor"""
        data = {
            'patient_id': patient_id,
            'severity': severity,
            'reason': reason
        }
        result = self.supabase.table('alerts').insert(data).execute()
        return result.data[0]

# Create global instance
db = Database()
print("✅ Database connection established!")