from django.urls import path
from . import views

urlpatterns = [
    path('getTemperature', views.getTemperatureHumidity),
    path('getRecommendation', views.getRecommendedClothes)
]