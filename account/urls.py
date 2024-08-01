from django.urls import path 
from . import views #get all function in views

urlpatterns = [
    path('add/', views.registerUser),
    path('logout/', views.logoutUser),
    path('get/', views.getUserDetail),
    path('update/', views.updateDetail),
    path('login/', views.login),
    path('refreshToken/', views.refreshToken),
    path('resetPassword/', views.resetPassword),
    # path('getGarment/<str:garment_id>', views.getGarment),
]