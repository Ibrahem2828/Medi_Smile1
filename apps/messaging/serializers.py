from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Room, Message
from apps.accounts.serializers import UserSerializer

User = get_user_model()


class RoomSerializer(serializers.ModelSerializer):
    participant1 = UserSerializer(read_only=True)
    participant2 = UserSerializer(read_only=True)
    participant1_id = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), source='participant1', write_only=True)
    participant2_id = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), source='participant2', write_only=True)

    class Meta:
        model = Room
        fields = ['id', 'participant1', 'participant2', 'participant1_id', 'participant2_id', 'created_at']
        read_only_fields = ['id', 'created_at']


class MessageSerializer(serializers.ModelSerializer):
    sender = UserSerializer(read_only=True)
    room = serializers.PrimaryKeyRelatedField(queryset=Room.objects.all())

    class Meta:
        model = Message
        fields = ['id', 'room', 'sender', 'content', 'sent_at', 'is_read']
        read_only_fields = ['id', 'sender', 'sent_at']