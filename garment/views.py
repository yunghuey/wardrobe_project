# from django.shortcuts import render
import base64
import tempfile
from datetime import datetime, timedelta
import math
from django.core.files.base import ContentFile
from rest_framework.response import Response
from rest_framework.decorators import api_view
from firebase_admin import firestore, storage
import calendar
from google.protobuf.timestamp_pb2 import Timestamp
from .models import Garment # models is filename, and Garment is class name
from .serializers import GarmentSerializer
from paddleocr import PaddleOCR
from collections import defaultdict,OrderedDict
import cv2
import easyocr
from PIL import Image
import numpy as np
import scipy.cluster
import re
import string
from fuzzywuzzy import process
import traceback
import sys
import pytz
import jwt


SIZES = ['2XS','XS', 'S', 'M', 'XXL', 'XL','L']
CLOTHES_COUNTRY = ['CHINA', 'MALAYSIA','PHILIPPINES', 'INDIA', 'INDONESIA',
                   'CAMBODIA', 'BANGLADESH', 'LAOS', 'TURKEY', 'MOROCCO', 
                   'PAKISTAN','VIETNAM', 'THAILAND', 'HONGKONG', 'SRILANKA', 'TAIWAN']
BRANDS_NAME = ['SKECHERS', 'ADIDAS', 'UNIQLO', 'ZARA','NIKE', 'COTTON ON', 
               'JORDAN','ASICS','NEW BALANCE',' TOMMYHILFIGER']
COLOUR_NAME = ['RED', 'PURPLE', 'PINK', 'BLUE', 'BLUE GREEN', 'GREEN','YELLOW GREEN',
               'YELLOW', 'ORANGE YELLOW', 'ORANGE','WHITE','BLACK', 'GREY']
MATERIAL_NAME = ['COTTON', 'OTHERS', 'NYLON', 'VISCOSE','WOOL',
                 'ELASTANE','CASHMERE', 'SPANDEX',
                 'RAYON','ACRYLIC','POLYESTER',
                 'POLYAMIDE','MOHAIR']
# done
""" GET ALL GARMENTS - will remove soon because dont have this function"""
@api_view(['GET'])
def getAllGarments(request):
    try:
        token = request.headers.get('Authorization','').split('Bearer ')[-1]
        decoded_token = jwt.decode(token, options={"verify_signature": False})
        user_id = decoded_token.get('uid') or decoded_token.get('user_id')
        selected_field = ['name','brand','country','image_url', 'id','status','user_id', 'colour']
        db = firestore.client()
        garment_reference = db.collection('garment')
        
        # the query to get all document
        query = garment_reference.select(selected_field).where('status', '==', True).where('user_id', '==', user_id)
        garments_list = query.stream()
        garment_data = []
        for garment in garments_list:
            garment_dict = garment.to_dict()
            garment_dict['id'] = garment.id
            garment_data.append(garment_dict)
        print(garment_data)
        # garment_data = {
        #     {'country': 'PAKISTAN', 'colour_name': 'ORANGE', 'user_id': 'TVy2qq9Up1W6opUeA9ns', 'image_url': 'https://storage.googleapis.com/wardrobepsm.appspot.com/LPdTCMen02Bh5fpFrskR_garment.jpg', 'name': 'jogging shirt', 'brand': 'COTTON ON', 'status': True},
        # {'country': 'VIETNAM', 'colour_name': 'GREY', 'user_id': 'TVy2qq9Up1W6opUeA9ns', 'image_url': 'https://storage.googleapis.com/wardrobepsm.appspot.com/SUudrSmI9iXAhMrRj1YT_garment.jpg', 'name': 'tennis fav', 'brand': 'ADIDAS', 'status': True}
        # }
        return Response({'garments': garment_data}, status=200)
    except jwt.ExpiredSignatureError:
    # Token has expired
        return Response({"error": "Token has expired"}, status=400)
    except jwt.InvalidTokenError:
    # Token is invalid
        return Response({'token': "Invalid token"}, status=400)
    except Exception as e:
        print(str(e))
        return Response({'error':str(e)}, status=400)

# done
""" GET INFORMATION OF ONE GARMENT BY id"""
@api_view(['GET'])
def getGarment(request, garment_id):
    try:
        token = request.headers.get('Authorization','').split('Bearer ')[-1]
        decoded_token = jwt.decode(token, options={"verify_signature": False})
        user_id = decoded_token.get('uid') or decoded_token.get('user_id')

        db = firestore.client()
        garment_table = db.collection('garment')
        doc_ref = garment_table.document(garment_id)
        garment = doc_ref.get().to_dict()
        
        if garment and garment.get('user_id') == user_id:
            garment['id'] = garment_id
            return Response({'garments': garment}, status=200)
        else:
            return Response({'error':'Garment not found'}, status=404)
    except jwt.ExpiredSignatureError:
    # Token has expired
        return Response({"error": "Token has expired"}, status=400)
    except jwt.InvalidTokenError:
    # Token is invalid
        return Response({'token': "Invalid token"}, status=400)
    except Exception as e:
        return Response({'error':str(e)}, status=400)

def handle_base64_image(image_data):
    decoded_image = base64.b64decode(image_data)
    image_file = ContentFile(decoded_image)
    return image_file

def extract_percentage(text1):
    text = text1.replace('O','0')
    print(f"Text is {text}")
    percent_start = text.find("%") or text.find("X")
    print(f"Percentage start: {percent_start}")
    if (percent_start == -1):
        # end = 0
        # while end < len(text) and text[end].isdigit():
        #     end += 1
        # if end == 0:
        #     return None
        # else:
        #     percentage = text[percent_start+1:end]
        #     if float(percentage) > 100:
        return None        
    else:
        end = percent_start - 1
        while end >= 0 and text[end].isdigit():
            end -= 1
        percentage = text[end+1:percent_start]
    if percentage.isdigit():
        return percentage
    else: 
        return None

def process_material(image_64):
    ocr = PaddleOCR(lang="en", use_gpu=False, model="ppocrv2")
    paddle_texts = []
    materials = []
    pending_percentage = None

    try:
        image_data = base64.b64decode(image_64)
        image_array = np.frombuffer(image_data, np.uint8)
        img = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
        # paddleOCR
        result = ocr.ocr(img)
        
        for line in result:
            print(f"data is{line[1][0]}")
            
        paddle_texts = [line[1][0] for line in result if line[1][1] > 0.5]
        
        for text in paddle_texts:
            if 'RIB' in text.upper():
                break                
            
            # split with . or ,
            pairs = re.split(r'([.,])', text)
            
            for pair in pairs:
                if not pending_percentage:
                    # get new percentage number
                    percentage = extract_percentage(pair)
                    
                    if percentage:
                        # percentage = min(100, float(percentage))
                        pending_percentage = percentage
                
                # get material
                valid_material = [m for m in MATERIAL_NAME if m.upper() in pair.upper()]
                if valid_material and pending_percentage:
                    
                    # to prevent exceed 100%
                    totalpercentage = 0
                    for aa in materials:
                        totalpercentage += aa['percentage']
                    
                    if totalpercentage < 100:
                        material_info = {
                            "material": valid_material[0],
                            "percentage": float(percentage) 
                        }
                        print(material_info)
                        materials.append(material_info)
                        pending_percentage = None
                    else:
                        break
                    
        # check if enough 100
        totalpercentage = 0
        for aa in materials:
            totalpercentage += aa['percentage']
        if totalpercentage < 100:
            cotton_exist = False
            for mat in materials:
                if mat['material'] == "COTTON":
                    mat['percentage'] += 100-totalpercentage
                    cotton_exist= True
                    break
            
            if not cotton_exist:
                material_info = {
                    "material": 'COTTON',
                    "percentage": 100 - totalpercentage
                }
                materials.append(material_info)
        return materials
        
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        print(f"An exception occurred on line {exc_tb.tb_lineno}: {e}")
        traceback.print_exc()
        return []
        
@api_view(['POST'])
def detectMaterial(request):
    token = request.headers.get('Authorization','').split('Bearer ')[-1]
    try:
        decoded_token = jwt.decode(token, options={"verify_signature": False})
        user_id = decoded_token.get('uid') or decoded_token.get('user_id')
        image64 = request.data.get('image')
        if user_id and image64 is not None and image64 != '':
            # call function to process image
            result = process_material(image64)
            # result = [
            #     { "material": "COTTON", "percentage" : 60,},
            #     {"material": "WOOL", "percentage" : 10,},
            #     {"material": "SILK", "percentage" : 10},
            #     {"material": "NYLON", "percentage" : 20}
            # ]
            
        return Response({"result": result}, status=201)
    except jwt.ExpiredSignatureError:
        return Response({"error": "Token has expired"}, status=400)
    except jwt.InvalidTokenError:
        return Response({'token': "Invalid token"}, status=400) 
    except Exception as e:
        print(str(e))
        return Response({'error': str(e)}, status=400)

# done
@api_view(['POST'])
def addGarment(request):
    token = request.headers.get('Authorization','').split('Bearer ')[-1]
    try:
        decoded_token = jwt.decode(token, options={"verify_signature": False})
        user_id = decoded_token.get('uid') or decoded_token.get('user_id')

        if user_id:
            serializer = GarmentSerializer(data=request.data)
            if serializer.is_valid():
                db = firestore.client()
                garment_reference = db.collection('garment')
                garment_data = serializer.validated_data

                timezone = pytz.timezone('Asia/Singapore')
                currentdatetime = datetime.now(timezone)
                
                garment_data = serializer.validated_data
                garment_data['created_date'] = currentdatetime
                garment_data['user_id'] = user_id
                materiallist=  request.data.get('material')
                if materiallist is not None:
                    print(materiallist)
                    garment_data['material'] = {}
                    for material in materiallist:
                        for key, value in material.items():
                            garment_data['material'][key] = value
                
                
                garment_documentID = garment_reference.add(garment_data)
                new_garment = garment_documentID[1].id
                
                firebase_storage = storage.bucket()
                
                garmentBase64Image = request.data.get('image')
                binaryOfGarmentImg = base64.b64decode(garmentBase64Image)
                garment_filename = new_garment+ "_garment.jpg"
                blob1 = firebase_storage.blob(garment_filename)
                blob1.upload_from_string(binaryOfGarmentImg,content_type='image/jpeg')
                
                materialBase64Image= request.data.get('materialImage')
                binaryOfMaterialImg = base64.b64decode(materialBase64Image)
                material_filename = new_garment+ "_material.jpg"
                blob2 = firebase_storage.blob(material_filename)
                blob2.upload_from_string(binaryOfMaterialImg,content_type='image/jpeg')
                
                image_url = f"https://storage.googleapis.com/{firebase_storage.name}/{garment_filename}"
                image2_url = f"https://storage.googleapis.com/{firebase_storage.name}/{material_filename}"
                garment_reference.document(new_garment).update({'image_url': image_url})
                garment_reference.document(new_garment).update({'material_url': image2_url})
                
                response_data = {'response':"success"}
                return Response(response_data,status=201)
            print(serializer.errors)
            return Response(serializer.errors, status=400)
            
    except jwt.ExpiredSignatureError:
        return Response({"error": "Token has expired"}, status=400)
    except jwt.InvalidTokenError:
        return Response({'token': "Invalid token"}, status=400) 
    except Exception as e:
        
        print(str(e))
        return Response({'error': str   (e)}, status=400)

# DONE
# update
@api_view(['PUT'])
def updateGarment(request, garment_id):
    try:
        token = request.headers.get('Authorization','').split('Bearer ')[-1]
        decoded_token = jwt.decode(token, options={"verify_signature": False})
        user_id = decoded_token.get('uid') or decoded_token.get('user_id')
        if user_id:
            db = firestore.client()
            garment_ref = db.collection('garment')
            doc_ref = garment_ref.document(garment_id) # get garment document by ID
            garment_data = doc_ref.get().to_dict() # convert into readable data
            #update garment data with request data
            
            request_data = request.data.copy()
            garment_data['brand'] = request.data.get('brand')
            garment_data['name'] = request.data.get('name')
            garment_data['colour_name'] = request.data.get('colour_name')
            garment_data['colour'] = request.data.get('colour')
            garment_data['size']= request.data.get('size')
            garment_data['country'] = request.data.get('country')
            
            materiallist = request_data.get('material')
            if materiallist is not None:
                garment_data['material'] = {}  # Initialize the 'material' field
                for material in materiallist:
                    for key, value in material.items():
                        garment_data['material'][key] = value
            
            
            doc_ref.set(garment_data)
            return Response(garment_data, status=200)
        return Response({'error':'problem in token'}, status=400)
    except jwt.ExpiredSignatureError:
    # Token has expired
        return Response({"error": "Token has expired"}, status=400)
    except jwt.InvalidTokenError:
    # Token is invalid
        return Response({'token': "Invalid token"}, status=400)
    except Exception as e:
        print(str(e))
        return Response({'error':str(e)}, status=400)
    
# done
# delete - make inactive
@api_view(['DELETE'])
def deleteGarment(request):
    try:
        token = request.headers.get('Authorization','').split('Bearer ')[-1]
        decoded_token = jwt.decode(token, options={"verify_signature": False})
        user_id = decoded_token.get('uid') or decoded_token.get('user_id')
        if user_id:
            db = firestore.client()
            garment_ref = db.collection('garment')
            doc_ref = garment_ref.document(request.data.get('id'))
            print(doc_ref)
            doc_ref.update({'status': False})
            return Response({'message': 'field updated'}, status=200)
    except jwt.ExpiredSignatureError:
        return Response({"error": "Token has expired"}, status=400)
    except jwt.InvalidTokenError:
        return Response({'token': "Invalid token"}, status=400)  
    except Exception as e:
        return Response({'error':str(e)}, status=400)

#image processing
# detect color from the image
def get_color(image):
    NUM_CLUSTERS = 5
    with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as temp_img_file:
        temp_img_path = temp_img_file.name
        cv2.imwrite(temp_img_path, image)
        
        im = Image.open(temp_img_path)
        im = im.resize((150, 150))
        ar = np.asarray(im)
        shape = ar.shape
        ar = ar.reshape(np.product(shape[:2]), shape[2]).astype(float)
        codes, dist = scipy.cluster.vq.kmeans(ar, NUM_CLUSTERS)
        vecs, dist = scipy.cluster.vq.vq(ar, codes)
        counts, bins = np.histogram(vecs, len(codes))
        index_max = np.argmax(counts)
        peak = codes[index_max]
        color = '#{:02x}{:02x}{:02x}'.format(*peak.astype(int))
        
        return color

# detect the colour name
def get_color_name(code):
    if '#' in code:
        code = code.replace('#', '')
    red = int(code[0:2], 16)
    green = int(code[2:4], 16)
    blue = int(code[4:6], 16) 
    print(f"({red}, {green}, {blue})")

    # find highest and lowest
    max_value = max(red, green, blue)
    min_value = min(red, green, blue)
    # for grey
    max_difference = max_value * 0.15

    if red and green and blue >= 240:
        return 'WHITE'
    elif red <= 60 and green <= 60 and blue <= 60:
        return 'BLACK'
    elif (abs(red - max_value) <= max_difference) and \
        (abs(green - max_value) <= max_difference) and \
        (abs(blue - max_value) <= max_difference):
        return 'GREY'
    elif blue == max_value and red < green:
        return 'BLUE'
    elif green == max_value and (blue/green*100 < 76):
        return 'GREEN'
    elif red == max_value and blue == min_value and (green/red*100) >= 90:
        if 70 < red < 150:
            return 'BROWN'
        return 'YELLOW'
    elif red == max_value and blue == min_value and (green/red*100) < 90:
        if 60 < red < 150:
            return 'BROWN'
        return 'ORANGE'
    elif green == min_value and blue == max_value and (red/blue*100 >= 25):
        return 'PURPLE'
    elif red == max_value and (green/red*100) <= 25 and (blue/red*100) <= 49 or (red < 150 and red == max_value and (green/red*100) <= 25 and (blue/red*100)):
        return 'RED'
    elif red == max_value and green == min_value:
        return 'PINK'
        
    return 'NONE'
    
def find_country(text):
    if 'MADE IN' in text:
        text = text.replace('MADE IN','')
    matches = process.extractBests(text, CLOTHES_COUNTRY, score_cutoff=80)
    if matches:
        return matches[0][0]
    else:
        return None
    
def find_brand(text):
    matches = process.extractBests(text, BRANDS_NAME, score_cutoff=75)
    if matches:
        # return first match
        return matches[0][0]
    else:
        return None

def process_data(image_64): 
    reader = easyocr.Reader(['en'], gpu=False)
    ocr = PaddleOCR(lang="en", use_gpu=False, model="ppocrv2")

    paddle_texts = []
    size_ocr = []
    country_ocr = []
    brand_ocr = []
    dump_store = []
    dump_store2 = []
    cottonon_size = []

    result_json = {}
    try:
        image_data = base64.b64decode(image_64)
        image_array = np.frombuffer(image_data, np.uint8)
        img = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
        # paddleOCR
        result = ocr.ocr(img)
        for line in result: 
            if line[1][1] > 0.7:
                paddle_texts.append(line[1][0])
    
        # Perform OCR using EasyOCR
        # imggrey = cv2.imdecode(image_array, cv2.IMREAD_GRAYSCALE)
        # text_ = reader.readtext(imggrey, batch_size=5)
        # for t in text_:
        #     if t[2] > 0.55:
        #         paddle_texts.append(t[1])
        # do sorting
        for i in range(len(paddle_texts)):
                if not paddle_texts[i].isdigit() :
                    paddle_texts[i] = ''.join(char for char in paddle_texts[i] if not char in string.punctuation)
                    dump_store.append(paddle_texts[i])
        print('pass2')
                
        # find sizes
        found_size = False
        for s in dump_store:
            if not found_size:
                if (s.upper() in [size.upper() for size in SIZES]) and (s not in size_ocr):
                    size_ocr.append(s.upper())
                    found_size = True
                elif s.__contains__('EUR'):
                    # custom size
                    parts = s.split()
                    for part in parts:
                        # print(f"Part is {part}")
                        valid_zara = [size for size in SIZES if size.upper() in part.upper()]
                        if valid_zara:
                            found_size = True
                            size_ocr.append(valid_zara[0])
                            print(valid_zara)
                            break
                
                elif len(s) >= 3:
                    dump_store2.append(s)
            # if found_size: 
            #     break  
            elif len(s) >= 3:
                dump_store2.append(s)

        if found_size is False:
            cottonon_size = dump_store
            
        # find country
        dump_store = []
        found_country = False
        for c in dump_store2:
            valid_country_matches = [country for country in CLOTHES_COUNTRY if country.upper() in c.upper()]
            if valid_country_matches:

                if valid_country_matches[0] not in country_ocr:
                    country_ocr.append(valid_country_matches[0])
                    found_country = True
            else: 
                dump_store.append(c)
        
        # country couldnt found
        if not found_country:
            dump_store = []
            for c1 in dump_store2:
                similar_country = find_country(c1)
                if similar_country and similar_country not in country_ocr:
                    country_ocr.append(similar_country)
                    found_country = True
                else:
                    dump_store.append(c1)
        
        brand_found = False
        for b in dump_store:
            valid_brand = [brand for brand in BRANDS_NAME if brand.upper() in b.upper()]
            if valid_brand and valid_brand[0] not in brand_ocr:
                brand_ocr.append(valid_brand[0])
                brand_found = True
            else:
                dump_store2.append(b)
        
        # check if brand not found
        dump_store = []
        if not brand_found:
            for b1 in dump_store2:
                similar_brand = find_brand(b1)
                if similar_brand and similar_brand not in brand_ocr:
                    brand_ocr.append(similar_brand)
                    brand_found = True
                else:
                    dump_store.append(b1)

        # new enhancement to increase readability
        if (found_size == False and found_country == True) and (brand_ocr[0] == 'TOMMYHILFIGER' or brand_ocr[0] == 'COTTON ON') :
            for s in cottonon_size:
                print(f"Cotton {s}")
                if ('I' in s.upper() or 'i' in s or 'GG' in s.upper() or 'PP' in s.upper()) and len(s) <= 7 and not re.search(r'\s', s):
                    # special for cotton on
                    print('inside cotton on area')
                    if s.upper().__contains__("GG"):
                        size_ocr.append("XL")
                        found_size = True
                    else:
                        get_size = [size for size in SIZES if size.upper() in s.upper() and (s not in size_ocr)] 
                        if get_size:
                            size_ocr.append(get_size[0].upper())
                            found_size = True
                            
        # get colour code
        color_code = get_color(img)
        
        
        if color_code:
            color_name = get_color_name(color_code)
            result_json['colour'] = color_code
            result_json['colour_name'] = color_name
        
        if size_ocr:
            result_json['size'] = size_ocr[0]
            
        if country_ocr:
            result_json['country'] = country_ocr[0]
            
        if brand_ocr:
            result_json['brand'] = brand_ocr[0]
        
        print(result_json)
        return result_json
        
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        print(f"An exception occurred on line {exc_tb.tb_lineno}: {e}")
        traceback.print_exc()
        return {}
   
# read image
@api_view(['POST'])
def processGarmentImage(request):
    try:
        result_json = {}
        image64 = request.data.get('image')
        if image64 is not None and image64 != '':
            result_json = process_data(image64)
            # result_json ={'colour': '#9ba666', 'colour_name': 'GREEN', 'size': 'S', 'country': 'INDONESIA', 'brand': 'ASICS'}
            
            return Response({'result': result_json}, status=200)
        else:
            return Response({'error': 'Failed'}, status=400) 
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        print(f"An exception occurred on line {exc_tb.tb_lineno}: {e}")
        traceback.print_exc()

@api_view(['GET'])
def getColourAnalysis(request):
    result = {}
    try:
        token = request.headers.get('Authorization','').split('Bearer ')[-1]
        decoded_token = jwt.decode(token, options={"verify_signature": False})
        user_id = decoded_token.get('uid') or decoded_token.get('user_id')
        if user_id:
            db = firestore.client()

            collection_ref = db.collection('garment')
            query = collection_ref.where('user_id', '==', user_id).where('status','==', True)
            query_snapshot = query.stream()
            for doc in query_snapshot:
                # Convert document to dictionary
                doc_dict = doc.to_dict()
                colour = doc_dict.get('colour_name', 'Unknown')
                if colour not in result:
                    result[colour] = {
                        'size': {},
                        'country': {},
                        'brand': {},
                        'total_num': 0
                    }

                if 'size' in doc_dict:
                    size = doc_dict['size']
                    if size in result[colour]['size']:
                        result[colour]['size'][size] += 1
                    else:
                        result[colour]['size'][size] = 1

                if 'country' in doc_dict:
                    country = doc_dict['country']
                    if country in result[colour]['country']:
                        result[colour]['country'][country] += 1
                    else:
                        result[colour]['country'][country] = 1

                if 'brand' in doc_dict:
                    brand = doc_dict['brand']
                    if brand in result[colour]['brand']:
                        result[colour]['brand'][brand] += 1
                    else:
                        result[colour]['brand'][brand] = 1
                result[colour]['total_num'] += 1

            # convert into list of dictionaries
            for colour in result:
                result[colour]['size'] = [
                    {size: count} for size, count in result[colour]['size'].items()
                ]
                result[colour]['country'] = [
                    {country: count} for country, count in result[colour]['country'].items()
                ]
                result[colour]['brand'] = [
                    {brand: count} for brand, count in result[colour]['brand'].items()
                ]
            return Response(result, status=200)
    except jwt.ExpiredSignatureError:
        return Response({"error": "Token has expired"}, status=400)
    except jwt.InvalidTokenError:
        return Response({'token': "Invalid token"}, status=400)  
    except Exception as e:
        print(str(e))
        return Response({'error':str(e)}, status=400)
 
@api_view(['GET'])
def getSizeAnalysis(request):
    result = {}
    try:
        token = request.headers.get('Authorization','').split('Bearer ')[-1]
        decoded_token = jwt.decode(token, options={"verify_signature": False})
        user_id = decoded_token.get('uid') or decoded_token.get('user_id')
        if user_id:
            db = firestore.client()

            collection_ref = db.collection('garment')
            query = collection_ref.where('user_id', '==', user_id).where('status','==', True)
            query_snapshot = query.stream()
            for doc in query_snapshot:
                # Convert document to dictionary
                doc_dict = doc.to_dict()
                size = doc_dict.get('size', 'Unknown')
                if size not in result:
                    result[size] = {
                        'colour_name': {},
                        'country': {},
                        'brand': {},
                        'total_num': 0
                    }

                if 'colour_name' in doc_dict:
                    colour = doc_dict['colour_name']
                    if colour in result[size]['colour_name']:
                        result[size]['colour_name'][colour] += 1
                    else:
                        result[size]['colour_name'][colour] = 1

                if 'country' in doc_dict:
                    country = doc_dict['country']
                    if country in result[size]['country']:
                        result[size]['country'][country] += 1
                    else:
                        result[size]['country'][country] = 1

                if 'brand' in doc_dict:
                    brand = doc_dict['brand']
                    if brand in result[size]['brand']:
                        result[size]['brand'][brand] += 1
                    else:
                        result[size]['brand'][brand] = 1
                result[size]['total_num'] += 1

            # convert into list of dictionaries
            for size in result:
                result[size]['colour_name'] = [
                    {colour: count} for colour, count in result[size]['colour_name'].items()
                ]
                result[size]['country'] = [
                    {country: count} for country, count in result[size]['country'].items()
                ]
                result[size]['brand'] = [
                    {brand: count} for brand, count in result[size]['brand'].items()
                ]
            return Response(result, status=200)
    except jwt.ExpiredSignatureError:
        return Response({"error": "Token has expired"}, status=400)
    except jwt.InvalidTokenError:
        return Response({'token': "Invalid token"}, status=400)  
    except Exception as e:
        print(str(e))
        return Response({'error':str(e)}, status=400)
 
@api_view(['GET'])
def getCountryAnalysis(request):
    result = {}
    try:
        token = request.headers.get('Authorization','').split('Bearer ')[-1]
        decoded_token = jwt.decode(token, options={"verify_signature": False})
        user_id = decoded_token.get('uid') or decoded_token.get('user_id')
        if user_id:
            db = firestore.client()

            collection_ref = db.collection('garment')
            query = collection_ref.where('user_id', '==', user_id).where('status','==', True)
            query_snapshot = query.stream()
            for doc in query_snapshot:
                # Convert document to dictionary
                doc_dict = doc.to_dict()
                country = doc_dict.get('country', 'Unknown')
                if country not in result:
                    result[country] = {
                        'colour_name': {},
                        'size': {},
                        'brand': {},
                        'total_num': 0
                    }

                if 'colour_name' in doc_dict:
                    colour = doc_dict['colour_name']
                    if colour in result[country]['colour_name']:
                        result[country]['colour_name'][colour] += 1
                    else:
                        result[country]['colour_name'][colour] = 1

                if 'size' in doc_dict:
                    size = doc_dict['size']
                    if size in result[country]['size']:
                        result[country]['size'][size] += 1
                    else:
                        result[country]['size'][size] = 1

                if 'brand' in doc_dict:
                    brand = doc_dict['brand']
                    if brand in result[country]['brand']:
                        result[country]['brand'][brand] += 1
                    else:
                        result[country]['brand'][brand] = 1
                result[country]['total_num'] += 1

            # convert into list of dictionaries
            for country in result:
                result[country]['colour_name'] = [
                    {colour: count} for colour, count in result[country]['colour_name'].items()
                ]
                result[country]['size'] = [
                    {size: count} for size, count in result[country]['size'].items()
                ]
                result[country]['brand'] = [
                    {brand: count} for brand, count in result[country]['brand'].items()
                ]
            # garmentresult['brandResult'] = result
            return Response(result, status=200)
    except jwt.ExpiredSignatureError:
        return Response({"error": "Token has expired"}, status=400)
    except jwt.InvalidTokenError:
        return Response({'token': "Invalid token"}, status=400)  
    except Exception as e:
        print(str(e))

        return Response({'error':str(e)}, status=400)
   
@api_view(['GET'])
def getBrandAnalysis(request):
    result = {}
    try:
        token = request.headers.get('Authorization','').split('Bearer ')[-1]
        decoded_token = jwt.decode(token, options={"verify_signature": False})
        user_id = decoded_token.get('uid') or decoded_token.get('user_id')
        garmentresult = {}
        if user_id:
            db = firestore.client()

            collection_ref = db.collection('garment')
            query = collection_ref.where('user_id', '==', user_id).where('status','==', True)
            query_snapshot = query.stream()
            for doc in query_snapshot:
                # Convert document to dictionary
                doc_dict = doc.to_dict()
                brand = doc_dict.get('brand', 'Unknown')
                if brand not in result:
                    result[brand] = {
                        'colour_name': {},
                        'size': {},
                        'country': {},
                        'total_num': 0
                    }

                if 'colour_name' in doc_dict:
                    colour = doc_dict['colour_name']
                    if colour in result[brand]['colour_name']:
                        result[brand]['colour_name'][colour] += 1
                    else:
                        result[brand]['colour_name'][colour] = 1

                if 'size' in doc_dict:
                    size = doc_dict['size']
                    if size in result[brand]['size']:
                        result[brand]['size'][size] += 1
                    else:
                        result[brand]['size'][size] = 1

                if 'country' in doc_dict:
                    country = doc_dict['country']
                    if country in result[brand]['country']:
                        result[brand]['country'][country] += 1
                    else:
                        result[brand]['country'][country] = 1
                result[brand]['total_num'] += 1

            # convert into list of dictionaries
            for brand in result:
                result[brand]['colour_name'] = [
                    {colour: count} for colour, count in result[brand]['colour_name'].items()
                ]
                result[brand]['size'] = [
                    {size: count} for size, count in result[brand]['size'].items()
                ]
                result[brand]['country'] = [
                    {country: count} for country, count in result[brand]['country'].items()
                ]
            garmentresult['brandResult'] = result
            return Response(garmentresult, status=200)
    except jwt.ExpiredSignatureError:
        return Response({"error": "Token has expired"}, status=400)
    except jwt.InvalidTokenError:
        return Response({'token': "Invalid token"}, status=400)  
    except Exception as e:
        print(str(e))
        return Response({'error':str(e)}, status=400)
   
@api_view(['GET'])
def getTotalGarmentNo(request):
    try:
        token = request.headers.get('Authorization','').split('Bearer ')[-1]
        decoded_token = jwt.decode(token, options={"verify_signature": False})
        user_id = decoded_token.get('uid') or decoded_token.get('user_id')
        garmentresult = {}

        if user_id:
            db = firestore.client()
            collection_ref = db.collection('garment')
            query = collection_ref.where('user_id', '==', user_id).where('status','==', True)
            # execute the query and get a result
            query_snapshot = query.stream()
            # count the number of documents in snapshot
            count = sum(1 for _ in query_snapshot)
            garmentresult['totalGarment'] = count
            return Response(garmentresult, status=200)
    except jwt.ExpiredSignatureError:
        return Response({"error": "Token has expired"}, status=400)
    except jwt.InvalidTokenError:
        return Response({'token': "Invalid token"}, status=400)  
    except Exception as e:
        print(str(e))
        return Response({'error':str(e)}, status=400)
    
# for website data
@api_view(['GET']) 
# to get the total number of user of the mobile application
def getTotalNumberUserCount(request):
    try:
        user_list = []
        token = request.headers.get('Authorization','').split('Bearer ')[-1]
        decoded_token = jwt.decode(token, options={"verify_signature": False})
        user_id = decoded_token.get('uid') or decoded_token.get('user_id')
        if user_id:
            db = firestore.client()
            collection_ref = db.collection('user')
            docs = collection_ref.select(['last_name', 'first_name', 'created_date'])\
                .where('username', '!=', 'admin')\
                .order_by('created_date').stream()
            for c in docs:
                user_list.append(f"{c.get('created_date').date()} : {c.get('first_name')} {c.get('last_name')} ")
            count =len(user_list) # to remove admin
            # count = 6
            
            # need to calculate the user growth rate
            current_date = datetime.now().date()
            
            first_day_current_month = datetime(current_date.year, current_date.month, 1)
            first_day_current_month = first_day_current_month.replace(hour=0, minute=0,second=0, microsecond=0)
            
            if current_date.month == 1:
                first_day_previous_month = datetime(current_date.year - 1, 12, 1)
            else:
                first_day_previous_month = datetime(current_date.year, current_date.month - 1, 1)
            first_day_previous_month = first_day_previous_month.replace(hour=0, minute=0, second=0, microsecond=0)
            last_day_previous_month = first_day_previous_month.replace(
                day=calendar.monthrange(first_day_previous_month.year, first_day_previous_month.month)[1],
                hour=23, minute=59, second=59, microsecond=999999
            )
            
            print(first_day_current_month)
            print(first_day_previous_month)
            query1 = collection_ref.select('created_date').where('created_date', '>=', first_day_current_month).stream()
            count_current_month = sum(1 for _ in query1)
            print(f"current month {count_current_month}")
            
            query2 = collection_ref.select('created_date').where('created_date', '>=', first_day_previous_month)\
                .where('created_date', '<=', last_day_previous_month).stream()
            count_previous_month = sum(1 for _ in query2)
            print(f"previous month {count_previous_month}")
            
            if count_previous_month == 0:
                growth_rate = float('inf')  # Handle division by zero
            else:
                growth_rate = ((count_current_month - count_previous_month) / count_previous_month) * 100

            return Response({'total_user': count, 'growth_rate': growth_rate, 'user_list':user_list }, status=200)
        return Response({'error': 'Unauthorized'}, status=401)
    except Exception as e:
        print(str(e))
        return Response({'error':str(e)}, status=400)


@api_view(['GET']) 
# to calculate the total number variance in each category
def getTotalVarianceCountForGarment(request):
    try:
        token = request.headers.get('Authorization','').split('Bearer ')[-1]
        decoded_token = jwt.decode(token, options={"verify_signature": False})
        user_id = decoded_token.get('uid') or decoded_token.get('user_id')
        if user_id:
            selected_field1 = ['name', 'brand', 'colour_name', 'country', 'size','user_id']
            db = firestore.client()
            garment_ref = db.collection('garment')
            
            # 1: total number of garment
            garments = list(garment_ref.select(selected_field1).stream())  # Retrieve all the documents once
            count = len(garments)
            
            # 2. garment name list
            # collect all user ID from garment list
            user_ids = set(g.get('user_id') for g in garments if g.get('user_id'))
            print(len(user_ids))
            user_name_map = {}
            if  user_ids:
                user_ref = db.collection('user')
                for id in user_ids:
                    user_doc = user_ref.document(id).get()
                    if user_doc.exists:
                        user_name = f"{user_doc.get('first_name')} {user_doc.get('last_name')}"
                        user_name_map[id] = user_name
                    
            garment_list = []
            print(len(user_name_map))
            for g in garments:
                user_id = g.get('user_id')
                user_name = user_name_map.get(user_id, 'Unknown') if user_id else 'Unknown'
                garment_list.append({
                    'garment_name': g.get('name'),
                    'garment_brand': g.get('brand'),
                    'garment_colour': g.get('colour_name'),
                    'garment_country': g.get('country'),
                    'garment_size': g.get('size'),
                    'user': user_name
                })

            # 3. list of data for variance in detail
            # 4. total variance summary
            colors = set()
            brands = set()
            countries = set()
            sizes = set()
            
            for garment in garments:
                garment_data = garment.to_dict()
                
                if 'colour_name' in garment_data:
                    colors.add(garment_data['colour_name'])
                
                if 'brand' in garment_data:
                    brands.add(garment_data['brand'])
                
                if 'country' in garment_data:
                    countries.add(garment_data['country'])
                
                if 'size' in garment_data:
                    sizes.add(garment_data['size'])
               
            # 5. calculate newly registered garment
            now = datetime.now()
            first_day_of_month = now.replace(day=1, hour=0, minute=0,second=0, microsecond=0)
            query2 = garment_ref.select('created_date').where('created_date', '>=', first_day_of_month).stream()
            new_garment_count = sum(1 for _ in query2)

            result = {
                'total_colors' : len(colors),
                'colour_list': colors,
                'total_brands' : len(brands),
                'brand_list': brands,
                'total_countries': len(countries),
                'country_list': countries,
                'total_sizes' : len(sizes),
                'sizes_list': sizes,
                'garment_list': garment_list,
                'total_garments': count,
                'new_garment_month': new_garment_count,
            }
            # result = {
            #     'total_colors' : 6,
            #     'total_brands' : 5,
            #     'total_countries': 7,
            #     'total_sizes' : 5
            # }
            if result != {}:
                return Response({'result': result}, status=200)
            return Response({'empty'}, status=404)
        return Response({'error':'No user found'}, status=401)
    except Exception as e:
        print(str(e))
        stack_trace = traceback.format_exc()
        
        # Print the stack trace to the console or logs
        print(stack_trace)
        return Response({'error':str(e)}, status=400)

@api_view(['GET'])
# to know the total garments registered in different duration  
def getGarmentByDuration(request,duration):
    try:
        token = request.headers.get('Authorization', '').split('Bearer ')[-1]
        decoded_token = jwt.decode(token, options={"verify_signature": False})
        user_id = decoded_token.get('uid') or decoded_token.get('user_id')
        end_timestamp = datetime.now().replace(hour=23, minute=23, second=23,microsecond=999999) 
        
        date_arr = []   
        if user_id:
            if duration == 1:
                # date_arr = [
                #     {"date":"2024-07-19","count":5},
                #     {"date":"2024-07-20","count":3},
                #     {"date":"2024-07-21","count":7},
                #     {"date":"2024-07-22","count":2},
                #     {"date":"2024-07-23","count":10},
                #     {"date":"2024-07-24","count":1},
                #     {"date":"2024-07-25","count":8},
                # ]

                start_timestamp = datetime.now() - timedelta(days=6)
                interval = 1
            elif duration == 2:
                # date_arr = [
                #         {"date":"2024-07-19","count":8},
                #         {"date":"2024-07-21","count":10},
                #         {"date":"2024-07-23","count":13},
                #         {"date":"2024-07-25","count":6},
                #         {"date":"2024-07-27","count":8},
                #         {"date":"2024-07-29","count":4},
                #         {"date":"2024-07-31","count":3}
                # ]
                start_timestamp = datetime.now() - timedelta(days=14)
                interval = 2
            else:
                # date_arr = [
                #         {"date":"2024-07-10","count":18},
                #         {"date":"2024-07-17","count":15},
                #         {"date":"2024-07-24","count":13},
                #         {"date":"2024-07-31","count":10},
                # ]
                start_timestamp = datetime.now() - timedelta(weeks=3)
                interval = 7
            start_timestamp = start_timestamp.replace(hour=0, minute=0, second=0,microsecond=0) 
            selected_fields = ['created_date','name']
            db = firestore.client()
            garment_ref = db.collection('garment')
            
            # first part
            query = garment_ref.where('created_date', '>', start_timestamp).where('created_date', '<=', end_timestamp).select(selected_fields)
            results = list(query.stream())

            grouped_data = defaultdict(int)
            # count the total number of garment created in each day
            for doc in results:
                doc_data = doc.to_dict()
                created_date = doc_data['created_date'].date()
                garment_name = doc_data['name']
                if garment_name:
                    grouped_data[created_date] += 1

            if duration == 1:
                while start_timestamp <= end_timestamp:
                    date_obj = start_timestamp.date()
                    print(date_obj)
                    # get the count between temp_timestamp
                    garment_number= 0
                    date_arr.append({
                        'date': date_obj,
                        'count': grouped_data.get(date_obj, 0)
                    })
                    start_timestamp += timedelta(days=interval)
            elif duration == 2:
                start_timestamp = (start_timestamp+ timedelta(days=1))
                temp_timestamp = start_timestamp
                start_timestamp += timedelta(days=1)
                while start_timestamp <= end_timestamp:
                    date_obj = start_timestamp.date()
                    # get the count between temp_timestamp
                    garment_number= 0
                    while (temp_timestamp <= start_timestamp):
                        garment_number += grouped_data.get(temp_timestamp.date(), 0)
                        print(f"{temp_timestamp.date()} has {garment_number}")
                        temp_timestamp += timedelta(days=1)
                    
                    date_arr.append({
                        'date': date_obj,
                        'count': garment_number
                    })
                    temp_timestamp = (start_timestamp + timedelta(days=1)).replace(hour=0, minute=0, second=0,microsecond=0)
                    start_timestamp += timedelta(days=interval)
            else:
                temp_timestamp = start_timestamp
                # start_timestamp += timedelta(days=1)
                while start_timestamp <= end_timestamp:
                    date_obj = start_timestamp.date()
                    # get the count between temp_timestamp
                    garment_number= 0
                    while (temp_timestamp <= start_timestamp):
                        garment_number += grouped_data.get(temp_timestamp.date(), 0)
                        print(f"{temp_timestamp.date()} has {garment_number}")
                        temp_timestamp += timedelta(days=1)
                    print(f"duration {date_obj} total count {garment_number}")
                    date_arr.append({
                        'date': date_obj,
                        'count': garment_number
                    })
                    temp_timestamp = (start_timestamp + timedelta(days=1)).replace(hour=0, minute=0, second=0,microsecond=0)
                    start_timestamp += timedelta(days=interval)
            
            
            
            return Response({'result': date_arr}, status=200)
        else:
            return Response({'result': 'empty'}, status=404)
    except Exception as e:
        print(str(e))
        print(traceback.format_exc())
        return Response({'error': str(e)}, status=400)

@api_view(['GET'])
# to know the percentage of garment for each size
def getGarmentCategoriesChart(request):
    try:
        token = request.headers.get('Authorization', '').split('Bearer ')[-1]
        decoded_token = jwt.decode(token, options={"verify_signature": False})
        user_id = decoded_token.get('uid') or decoded_token.get('user_id')
        if user_id:
            selected_fields = ['size','name', 'brand','colour_name', 'country']
            db = firestore.client()
            results = list(db.collection('garment').select(selected_fields).stream())
            
            garment_total_count = len(results)
            
            size_data = defaultdict(int)
            for doc in results:
                doc_data = doc.to_dict()
                size = doc_data.get('size')
                garment_count = doc_data.get('name')
                if garment_count:
                    size_data[size] += 1
                    
            brand_data = defaultdict(int)
            for doc in results:
                doc_data = doc.to_dict()
                brand = doc_data.get('brand')
                garment_count = doc_data.get('name')
                if garment_count:
                    brand_data[brand] += 1
            
            colour_data = defaultdict(int)
            for doc in results:
                doc_data = doc.to_dict()
                colour = doc_data['colour_name']
                garment_count = doc_data['name']
                if garment_count:
                    colour_data[colour] += 1
            
            country_data = defaultdict(int)
            for doc in results:
                doc_data = doc.to_dict()
                select_country = doc_data['country']
                garment_count = doc_data['name']
                if garment_count:
                    country_data[select_country] += 1
            
            sorted_size_data = OrderedDict(sorted(size_data.items(), key=lambda item: item[1], reverse=True))
            sorted_brand_data = OrderedDict(sorted(brand_data.items(), key=lambda item: item[1], reverse=True))
            sorted_colour_data = OrderedDict(sorted(colour_data.items(), key=lambda item: item[1], reverse=True))
            sorted_country_data = OrderedDict(sorted(country_data.items(), key=lambda item: item[1], reverse=True))
            
            top_size = OrderedDict(list(sorted_size_data.items())[:3])
            top_brand = OrderedDict(list(sorted_brand_data.items())[:3])
            top_country = OrderedDict(list(sorted_country_data.items())[:3])
            top_colour = OrderedDict(list(sorted_colour_data.items())[:3])
            
            results = {
                'size' : sorted_size_data, 
                'brand' : sorted_brand_data,
                'colour': sorted_colour_data,
                'country': sorted_country_data,
                'top_size': top_size,
                'top_brand':top_brand,
                'top_country':top_country,
                'top_colour': top_colour,
                'total_garments' : garment_total_count
            }
            
            
            # grouped_data = {
            #     "XS": 2,
            #     "S":5,
            #     "M":3,
            #     "L":6,
            #     "XL":2
            # }
            return Response({'result': results}, status=200)
        return Response({'unauthorized': 'token error'}, status=401)
    except Exception as e:
        print(str(e))
        print(traceback.format_exc())
        return Response({'error': str(e)}, status=400)