from django.shortcuts import render
from rest_framework.decorators import api_view
from .serializers import UserSerializer
from rest_framework.response import Response
from firebase_admin import firestore, storage
from django.contrib.auth.hashers import make_password
import pytz
import datetime

@api_view(['POST'])
def registerUser(request):
    serializer = UserSerializer(data=request.data)
    if serializer.is_valid():
        validated_data = serializer.validated_data
        
        db = firestore.client()
        user_table = db.collection('user')
        # check for existing user with the same email
        existing_email = user_table.where('email', '==', validated_data['email']).get()
        if existing_email:
            return Response({'error':'Email already exists.'}, status=400)
        
        existing_username = user_table.where('username', '==', validated_data['username']).get()
        if existing_username:
            return Response({'error':'Username already exists.'}, status=400)
        
        validated_data['password'] = make_password(validated_data['password'])
        validated_data['is_logged'] = True
        
        timezone = pytz.timezone('Asia/Singapore')
        current_datetime = datetime.datetime.now(timezone)
        validated_data['created_date'] = current_datetime
        
        user_document_ref = user_table.add(serializer.validated_data)[1]
       
        return Response({'id': user_document_ref.id}, status=201)
    return Response(serializer.errors, status=400)