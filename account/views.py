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
    # take note to save id into SharedPreference 
    return Response(serializer.errors, status=400)

@api_view(['PUT'])
def logoutUser(request):
    try:
        db = firestore.client()
        user_table = db.collection('user')
        user_row = user_table.document(request.data.get('id'))
        user_row.update({'is_logged': False})
        return Response({'message': 'successfully logged out'}, status=200)
    except Exception as e:
        return Response({'error': str(e)}, status=400)

@api_view(['GET'])
def getUserDetail(request, user_id):
    try:
        db = firestore.client()
        user_table = db.collection('user')
        user_row = user_table.document(user_id)
        doc_snapshot = user_row.get()
        if doc_snapshot.exists:
            user_data = doc_snapshot.to_dict()
            user_data['id'] = user_id
            return Response({'user': user_data}, status=200)
        else:
            return Response({'error': 'User not found'}, status=404)
    except Exception as e:
        return Response({'error':str(e)}, status=400)
    
@api_view(['PUT'])
def updateDetail(request, user_id):
    try:
        db = firestore.client()
        user_table = db.collection('user')
        user_row = user_table.document(user_id)
        user_data = user_row.get().to_dict()
        print(user_data)
        # print(user_data.where('is_logged', '==',True))
        if user_data['is_logged'] == True:
            if user_data['email'] == request.data.get('email'):
                return Response({'error':'Email already exists.'}, status=400)
            
            if user_data['username'] == request.data.get('username'):
                return Response({'error':'Username already exists.'}, status=400)
            user_data.update(request.data)
            user_row.set(user_data)
            return Response(user_data, status=200)
        return Response({'error': 'User is not logged in'}, status=409)
    except Exception as e:
        return Response({'error': str   (e)}, status=400)
    
# def login(request):
    
    
