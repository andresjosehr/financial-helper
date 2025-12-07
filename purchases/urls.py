from django.urls import path
from . import views

app_name = 'purchases'

urlpatterns = [
    path('', views.purchase_list, name='list'),
    path('update-telegram-user/', views.update_telegram_user, name='update_telegram_user'),
    path('<uuid:pk>/', views.purchase_detail, name='detail'),
    path('<uuid:pk>/delete/', views.delete_purchase, name='delete'),
    path('<uuid:pk>/update-total/', views.update_purchase_total, name='update_total'),
    path('<uuid:pk>/update-rates/', views.update_purchase_rates, name='update_rates'),
    path('<uuid:pk>/items/<uuid:item_pk>/update/', views.update_purchase_item, name='update_item'),
]
