from rest_framework import viewsets, permissions, status
from rest_framework.permissions import AllowAny
from rest_framework.decorators import action
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from django.db.models import Q
from .models import Room, Message
from .serializers import RoomSerializer, MessageSerializer

User = get_user_model()


class RoomViewSet(viewsets.ModelViewSet):
    queryset = Room.objects.all()
    serializer_class = RoomSerializer
    # permission_classes = [permissions.IsAuthenticated]  # معلق مؤقتاً - تم تعطيل المصادقة
    permission_classes = [AllowAny]  # مؤقتاً للسماح بالوصول بدون مصادقة

    def get_queryset(self):
        user = self.request.user
        return Room.objects.filter(Q(participant1=user) | Q(participant2=user))

    def create(self, request, *args, **kwargs):
        # Ensure the current user is one of the participants
        participant2_id = request.data.get('participant2_id')
        if not participant2_id:
            return Response({'error': 'participant2_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            participant2 = User.objects.get(id=participant2_id)
        except User.DoesNotExist:
            return Response({'error': 'participant2 not found'}, status=status.HTTP_404_NOT_FOUND)

        user = request.user
        # Check if room exists in either order
        room = Room.objects.filter(
            (Q(participant1=user) & Q(participant2=participant2)) |
            (Q(participant1=participant2) & Q(participant2=user))
        ).first()
        if room:
            serializer = self.get_serializer(room)
            return Response(serializer.data, status=status.HTTP_200_OK)

        # Create new room with current user as participant1
        room = Room.objects.create(participant1=user, participant2=participant2)
        serializer = self.get_serializer(room)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


class MessageViewSet(viewsets.ModelViewSet):
    queryset = Message.objects.all()
    serializer_class = MessageSerializer
    # permission_classes = [permissions.IsAuthenticated]  # معلق مؤقتاً - تم تعطيل المصادقة
    permission_classes = [AllowAny]  # مؤقتاً للسماح بالوصول بدون مصادقة

    def get_queryset(self):
        user = self.request.user
        return Message.objects.filter(
            Q(room__participant1=user) | Q(room__participant2=user)
        )

    def perform_create(self, serializer):
        room = serializer.validated_data['room']
        user = self.request.user
        # Validate membership
        if user != room.participant1 and user != room.participant2:
            raise permissions.PermissionDenied('You are not a participant in this room')
        serializer.save(sender=user)

    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        message = self.get_object()
        user = request.user
        # Only participants other than sender can mark as read
        if user == message.sender:
            return Response({'error': 'Sender cannot mark own message as read'}, status=status.HTTP_400_BAD_REQUEST)
        if user != message.room.participant1 and user != message.room.participant2:
            return Response({'error': 'Not allowed'}, status=status.HTTP_403_FORBIDDEN)
        message.is_read = True
        message.save(update_fields=['is_read'])
        return Response({'message': 'Marked as read'})
    