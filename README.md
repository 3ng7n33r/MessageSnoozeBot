# SnoozeBot 🛌

**Right-click Discord messages → Snooze → DM reminder.** MIT License.

## ✨ Features

- Right-click → 15m/1h/4h/Tomorrow/Custom (`2h30m`)
- DM with jump link
- 100% secure (parameterized SQL)
- uv + systemd ready


## 🚀 Setup

```bash
git clone <repo> && cd snoozebot
cp .env.example .env  # Add DISCORD_TOKEN
uv sync
uv run python main.py
```

**Bot Invite**: `Send Messages` + `Use Slash Commands` + `Read Message History`

## 📁 Production (VPS)

```bash
scp -r snoozebot user@vps:~/
cd snoozebot && uv sync
sudo systemctl enable --now snoozebot  # See systemd service in repo
```


## 📖 Usage

```
Right-click message → 🛌 Snooze Message → Pick time → Get DM ✅
```


## 🔧 Customize

Edit `SnoozeView` class → add buttons, change times.

## 📄 License

MIT - © 2026
