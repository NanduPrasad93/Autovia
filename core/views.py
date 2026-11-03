from django.shortcuts import render, redirect
from django.contrib import messages
from .models import ContactMessage


def home(request):
    """Homepage view showcasing AutoVia features, services, and highlights."""
    return render(request, 'core/home.html', {
        'page_title': 'AutoVia – Integrated Automobile Management and Assistance System',
    })


def about(request):
    """About page view describing AutoVia mission, vision, and team."""
    return render(request, 'core/about.html', {
        'page_title': 'About Us | AutoVia',
    })


def services_view(request):
    """Services view detailing all platform automobile capabilities."""
    return render(request, 'core/services.html', {
        'page_title': 'Our Services | AutoVia',
    })


def contact(request):
    """Contact page view with form submission and validation."""
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip()
        subject = request.POST.get('subject', '').strip()
        message = request.POST.get('message', '').strip()

        if not name or not email or not subject or not message:
            messages.error(request, 'Please complete all fields before sending your message.')
        elif '@' not in email or '.' not in email:
            messages.error(request, 'Please enter a valid email address.')
        else:
            ContactMessage.objects.create(
                name=name,
                email=email,
                subject=subject,
                message=message
            )
            messages.success(request, 'Thank you! Your message has been sent successfully. Our team will get in touch with you shortly.')
            return redirect('core:contact')

    return render(request, 'core/contact.html', {
        'page_title': 'Contact Us | AutoVia',
    })


def login_placeholder(request):
    """Redirect to accounts login view."""
    return redirect('accounts:login')


def register_placeholder(request):
    """Redirect to accounts register view."""
    return redirect('accounts:register')
