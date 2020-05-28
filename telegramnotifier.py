import requests

class TelegramNotifier:
    def __init__(self, token, chat_ids):
        self.token = token
        self.chat_ids = chat_ids

    def send(self, message):
        for cid in self.chat_ids:
            payload = {
                'chat_id': cid,
                'text': message,
                'parse_mode': 'HTML'
            }
            res = requests.post("https://api.telegram.org/bot%s/sendMessage" % self.token, data=payload).content
