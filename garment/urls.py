from django.urls import path 
from . import views

urlpatterns = [
    path('getAll/', views.getAllGarments),
    path('getGarment/<str:garment_id>', views.getGarment),
    path ('add/', views.addGarment),
    path ('submitImage', views.processGarmentImage),
    path ('update/<str:garment_id>', views.updateGarment),
    path ('delete/', views.deleteGarment),
    path('getTotalGarment', views.getTotalGarmentNo),
    path('getBrandAnalysis', views.getBrandAnalysis),
    path('getCountryAnalysis', views.getCountryAnalysis),
    path('getColourAnalysis', views.getColourAnalysis),
    path('getSizeAnalysis', views.getSizeAnalysis),
    path('detectMaterial', views.detectMaterial),
    # for website
    path('getTotalNumberUserCount', views.getTotalNumberUserCount),
    # path('getTotalNumberGarmentCount', views.getTotalNumberGarmentCount),
    path('getTotalVarianceCountForGarment', views.getTotalVarianceCountForGarment),
    path('getGarmentByDuration/<int:duration>', views.getGarmentByDuration),
    path('getGarmentCategoriesChart', views.getGarmentCategoriesChart),
]