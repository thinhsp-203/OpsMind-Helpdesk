"""Run inside the helpdesk container after sending /start@BotUsername in the group."""
import json
import os
from urllib.request import Request, urlopen

token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
if not token:
    raise SystemExit("Chưa cấu hình TELEGRAM_BOT_TOKEN.")
try:
    request = Request(
        f"https://api.telegram.org/bot{token}/getUpdates",
        data=b'{"timeout":0}',
        headers={"Content-Type": "application/json"},
    )
    with urlopen(request, timeout=10) as response:
        result = json.load(response)
    groups = {}
    for update in result.get("result", []):
        for key in ("message", "my_chat_member"):
            chat = update.get(key, {}).get("chat", {})
            if chat.get("type") in ("group", "supergroup"):
                groups[chat["id"]] = chat.get("title", "Nhóm")
    for chat_id, title in groups.items():
        print(f"{title}: {chat_id}")
    if not groups:
        print("Chưa thấy nhóm. Gửi /start@TênBot trong nhóm rồi chạy lại. Bot dùng webhook hoặc có dịch vụ khác đọc cập nhật có thể không dùng được cách này.")
except Exception:
    raise SystemExit("Không lấy được mã nhóm. Kiểm tra token, mạng và bot có đang dùng webhook/dịch vụ khác không.")
