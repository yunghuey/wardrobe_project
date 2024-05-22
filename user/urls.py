from django.urls import path 
from . import views #get all function in views

urlpatterns = [
    path('add/', views.registerUser),
    # path('getGarment/<str:garment_id>', views.getGarment),
]