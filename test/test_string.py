import re

txt_list = [
    "1、 鞋名刘庆辉"
    "2、 性别男i"
    "3、 民族汉"
    "4、 出生1989年3月4日"
    "5、 住址安微省临泉具范兴集乡刘"
    "6、 营行政村东刘营6号"
    "7、 公民身份号码341221198903048135"
]
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
addressFrontIndex = 0
addressBackedIndex = 0

for k, str in enumerate(txt_list):
    print('k：', k)
    print('str：')
    str = str.replace(" ", "")
    txt = str.split("、", 1)[1]
    if "身份号码" in txt or "公民" in txt:
        id_info['id_number'] = re.findall(r"\d+", txt)
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
    if "姓名" in txt:
        id_info['name'] = txt.replace('姓名', '')
    if "住址" in txt:
        addressFrontIndex = k
        if isPositiveUpload:
            addressBackedIndex = addressFrontIndex + 1
        else:
            addressBackedIndex = addressFrontIndex - 1

addressFrontList = txt_list[addressFrontIndex].replace(" ", "").split("、", 1)
addressFront = ''
addressBacked = ''
if len(addressFrontList) > 1:
    addressFront = addressFrontList[1].replace('住址', '')

addressBackedList = txt_list[addressBackedIndex].replace(" ", "").split("、", 1)
if len(addressBackedList) > 1:
    addressBacked = addressBackedList[1]

id_info['address'] = addressFront + addressBacked

print(id_info)
