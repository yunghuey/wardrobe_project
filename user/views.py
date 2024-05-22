from django.shortcuts import render
from rest_framework.decorators import api_view
from .serializers import UserSerializer
from rest_framework.response import Response
from firebase_admin import firestore, storage

@api_view(['POST'])
def registerUser(request):
    serializer = UserSerializer(data=request.data)
    if serializer.is_valid():
        db = firestore.client()
        user_table = db.collection('user')
        user_document = user_table.add(serializer.validated_data)
        return Response(user_document, status=201)
    return Response(serializer.errors, status=400)