import re
import unittest


class TestDemoCase(unittest.TestCase):
    def test_id_parse(self):
        txt_list = [
            "1、 公民身份号码341221198903048135",
            "2、 营行政村东刘营6号",
            "3、 住址安徽省临泉具范兴集乡刘",
            "4、 出生1989年3月4日",
            "5、 性别男民族汉",
            "6、 姓名刘庆辉"
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

        for str in txt_list:
            txt = str.split("、", 1)
            if "身份号码" in txt or "公民" in txt:
                id_info['id_number'] = re.findall(r"\d+", txt)
            if "出生" in txt and "年" in txt:
                id_info['birthday'] = re.findall(r"\d+", txt)
            if "民族" in txt:
                id_info['nation'] = txt.replace('民族', '')
            if "性别" in txt:
                id_info['sex'] = txt.replace('性别', '')
            if "姓名" in txt:
                id_info['name'] = txt.replace('姓名', '')
        print(id_info)
        return id_info


unittest.main()
