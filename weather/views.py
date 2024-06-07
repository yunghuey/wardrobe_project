from django.shortcuts import render
import requests
from rest_framework.response import Response
from rest_framework.decorators import api_view
import jwt
from firebase_admin import firestore, storage


# Create your views here.
api_key = 'a6ef8f8d478ae7fffc77f8b87e10323c'

@api_view(['POST'])
def getTemperatureHumidity(request):
    try:
        result = {}
        token = request.headers.get('Authorization','').split('Bearer ')[-1]
        decoded_token = jwt.decode(token, options={"verify_signature": False})
        user_id = decoded_token.get('uid') or decoded_token.get('user_id')
        if user_id:
            long = request.data.get('longitude')
            lat = request.data.get('latitude')
            url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={long}&APPID={api_key}"
            print(url)
            weather_data = requests.get(url).json()
            weathername = weather_data["weather"][0]["main"]
            desc = weather_data["weather"][0]["description"]
            temperature = weather_data["main"]["temp"] - 273.15  # Convert to Celsius
            humidity = weather_data["main"]["feels_like"] - 273.15
            
            result['weathername'] = weathername
            result['description'] = desc
            result['temperature'] = round(temperature,2)
            result['humidity'] = round(humidity,2)
            return Response(result, status=200)

    except jwt.ExpiredSignatureError:
    # Token has expired
        return Response({"error": "Token has expired"}, status=400)
    except jwt.InvalidTokenError:
    # Token is invalid
        return Response({'token': "Invalid token"}, status=400)
    except Exception as e:
        return Response({'error':str(e)}, status=400)
    except Exception as e:
        return Response({'error':str(e)}, status=400)

@api_view(['POST'])
def getRecommendedClothes(request):
    try:
        token = request.headers.get('Authorization','').split('Bearer ')[-1]
        decoded_token = jwt.decode(token, options={"verify_signature": False})
        user_id = decoded_token.get('uid') or decoded_token.get('user_id')
        result = {}
        if user_id: 
            # get the weather first
            long = request.data.get('longitude')
            lat = request.data.get('latitude')
            url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={long}&APPID={api_key}"
            print(url)
            weather_data = requests.get(url).json()
            temperature = weather_data["main"]["temp"] - 273.15
            humidity = weather_data["main"]["feels_like"] - 273.15
            
            db = firestore.client()
            garment_collection = db.collection('garment')
            # connect to db to get the list of shirt
            query = garment_collection.where('user_id','==',user_id).where('status','==',True)
            garments_list = query.stream()
            garment_data = []

            for garment in garments_list:
                garment_dict = garment.to_dict()
                garment_dict['id'] = garment.id
                material_list = garment_dict.get('material')    
                if humidity > 31:
                    if 'COTTON' in material_list:
                    # for m in material_list:
                        
                        # for key, value, in m.items():
                            # if key == 'COTTON':
                        garment_data.append(garment_dict)
                                
            if not garment_data:
                return Response({'message': 'No garments found.'}, status=204)
            else:
                return Response({'garments':garment_data}, status=200)

        return Response(result, status=204)
    except Exception as e:
        print(str(e))
        return Response({'error':str(e)}, status=400)
    