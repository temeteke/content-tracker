from django.urls import path
from content.api import api

urlpatterns = [path("api/", api.urls)]
