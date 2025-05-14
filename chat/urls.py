from django.urls import path
from . import views

urlpatterns = [
    path('', views.chat_rooms, name='chat_rooms'),
    path('<int:room_id>/', views.room, name='room'),
    path('create/private/<int:friend_id>/', views.create_private_chat, name='create_private_chat'),
    path('create/group/', views.create_group_chat, name='create_group_chat'),
    path('unread/count/', views.unread_message_count, name='unread_message_count'),
]

from django.conf import settings
from django.conf.urls.static import static

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)