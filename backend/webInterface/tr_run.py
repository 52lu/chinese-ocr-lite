import time
from model import OcrHandle
import tornado.web
import tornado.gen
import tornado.httpserver
import base64
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import datetime
import json
import os
import re

from backend.tools.np_encoder import NpEncoder
from backend.tools import log
import logging

logger = logging.getLogger(log.LOGGER_ROOT_NAME + '.' + __name__)

ocrhandle = OcrHandle()

request_time = {}
now_time = time.strftime("%Y-%m-%d", time.localtime(time.time()))
from config import max_post_time, dbnet_max_size, white_ips


class TrRun(tornado.web.RequestHandler):
    """
    使用 tr 的 run 方法
    """

    def get(self):
        self.set_status(404)
        self.write("404 : Please use POST")

    @tornado.gen.coroutine
    def post(self):
        """

        :return:
        报错：
        400 没有请求参数

        """
        start_time = time.time()
        short_size = 990
        global now_time
        global request_time
        img_up = self.request.files.get('file', None)
        img_b64 = self.get_argument('img', None)
        compress_size = self.get_argument('compress', short_size)

        # 判断是上传的图片还是base64
        self.set_header('content-type', 'application/json')
        up_image_type = None
        if img_up is not None and len(img_up) > 0:
            img_up = img_up[0]
            up_image_type = img_up.content_type
            up_image_name = img_up.filename
            img = Image.open(BytesIO(img_up.body))
        elif img_b64 is not None:
            raw_image = base64.b64decode(img_b64.encode('utf8'))
            img = Image.open(BytesIO(raw_image))
        else:
            self.set_status(400)
            logger.error(json.dumps({'code': 400, 'msg': '没有传入参数'}, cls=NpEncoder))
            self.finish(json.dumps({'code': 400, 'msg': '没有传入参数'}, cls=NpEncoder))
            return

        try:
            if hasattr(img, '_getexif') and img._getexif() is not None:
                orientation = 274
                exif = dict(img._getexif().items())
                if orientation not in exif:
                    exif[orientation] = 0
                if exif[orientation] == 3:
                    img = img.rotate(180, expand=True)
                elif exif[orientation] == 6:
                    img = img.rotate(270, expand=True)
                elif exif[orientation] == 8:
                    img = img.rotate(90, expand=True)
        except Exception as ex:
            error_log = json.dumps({'code': 400, 'msg': '产生了一点错误，请检查日志', 'err': str(ex)}, cls=NpEncoder)
            logger.error(error_log, exc_info=True)
            self.finish(error_log)
            return
        img = img.convert("RGB")

        time_now = time.strftime("%Y-%m-%d-%H_%M_%S", time.localtime(time.time()))
        time_day = time.strftime("%Y-%m-%d", time.localtime(time.time()))
        if time_day != now_time:
            now_time = time_day
            request_time = {}

        '''
        是否开启图片压缩
        默认为960px
        值为 0 时表示不开启压缩
        非 0 时则压缩到该值的大小
        '''
        res = []
        do_det = True
        remote_ip_now = self.request.remote_ip
        if remote_ip_now not in request_time:
            request_time[remote_ip_now] = 1
        elif request_time[remote_ip_now] > max_post_time - 1 and remote_ip_now not in white_ips:
            res.append("今天访问次数超过{}次！".format(max_post_time))
            do_det = False
        else:
            request_time[remote_ip_now] += 1

        if compress_size is not None:
            try:
                compress_size = int(compress_size)
            except ValueError as ex:
                # logger.error(exc_info=True)
                res.append("短边尺寸参数类型有误，只能是int类型")
                do_det = False
                # self.finish(json.dumps({'code': 400, 'msg': 'compress参数类型有误，只能是int类型'}, cls=NpEncoder))
                # return

            short_size = compress_size
            if short_size < 64:
                res.append("短边尺寸过小，请调整短边尺寸")
                do_det = False

            short_size = 32 * (short_size // 32)

        img_w, img_h = img.size
        if max(img_w, img_h) * (short_size * 1.0 / min(img_w, img_h)) > dbnet_max_size:
            # logger.error(exc_info=True)
            res.append("图片reize后长边过长，请调整短边尺寸")
            do_det = False
            # self.finish(json.dumps({'code': 400, 'msg': '图片reize后长边过长，请调整短边尺寸'}, cls=NpEncoder))
            # return

        if do_det:

            res = ocrhandle.text_predict(img, short_size)

            img_detected = img.copy()
            img_draw = ImageDraw.Draw(img_detected)
            colors = ['red', 'green', 'blue', "purple"]

            for i, r in enumerate(res):
                rect, txt, confidence = r

                x1, y1, x2, y2, x3, y3, x4, y4 = rect.reshape(-1)
                size = max(min(x2 - x1, y3 - y2) // 2, 20)

                myfont = ImageFont.truetype(os.path.join(os.getcwd(), "fangsong_GB2312.ttf"), size=size)
                fillcolor = colors[i % len(colors)]
                img_draw.text((x1, y1 - size), str(i + 1), font=myfont, fill=fillcolor)
                for xy in [(x1, y1, x2, y2), (x2, y2, x3, y3), (x3, y3, x4, y4), (x4, y4, x1, y1)]:
                    img_draw.line(xy=xy, fill=colors[i % len(colors)], width=2)

            output_buffer = BytesIO()
            img_detected.save(output_buffer, format='JPEG')
            byte_data = output_buffer.getvalue()
            img_detected_b64 = base64.b64encode(byte_data).decode('utf8')

        else:
            output_buffer = BytesIO()
            img.save(output_buffer, format='JPEG')
            byte_data = output_buffer.getvalue()
            img_detected_b64 = base64.b64encode(byte_data).decode('utf8')

        log_info = {
            'ip': self.request.remote_ip,
            'return': res,
            'time': time_now
        }
        txt_list = []
        for text in res:
            txt_list.append(text[1])
        # 解析身份证信息
        try:
            id_info = self.parseIdCard(txt_list)
        except Exception as ex:
            log_info['err'] = ex
            logger.error(json.dumps({'error': log_info}, cls=NpEncoder))
            self.finish(json.dumps({'code': 410, 'msg': '身份证识别失败~'}, cls=NpEncoder))
            return

        data = {
            'speed_time': round(time.time() - start_time, 2),
            'txt_list': txt_list
        }
        ocr_type = self.get_argument('ocr_type', None)
        data['ocr_type'] = ocr_type
        if ocr_type is None:
            data['img_detected'] = 'data:image/jpeg;base64,' + img_detected_b64
            data['raw_out'] = res
        else:
            data['id_info'] = id_info

        # 输出
        logger.info(json.dumps(data, cls=NpEncoder))

        self.finish(json.dumps(
            {
                'code': 200,
                'msg': '成功',
                'data': data
            },
            cls=NpEncoder))
        return

    def parseIdCard(self, txt_list):
        ocr_type = self.get_argument('ocr_type', None)
        if ocr_type is None:
            return []
        # 解析身份证信息
        id_info = {
            'id_number': '',  # 身份证号码
            'name': '',  # 姓名
            'sex': '',  # 性别
            'birthday': '',  # 生日
            'address': '',  # 户籍地址
            'nation': '',  # 民族
        }

        # 判断是否倒着上传
        positiveStr = txt_list[0]
        isPositiveUpload = True
        if "身份号码" in positiveStr or "公民" in positiveStr:
            isPositiveUpload = False

        # 户籍地址组成部分
        addressFrontIndex = None
        addressBackedIndex = None

        for k, text in enumerate(txt_list):
            text = text.replace(" ", "")
            txt = text.split("、", 1)[1]
            if "身份号码" in txt or "公民" in txt:
                pattern = r'号码(.*)'
                match = re.search(pattern, txt)
                if match:
                    id_info['id_number'] = match.group(1)
            if "出生" in txt and "年" in txt:
                birthdayList = re.findall(r"\d+", txt)
                id_info['birthday'] = birthdayList[0] + '-' + birthdayList[1] + '-' + birthdayList[2]
            if "民族" in txt:
                pattern = r'民族(.*)'
                match = re.search(pattern, txt)
                if match:
                    id_info['nation'] = match.group(1)
            if "性别" in txt:
                pattern = r'性别([\u4e00-\u9fa5])'
                match = re.search(pattern, txt)
                if match:
                    id_info['sex'] = match.group(1)
            if "名" in txt:
                if "姓名" in txt:
                    id_info['name'] = txt.replace('姓名', '')
                    break

                if id_info['name'] == '':
                    pattern = r'名(.*)'
                    match = re.search(pattern, txt)
                    if match:
                        id_info['name'] = match.group(1)
            if "住址" in txt:
                addressFrontIndex = k
                if isPositiveUpload:
                    addressBackedIndex = addressFrontIndex + 1
                else:
                    addressBackedIndex = addressFrontIndex - 1

        if addressFrontIndex is not None:
            addressFrontList = txt_list[addressFrontIndex].replace(" ", "").split("、", 1)
            addressFront = ''
            addressBacked = ''
            if len(addressFrontList) > 1:
                addressFront = addressFrontList[1].replace('住址', '')

            addressBackedList = txt_list[addressBackedIndex].replace(" ", "").split("、", 1)
            if len(addressBackedList) > 1:
                addressBacked = addressBackedList[1]
            id_info['address'] = addressFront + addressBacked

        return id_info
