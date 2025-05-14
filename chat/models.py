from django.db import models
from django.contrib.auth.models import User

class ChatRoom(models.Model):
    ROOM_TYPES = [
        ('private', 'Private Chat'),
        ('group', 'Group Chat'),
    ]
    
    name = models.CharField(max_length=255)
    type = models.CharField(max_length=7, choices=ROOM_TYPES, default='private')
    created_at = models.DateTimeField(auto_now_add=True)
    participants = models.ManyToManyField(User, related_name='chat_rooms')
    
    def __str__(self):
        return f"{self.name} ({self.get_type_display()})"
        
    def add_participant(self, user):
        self.participants.add(user)
        
    def remove_participant(self, user):
        self.participants.remove(user)
        
    @property
    def group_name(self):
        """Return the group name for the WebSocket group"""
        return f"chat_{self.id}"

class Message(models.Model):
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='messages', null=True)
    is_read = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['timestamp']
    
    def __str__(self):
        return f"{self.user.username}: {self.content[:30]}"