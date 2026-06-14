from django.shortcuts import render

from django.shortcuts import render, redirect
from django.contrib import messages
from .forms import UserRegisterForm

def register(request):
    if request.user.is_authenticated:
        return redirect('groups_dashboard')
        
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Save the display name in user.first_name for easy display
            user.first_name = form.cleaned_data.get('first_name')
            user.save()
            
            messages.success(request, f"Account created successfully for {user.username}! You can now login.")
            return redirect('login')
        else:
            messages.error(request, "Failed to create account. Please check the errors below.")
    else:
        form = UserRegisterForm()
        
    return render(request, 'accounts/register.html', {'form': form})

