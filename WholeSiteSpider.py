# -*- coding: utf-8 -*-
# @Time    : 11/18/17 2:13 PM

# 构建协程爬虫
from gevent import monkey
monkey.patch_all()

from settings import *
import requests
import random
from lxml import etree
import time
import re
import pymongo

from gevent.pool import Pool
from gevent.queue import Queue

# 定义队列
desigers_queue = Queue()
details_queue  = Queue()
recent_viwer_queue = Queue()

# 定义协程池
pool = Pool(10)
timeout = 10


mongoclient = pymongo.MongoClient(MONGOCLIENT)
database = mongoclient.get_database(DATABASE)
collection = database.get_collection("whole_zcool_member")

start_url = "http://www.zcool.com.cn/designer"
recent_viwer_url_base = "http://www.zcool.com.cn/u/%s/recentViewer"
headers = {'User-Agent': random.choice(UserAgentList)}

rules = {
    # 列表页提取规则
    "list_page": "//div[@class='designer-list-box clear']//div[@class='card-designer-list']/div/a/@href",
    # 用户id提取规则
    "user_id": "//div[@id='body']/@data-id",
    # 资料页提取规则
    "user_name": u"//th[text()='用户名']/../td/text()",
    "male": u"//th[text()='性别']/../td/text()",
    "sign": u"//th[text()='签名']/../td/text()",
    "goodat": u"//th[text()='领域']/../td/text()",
    "address": u"//th[text()='地址']/../td/text()",
    "hometown": u"//th[text()='家乡']/../td/text()",
    "livenow": u"//th[text()='现居']/../td/text()",
    "job": u"//th[text()='职业']/../td/text()",
    "z_age": u"//th[text()='酷龄']/../td/text()",
    "profile": u"//th[text()='简介']/../td/text()",
    "educated": u"//th[text()='毕业院校']/../td/text()",
    "QQ": u"//th[text()='QQ']/../td/text()",
    "wechat": u"//th[text()='微信']/../td/text()",
    "weibo": u"//a[@title='weibo']/@href",
    "renren": u"//a[@title='renren']/@href",
    "behance": u"//a[@title='behance']/@href",
    "dribbble": u"//a[@title='dribbble']/@href",
    "facebook": u"//a[@title='facebook']/@href",
    "twitter": u"//a[@title='twitter']/@href",
    "flickr": u"//a[@title='flickr']/@href",
    "devlantart": u"//a[@title='devlantart']/@href",


}


def crawl(url):
    """
    爬取设计师列表页
    """
    html = fetch(url)
    desigers = parse(html, rules['list_page'])
    for each_desiger in desigers:
        desigers_queue.put(each_desiger)


def crawl_home(url):
    """ 
     爬取设计师首页
    """

    html = fetch(url)
    user_id = parse(html, rules['user_id'])
    if not user_id:
        obj = {'url': url}
        if not _check_mongo_url(obj):
            obj['valid'] = '0'
            _insert_to_mongo(obj)
        return

    obj = {"uid": user_id[0]}
    if _check_mongo(obj):
        return
    obj['valid'] = '1'
    _insert_to_mongo(obj)

    recent_viwer_url = recent_viwer_url_base % (user_id[0])
    recent_viwer_queue.put(recent_viwer_url)

    details_url = url + "/profile#tab_anchor"
    details_queue.put(details_url)


def crawl_infors(url):
    """ 
     爬取设计师资料页
    """
    html = fetch(url)
    infor = {
        "uid": parse(html, rules['user_id'])[0],
        "username": parse(html, rules['user_name'])[0],
        "male": infor_parse(html, "male"),
        "sign": infor_parse(html, "sign"),
        "goodat": infor_parse(html, "goodat"),
        "address": infor_parse(html, "address"),
        "hometown": infor_parse(html, "hometown"),
        "livenow": infor_parse(html, "livenow"),
        "job": infor_parse(html, "job"),
        "z_age": infor_parse(html, "z_age"),
        "profile": infor_parse(html, "profile"),
        "educated": infor_parse(html, "educated"),
        "contact": [
            infor_parse(html, "QQ"),
            infor_parse(html, "wechat"),
        ],
        "personal_link":[
            {"weibo": infor_parse(html, "weibo")},
            {"renren": infor_parse(html, "renren")},
            {"behance": infor_parse(html, "behance")},
            {"dribbble": infor_parse(html, "dribbble")},
            {"facebook": infor_parse(html, "facebook")},
            {"twitter": infor_parse(html, "twitter")},
            {"flickr": infor_parse(html, "flickr")},
            {"devlantart": infor_parse(html, "devlantart")},
        ],

    }
    _update_mongo(infor)


def infor_parse(html, infor):
    return None if not parse(html, rules[infor]) else parse(html, rules[infor])[0].strip()

def crawl_desigers_queue():
    """
    爬取设计师队列 
    """
    while True:
        # timeout为等待时间，时间过长没有找到的话，就返回，这里对于协程的理解还不够深刻，需要再补课
        desiger_url = desigers_queue.get(timeout=timeout)
        # if desigers_queue.empty():
        #     return
        pool.spawn(crawl_home, desiger_url)


def crawl_recent_viewer_queue():
    """ 
     爬取最近访问用户队列
    """
    while True:
        url = recent_viwer_queue.get()
        pool.spawn(crawl_recent_viewer, url)


def crawl_recent_viewer(url):
    """
    爬取最近访客页 
    """
    html = fetch(url)
    covert2json = eval(html)
    for each_member in covert2json['data']['content']:
        obj = {"uid": str(each_member["memberTinyCard"]["id"])}
        if _check_mongo(obj):
            continue
        memberurl = each_member["memberTinyCard"]["pageUrl"]
        desigers_queue.put(memberurl)


def crawl_infor_queue():
    """
    爬取设计师资料页队列 
    """
    while True:
        url = details_queue.get()
        pool.spawn(crawl_infors, url)


def parse(html, rule):
    """
    解析网页
    """
    return etree.HTML(html).xpath(rule)


def fetch(url):
    """
    发起http请求,返回html 
    """
    req = requests.get(url, headers=headers)
    html = req.text
    return html


def _insert_to_mongo(data):
    collection.insert(data)


def _check_mongo(data):
    _exists = collection.find_one(data)
    return True if _exists else False


def _check_mongo_url(data):
    _exists = collection.find_one({"url": data['url']})
    return True if _exists else False


def _update_mongo(data):
    collection.update({"uid": data['uid']}, {"$set": data})


def run():
    # 爬取列表页
    crawl(start_url)
    # 爬取设计师队列
    pool.spawn(crawl_desigers_queue)
    # 爬取最近访客队列
    pool.spawn(crawl_recent_viewer_queue)
    # 爬取设计师资料队列页
    pool.spawn(crawl_infor_queue)

    pool.join()

if __name__ == '__main__':
    run()