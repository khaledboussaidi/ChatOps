from slack import WebClient
from chatBot import ChatBot
import os
token = '********'

# Create a slack client
slack_web_client = WebClient(token=token)

# Get a new CoinBot
coin_bot = ChatBot("#general")

# Get the onboarding message payload
message = coin_bot.get_message_payload()

# Post the onboarding message in Slack
slack_web_client.chat_postMessage(**message)