# encoding: UTF-8
import re
import requests
import json
import os
import time
import traceback
import hashlib
import hmac
import urllib
import urllib.parse
import urllib.request

import multiprocessing
#from multiprocessing import Process, Queue

import logging

from logging.handlers import RotatingFileHandler

#pip install ConcurrentLogHandler
#from cloghandler import ConcurrentRotatingFileHandler

#pip install concurrent-log-handler
from concurrent_log_handler import ConcurrentRotatingFileHandler
from client import Client

import exceptions


logger = logging.getLogger('main')
#logfile = "tri_bitcoin_id_{0}.log".format(int(time.time()))
logfile = "log_cek_press.log"
rotateHandler = ConcurrentRotatingFileHandler(logfile, "a", 2*1024*1024, 50)
#rotateHandler = RotatingFileHandler(logfile, "a", 2*1024*1024, 50)
formatter = logging.Formatter("%(asctime)s - %(filename)s[line:%(lineno)d] - %(levelname)s: %(message)s")
rotateHandler.setFormatter(formatter)
logger.addHandler(rotateHandler)
logger.setLevel(logging.INFO)
#logger.info("init!")



api_key='XXXXXXX'

client = Client(api_key)



depth = client.get_order_book('EOS-BTC')
logger.info(depth)


interval=0
total_time=10
i=0
process_timeout=20

while(i<total_time):
    logger.info("try times:{0}".format(i+1))
    print("try times:{0}".format(i + 1))
    #get_user_balance(i)
    #get_depth_btc_idr()

    re_output_p1 = multiprocessing.Queue()
    re_output_p2 = multiprocessing.Queue()
    re_output_p3 = multiprocessing.Queue()
    re_output_p4 = multiprocessing.Queue()
    re_output_p5 = multiprocessing.Queue()
    re_output_p6 = multiprocessing.Queue()

    # p6 = multiprocessing.Process(target=client.get_order_book_process, args=('EOS-BTC', re_output_p6,))

    p1 = multiprocessing.Process(target=client.get_accounts_fb, args=(re_output_p1,))

    p2 = multiprocessing.Process(target=client.get_accounts_fb, args=(re_output_p2,))

    p3 = multiprocessing.Process(target=client.get_accounts_fb, args=(re_output_p3,))

    p4 = multiprocessing.Process(target=client.get_accounts_fb, args=(re_output_p4,))

    p5 = multiprocessing.Process(target=client.get_accounts_fb, args=(re_output_p5,))

    p6 = multiprocessing.Process(target=client.get_accounts_fb, args=(re_output_p6,))



    p1.start()  # process of get_depth_btc_idr
    p2.start()  # process of get_depth_str_btc
    p3.start()  # process of get_depth_str_idr
    p4.start()  # process of get_depth_str_idr
    p5.start()  # process of get_depth_str_idr
    p6.start()  # process of get_depth_str_idr


    p1.join(timeout=process_timeout)
    p2.join(timeout=process_timeout)
    p3.join(timeout=process_timeout)
    p4.join(timeout=process_timeout)
    p5.join(timeout=process_timeout)
    p6.join(timeout=process_timeout)

    if not re_output_p1.empty():
        arr_re_p1 = re_output_p1.get(True)
        print(arr_re_p1)
        logger.info("output for p1:{0}".format(arr_re_p1))
    else:
        # TODO 增加错误的处理
        print("error!empty queue")


    if not re_output_p2.empty():
        arr_re_p2 = re_output_p2.get(True)
        print(arr_re_p2)
        logger.info("output for p2:{0}".format(arr_re_p2))
    else:
        # TODO 增加错误的处理
        print("error!empty queue")


    if not re_output_p3.empty():
        arr_re_p3 = re_output_p3.get(True)
        print(arr_re_p3)
        logger.info("output for p3:{0}".format(arr_re_p3))
    else:
        # TODO 增加错误的处理
        print("error!empty queue")

    if not re_output_p4.empty():
        arr_re_p4 = re_output_p4.get(True)
        print(arr_re_p4)
        logger.info("output for p4:{0}".format(arr_re_p4))
    else:
        # TODO 增加错误的处理
        print("error!empty queue")

    if not re_output_p5.empty():
        arr_re_p5 = re_output_p5.get(True)
        print(arr_re_p5)
        logger.info("output for p5:{0}".format(arr_re_p5))
    else:
        # TODO 增加错误的处理
        print("error!empty queue")

    if not re_output_p6.empty():
        arr_re_p6 = re_output_p6.get(True)
        print(arr_re_p6)
        logger.info("output for p6:{0}".format(arr_re_p6))
    else:
        # TODO 增加错误的处理
        print("error!empty queue")


    logger.info("this time finished!")
    time.sleep(interval)
    i+=1



depth = client.get_order_book('EOS-BTC')
logger.info(depth)

