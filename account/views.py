from django.shortcuts import render
from rest_framework.decorators import api_view
from .serializers import UserSerializer
from rest_framework.response import Response
from firebase_admin import firestore, storage
from django.contrib.auth.hashers import make_password

@api_view(['POST'])
def registerUser(request):
    serializer = UserSerializer(data=request.data)
    if serializer.is_valid():
        validated_data = serializer.validated_data
        validated_data['password'] = make_password(validated_data['password'])
        db = firestore.client()
        user_table = db.collection('user')
        user_document_ref = user_table.add(serializer.validated_data)[1]
       
        return Response({'id': user_document_ref.id}, status=201)
    return Response(serializer.errors, status=400)