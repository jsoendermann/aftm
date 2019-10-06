#!/usr/bin/env python3

import toml
import requests
import pyqrcode
from picamera import PiCamera
from time import sleep
from picamera.array import PiRGBArray
from pyzbar.pyzbar import decode
from os import path
from sys import exit
from enum import Enum
from random import choice, choices, shuffle, sample
from string import ascii_letters, digits
from Adafruit_Thermal import *
from serial import Serial
from PIL import Image
from io import BytesIO
from math import sqrt

TOKEN_FILE = './tokens.toml'
FORTUNES_FILE = './fortunes.toml'
FORTUNES_URL = 'http://aftm-fortunes.j51.eu/fortunes.toml'

used_tokens = []
active_tokens = []

print('Initializing camera...')
camera = PiCamera()
camera.framerate = 20

rawCapture = PiRGBArray(camera)
sleep(0.1)


print('Initializing printer...')
printer = Adafruit_Thermal('/dev/serial0', 19200, timeout=5)


fortunes = None

#print('Loading tokens...')
## Load saved token lists
#if path.isfile(TOKEN_FILE):
#    with open(TOKEN_FILE, 'r') as token_file:
#        d = toml.load(token_file)
#        if 'used_tokens' in d:
#            used_tokens = d['used_tokens']
#        if 'active_tokens' in d:
#            active_tokens = d['active_tokens']

def load_fortunes():
#    if path.isfile(FORTUNES_FILE):
#        with open(FORTUNES_FILE) as fortunes_file:
#            return toml.load(fortunes_file)['fortunes']
    try:
        response = requests.get(FORTUNES_URL)
        response.raise_for_status()
        data = toml.loads(response.text)

        return data['fortunes']
    except Exception as err:
        print(f'Could not load fortunes file from server: {err}')

#def save_tokens():
#    with open(TOKEN_FILE, 'w') as token_file:
#        d = {'used_tokens': used_tokens, 'active_tokens': active_tokens}
#        token_file.write(toml.dumps(d))

print('Loading fortunes...')
fortunes = load_fortunes()

if fortunes is None:
    print('Could not load fortunes, quitting')
    exit(-1)
else:
    with open(FORTUNES_FILE, 'w') as fortunes_file:
        fortunes_file.write(toml.dumps({'fortunes': fortunes}))

def get_qr_code_bitmap(url):
    q = pyqrcode.create(url)
    buf = BytesIO()

    q.png(buf, scale=4)
    it = Image.open(buf)
    i_i = it.convert('1')

    i_i.getdata()

    i = []
    for b in i_i.getdata():
        if b == 255:
            i.append(0)
        elif b == 0:
            i.append(255)
        else:
            print('ERROR')

    l = int(sqrt(len(i)))

    bitmap = []
    byte = 0
    counter = 0
    column_counter = 0
    for pixel in i:
        byte = byte << 1
        if pixel:
            byte = byte | 1
        counter = counter + 1
        column_counter = column_counter + 1


        if counter == 8:
            bitmap.append(byte)
            byte = 0
            counter = 0
        elif column_counter == l:
            byte = byte << 8 - counter
            bitmap.append(byte)
            byte = 0
            counter = 0
            column_counter = 0

    return [l, bitmap]

class UseTokenReturnValue(Enum):
    ALREADY_USED = 1
    NOT_ACTIVE = 2
    SUCCESS = 3

def use_token(token):
    print(token)
    print(used_tokens)
    print(f'Using token {token}...')
    if token in used_tokens:
        print('Token has already been used')
        return UseTokenReturnValue.ALREADY_USED
    if not token in active_tokens:
        print('Token is not active')
        return UseTokenReturnValue.NOT_ACTIVE

    used_tokens.append(token)
    active_tokens.remove(token)
#    save_tokens()
    
    return UseTokenReturnValue.SUCCESS

def generate_token():
    return ''.join(choices(ascii_letters + digits, k=10))

def generate_and_activate_tokens():
    tokens = [generate_token(), generate_token()]
    active_tokens.extend(tokens)
#    save_tokens()
    return tokens

def parse_qr_string(qr_string):
    return qr_string.lstrip('http://aftm.j51.eu/t/')

def get_qr_string(image):
    codes = decode(image)
    if len(codes) > 0:
        return codes[0].data.decode('utf-8')
    return None

def play_diagnostics():
    printer.println(f'active_tokens: {active_tokens}')
    printer.println('')
    printer.println(f'used_tokens: {used_tokens}')
    printer.feed(5)

def reset_state():
    load_fortunes()
    used_tokens = []
    active_tokens = []
    # check if printer has paper
    play_did_reset_message()

def play_already_used_message():
    print('play_already_used_message')
    pass

def play_not_active_message():
    print('play_not_active_message')
    pass

def play_did_reset_message():
    print('play_did_reset_message')
    pass

def play_unrecognized_fortune_type_message(type):
    print('play_unrecognized_fortune_type_message')
    pass

def qr_codes_printer(print_fortune):
    def wrapped_print_fortune(fortune, tokens):
        print_fortune(fortune)
        printer.feed(1)
        printer.println('Thanks for using our services. Here are two more codes:')
        printer.feed(3)
        [len1, bm1] = get_qr_code_bitmap('http://aftm.j51.eu/t/'+tokens[0])
        printer.printBitmap(len1, len1, bm1, LaaT=True)
        printer.feed(4)
        [len2, bm2] = get_qr_code_bitmap('http://aftm.j51.eu/t/'+tokens[1])
        printer.printBitmap(len2, len2, bm2, LaaT=True)
        printer.feed(4)

    return wrapped_print_fortune

@qr_codes_printer
def print_fortune(fortune):
    print(f'printing {fortune}')
    if fortune['type'] == 'SIMPLE':
        print_simple_fortune(fortune['text'])
    elif fortune['type'] == 'SIMPLE_WITH_TITLE':
        print_simple_fortune_with_title(fortune['title'], fortune['text'])
    elif fortune['type'] == 'TEMP_TAROT':
        print_temp_tarot(fortune)
    else:
        play_unrecognized_fortune_type_message(fortune['type'])

def print_temp_tarot(fortune):
    printer.doubleHeightOn()
    printer.doubleWidthOn()
    printer.justify('C')
    printer.print(fortune['title'])
    printer.feed(2)
    
    printer.doubleHeightOff()
    printer.doubleWidthOff()
    printer.boldOn()
    printer.justify('R')
    keywords = sample(fortune['keywords'], k=2)
    printer.println(keywords[0])
    printer.println(keywords[1])
    
    printer.doubleHeightOff()
    printer.doubleWidthOff()
    printer.boldOff()
    printer.underlineOn()
    printer.justify('C')
    printer.println('Light:')
    printer.underlineOff()
    printer.justify('L')
    light = sample(fortune['light'], k=3)
    printer.println('- '+light[0])
    printer.println('- '+light[1])
    printer.println('- '+light[2])
    printer.feed(1)
    printer.underlineOn()
    printer.justify('C')
    printer.println('Shadow:')
    printer.underlineOff()
    printer.justify('L')
    dark = sample(fortune['shadow'], k=3)
    printer.println('- '+dark[0])
    printer.println('- '+dark[1])
    printer.println('- '+dark[2]) 

def print_simple_fortune_with_title(title, text):
    printer.doubleHeightOn()
    printer.doubleWidthOn()
    printer.justify('C')
    printer.print(title)

    printer.doubleHeightOff()
    printer.doubleWidthOff()
    printer.justify('L')
    printer.print(text)

def print_simple_fortune(text):
    printer.doubleHeightOff()
    printer.doubleWidthOff()
    printer.justify('L')
    printer.print(text)

def print_seed_token():
    printer.println('seeding')
    tokens = generate_and_activate_tokens()
    [len1, bm1] = get_qr_code_bitmap('http://aftm.j51.eu/t/'+tokens[0])
    printer.printBitmap(len1, len1, bm1, LaaT=True)
    printer.feed(5)
    [len2, bm2] = get_qr_code_bitmap('http://aftm.j51.eu/t/'+tokens[1])
    printer.printBitmap(len2, len2, bm2, LaaT=True)
    printer.feed(5)

#[len1, bm1] = get_qr_code_bitmap('http://aftm.j51.eu/t/'+'SEED')
#printer.printBitmap(len1, len1, bm1, LaaT=True)
#printer.feed(5)
#[len2, bm2] = get_qr_code_bitmap('http://aftm.j51.eu/t/'+'DIAGNOSTICS')
#printer.printBitmap(len2, len2, bm2, LaaT=True)
#printer.feed(5)
    
    
fortune = choice(fortunes)
fresh_tokens = generate_and_activate_tokens()
print_fortune(fortune, fresh_tokens)
    
    
for frame in camera.capture_continuous(rawCapture, format="bgr", use_video_port=True):
    try:
        print('Processing frame...')
        image = frame.array
 
        qr_string = get_qr_string(image)
        rawCapture.truncate(0)

        if not qr_string:
            print('nothing found, sleeping...')
            sleep(0)
            continue

        print('Found code')

        token = parse_qr_string(qr_string)

        if token == 'DIAGNOSTICS':
            play_diagnostics()
            continue
        elif token == 'RESET':
            reset_state()
            continue
        elif token == 'SEED':
            print_seed_token()
            continue
    
        status = use_token(token)

        if status == UseTokenReturnValue.ALREADY_USED:
            play_already_used_message()
            continue
        elif status == UseTokenReturnValue.NOT_ACTIVE:
            play_not_active_message()
            continue

        fortune = choice(fortunes)

        fresh_tokens = generate_and_activate_tokens()
        print_fortune(fortune, fresh_tokens)
        printer.feed(5)
    except Exception as e:
        printer.println(f'Error: {e}')

  
        

