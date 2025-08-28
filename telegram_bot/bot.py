import os, sys
from pathlib import Path

from flask import app

# Get the project root directory (one level up from current directory)
ROOT_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = os.path.join(ROOT_DIR, '.env')

# Set timezone environment variable early
os.environ.setdefault("TZ", "UTC")

# More robust timezone patch
try:
    import pytz
    import importlib
    
    # Patch tzlocal
    try:
        import tzlocal
        tzlocal.get_localzone = lambda: pytz.timezone("UTC")
    except ImportError:
        pass
    
    # Direct patch for apscheduler.util.astimezone
    try:
        import apscheduler.util
        original_astimezone = getattr(apscheduler.util, "astimezone", None)
        def patched_astimezone(tz):
            if tz is None:
                return pytz.UTC
            return tz
        apscheduler.util.astimezone = patched_astimezone
    except (ImportError, AttributeError):
        pass
except ImportError:
    pass

import io, mimetypes, requests
import telegram
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, ConversationHandler,
    ContextTypes, filters
)
from fastapi import FastAPI, Request

# Load environment variables from the root .env file
load_dotenv(ENV_PATH)
print(f"Loading .env from: {ENV_PATH}")

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
API_BASE = os.getenv("API_BASE")  # e.g., https://<username>-email-api.hf.space

# Add these missing state definitions at the top with your other states
ROLE, TONE, TOPIC, SUBJECT, NAME, POSITION, RECIPIENT_NAME, RECIPIENT, ATTACH_OR_SEND, WAIT_ATTACHMENTS, CONFIRM = range(11)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Welcome to the Email Generator Bot! I'll help you craft professional emails.\n\n"
        "What's your professional role? (e.g., manager, developer, student)"
    )
    context.user_data.clear()  # Reset user data
    return ROLE

async def get_role(update: Update, context: ContextTypes.DEFAULT_TYPE):
    role = update.message.text.strip()
    context.user_data["role"] = role
    
    # Ask for user's name
    await update.message.reply_text("What's your name?")
    return NAME

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text.strip()
    context.user_data["name"] = name
    
    # Customize questions based on role
    role = context.user_data["role"].lower()
    if "student" in role:
        await update.message.reply_text("What's your field of study? (e.g., Computer Science, Engineering)")
        return POSITION
    elif "dev" in role or "developer" in role:
        await update.message.reply_text("What's your position? (e.g., Frontend Developer, Backend Developer)")
        return POSITION
    else:
        await update.message.reply_text("What's your position?")
        return POSITION

async def get_position(update: Update, context: ContextTypes.DEFAULT_TYPE):
    position = update.message.text.strip()
    context.user_data["position"] = position
    
    await update.message.reply_text(
        "What tone would you like? (e.g., formal, casual)"
    )
    return TONE

async def get_tone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tone = update.message.text.strip()
    context.user_data["tone"] = tone
    
    await update.message.reply_text(
        "What topic would you like to write about? (e.g., meeting, project update)"
    )
    return TOPIC

async def get_topic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Existing function
    topic = update.message.text.strip()
    context.user_data["topic"] = topic
    
    # Add recipient name question
    await update.message.reply_text("Who is the recipient? (name or title)")
    return RECIPIENT_NAME

async def get_recipient_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    recipient_name = update.message.text.strip()
    context.user_data["recipient_name"] = recipient_name
    
    await update.message.reply_text("What's the recipient's email address?")
    return RECIPIENT

async def get_recipient(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["recipient"] = update.message.text.strip()
    kb = ReplyKeyboardMarkup([["Send now"], ["Add attachment(s)"]], one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text("Do you want to send now or add attachment(s)?", reply_markup=kb)
    return ATTACH_OR_SEND

async def attach_or_send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    choice = update.message.text.strip().lower()
    if "attach" in choice:
        context.user_data["files"] = []  # list of (name, bytes, mime)
        await update.message.reply_text(
            "📎 Send me document/photo(s).\n\n"
            "⚠️ *Important:*\n"
            "• When you're finished adding attachments, type /done\n"
            "• Keep files under 5MB\n"
            "• Wait for confirmation before sending the next file",
            parse_mode="Markdown"
        )
        return WAIT_ATTACHMENTS
    else:
        return await _send_now(update, context)

async def receive_attachment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if document := update.message.document:
            # Check file size (10MB limit)
            if document.file_size > 10 * 1024 * 1024:
                await update.message.reply_text("⚠️ File is too large (max 10MB)")
                return WAIT_ATTACHMENTS
            
            file = await document.get_file()
            bio = io.BytesIO()
            
            # Retry logic without timeout parameter
            max_retries = 3
            current_retry = 0
            
            while current_retry < max_retries:
                try:
                    # Remove timeout parameter
                    await file.download_to_memory(out=bio)
                    break
                except telegram.error.TimedOut:
                    current_retry += 1
                    if current_retry < max_retries:
                        await update.message.reply_text(f"⚠️ Download timed out. Retrying ({current_retry}/{max_retries})...")
                    else:
                        raise
            
            bio.seek(0)
            filename = document.file_name or f"file_{document.file_unique_id}"
            mime = mimetypes.guess_type(filename)[0] or "application/octet-stream"
            context.user_data["files"].append((filename, bio, mime))
            await update.message.reply_text(
                f"✅ Got file: {filename}\n\n"
                f"Send more attachments or type /done when finished"
            )

        elif photos := update.message.photo:
            # Take the largest size
            photo = photos[-1]
            file = await photo.get_file()
            bio = io.BytesIO()
            
            # Retry logic for photos without timeout
            max_retries = 3
            current_retry = 0
            
            while current_retry < max_retries:
                try:
                    # Remove timeout parameter
                    await file.download_to_memory(out=bio)
                    break
                except telegram.error.TimedOut:
                    current_retry += 1
                    if current_retry < max_retries:
                        await update.message.reply_text(f"⚠️ Download timed out. Retrying ({current_retry}/{max_retries})...")
                    else:
                        raise
                        
            bio.seek(0)
            filename = f"photo_{file.file_unique_id}.jpg"
            mime = "image/jpeg"
            context.user_data["files"].append((filename, bio, mime))
            await update.message.reply_text(
                "✅ Got photo\n\n"
                "Send more attachments or type /done when finished"
            )
    
    except telegram.error.TimedOut:
        await update.message.reply_text("⚠️ Download timed out. Try a smaller file or better connection.")
    except Exception as e:
        await update.message.reply_text(f"⚠️ Error processing attachment: {str(e)}")

    return WAIT_ATTACHMENTS

async def done_attachments(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Check if email has been generated yet
    if "generated_email" not in context.user_data or "generated_subject" not in context.user_data:
        # We need to generate the email first
        await update.message.reply_text("⏳ Generating your email, please wait...")
        email_text, subject = await generate_email_from_api(context)
        context.user_data["generated_email"] = email_text
        context.user_data["generated_subject"] = subject
    
    # Show a summary with attachments
    attachments_count = len(context.user_data.get("files", []))
    attachment_text = f"📎 {attachments_count} attachment(s)" if attachments_count > 0 else "No attachments"
    
    # Show email preview
    preview = (f"📝 Email Summary:\n\n"
               f"To: {context.user_data['recipient']}\n"
               f"Subject: {context.user_data['generated_subject']}\n"
               f"Attachments: {attachment_text}\n\n"
               f"Message Preview:\n{context.user_data['generated_email'][:200]}...\n\n"
               f"Ready to send?")
    
    kb = ReplyKeyboardMarkup([["✅ Send Now"], ["❌ Cancel"]], resize_keyboard=True)
    await update.message.reply_text(preview, reply_markup=kb)
    return CONFIRM

# Update confirm_send to handle both attachment and non-attachment flows
async def confirm_send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    choice = update.message.text.strip().lower()
    if "send" in choice or "✅" in choice:
        # If we already have attachments, send directly
        if "files" in context.user_data and context.user_data["files"]:
            return await _send_now(update, context)
        else:
            # Otherwise ask if they want to add attachments
            kb = ReplyKeyboardMarkup([["Send now"], ["Add attachment(s)"]], one_time_keyboard=True, resize_keyboard=True)
            await update.message.reply_text("Do you want to send now or add attachment(s)?", reply_markup=kb)
            return ATTACH_OR_SEND
    else:
        await update.message.reply_text("❌ Email canceled.")
        return ConversationHandler.END

# Make _send_now more robust with fallbacks for missing keys
async def _send_now(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Check if we have the necessary data
    if "generated_email" not in context.user_data or "generated_subject" not in context.user_data:
        await update.message.reply_text("⚠️ Email content is missing. Let's start over.")
        return ConversationHandler.END
        
    # Send via HF /send-email
    data = {
        "recipient": context.user_data["recipient"],
        "subject": context.user_data["generated_subject"],
        "body": context.user_data["generated_email"]
    }

    files = []
    for (filename, bio, mime) in context.user_data.get("files", []):
        files.append(("attachments", (filename, bio, mime)))

    try:
        await update.message.reply_text("📤 Sending email...")
        r = requests.post(f"{API_BASE}/send-email", data=data, files=files if files else None, timeout=60)
        resp = r.json()
        if r.ok:
            await update.message.reply_text(f"✅ Email sent to {resp.get('to', data['recipient'])} successfully!")
        else:
            error_msg = resp.get('error', str(resp))
            if "BadCredentials" in str(error_msg):
                await update.message.reply_text("❌ Email login failed. Please check GMAIL_USER and GMAIL_PASS in server config.")
            else:
                await update.message.reply_text(f"❌ Failed: {error_msg}")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)[:100]}...")

    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Cancelled.")
    return ConversationHandler.END

async def generate_email_from_api(context):
    # Include position/field based on role
    role = context.user_data["role"]
    position = context.user_data.get("position", "")
    
    # Customize position display based on role
    if "student" in role.lower():
        position_info = f"Student of {position}"
    else:
        position_info = position
    
    data = {
        "role": role,
        "tone": context.user_data["tone"],
        "topic": context.user_data["topic"],
        "subject": context.user_data.get("subject", "auto"),
        "name": context.user_data.get("name", ""),
        "position": position_info,
        "recipient_name": context.user_data.get("recipient_name", "Dear Sir/Madam")
    }
    
    try:
        r = requests.post(f"{API_BASE}/generate-email", data=data, timeout=30)
        r.raise_for_status()
        resp = r.json()
        return resp.get("email", ""), resp.get("subject", "")
    except Exception as e:
        return f"⚠️ Failed to generate email: {str(e)}", ""

# Add this missing function for subject handling
async def get_subject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    subject_choice = update.message.text.strip()
    if subject_choice.lower() != "auto":
        context.user_data["subject"] = subject_choice
    
    # Generate email
    await update.message.reply_text("⏳ Generating your email, please wait...")
    email_text, subject = await generate_email_from_api(context)
    context.user_data["generated_email"] = email_text
    context.user_data["generated_subject"] = subject
    
    # Show preview
    preview = f"📝 Preview\nSubject: {subject}\n\n{email_text[:300]}...\n\nReady to send?"
    kb = ReplyKeyboardMarkup([["✅ Send"], ["❌ Cancel"]], resize_keyboard=True)
    await update.message.reply_text(preview, reply_markup=kb)
    return CONFIRM

# Update main() to use webhooks when deployed
async def main():
    token = TELEGRAM_TOKEN
    if not token:
        raise RuntimeError("Set TELEGRAM_TOKEN in .env")
    
    # Determine if we're running on Hugging Face
    is_production = os.environ.get("PRODUCTION", "False").lower() == "true"
    
    # Build application
    app = Application.builder().token(token).job_queue(None).build()
    
    # Add handlers
    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            ROLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_role)],
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            POSITION: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_position)],
            TONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_tone)],
            TOPIC: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_topic)],
            RECIPIENT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_recipient_name)],
            RECIPIENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_recipient)],
            SUBJECT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_subject)],
            CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_send)],
            ATTACH_OR_SEND: [MessageHandler(filters.TEXT & ~filters.COMMAND, attach_or_send)],
            WAIT_ATTACHMENTS: [
                MessageHandler(filters.PHOTO | filters.Document.ALL, receive_attachment),
                CommandHandler("done", done_attachments)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    app.add_handler(conv)
    
    print("🤖 Telegram bot running in polling mode... /start")
    await app.run_polling()
        
    return app

if __name__ == "__main__":
    import asyncio
    try:
        asyncio.run(main())
    except Exception as e:
        print("BOT STARTUP ERROR:", e, flush=True)
        import sys
        sys.exit(1)

import sys
sys.stderr = sys.stdout
