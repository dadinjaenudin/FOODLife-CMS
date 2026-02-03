"""
Session persistence middleware - ensure session is always saved
"""


class SessionPersistenceMiddleware:
    """
    Explicitly mark session as modified setiap request
    Ini memastikan session selalu di-save ke database+cache
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        
        # Ensure session is saved jika user authenticated
        if request.user.is_authenticated:
            # Mark session as modified untuk force save
            request.session.modified = True
            
            # Ensure session cookie is set properly on response
            # This prevents session loss during navigation
            if hasattr(request, 'session') and request.session.session_key:
                response.set_cookie(
                    key='foodlife_sessionid',
                    value=request.session.session_key,
                    max_age=60 * 60 * 12,  # 12 hours
                    path='/',
                    secure=False,  # Set to True in production with HTTPS
                    httponly=True,
                    samesite='Lax'
                )
        
        return response
