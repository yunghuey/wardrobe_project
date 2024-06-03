from django.shortcuts import render
import requests
from rest_framework.response import Response
from rest_framework.decorators import api_view
import jwt


# Create your views here.
api_key = 'a6ef8f8d478ae7fffc77f8b87e10323c'

@api_view(['GET'])
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
            desc = weather_data["weather"][0]["main"]
            temperature = weather_data["main"]["temp"] - 273.15  # Convert to Celsius
            humidity = weather_data["main"]["feels_like"] - 273.15
            
            
            result['weather'] = desc
            result['temperature'] = round(temperature,2)
            result['humidity'] = round(humidity,2)
            # result = result.to_dict()
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
    