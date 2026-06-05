# dashboard.py - Streamlit Dashboard
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
from supabase import create_client
import os
from dotenv import load_dotenv

load_dotenv()

# Initialize Supabase
supabase = create_client(
    os.getenv('SUPABASE_URL'),
    os.getenv('SUPABASE_KEY')
)

st.set_page_config(page_title="Patient Follow-up Dashboard", page_icon="🏥", layout="wide")

st.title("🏥 Autonomous Patient Follow-up Agent")
st.markdown("### Real-time Patient Monitoring Dashboard")

# Fetch data
@st.cache_data(ttl=10)
def fetch_data():
    patients = supabase.table('patients').select('*').execute()
    checkins = supabase.table('checkins').select('*').order('created_at', desc=True).limit(100).execute()
    alerts = supabase.table('alerts').select('*').order('created_at', desc=True).execute()
    return patients.data, checkins.data, alerts.data

# Auto-refresh every 10 seconds
auto_refresh = st.checkbox("Auto-refresh every 10 seconds", value=True)
if auto_refresh:
    st.rerun()

patients, checkins, alerts = fetch_data()

# Top Metrics
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("👥 Total Patients", len(patients))

with col2:
    high_risk = len([p for p in patients if p.get('risk_level') == 'HIGH'])
    critical_risk = len([p for p in patients if p.get('risk_level') == 'CRITICAL'])
    st.metric("⚠️ High Risk Patients", high_risk + critical_risk)

with col3:
    today = datetime.now().date()
    today_checkins = 0
    for c in checkins:
        try:
            if datetime.fromisoformat(c['created_at'].replace('Z', '+00:00')).date() == today:
                today_checkins += 1
        except:
            pass
    st.metric("📝 Today's Check-ins", today_checkins)

with col4:
    active_alerts = len([a for a in alerts if not a.get('resolved', False)])
    st.metric("🚨 Active Alerts", active_alerts)

# Two columns for charts
col1, col2 = st.columns(2)

with col1:
    st.subheader("Risk Distribution")
    if patients:
        risk_counts = {'LOW': 0, 'MEDIUM': 0, 'HIGH': 0, 'CRITICAL': 0}
        for p in patients:
            risk_level = p.get('risk_level', 'LOW')
            risk_counts[risk_level] = risk_counts.get(risk_level, 0) + 1
        
        df_risk = pd.DataFrame({'Risk Level': list(risk_counts.keys()), 'Count': list(risk_counts.values())})
        fig = px.pie(df_risk, values='Count', names='Risk Level', color='Risk Level',
                     color_discrete_map={'LOW': 'green', 'MEDIUM': 'yellow', 'HIGH': 'orange', 'CRITICAL': 'red'})
        st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("Recent Check-ins")
    if checkins:
        df_checkins = pd.DataFrame(checkins[:10])
        if 'created_at' in df_checkins.columns:
            df_checkins['time'] = pd.to_datetime(df_checkins['created_at']).dt.strftime('%H:%M')
            df_checkins['short_msg'] = df_checkins['message'].str[:50] + '...'
            st.dataframe(df_checkins[['time', 'short_msg', 'risk_score']], use_container_width=True)

# Recent Alerts
st.subheader("🚨 Recent Alerts")
if alerts:
    alert_df = pd.DataFrame(alerts[:10])
    alert_df['created_at'] = pd.to_datetime(alert_df['created_at']).dt.strftime('%Y-%m-%d %H:%M')
    
    # Get patient names
    patient_map = {p['id']: p['name'] for p in patients}
    alert_df['patient_name'] = alert_df['patient_id'].map(patient_map)
    
    # Color-code severity
    def color_severity(severity):
        if severity == 'CRITICAL':
            return '🔴 CRITICAL'
        elif severity == 'HIGH':
            return '🟠 HIGH'
        elif severity == 'MEDIUM':
            return '🟡 MEDIUM'
        else:
            return '🟢 LOW'
    
    alert_df['severity_display'] = alert_df['severity'].apply(color_severity)
    
    st.dataframe(
        alert_df[['created_at', 'patient_name', 'severity_display', 'reason', 'resolved']],
        use_container_width=True
    )
else:
    st.info("No alerts generated yet. Send some test messages to your bot!")

# Patient List
st.subheader("📋 Patient List")
if patients:
    patient_df = pd.DataFrame(patients)
    if 'surgery_date' in patient_df.columns:
        patient_df['surgery_date'] = pd.to_datetime(patient_df['surgery_date']).dt.strftime('%Y-%m-%d')
    st.dataframe(
        patient_df[['name', 'surgery_type', 'surgery_date', 'risk_level', 'status']],
        use_container_width=True
    )
else:
    st.info("No patients registered yet. Send /start to your bot!")

st.markdown("---")
st.caption("🏥 Autonomous Patient Follow-up Agent | Data refreshes every 10 seconds")