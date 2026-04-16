from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from .forms import UploadForm
from .models import Professor
import pandas as pd
from django.core.mail import get_connection, EmailMessage
from django.conf import settings
import ssl
import certifi

ALLOWED_EMAIL_DOMAIN = '@ifheindia.org'

def signup(request):
    error = None
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        email = request.POST.get('email', '').strip()
        if not email.endswith(ALLOWED_EMAIL_DOMAIN):
            error = f'Only {ALLOWED_EMAIL_DOMAIN} email addresses are allowed.'
        elif form.is_valid():
            user = form.save()
            user.email = email
            user.save()
            login(request, user)
            return redirect('/')
    else:
        form = UserCreationForm()
    return render(request, 'registration/signup.html', {
        'form': form,
        'error': error,
        'domain': ALLOWED_EMAIL_DOMAIN
    })

@login_required
def upload_file(request):
    message = ""
    data = []

    try:
        prof = request.user.professor
    except Professor.DoesNotExist:
        # Professor profile doesn't exist — let them set it up themselves
        if request.method == 'POST' and 'app_password' in request.POST:
            app_password = request.POST.get('app_password', '').strip()
            if app_password:
                Professor.objects.create(
                    user=request.user,
                    app_password=app_password
                )
                return redirect('/')
        return render(request, 'setup_profile.html', {
            'email': request.user.email,
            'username': request.user.username
        })

    if request.method == 'POST':
        form = UploadForm(request.POST, request.FILES)
        if form.is_valid():
            instance = form.save()
            file_path = instance.file.path

            df = pd.read_excel(file_path, dtype={'Enrollment Number': str})
            df.columns = df.columns.str.strip().str.lower()
            df.rename(columns={
                'enrollment number': 'enrollment',
                'name': 'name',
                'mail': 'mail',
                'marks': 'marks'
            }, inplace=True)

            ssl_context = ssl.create_default_context(cafile=certifi.where())

            connection = get_connection(
                backend='django.core.mail.backends.smtp.EmailBackend',
                host=settings.EMAIL_HOST,
                port=settings.EMAIL_PORT,
                username=request.user.email,
                password=prof.app_password,
                use_tls=True,
                ssl_context=ssl_context,
            )

            success_count = 0
            fail_count = 0
            connection.open()

            for _, row in df.iterrows():
                try:
                    name = str(row['name'])
                    email = str(row['mail'])
                    marks = row['marks']

                    email_message = f"""Hi {name},

Your marks are: {marks}

Regards,
{request.user.get_full_name() or request.user.username}"""

                    msg = EmailMessage(
                        subject=f"Marks for {name}",
                        body=email_message,
                        from_email=request.user.email,
                        to=[email],
                        connection=connection,
                    )
                    msg.send()
                    success_count += 1

                except Exception as e:
                    print("Error:", e)
                    fail_count += 1

            connection.close()
            data = df.values.tolist()

            return render(request, 'success.html', {
                'success_count': success_count,
                'fail_count': fail_count,
                'data': data
            })

    else:
        form = UploadForm()

    return render(request, 'upload.html', {
        'form': form,
        'professor_email': request.user.email,
        'professor_name': request.user.get_full_name() or request.user.username,
    })