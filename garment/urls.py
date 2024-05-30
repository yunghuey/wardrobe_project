from django.urls import path 
from . import views #get all function in views

urlpatterns = [
    path('getAll/', views.getAllGarments),
    path('getGarment/<str:garment_id>', views.getGarment),
    path ('add/', views.addGarment),
    path ('submitImage', views.processGarmentImage),
    path ('update/<str:garment_id>', views.updateGarment),
    path ('delete/', views.deleteGarment),
    path('add', views.processGarmentImage),
    path('getInfo', views.getStatisticNumber),
]