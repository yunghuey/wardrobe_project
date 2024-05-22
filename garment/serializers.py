from rest_framework import serializers
from garment.models import Garment

class GarmentSerializer(serializers.ModelSerializer):
    # convert json data into python object
    class Meta:
        model = Garment
        fields = '__all__'