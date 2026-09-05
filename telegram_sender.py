"""
Telegram Sender Utility for Standalone AnimeVist Automation Service.
Communicates directly with Telegram Bot API via Python urllib (zero external dependencies).
"""

import os
import sys
import json
import urllib.request
import urllib.parse
import urllib.error

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

def load_config():
    config_path = os.path.join(os.path.dirname(__file__), 'config.json')
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_config(conf):
    config_path = os.path.join(os.path.dirname(__file__), 'config.json')
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(conf, f, ensure_ascii=False, indent=2)

class TelegramSender:
    def __init__(self, bot_token=None, channel_id=None):
        config = load_config()
        tg_conf = config.get('telegram', {})
        self.bot_token = bot_token or tg_conf.get('bot_token')
        self.channel_id = channel_id or tg_conf.get('channel_id')
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"

    def send_message(self, text, chat_id=None, reply_markup=None, disable_preview=False):
        target_chat = chat_id or self.channel_id
        if not self.bot_token or not target_chat:
            return {"ok": False, "description": "bot_token or chat_id not configured"}

        payload = {
            "chat_id": target_chat,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": disable_preview
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup

        return self._make_request("sendMessage", payload)

    def send_photo(self, photo_url_or_path, caption="", chat_id=None, reply_markup=None):
        target_chat = chat_id or self.channel_id
        if not self.bot_token or not target_chat:
            return {"ok": False, "description": "bot_token or chat_id not configured"}

        if photo_url_or_path.startswith("http://") or photo_url_or_path.startswith("https://"):
            payload = {
                "chat_id": target_chat,
                "photo": photo_url_or_path,
                "caption": caption,
                "parse_mode": "HTML"
            }
            if reply_markup:
                payload["reply_markup"] = reply_markup
            return self._make_request("sendPhoto", payload)
        elif os.path.isfile(photo_url_or_path):
            return self._send_multipart("sendPhoto", "photo", photo_url_or_path, {
                "chat_id": str(target_chat),
                "caption": caption,
                "parse_mode": "HTML",
                "reply_markup": json.dumps(reply_markup) if reply_markup else None
            })
        else:
            return self.send_message(f"<b>[Медиа]</b>\n{caption}", chat_id=target_chat, reply_markup=reply_markup)

    def send_document(self, file_path, caption="", chat_id=None):
        target_chat = chat_id or self.channel_id
        if not os.path.isfile(file_path):
            return {"ok": False, "description": f"File not found: {file_path}"}
        return self._send_multipart("sendDocument", "document", file_path, {
            "chat_id": str(target_chat),
            "caption": caption,
            "parse_mode": "HTML"
        })

    def pin_chat_message(self, message_id, chat_id=None, disable_notification=False):
        target_chat = chat_id or self.channel_id
        if not self.bot_token or not target_chat:
            return {"ok": False, "description": "bot_token or chat_id not configured"}
        payload = {
            "chat_id": target_chat,
            "message_id": message_id,
            "disable_notification": disable_notification
        }
        return self._make_request("pinChatMessage", payload)

    def edit_message_text(self, message_id, text, chat_id=None, reply_markup=None, disable_preview=False):
        target_chat = chat_id or self.channel_id
        if not self.bot_token or not target_chat:
            return {"ok": False, "description": "bot_token or chat_id not configured"}
        payload = {
            "chat_id": target_chat,
            "message_id": message_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": disable_preview
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup
        return self._make_request("editMessageText", payload)

    def get_me(self):
        return self._make_request("getMe", {})

    def _make_request(self, method, payload):
        url = f"{self.base_url}/{method}"
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json", "User-Agent": "AnimeVistBot/1.0"}
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            try:
                return json.loads(e.read().decode('utf-8'))
            except Exception:
                return {"ok": False, "description": f"HTTP {e.code}: {e.reason}"}
        except Exception as e:
            return {"ok": False, "description": str(e)}

    def _send_multipart(self, method, file_field_name, file_path, fields):
        boundary = "----AnimeVistStandaloneBoundaryXYZ"
        url = f"{self.base_url}/{method}"
        body_parts = []

        for key, val in fields.items():
            if val is not None:
                body_parts.append(f"--{boundary}\r\n".encode('utf-8'))
                body_parts.append(f'Content-Disposition: form-data; name="{key}"\r\n\r\n'.encode('utf-8'))
                body_parts.append(f"{val}\r\n".encode('utf-8'))

        filename = os.path.basename(file_path)
        with open(file_path, "rb") as f:
            file_bytes = f.read()

        body_parts.append(f"--{boundary}\r\n".encode('utf-8'))
        body_parts.append(f'Content-Disposition: form-data; name="{file_field_name}"; filename="{filename}"\r\n'.encode('utf-8'))
        body_parts.append(b"Content-Type: application/octet-stream\r\n\r\n")
        body_parts.append(file_bytes)
        body_parts.append(b"\r\n")
        body_parts.append(f"--{boundary}--\r\n".encode('utf-8'))

        data = b"".join(body_parts)
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Content-Type": f"multipart/form-data; boundary={boundary}",
                "Content-Length": str(len(data)),
                "User-Agent": "AnimeVistBot/1.0"
            }
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return json.loads(resp.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            try:
                return json.loads(e.read().decode('utf-8'))
            except Exception:
                return {"ok": False, "description": f"HTTP {e.code}: {e.reason}"}
        except Exception as e:
            return {"ok": False, "description": str(e)}
