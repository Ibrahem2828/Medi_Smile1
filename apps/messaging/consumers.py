import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from .models import Room, Message

User = get_user_model()


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.conversation_group_name = f'chat_{self.room_id}'
        # Require authenticated user
        user = self.scope.get('user')
        if not user or not user.is_authenticated:
            await self.close()
            return
        # Ensure user is a participant in the conversation
        is_participant = await self.is_participant(self.room_id, user.id)
        if not is_participant:
            await self.close()
            return
        
        # Join room group
        await self.channel_layer.group_add(
            self.conversation_group_name,
            self.channel_name
        )
        
        await self.accept()
    
    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.conversation_group_name,
            self.channel_name
        )
    
    # Receive message from WebSocket
    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message_content = text_data_json['message']
        user = self.scope['user']
        
        # Get room
        room = await self.get_room(self.room_id)
        
        # Save message to database
        message = await self.save_message(room, user, message_content)
        
        # Send message to room group
        await self.channel_layer.group_send(
            self.conversation_group_name,
            {
                'type': 'chat_message',
                'message': {
                    'id': str(message.id),
                    'sender': {
                        'id': str(user.id),
                        'first_name': user.first_name,
                        'last_name': user.last_name
                    },
                    'content': message.content,
                    'sent_at': message.sent_at.isoformat()
                }
            }
        )
    
    # Receive message from room group
    async def chat_message(self, event):
        message = event['message']
        
        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'message': message
        }))
    
    @database_sync_to_async
    def get_room(self, room_id):
        return Room.objects.get(id=room_id)
    
    @database_sync_to_async
    def save_message(self, room, user, content):
        return Message.objects.create(
            room=room,
            sender=user,
            content=content
        )

    @database_sync_to_async
    def is_participant(self, room_id, user_id):
        room = Room.objects.get(id=room_id)
        return room.participant1_id == user_id or room.participant2_id == user_id