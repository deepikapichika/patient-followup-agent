# bot.py - Main Telegram Bot File
import os
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

from database import db
from risk_engine import risk_engine

load_dotenv()

# Setup logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start - Register patient"""
    user = update.effective_user
    chat_id = update.effective_chat.id
    
    # Register in database
    patient = db.register_patient(chat_id, user.first_name)
    
    welcome_msg = (
        f"🏥 **Welcome {user.first_name}!**\n\n"
        f"I'm your autonomous patient follow-up agent. I'll analyze your daily check-ins and alert your doctor if needed.\n\n"
        f"📋 **How it works:**\n"
        f"• Send me daily updates about your recovery\n"
        f"• I'll analyze symptoms and pain levels\n"
        f"• High-risk cases are automatically flagged\n\n"
        f"✅ You're registered! Just message me how you're feeling.\n\n"
        f"📝 **Example messages:**\n"
        f"• 'I'm feeling good today'\n"
        f"• 'I have pain level 7'\n"
        f"• 'I have fever and bleeding'"
    )
    
    await update.message.reply_text(welcome_msg, parse_mode='Markdown')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process patient message with risk analysis"""
    chat_id = update.effective_chat.id
    user_message = update.message.text
    
    # Get patient from database
    patient = db.get_patient_by_chat_id(chat_id)
    
    if not patient:
        await update.message.reply_text("Please use /start to register first.")
        return
    
    # Get patient's history (simplified - would fetch from DB in production)
    history = []
    
    # Analyze risk
    risk_result = risk_engine.calculate_risk_score(user_message, history)
    
    print(f"📊 Patient: {patient['name']}")
    print(f"   Risk Score: {risk_result['risk_score']} ({risk_result['severity']})")
    print(f"   Symptoms: {risk_result['detected_symptoms']}")
    
    # Save check-in to database
    db.save_checkin(
        patient['id'], 
        user_message, 
        risk_result['risk_score'],
        risk_result['detected_symptoms']
    )
    
    # Create alert if high risk
    if risk_result['severity'] in ['HIGH', 'CRITICAL']:
        alert = db.create_alert(
            patient['id'],
            risk_result['severity'],
            f"Risk score {risk_result['risk_score']}: {', '.join(risk_result['detected_symptoms'][:3])}"
        )
        logger.warning(f"🚨 ALERT created for patient {patient['name']}: {risk_result['severity']}")
        print(f"   🚨 ALERT sent to doctor!")
    
    # Generate response
    response = risk_engine.get_response_message(risk_result)
    
    # Add detailed info for high-risk cases
    if risk_result['severity'] in ['HIGH', 'CRITICAL']:
        response += f"\n\n📊 **Risk Analysis:**\n• Symptoms: {', '.join(risk_result['detected_symptoms'][:5]) or 'None detected'}\n• Risk Score: {risk_result['risk_score']}"
    
    await update.message.reply_text(response, parse_mode='Markdown')

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors"""
    logger.error(f"Update {update} caused error {context.error}")
    print(f"❌ Error: {context.error}")

def main():
    """Start the bot"""
    print("=" * 50)
    print("🤖 Starting Autonomous Patient Follow-up Agent...")
    print("📊 Risk Engine Active")
    print("💾 Database Connected")
    print("=" * 50)
    
    # Create application
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Add handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_error_handler(error_handler)
    
    print("✅ Bot is running! Talk to it on Telegram")
    print("=" * 50)
    
    # Start bot
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    import os
    port = int(os.environ.get("PORT", 10000))
    print(f"Starting bot on port {port}")
    main()