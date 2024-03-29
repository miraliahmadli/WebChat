import asyncio
import json
from django.contrib.auth import get_user_model
from channels.consumer import AsyncConsumer
from channels.db import database_sync_to_async

from .models import Thread, ChatMessage

class ChatConsumer(AsyncConsumer):
    async def websocket_connect(self, event):
        # when socket connects
        print("connected", event)

        other_user = self.scope['url_route']['kwargs']['username']
        me = self.scope['user']
        # print(me, other_user)

        thread_obj = await self.get_thread(me, other_user)
        self.thread_obj = thread_obj
        chat_room = f"thread_{thread_obj.id}"
        self.chat_room = chat_room
        print(thread_obj)

        await self.channel_layer.group_add(
            chat_room,
            self.channel_name
        )

        await self.send({
            "type": "websocket.accept"
        })


    async def websocket_receive(self, event):
        # when message is received from the websocket
        print("received", event)

        front_text = event.get('text', event)
        if front_text is not None:
            loaded_data = json.loads(front_text)
            msg = loaded_data.get('message')
            
            user = self.scope['user']
            username = "default"
            if user.is_authenticated:
                username = user.username
            myResponse = {
                'message' : msg,
                "username" : username
            }
            
            await self.create_chat_message(user, msg)

            # broadcast the message event to be sent
            await self.channel_layer.group_send(
                self.chat_room,
                {
                    "type" : "chat_message",
                    "text" : json.dumps(myResponse)
                }
            )

    async def chat_message(self, event):
        # sends the message
        await self.send({
            "type" : "websocket.send",
            "text" : event['text']
        })
    async def websocket_disconnect(self, event):
        print("disconnected", event)

    @database_sync_to_async
    def get_thread(self, user, other_user):
        return Thread.objects.get_or_new(user, other_user)[0]

    @database_sync_to_async
    def create_chat_message(self, user, msg):
        return ChatMessage.objects.create(thread = self.thread_obj, user = user, message = msg)
    