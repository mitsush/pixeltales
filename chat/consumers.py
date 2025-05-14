# chat/consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import ChatRoom, Message
from django.contrib.auth.models import User
import logging

logger = logging.getLogger('chat_logger')

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.room_group_name = f"chat_{self.room_id}"
        
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        # Check if user is allowed in this room
        user = self.scope["user"]
        
        # Log connection attempt
        logger.info(f"WebSocket connection attempt: user={user.username}, room_id={self.room_id}")
        
        if not await self.is_user_in_room(user, self.room_id):
            logger.warning(f"User {user.username} tried to connect to room {self.room_id} but is not a participant")
            await self.close()
            return
            
        await self.accept()
        logger.info(f"WebSocket connection accepted: user={user.username}, room_id={self.room_id}")
        
        # Send user's previous messages when they connect
        previous_messages = await self.get_previous_messages(self.room_id, 50)
        for message in previous_messages:
            await self.send(text_data=json.dumps({
                'message_id': message['id'],
                'message': message['content'],
                'user': message['username'],
                'timestamp': message['timestamp'],
            }))

    async def disconnect(self, close_code):
        logger.info(f"WebSocket disconnected: user={self.scope['user'].username}, room_id={self.room_id}, code={close_code}")
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    # Receive message from WebSocket
    async def receive(self, text_data):
        try:
            text_data_json = json.loads(text_data)
            message = text_data_json['message']
            user = self.scope["user"]
            
            logger.info(f"Message received: user={user.username}, room_id={self.room_id}, message={message[:20]}...")
            
            # Save message to database
            message_obj = await self.save_message(user.id, self.room_id, message)
            
            # Send message to room group
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message_id': message_obj['id'],
                    'message': message,
                    'user_id': user.id,
                    'username': user.username,
                    'timestamp': message_obj['timestamp'],
                }
            )
        except Exception as e:
            logger.error(f"Error in receive method: {str(e)}")
            await self.send(text_data=json.dumps({
                'error': 'Failed to process message'
            }))

    # Receive message from room group
    async def chat_message(self, event):
        try:
            # Send message to WebSocket
            await self.send(text_data=json.dumps({
                'message_id': event['message_id'],
                'message': event['message'],
                'user': event['username'],
                'timestamp': event['timestamp'],
            }))
            logger.info(f"Message sent to client: user={self.scope['user'].username}, room_id={self.room_id}")
        except Exception as e:
            logger.error(f"Error in chat_message method: {str(e)}")
    
    @database_sync_to_async
    def is_user_in_room(self, user, room_id):
        try:
            room = ChatRoom.objects.get(id=room_id)
            return user in room.participants.all()
        except ChatRoom.DoesNotExist:
            return False
    
    @database_sync_to_async
    def save_message(self, user_id, room_id, content):
        user = User.objects.get(id=user_id)
        room = ChatRoom.objects.get(id=room_id)
        message = Message.objects.create(
            user=user,
            room=room,
            content=content
        )
        return {
            'id': message.id,
            'timestamp': message.timestamp.isoformat(),
        }
    
    @database_sync_to_async
    def get_previous_messages(self, room_id, limit=50):
        messages = Message.objects.filter(room_id=room_id).order_by('-timestamp')[:limit]
        result = []
        for message in reversed(messages):
            result.append({
                'id': message.id,
                'content': message.content,
                'username': message.user.username,
                'timestamp': message.timestamp.isoformat(),
            })
        return result