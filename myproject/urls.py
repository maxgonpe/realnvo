from django.contrib.auth import views as auth_views
from django.contrib.auth.views import LogoutView
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('',include("extintores.urls")),
    path('login/', auth_views.LoginView.as_view(template_name='registro/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='intervencion_lista'), name='logout'),
    path('summernote/', include('django_summernote.urls')),
]
