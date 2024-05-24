from django.shortcuts import render
from rest_framework.decorators import api_view
from .serializers import UserSerializer
from rest_framework.response import Response
from firebase_admin import firestore,auth
from django.contrib.auth.hashers import make_password, check_password
import pytz
import jwt
import datetime
from datetime import timedelta

# done
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
        
        
        user_document_ref = user_table.add(validated_data)[1]
        print(user_document_ref)
        
        # do token 
        expiration_time = current_datetime + timedelta(days=10)
        payload = {
            'user_id': user_document_ref.id,
            'exp': expiration_time  # Expiration time
        }
        token = jwt.encode(payload, key=None, algorithm=None) 
        user_document_ref.update({'token':token})
        return Response({'token': token}, status=201)
    # take note to save id into SharedPreference 
    return Response(serializer.errors, status=400)

# Done
@api_view(['PUT'])
def logoutUser(request):
    try:
        db = firestore.client()
        token = request.headers.get('Authorization','').split('Bearer ')[-1]
        if not token:
            return Response({'error': 'no token found'}, stauts=404)
        try:
        # Decode the JWT token
            print(token)
            decoded_token = jwt.decode(token, options={"verify_signature": False})
            user_id = decoded_token['uid']
            user_table = db.collection('user')
            user_row = user_table.document(user_id)
            user_row.update({'is_logged': False})
            user_row.update({'token': firestore.DELETE_FIELD})
            return Response({'message': 'successfully logout'}, status=200)
        except jwt.ExpiredSignatureError:
        # Token has expired
            return Response({"error": "Token has expired"}, status=400)
        except jwt.InvalidTokenError:
        # Token is invalid
            return Response({'token': "Invalid token"}, status=400)       
        
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

# Done
@api_view(['POST']) 
def login(request):
    try:
        username = request.data.get('username')
        password = request.data.get('password')  
        if username and password:
            # username and password not null
            db = firestore.client()
            user_table = db.collection('user')

            # get the username  
            user_reference = db.collection('user').where('username', '==', username).limit(1).get()
            if not user_reference:
                return Response({'error': 'username does not exist'}, status=404)
            # username exist
            # get user document and user id
            user_doc = user_reference[0].to_dict()
            user_id = user_reference[0].id 

            if check_password(password, user_doc['password']):
                # generate custom token
                timezone = pytz.timezone('Asia/Singapore')
                current_datetime = datetime.datetime.now(timezone)
                expiration_time = current_datetime + timedelta(days=10)
                payload = {
                    'user_id': user_id,
                    'exp': expiration_time  # Expiration time
                } 
                token = jwt.encode(payload, key=None, algorithm=None) 
                ## update into row
                user_row = user_table.document(user_id)
                user_row.update({'token': token})
                return Response({'token':token}, status=200)
            return Response({'error':'wrong password'}, status=400)
        return Response({'error': 'Username and password is wrong'}, stauts=400)
    except Exception as e:
        return Response({'error':str(e)}, status=400)