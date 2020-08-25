import random
class ChatBot:
    COIN_BLOCK = {
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": (
                "hello \n\n"
            ),
        },
    }

    def __init__(self, channel):
        self.channel = channel

    def _flip_coin(self):
        rand_int = random.randint(0, 1)
        if rand_int == 0:
            results = "how are you ?"
        else:
            results = "whatsapp !!!"

        text = f" {results}"

        return {"type": "section", "text": {"type": "mrkdwn", "text": text}},

    def get_message_payload(self):
        return {
            "channel": self.channel,
            "blocks": [
                self.COIN_BLOCK,
                *self._flip_coin(),
            ],
        }