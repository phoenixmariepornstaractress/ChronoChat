# ChronoChat

Exciting News: ChronoChat is Coming to GitHub!

I'm thrilled to announce that I'll be uploading ChronoChat to GitHub soon. This innovative Telegram bot project is designed to automate and schedule messages, with plenty of room for further enhancement.

I'm actively seeking skilled Python developers with experience in creating Telegram bots to join the project. If you're interested in collaborating to enhance and expand the features of ChronoChat, your expertise would be greatly appreciated.

Please consider contributing to this exciting project and help make ChronoChat even better!

To get a group's or channel's ID using the Telegram Bot API via getUpdates, you can follow these steps:
1) Send a message in the group or channel: First, add your bot to the group or channel. After that, Send any message in the group or channel to create an update that the bot can retrieve.
2) Use the getUpdates method: Make an API request to getUpdates to get the latest updates your bot has received. Replace <BOT_ID> with your bot's actual token.
3) Check the response: The response will be a JSON object containing the updates (messages, etc.) that the bot has received.  Look for the message object within the response. It contains a field named chat.  The chat object includes an id field, which is the unique identifier of the group or channel.


https://api.telegram.org/bot<BOT_ID>/getUpdates

https://api.telegram.org/bot<token>/sendMessage?chat_id=<chat_id>&text=<your_message>
