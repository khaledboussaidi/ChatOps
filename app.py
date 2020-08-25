import os
import logging
from flask import Flask
from slack import WebClient
from slackeventsapi import SlackEventAdapter
from chatBot import ChatBot

app = Flask(__name__)
SLACK_EVENTS_TOKEN="f05b22b4a1e23fd0cd53fe19bc31365b"
slack_events_adapter = SlackEventAdapter(SLACK_EVENTS_TOKEN, "/slack/events", app)

SLACK_TOKEN='xoxb-1304583701447-1343214786064-zmVH4hBms1ZTQgD2RdW8Fvqj'
slack_web_client = WebClient(token=SLACK_TOKEN)

def flip_coin(channel):

    coin_bot = ChatBot(channel)

    message = coin_bot.get_message_payload()

    slack_web_client.chat_postMessage(**message)



@slack_events_adapter.on("message")
def message(payload):

    event = payload.get("event", {})

    text = event.get("text")


    if "hey"in text.lower():

        channel_id = event.get("channel")


        return flip_coin(channel_id)

if __name__ == "__main__":
    logger = logging.getLogger()

    logger.setLevel(logging.DEBUG)

    logger.addHandler(logging.StreamHandler())


    app.run(host='0.0.0.0', port=8080)