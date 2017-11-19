# -*- coding: utf-8 -*-
# @Time    : 11/11/17 7:49 AM
import logging

UserAgent = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36'}


# 日志文件各种初始化
loggername = 'zcoolspider'
logger = logging.getLogger(loggername)
logger.setLevel(logging.DEBUG)

ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)

fh = logging.FileHandler('zcoolspider.log')
fh.setLevel(logging.DEBUG)

formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
fh.setFormatter(formatter)

logger.addHandler(ch)
logger.addHandler(fh)


MONGOCLIENT = "127.0.0.1:27017"
DATABASE    = "zcool"

FILEPATH    =  './'

SEARCHWORD = u'双十一'


# 邮件发送配置
SENDER = "1807651407@qq.com"
PASSCODE = "bwzsavkdrvtdebha"
RECEIVERS = ['113748870@qq.com']


# 定义随机请求头
UserAgentList = [
    'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2228.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:40.0) Gecko/20100101 Firefox/40.1',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.75.14 (KHTML, like Gecko) Version/7.0.3 Safari/7046A194A',
    'Mozilla/5.0 (Windows NT 6.1; WOW64; Trident/7.0; AS; rv:11.0) like Gecko',
]