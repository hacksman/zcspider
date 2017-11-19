# -*- coding: utf-8 -*-
# @Time    : 11/11/17 7:46 AM

import requests
from settings import *
from s_settings import *
from lxml import etree
import re
import time
import os
import pymongo
import zipfile
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.header import Header
from pypinyin import lazy_pinyin


# 协程爬取
from gevent import monkey
monkey.patch_all()

from gevent.pool import Pool
from gevent.queue import Queue

# 定义队列
list_queue = Queue()

# 定义协程池
pool = Pool(size=10)

num_reg = re.compile('\d+')
small_img_reg = re.compile('.*jpg@(\d+)w.*')

neturl = "http://www.zcool.com.cn"

mongoclient = pymongo.MongoClient(MONGOCLIENT)
mongo       = mongoclient.get_database(DATABASE)

filepath    = FILEPATH

def inputword(word):
    url = 'http://www.zcool.com.cn/search/content?field=0&other=0&sort=5&word=%s&type=0&recommend=3&requestId=requestId_1510357168836' % word
    return [url, word]

def searchparse(url=None, word=None, nexturl=None, obj=None):

    if nexturl:
        url = nexturl

    req = requests.get(url, headers=UserAgent)
    if not req.status_code == 200:
        logger.debug('search page is error: %s' % req.text)
        return
    if u'没有找到符合条件的结果' in req.text:
        print('no result， Please try another one.')
        return

    wait2xpath = etree.HTML(req.text)

    if not obj:
        total_count_raw = wait2xpath.xpath('//*[@class="compatible-title-space"]/p/text()')[0]
        total_count = num_reg.findall(total_count_raw)[0]
        obj = {
            "search_word": word,
            "total_count": total_count,
            "work_infors": {}
        }
        if check_mongo(obj):
            print(u'该关键词已经被检索过，跳过！！！')
            return

    work_list = wait2xpath.xpath('//div[@class="work-list-box clear"]//div[@data-objid]')
    for each_work in work_list:
        pid         = each_work.xpath('./@data-objid')[0]
        ptype       = each_work.xpath('./@data-objtype')[0]
        inner_url   = each_work.xpath('./div[@class="card-img"]/a/@href')[0]
        title       = each_work.xpath('./div[@class="card-img"]/a/@title')[0].replace('.', '')
        cover_img   = each_work.xpath('./div[@class="card-img"]/a/img/@src')[0]
        work_type   = each_work.xpath('./div[@class="card-info"]/p[@class="card-info-type"]/@title')[0]
        hot         = num_reg.findall(each_work.xpath('./div[@class="card-info"]/p[@class="card-info-item"]/span[@class="statistics-view"]/@title')[0])[0]
        comment     = num_reg.findall(each_work.xpath('./div[@class="card-info"]/p[@class="card-info-item"]/span[@class="statistics-comment"]/@title')[0])[0]
        recommend   = num_reg.findall(each_work.xpath('./div[@class="card-info"]/p[@class="card-info-item"]/span[@class="statistics-tuijian"]/@title')[0])[0]
        author      = each_work.xpath('./div[@class="card-item"]/span[@class="user-avatar showMemberCard"]/a/@title')[0]
        author_url  = each_work.xpath('./div[@class="card-item"]/span[@class="user-avatar showMemberCard"]/a/@href')[0]
        creat_time  = each_work.xpath('./div[@class="card-item"]/span[@class="time"]/@title')[0].split(u'创建时间：')[1]

        if obj['work_infors'].get(title):
            title = title + str('-2')

        obj['work_infors'][title] = {
            "pid": pid,
            "ptype": ptype,
            "inner_url": inner_url,
            "title": title,
            "cover_img": cover_img,
            "work_type": work_type,
            "hot": hot,
            "comment": comment,
            "recommend": recommend,
            "author": author,
            "author_url": author_url,
            "creat_time": creat_time,
            "imglist": []
        }

        # 协程爬取
        pool.spawn(innerpage_parse, inner_url, obj, title)
        pool.join()

    next_page_url = wait2xpath.xpath('//a[@class="laypage_next"]/@href')
    if next_page_url:
        next_page_url = neturl + next_page_url[0]
        print(next_page_url)
        searchparse(nexturl=next_page_url, obj=obj)

def innerpage_parse(url, obj, title):
    req = requests.get(url, headers=UserAgent)
    total_count = int(obj.get('total_count'))
    if not req.status_code == 200:
        logger.debug('inner page is error: %s' % req.text)
        return
    wait2xpath = etree.HTML(req.text)

    # 存在两种情况的图片，需要区分情况
    imglist = wait2xpath.xpath('//div[@class="article-content-wraper"]//img/@src') or wait2xpath.xpath('//div[@class="work-show-box"]//div[@class="reveal-work-wrap"]//img/@data-src') or wait2xpath.xpath('//div[@class="work-show-box"]//div[@class="reveal-work-wrap"]//img/@src')

    for img in imglist:
        obj['work_infors'][title]['imglist'].append(img)

    if total_count > 2000:
        total_count = 2000

    if len(obj['work_infors']) < total_count:
        print(u'现在的长度是 %s 还是没有达到你的要求长度 %s，返回咯' % (str(len(obj['work_infors'])), str(total_count)))
        return

    save_img_local(filepath, obj)

    mongo.get_collection("zcool").insert(obj)

def save_img_local(filepath, obj):
    os.mkdir(filepath + obj['search_word'])
    for work_key, work_value in obj['work_infors'].items():
        work_key = work_key.replace('/', '')
        os.makedirs(filepath + obj['search_word'] + "/" + work_key)
        length = len(work_value.get('imglist'))
        if not length:
            continue
        for img_num, img_url in zip(range(length), work_value.get("imglist")):
            content = requests.get(img_url).content
            time.sleep(0.5)
            with open(filepath + obj['search_word'] + '/' + work_key + '/' + str(img_num) + '.jpg', 'wb') as f:
                f.write(content)

def check_mongo(obj):
    _exists = mongo.get_collection("zcool").find_one({"search_word": obj.get("search_word")})
    return True if _exists else False

def package2zip(source_dir, out_filename):
    zipf = zipfile.ZipFile(out_filename, "w")
    par_len = len(os.path.dirname(source_dir))
    for parent, dirnames, filenames in os.walk(source_dir):
        for filename in filenames:
            pathfile = os.path.join(parent, filename)
            arcname  = pathfile[par_len:].strip(os.path.sep)
            zipf.write(pathfile, arcname)
    zipf.close()

def send_smtp_friend(sender, receiver, passcode, filename):
    # 创建附件实例
    message = MIMEMultipart()
    message['From']     = Header('解忧杂货铺', 'utf-8')
    message['To']       = Header('一个神秘人', 'utf-8')
    message['Subject']  = Header(filename.strip('./').strip('.zip'), 'utf-8')

    # 邮件正文
    message.attach(MIMEText('这是一封神奇的邮件，来自神奇的解忧杂货铺', 'plain', 'utf-8'))

    # 构造附件
    att1 = MIMEApplication(open(filename, 'rb').read())
    att1['Content-Type'] = 'application/octet-stream'
    # 此处filename可以任意改名
    filename2pinyin = "".join(lazy_pinyin(filename.strip('./').strip('.zip')))
    att1['Content-Disposition'] = 'attachment; filename=%s' % (filename2pinyin + '.zip')
    message.attach(att1)

    try:
        smtp_obj = smtplib.SMTP_SSL("smtp.qq.com", 465)
        smtp_obj.login(sender, passcode)
        smtp_obj.sendmail(sender, receiver, message.as_string())
        smtp_obj.quit()
        print('邮件发送成功')

    except smtplib.SMTPException as e:
        print('Error: 发送失败, 原因是: %s' % e)

def run():
    # infor = inputword(SEARCHWORD)
    # searchparse(infor[0], infor[1])
    package2zip('./%s' % SEARCHWORD, SEARCHWORD + '.zip')
    send_smtp_friend(SENDER, RECEIVERS, PASSCODE, './' + SEARCHWORD + '.zip')

if __name__ == '__main__':
    print('startTime: %s' % time.strftime("%Y-%m-%d %H-%M-%S"))
    run()
    print("endTime: %s" % time.strftime("%Y-%m-%d %H-%M-%S"))
