from django.test import TestCase
from django.contrib.auth import get_user_model
from cases.models import Case
from .models import Conversation, Message, Notification

User = get_user_model()


class MessagingModelsTest(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(
            email='patient@example.com',
            password='password123',
            first_name='John',
            last_name='Doe',
            role='patient'
        )
        
        self.user2 = User.objects.create_user(
            email='student@example.com',
            password='password123',
            first_name='Jane',
            last_name='Smith',
            role='student'
        )
        
        self.case = Case.objects.create(
            university_id=self.user2.university.id,
            patient=self.user1
        )
        
        self.conversation = Conversation.objects.create(case=self.case)
    
    def test_conversation_creation(self):
        self.assertEqual(self.conversation.case, self.case)
        self.assertEqual(str(self.conversation), f"Conversation for Case {self.case.id}")
    
    def test_message_creation(self):
        message = Message.objects.create(
            conversation=self.conversation,
            sender=self.user1,
            body="Hello, this is a test message"
        )
        self.assertEqual(message.conversation, self.conversation)
        self.assertEqual(message.sender, self.user1)
        self.assertEqual(message.body, "Hello, this is a test message")
        self.assertEqual(str(message), f"Message from {self.user1.first_name} in {self.conversation}")
    
    def test_notification_creation(self):
        notification = Notification.objects.create(
            user=self.user2,
            type='test_notification',
            payload={'key': 'value'}
        )
        self.assertEqual(notification.user, self.user2)
        self.assertEqual(notification.type, 'test_notification')
        self.assertEqual(notification.payload, {'key': 'value'})
        self.assertEqual(str(notification), f"Notification for {self.user2.first_name}: test_notification")