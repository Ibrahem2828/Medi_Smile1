from django.test import TestCase
from django.contrib.auth import get_user_model
from .models import (
    PatientProfile, StudentProfile, 
    SupervisorProfile, UniversityAdminProfile, TechSupportProfile
)

User = get_user_model()


class UserModelTest(TestCase):
    """Test cases for User model."""
    
    def test_create_user(self):
        """Test creating a user."""
        user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            first_name='Test',
            last_name='User',
            password='testpass123'
        )
        self.assertEqual(user.email, 'test@example.com')
        self.assertEqual(user.username, 'testuser')
        self.assertEqual(user.first_name, 'Test')
        self.assertEqual(user.last_name, 'User')
        self.assertTrue(user.check_password('testpass123'))
        self.assertEqual(user.role, 'patient')  # Default role
    
    def test_create_user_with_role(self):
        """Test creating a user with a specific role."""
        user = User.objects.create_user(
            email='student@example.com',
            username='student',
            first_name='Student',
            last_name='User',
            password='testpass123',
            role='student'
        )
        self.assertEqual(user.role, 'student')
    
    def test_create_superuser(self):
        """Test creating a superuser."""
        admin_user = User.objects.create_superuser(
            email='admin@example.com',
            username='admin',
            first_name='Admin',
            last_name='User',
            password='adminpass123'
        )
        self.assertTrue(admin_user.is_staff)
        self.assertTrue(admin_user.is_superuser)


class ProfileModelTest(TestCase):
    """Test cases for Profile models."""
    
    def setUp(self):
        """Set up test data."""
        self.patient_user = User.objects.create_user(
            email='patient@example.com',
            username='patient',
            first_name='Patient',
            last_name='User',
            password='testpass123',
            role='patient'
        )
        self.student_user = User.objects.create_user(
            email='student@example.com',
            username='student',
            first_name='Student',
            last_name='User',
            password='testpass123',
            role='student'
        )
        self.supervisor_user = User.objects.create_user(
            email='supervisor@example.com',
            username='supervisor',
            first_name='Supervisor',
            last_name='User',
            password='testpass123',
            role='supervisor'
        )
        self.university_admin_user = User.objects.create_user(
            email='university_admin@example.com',
            username='university_admin',
            first_name='University',
            last_name='Admin',
            password='testpass123',
            role='university_admin'
        )
        self.tech_support_user = User.objects.create_user(
            email='tech_support@example.com',
            username='tech_support',
            first_name='Tech',
            last_name='Support',
            password='testpass123',
            role='tech_support'
        )
    
    def test_patient_profile_creation(self):
        """Test patient profile creation."""
        profile = PatientProfile.objects.get(user=self.patient_user)
        self.assertEqual(profile.user, self.patient_user)
    
    def test_student_profile_creation(self):
        """Test student profile creation."""
        profile = StudentProfile.objects.get(user=self.student_user)
        self.assertEqual(profile.user, self.student_user)
    
    def test_supervisor_profile_creation(self):
        """Test supervisor profile creation."""
        profile = SupervisorProfile.objects.get(user=self.supervisor_user)
        self.assertEqual(profile.user, self.supervisor_user)
    
    def test_university_admin_profile_creation(self):
        """Test university admin profile creation."""
        profile = UniversityAdminProfile.objects.get(user=self.university_admin_user)
        self.assertEqual(profile.user, self.university_admin_user)
    
    def test_tech_support_profile_creation(self):
        """Test tech support profile creation."""
        profile = TechSupportProfile.objects.get(user=self.tech_support_user)
        self.assertEqual(profile.user, self.tech_support_user)