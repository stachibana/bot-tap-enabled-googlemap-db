# -*- coding: utf-8 -*-
import sys
import os
from flask import Flask, request, abort, send_file
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent, TextMessage, LocationMessage, LocationSendMessage,TextSendMessage, StickerSendMessage, MessageImagemapAction, ImagemapArea, ImagemapSendMessage, BaseSize
)
from io import BytesIO, StringIO
from PIL import Image
import requests
import urllib.parse
import numpy
import math

app = Flask(__name__)

line_bot_api = LineBotApi(os.environ.get('CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.environ.get('CHANNEL_SECRET'))

@app.route("/", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']

    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'

pins = [
        [35.690810, 139.704500, 'A1'],
        [35.691321, 139.703438, 'A5'],
        [35.691074, 139.705056, 'B2'],
        [35.691172, 139.704962, 'B3'],
        [35.691209, 139.704300, 'B4'],
        [35.692279, 139.702208, 'B10'],
        [35.690521, 139.705810, 'C4'],
        [35.690621, 139.706777, 'C5'],
        [35.691267, 139.706879, 'C6'],
        [35.691502, 139.707242, 'C7'],
        [35.693777, 139.706166, 'E1'],
        [35.693143, 139.706104, 'E2'],
        [35.689273, 139.703907, 'E5'],
        [35.688629, 139.703212, 'E6'],
        [35.688497, 139.703397, 'E7'],
        [35.689831, 139.703384, 'E9'],
        [35.689421, 139.701877, 'E10'],
        ];

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    if event.message.text.isdigit():
        line_bot_api.reply_message(
            event.reply_token,
            [
                LocationSendMessage(
                    title = pins[int(event.message.text)][2],
                    address = '東京都新宿区',
                    latitude = pins[int(event.message.text)][0],
                    longitude = pins[int(event.message.text)][1]
                )
            ]
        )
    else:
        line_bot_api.reply_message(
            event.reply_token,
            [
                TextSendMessage(text='位置情報を送ると近くで終電まで空いている駅一覧を教えるよ􀀪 '),
                TextSendMessage(text='line://nv/location'),
            ]
        )

@app.route("/imagemap/<path:url>/<size>")
def imagemap(url, size):
    map_image_url = urllib.parse.unquote(url)
    response = requests.get(map_image_url)
    img = Image.open(BytesIO(response.content))
    img_resize = img.resize((int(size), int(size)))
    byte_io = BytesIO()
    img_resize.save(byte_io, 'PNG')
    byte_io.seek(0)
    return send_file(byte_io, mimetype='image/png')

@handler.add(MessageEvent, message=LocationMessage)
def handle_location(event):
    lat = event.message.latitude
    lon = event.message.longitude

    zoomlevel = 18
    imagesize = 1040
    # 縦横1040ピクセルの画像を取得
    map_image_url = 'https://maps.googleapis.com/maps/api/staticmap?center={},{}&zoom={}&size=520x520&scale=2&maptype=roadmap&key={}'.format(lat, lon, zoomlevel, 'AIzaSyAtbs1MG9dES1JhT1gRDmx-QQtyhYpr2_g');
    map_image_url += '&markers=color:{}|label:{}|{},{}'.format('blue', '', lat, lon)

    # タップ可能なピンを配置する

    center_lat_pixel, center_lon_pixel = latlon_to_pixel(lat, lon)

    marker_color = 'red';
    label = 'E';

    # タップエリアのサイズ
    pin_width = 60 * 1.5;
    pin_height = 84 * 1.5;

    actions = []
    for i, pin in enumerate(pins):

        # 中心の緯度経度をピクセルに変換
        target_lat_pixel, target_lon_pixel = latlon_to_pixel(pin[0], pin[1])

        # 差分を計算
        delta_lat_pixel  = (target_lat_pixel - center_lat_pixel) >> (21 - zoomlevel - 1);
        delta_lon_pixel  = (target_lon_pixel - center_lon_pixel) >> (21 - zoomlevel - 1);

        marker_lat_pixel = imagesize / 2 + delta_lat_pixel;
        marker_lon_pixel = imagesize / 2 + delta_lon_pixel;

        x = marker_lat_pixel
        y = marker_lon_pixel

        # 範囲外のを除外
        if(pin_width / 2 < x < imagesize - pin_width / 2 and pin_height < y < imagesize - pin_width):

            map_image_url += '&markers=color:{}|label:{}|{},{}'.format(marker_color, label, pin[0], pin[1])

            actions.append(MessageImagemapAction(
                text = str(i),
                area = ImagemapArea(
                    x = x - pin_width / 2,
                    y = y - pin_height / 2,
                    width = pin_width,
                    height = pin_height
                )
            ))
            if len(actions) > 10:
                break

    # Imagemap Message
    message = ImagemapSendMessage(
        base_url = 'https://{}/imagemap/{}'.format(request.host, urllib.parse.quote_plus(map_image_url)),
        alt_text = '地図',
        base_size = BaseSize(height=imagesize, width=imagesize),
        actions = actions
    )
    line_bot_api.reply_message(
        event.reply_token,
        [
            TextSendMessage(text='終電まで空いている出口一覧です􀁇'),
            message
        ]
    )

# 緯度経度を逆グーデルマン関数使ってピクセルに変換
offset = 268435456;
radius = offset / numpy.pi;

def latlon_to_pixel(lat, lon):
    lat_pixel = round(offset + radius * lon * numpy.pi / 180);
    lon_pixel = round(offset - radius * math.log((1 + math.sin(lat * numpy.pi / 180)) / (1 - math.sin(lat * numpy.pi / 180))) / 2);
    return lat_pixel, lon_pixel

if __name__ == "__main__":
    app.run()
