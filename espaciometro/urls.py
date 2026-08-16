from django.urls import path

from . import views


app_name = "espaciometro"


urlpatterns = [
    path("",views.dashboard,name="dashboard",),
    path("estructura/",views.estructura,name="estructura",),
]