from django.urls import path 
from . import views #get all function in views

urlpatterns = [
    path('add/', views.registerUser),
    path('logout/', views.logoutUser),
    path('get/<str:user_id>', views.getUserDetail),
    path('update/<str:user_id>', views.updateDetail),
    path('login/', views.login),
    # path('getGarment/<str:garment_id>', views.getGarment),
]