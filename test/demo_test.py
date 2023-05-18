import re
import unittest


class MyTestCase(unittest.TestCase):
    def test_something(self):
        self.assertEqual(True, False)  # add assertion here

    def test_id_parse(self):
        txt_list = [
            "1、 姓名，赵婷媒",
            "2、 性别女民族汉",
            "3、 出生1993年4月18日",
            "4、 可",
            "5、 住址辽字省昌图县昌盛路利民",
            "6、 第二小区1排3号",
            "7、 公民身份号码211224199304185327"
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
                    continue

                if id_info['name'] == '':
                    pattern = r'名(.*)'
                    match = re.search(pattern, txt)
                    if match:
                        id_info['name'] = match.group(1)
            # 身份证二次提取
            if len(txt) == 15 or len(txt) == 18:
                if id_info['id_number'] == '':
                    id_info['id_number'] = txt

        print(id_info)
        return id_info


if __name__ == '__main__':
    unittest.main()
