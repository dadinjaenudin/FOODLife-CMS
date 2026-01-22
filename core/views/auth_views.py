from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages


def login_view(request):
    """
    User login view with HTMX support
    """
    if request.user.is_authenticated:
        return redirect('dashboard:index')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            messages.success(request, f'Welcome back, {user.get_full_name() or user.username}!')
            
            # Check if HTMX request
            if request.htmx:
                response = redirect('dashboard:index')
                response['HX-Redirect'] = '/dashboard/'
                return response
            
            return redirect('dashboard:index')
        else:
            messages.error(request, 'Invalid username or password.')
            
            if request.htmx:
                return render(request, 'auth/partials/login_form.html', {
                    'error': 'Invalid credentials'
                })
    
    return render(request, 'auth/login.html')


@login_required
def logout_view(request):
    """
    User logout view
    """
    logout(request)
    messages.info(request, 'You have been logged out successfully.')
    return redirect('auth:login')
