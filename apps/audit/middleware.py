import json
from django.utils.deprecation import MiddlewareMixin
from django.contrib.contenttypes.models import ContentType
from .models import AuditLog


class AuditMiddleware(MiddlewareMixin):
    """Middleware to log user activities."""
    
    def process_request(self, request):
        """Process request to store information for logging."""
        # Store request information for later use
        request._audit_data = {
            'ip_address': self.get_client_ip(request),
            'user_agent': request.META.get('HTTP_USER_AGENT', ''),
        }
        return None
    
    def process_response(self, request, response):
        """Process response to log activities."""
        # Only log for authenticated users
        if hasattr(request, 'user') and request.user.is_authenticated:
            # Get request information
            audit_data = getattr(request, '_audit_data', {})
            ip_address = audit_data.get('ip_address', '')
            user_agent = audit_data.get('user_agent', '')
            
            # Determine action based on HTTP method and path
            method = request.method
            path = request.path
            
            action = 'other'
            description = f"{method} {path}"
            
            # Login action
            if path == '/api/v1/accounts/login/' and method == 'POST':
                action = 'login'
                description = 'User logged in'
            
            # Logout action
            elif path == '/api/v1/accounts/logout/' and method == 'POST':
                action = 'logout'
                description = 'User logged out'
            
            # Create actions
            elif method == 'POST':
                action = 'create'
                if '/cases/' in path:
                    description = 'Created a new case'
                elif '/appointments/' in path:
                    description = 'Created a new appointment'
                elif '/evaluations/' in path:
                    description = 'Created a new evaluation'
                elif '/community/' in path:
                    description = 'Created new community content'
                elif '/attachments/' in path:
                    description = 'Uploaded a new attachment'
            
            # Update actions
            elif method in ['PUT', 'PATCH']:
                action = 'update'
                if '/cases/' in path:
                    description = 'Updated a case'
                elif '/appointments/' in path:
                    description = 'Updated an appointment'
                elif '/community/' in path:
                    description = 'Updated community content'
            
            # Delete actions
            elif method == 'DELETE':
                action = 'delete'
                if '/cases/' in path:
                    description = 'Deleted a case'
                elif '/appointments/' in path:
                    description = 'Deleted an appointment'
                elif '/community/' in path:
                    description = 'Deleted community content'
                elif '/attachments/' in path:
                    description = 'Deleted an attachment'
            
            # Download actions
            elif '/download/' in path:
                action = 'download'
                description = 'Downloaded an attachment'
            
            # View actions
            elif method == 'GET':
                action = 'view'
                if '/cases/' in path and len(path.split('/')) > 4:  # Specific case
                    description = 'Viewed a case'
                elif '/appointments/' in path and len(path.split('/')) > 4:  # Specific appointment
                    description = 'Viewed an appointment'
                elif '/community/' in path and len(path.split('/')) > 4:  # Specific content
                    description = 'Viewed community content'
            
            # Create audit log
            AuditLog.objects.create(
                user=request.user,
                action=action,
                description=description,
                ip_address=ip_address,
                user_agent=user_agent,
                additional_data={
                    'method': method,
                    'path': path,
                    'status_code': response.status_code,
                }
            )
        
        return response
    
    def get_client_ip(self, request):
        """Get the client IP address."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip