"""
URL configuration for armitagen project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('home.urls', namespace='home')),
    path('team/', include('team.urls', namespace='team')),
    path('services/', include('services.urls', namespace='services')),
    path('council/', include('council.urls', namespace='council')),
    path('blog/', include('blog.urls', namespace='blog')),
    path('academy/', include('academy.urls', namespace='academy')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler404 = 'errors.views.custom_404'
handler500 = 'errors.views.custom_500'
handler400 = 'errors.views.custom_400'
handler403 = 'errors.views.custom_403'