from rest_framework import serializers
from .models import User

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['email', 'username','password','first_name','last_name', 'is_logged','created_date']
        
        # def create(self, validated_data):
        #     user = User(
        #         id=validated_data['id'],
        #         username=validated_data['username'],
        #         email=validated_data['email'],
        #         first_name=validated_data['first_name'],
        #         last_name=validated_data['last_name'],
        #         is_logged=validated_data['is_logged'],
        #         created_date=validated_data['created_date'],
        #     )
        #     user.set_password(validated_data['password'])
        #     user.save()
        #     return user