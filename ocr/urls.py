from django.urls import path
from . import views

app_name = 'ocr'

urlpatterns = [
    path('extract-text/', views.extract_text_from_image, name='extract_text'),
    path('status/', views.api_status, name='status'),
]
