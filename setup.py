import os
import requests
from dotenv import load_dotenv

load_dotenv()

def setup_webhook():
    token = os.environ.get("TELEGRAM_TOKEN")
    hf_space_name = os.environ.get("HF_SPACE_NAME")
    
    if not token or not hf_space_name:
        print("Missing TELEGRAM_TOKEN or HF_SPACE_NAME in environment variables")
        return
    
    webhook_url = f"https://{hf_space_name}.hf.space/telegram-webhook"
    api_url = f"https://api.telegram.org/bot{token}/setWebhook?url={webhook_url}"
    
    response = requests.get(api_url)
    print(f"Webhook setup response: {response.json()}")

if __name__ == "__main__":
    setup_webhook()