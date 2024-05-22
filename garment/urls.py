from django.urls import path 
from . import views #get all function in views

urlpatterns = [
    path('getAll/', views.getAllGarments),
    path('getGarment/<str:garment_id>', views.getGarment),
    path ('add/', views.addGarment),
    # datatype:paramter name at the function 
    path ('update/<str:garment_id>', views.updateGarment),
    path ('delete/', views.deleteGarment),
    path('submitImage', views.processGarmentImage),
]