# 🤖 MyBot — Telegram Bot for Content Parsing and Publishing

Telegram bot for parsing content from lombard-perspectiva.ru and publishing posts to channels. Supports text editing and image management before publication.

---

## ⚡ Features

- **📑 Content Parsing** from lombard-perspectiva.ru
- **🖼️ Image Selection & Sorting** before publication
- **✏️ Text Editing** capabilities
- **📤 Automatic Publishing** to Telegram channels
- **🔒 Environment-based Configuration** (.env)
- **🐳 Containerization** via Podman/Quadlet
- **🚀 Modern Python Stack** with uv
- **🔐 Secure Secret Management**
- **⚙️ Systemd Service Integration**

---

## 🛠️ Quick Start

### Prerequisites
- Python 3.12+
- Podman (for container deployment)
- Telegram Bot Token & API credentials

### Setup `.env`

```bash
CHANNEL_ID=@your_channel
ADMIN_ID=your_admin_id
BOT_TOKEN=your_bot_token
API_ID=your_api_id
API_HASH=your_api_hash
```

### Local Development
uv sync  
source .venv/bin/activate  # Linux/Mac  
# .venv\Scripts\activate  # Windows  
python main.py

### Run Container
podman run --rm --env-file .env my-bot

### 🧪 Running Tests
Tests are located in the `tests` directory. To run tests, use:

```bash
pytest tests/
```

---

🐳 Production Deployment with Systemd  
Quadlet Configuration  
Create ~/.config/containers/systemd/mybot.container:  
[Unit]  
Description=MyBot Container Service  
Wants=network-online.target  
After=network-online.target

[Container]  
Image=quay.io/nikolasheva/my-bot:latest  
ContainerName=mybot  
EnvironmentFile=%h/my-bot/.env  
Volume=%h/my-bot/media:/app/pics:Z  
Network=host

[Service]  
Restart=always  
RestartSec=10  
TimeoutStopSec=60

[Install]  
WantedBy=default.target

Service Management  
# Enable and start service  
systemctl --user daemon-reload  
systemctl --user start mybot.service
systemctl --user stop mybot.service

# Monitor logs  
journalctl --user -u mybot.service -f  
🔧 Configuration

Environment Variables  
Variable	Description	Required  
BOT_TOKEN	Telegram Bot Token from @BotFather	✅  
API_ID	Telegram API ID from my.telegram.org	✅  
API_HASH	Telegram API Hash from my.telegram.org	✅  
CHANNEL_ID	Target channel username (@channel)	✅  
ADMIN_ID	Admin user ID for bot control	✅

File Structure  
my-bot/  
├── main.py                 # Main application  
├── Containerfile           # Container configuration  
├── pyproject.toml          # Dependencies (uv)  
├── uv.lock                 # Lock file  
├── .env.example            # Environment template  
├── .gitignore             # Git ignore rules  
├── README.md               # This file  
└── tests/                  # Test directory  
    └── test_basic.py       # Basic test file
|___pics                    # Extra pics    

🔒 Security Notes  
Never commit .env file to version control

Use environment variables for production secrets

Regular dependency updates with uv update

Container images signed and verified

🔒 Security scanning

Images available at:

Quay.io: quay.io/nikolasheva/my_bot:latest

📊 Monitoring  
bash  
### Service status  
systemctl --user status mybot.service

### Live logs  
journalctl --user -u mybot.service -f --since "5 minutes ago"

### Resource usage  
podman stats mybot  
🆘 Troubleshooting

Permission denied on media directory:  
chmod 755 pics/

Container startup issues:  
podman logs mybot

Network connectivity:  
podman exec -it mybot curl api.telegram.org

Debug Mode  
podman run --rm --env-file .env -e DEBUG=true my-bot

📝 License  
MIT License - see LICENSE file for details.

📮 Support  
📧 Email: niksheva7@gmail.com

💬 Issues: GitHub Issues

🐙 Repository: github.com/nikolasheva/my-bot

Version: v0.1.0  
Last Updated: September 2025  
Compatibility: Python 3.12+, Podman 4.0+


---

# File: tests/test_basic.py

def test_dummy():
    assert True
