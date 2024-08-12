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
    try:
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            validated_data = serializer.validated_data
            
            db = firestore.client()
            user_table = db.collection('user')
            
            email_query = user_table.where('email', '==', request.data.get('email')) # Limiting to 1 document
            email_docs = email_query.get()
            
            if len(email_docs) > 0:
                return Response({'error': 'Email already exists.'}, status=400)
            
            username_query = user_table.where('username', '==', request.data.get('username')) # Limiting to 1 document
            username_docs = username_query.get()
            if len(username_docs) > 0:
                return Response({'error':'Username already exists.'}, status=400)
            
            validated_data['password'] = make_password(validated_data['password'])
            
            timezone = pytz.timezone('Asia/Singapore')
            current_datetime = datetime.datetime.now(timezone)
            validated_data['created_date'] = current_datetime
            
            
            user_document_ref = user_table.add(validated_data)[1]
            print(user_document_ref)
            
            # do token 
            expiration_time = current_datetime + timedelta(days=10)
            payload = {
                'uid': user_document_ref.id,
                'exp': expiration_time  # Expiration time
            }
            token = jwt.encode(payload, key=None, algorithm=None) 
            user_document_ref.update({'token':token})
            return Response({'token': token}, status=201)
        return Response(serializer.errors, status=400)
    except Exception as e:
        return Response({'error': str(e)}, status=400)

# Done
@api_view(['PUT'])
def logoutUser(request):
    try:
        db = firestore.client()
        token = request.headers.get('Authorization','').split('Bearer ')[-1]
        if not token:
            return Response({'error': 'no token found'}, status=404)
        try:
        # Decode the JWT token
            print(token)
            decoded_token = jwt.decode(token, options={"verify_signature": False})
            user_id = decoded_token.get('uid') or decoded_token.get('user_id')
            user_table = db.collection('user')
            user_row = user_table.document(user_id)
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

# done
@api_view(['POST'])
def refreshToken(request):
    try:
        token = request.headers.get('Authorization','').split('Bearer ')[-1]
        decoded_token = jwt.decode(token, options={"verify_signature": False})
        user_id = decoded_token.get('uid') or decoded_token.get('user_id')
        timezone = pytz.timezone('Asia/Singapore')
        current_datetime = datetime.datetime.now(timezone)
        expiration_time = current_datetime + timedelta(days=10)
        payload = {
            'uid': user_id,
            'exp': expiration_time  # Expiration time
        }
        newtoken = jwt.encode(payload, key=None, algorithm=None)
        db = firestore.client()
        user_table = db.collection('user')
        user_row = user_table.document(user_id) 
        user_row.update({'token':newtoken})
        return Response({'token': newtoken}, status=201)
    except Exception as e:
        return Response({'error': str(e)}, status=400)

#done 
@api_view(['GET'])
def getUserDetail(request):
    token = request.headers.get('Authorization','').split('Bearer ')[-1]
    try:
        # Decode the JWT token
        decoded_token = jwt.decode(token, options={"verify_signature": False})
        user_id = decoded_token.get('uid') or decoded_token.get('user_id')
        if user_id:
            db = firestore.client()
            user_table = db.collection('user')
            user_row = user_table.document(user_id)
            doc_snapshot = user_row.get().to_dict()
            del doc_snapshot['password']
            del doc_snapshot['token']
            del doc_snapshot['created_date']
            
            return Response({'user': doc_snapshot}, status=200)
        else:
            return Response({'error': 'User not found'}, status=404)
    except jwt.ExpiredSignatureError:
        return Response({"error": "Token has expired"}, status=405)
    except jwt.InvalidTokenError:
        return Response({'token': "Invalid token"}, status=405) 
    except Exception as e:
        print(str(e))
        return Response({'error':str(e)}, status=400)
    
@api_view(['PUT'])
def updateDetail(request):
    token = request.headers.get('Authorization','').split('Bearer ')[-1]
    try:
        decoded_token = jwt.decode(token, options={"verify_signature": False})
        user_id = decoded_token.get('uid') or decoded_token.get('user_id')
        if user_id:
            db = firestore.client()
            user_table = db.collection('user')
            user_row = user_table.document(user_id)
            user_data = user_row.get().to_dict()

            email_query = user_table.where('email', '==', request.data.get('email'))
            email_docs = list(email_query.stream())
            print(email_docs)
            if email_docs and email_docs[0].id != user_id:
                return Response({'error':'Email already exists.'}, status=400)
            
            username_query = user_table.where('username', '==', request.data.get('username'))
            username_docs = list(username_query.stream())
            if username_docs and username_docs[0].id != user_id:
                return Response({'error':'Username already exists.'}, status=400)
            user_data.update(request.data)
            user_row.set(user_data)
            return Response(user_data, status=200)
    except jwt.ExpiredSignatureError:
        return Response({"error": "Token has expired"}, status=400)
    except jwt.InvalidTokenError:
        return Response({'token': "Invalid token"}, status=400) 
    except Exception as e:
        return Response({'error': str   (e)}, status=400)

@api_view(['PUT'])
def resetPassword(request):
    token = request.headers.get('Authorization','').split('Bearer ')[-1]
    try:
        old_password = request.data.get('old_password')
        new_password = request.data.get('new_password')
        print(old_password)
        print(new_password)
        decoded_token = jwt.decode(token, options={"verify_signature": False})
        user_id = decoded_token.get('uid') or decoded_token.get('user_id')
        if user_id:
            db = firestore.client()
            user_table = db.collection('user')
            user_row = user_table.document(user_id)
            user_data = user_row.get().to_dict()
            print(user_data['password'])
            # need to check for old password
            if check_password(old_password, user_data['password']):
                print('hello')
                user_data.update({'password':make_password(new_password)})
                user_row.set(user_data)
                return Response({'message':'Password updated'}, status=200)
            return Response({'old_password':'Password different'}, status=401)
    except Exception as e:
        return Response({'error':str(e)}, status=400)
        
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
            return Response({'error':'password wrong'}, status=401)
        return Response({'error': 'Username and password is wrong'}, status=401)
    except Exception as e:
        return Response({'error':str(e)}, status=400)