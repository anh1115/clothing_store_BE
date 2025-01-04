from django.urls import path
from .views import register, user_login, user_logout, user_detail, update_user, change_password

urlpatterns = [
    path('register/', register, name='register'),
    path('login/', user_login, name='login'),
    path('logout/', user_logout, name='logout'),
    path('detail/', user_detail, name='user_detail'),
    path('update/', update_user, name='update_user'),
    path('change-password/', change_password, name='change_password'),
]
