from django.contrib import admin
from .models import Room, Message


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ('id', 'participant1', 'participant2', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('id', 'participant1__email', 'participant2__email')


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'room', 'sender', 'sent_at', 'is_read')
    list_filter = ('sent_at', 'is_read')
    search_fields = ('room__id', 'sender__email', 'content')