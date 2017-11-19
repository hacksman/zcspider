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

import gevent
from gevent.pool import Pool
from gevent.queue import Queue

# 定义队列
desigers_queue = Queue()
details_queue  = Queue()

# 定义协程池
pool = Pool(4)
timeout = 180

start_url = "http://www.zcool.com.cn/designer"
headers = {'User-Agent': random.choice(UserAgentList)}

rules = {
    # 列表页提取规则
    "list_page": "//div[@class='designer-list-box clear']//div[@class='card-designer-list']/div/a/@href",
    # 访客列表提取规则  # 遇到JavaScript和ajax加载的信息，需要反破译
    "viwer_list": "//*[@class='visitor-list']"

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
    # 访客下所有用户
    viwers = parse(html, rules["viwer_list"])
    print(viwers)
    print('I am here')
    for each_viwer in viwers:
        print(each_viwer)




def crawl_infors(url):
    """ 
     爬取设计师资料页
    """
    pass

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

def heihei():
    # 爬取列表页
    crawl(start_url)
    # 爬取设计师队列
    pool.spawn(crawl_desigers_queue)
    pool.join()

if __name__ == '__main__':
    heihei()