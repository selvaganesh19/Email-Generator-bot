# 📧 Email-Generator-bot

Welcome to **Email-Generator-bot**! This project provides a robust backend and Telegram bot for generating, managing, and sending emails with attachment support and modern API design. Built using FastAPI and Python, it enables seamless integration and automation of email workflows.

---

## 🚀 Introduction

**Email-Generator-bot** is designed to streamline the process of composing and sending emails via a user-friendly API and a convenient Telegram bot interface. Whether you're automating notifications, sending files, or integrating email capabilities into your own application, this tool provides a flexible and extensible solution.

---

## ✨ Features

- **FastAPI Backend:** Secure and high-performance REST API for email operations  
- **Telegram Bot:** Interact with the bot to send emails directly from Telegram  
- **Attachment Support:** Easily send files and attachments with your emails  
- **CORS Enabled:** Ready for integration with web frontends and external services  
- **Environment Variable Management:** Uses `.env` files for sensitive configuration  
- **Timezone Handling:** Ensures consistent time-based operations  
- **Extensible:** Modular codebase for easy customization and integration

---

## 🛠️ Installation

### 1. Clone the Repository

```bash
git clone https://github.com/selvaganesh19/Email-Generator-bot.git
cd Email-Generator-bot
```

### 2. Create and Activate a Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Set Up Environment Variables

Create a `.env` file at the project root with necessary configurations, such as SMTP credentials and Telegram bot token.

---

## 📖 Usage

### Start the FastAPI Server

```bash
cd api
uvicorn app:app --reload
```

### Run the Telegram Bot

```bash
cd telegram_bot
python bot.py
```

### Example API Request

Send a POST request to `/send-email` (adjust endpoint as implemented):

```http
POST /send-email
Content-Type: application/json

{
  "to": "recipient@example.com",
  "subject": "Hello!",
  "body": "This is a test email."
}
```

### Using the Telegram Bot

1. Start a chat with your bot on Telegram.
2. Use provided commands (such as `/sendemail`) to compose and send emails right from the chat.

---

## 🤝 Contributing

We welcome contributions! To get started:

1. Fork this repository
2. Create a new branch (`git checkout -b feature/your-feature`)
3. Commit your changes (`git commit -am 'Add new feature'`)
4. Push to the branch (`git push origin feature/your-feature`)
5. Create a Pull Request

Please read our [CONTRIBUTING.md](CONTRIBUTING.md) for more details.

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).

---

**Happy emailing!** ✉️

## License
This project is licensed under the **MIT** License.

---
🔗 GitHub Repo: https://github.com/selvaganesh19/Email-Generator-bot