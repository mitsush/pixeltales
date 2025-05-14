import logging
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, Http404
from django.contrib.auth.models import User
from django.db.models import Q
from .models import ChatRoom, Message
from social_network.models import Profile

logger = logging.getLogger('chat_logger')

@login_required
def chat_rooms(request):
    """Show all chat rooms for the current user"""
    user = request.user
    chat_rooms = ChatRoom.objects.filter(participants=user).order_by('-created_at')
    
    # Calculate unread message count for each room
    for room in chat_rooms:
        room.unread_count = Message.objects.filter(
            room=room
        ).exclude(
            user=user
        ).filter(
            is_read=False
        ).count()
    
    return render(request, 'chat/rooms.html', {
        'chat_rooms': chat_rooms
    })

@login_required
def room(request, room_id):
    """Show a specific chat room"""
    room = get_object_or_404(ChatRoom, id=room_id)
    
    # Check if user is participant
    if request.user not in room.participants.all():
        return redirect('chat_rooms')
        
    # Mark messages as read
    Message.objects.filter(room=room).exclude(user=request.user).update(is_read=True)
    
    # Get room messages
    messages = Message.objects.filter(room=room).order_by('timestamp')
    
    # For group chats, get other participants
    other_participants = room.participants.exclude(id=request.user.id)
    
    return render(request, 'chat/room.html', {
        'room_name': room.name,
        'room_id': room.id,
        'room_type': room.type,
        'messages': messages,
        'other_participants': other_participants,
    })

@login_required
def create_private_chat(request, friend_id):
    """Create or get a private chat with a friend"""
    user = request.user
    friend = get_object_or_404(User, id=friend_id)
    
    # Check if they are friends
    if not user.profile.is_friend(friend.profile):
        logger.warning(f"User {user.username} tried to create chat with non-friend {friend.username}")
        return redirect('list_friends')
    
    # Check if a private chat already exists
    existing_rooms = ChatRoom.objects.filter(
        type='private',
        participants=user
    ).filter(
        participants=friend
    )
    
    if existing_rooms.exists() and existing_rooms.first().participants.count() == 2:
        # Return existing room
        return redirect('room', room_id=existing_rooms.first().id)
    
    # Create new private chat room
    room_name = f"Chat between {user.username} and {friend.username}"
    new_room = ChatRoom.objects.create(name=room_name, type='private')
    new_room.participants.add(user, friend)
    
    logger.info(f"New private chat created between {user.username} and {friend.username}")
    
    return redirect('room', room_id=new_room.id)

# chat/views.py

@login_required
def create_group_chat(request):
    """Create a new group chat"""
    if request.method == 'POST':
        name = request.POST.get('name')
        participant_ids = request.POST.getlist('participants')
        
        if not name:
            messages.error(request, 'Group name is required')
            return redirect('create_group_chat')
        
        # Create room
        new_room = ChatRoom.objects.create(name=name, type='group')
        
        # Add creator
        new_room.participants.add(request.user)
        
        # Add participants (check if they are friends)
        participants_added = 0
        for participant_id in participant_ids:
            try:
                participant = User.objects.get(id=participant_id)
                if request.user.profile.is_friend(participant.profile):
                    new_room.participants.add(participant)
                    participants_added += 1
            except User.DoesNotExist:
                pass
        
        # Log for debugging
        logger = logging.getLogger('chat_logger')
        logger.info(f"New group chat '{name}' created by {request.user.username} with {participants_added} participants")
        
        return redirect('room', room_id=new_room.id)
    
    # Show create group chat form
    user = request.user
    
    # Get user's profile and friends
    try:
        profile = Profile.objects.get(user=user)
        friends_profiles = profile.friends.all()
        friends = [profile.user for profile in friends_profiles]
    except Profile.DoesNotExist:
        friends = []
    
    return render(request, 'chat/create_group.html', {
        'friends': friends
    })
    
@login_required
def unread_message_count(request):
    """Get count of unread messages for the current user"""
    unread_count = Message.objects.filter(
        room__participants=request.user
    ).exclude(
        user=request.user
    ).filter(
        is_read=False
    ).count()
    
    return JsonResponse({'unread_count': unread_count})