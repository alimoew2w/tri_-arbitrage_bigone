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
import math

import multiprocessing
#from multiprocessing import Process, Queue

import logging

from logging.handlers import RotatingFileHandler

#pip install ConcurrentLogHandler
#from cloghandler import ConcurrentRotatingFileHandler

#pip install concurrent-log-handler
from concurrent_log_handler import ConcurrentRotatingFileHandler
from client import Client

from exceptions import BigoneAPIException




class arbitrage_bitcoin:

    # ----------------------通用设置区----------------------
    #eg: base_cur:EOS -> quote_cur:BTC    EOS/BTC -> mid_cur:USDT
    #基准货币
    #base_cur = 'EOS'
    #base_cur = 'ETH'
    base_cur = 'IDT'



    #定价货币
    #quote_cur = 'BTC'
    #quote_cur = 'EOS'
    quote_cur = 'ETH'

    #中间货币
    #mid_cur = 'USDT'
    #mid_cur = 'BTC'
    mid_cur = 'BTC'

    # 用于统计重大错误的次数
    err_amt = 0

    # 重大错误的阈值
    err_limit = 500000000

    # 线程的超时时间
    process_timeout = 600

    # 多个线程中的每个操作api的间隔时间
    # interval_in_thread_api=0.2
    interval_in_thread_api = 0

    #trade的重试次数
    MAX_TRADE_TIMES = 10

    # 重大成功套现的次数，超过就退出
    suc_limit = 10000

    # 用于统计成功的套现的次数
    suc_amt = 0

    #自动退出的检测文件，判断如果有此文件存放，删除后并退出
    AUTO_QUIT_FILENAME = "smallmummy.quit"

    #bigone的apikey
    big_one_api_key = 'XXXXXX'
    # ----------------------通用设置区----------------------




    # ----------------------触发限制设置区----------------------
    AMT_TRI_POS = 1.001  # 触发pos的门限制

    AMT_TRI_NAG = 1.001  # 触发nag的门限制

    PROFIT_AMT_TRI_POS = 0  #-1e-05  # 触发pos的门限制(根据预估利润), 以中间货币结算

    PROFIT_AMT_TRI_NAG = 0  #-1e-05  # 触发nag的门限制(根据预估利润), 以中间货币结算

    #base货币中可用的仓位比例
    BAL_BASE_RATIO = 1

    #quote货币中可用的仓位比例
    BAL_QUOTE_RATIO = 0.5

    #mid货币中可用的仓位比例
    BAL_MID_RATIO = 0.5
    # ----------------------触发限制设置区----------------------



    # ----------------------货币精度、限制设置区----------------------
    #为了控制风险，最大可以一次性交易的base_cur
    #MAX_BASE_AMT_TRADE = 10  # EOS
    MAX_BASE_AMT_TRADE = 1900  # ETH


    # 最小的base_cur的交易单位，太小的话影响精确度，而且容易超出系统限制(一般设置为exchanges的限制)
    #MIN_BASE_CUR_AMT = 1.2  #EOS
    MIN_BASE_CUR_AMT = 150  # ETH

    #TODO 增加处理逻辑
    #最小的定价货币限制(一般设置为exchanges的限制)
    MIN_QUOTE_CUR_AMT = 1.2

    # TODO 增加处理逻辑
    # 最小的定价货币限制(一般设置为exchanges的限制)
    MIN_MID_CUR_AMT = 1.2

    #exchanges的小数点最小精度要求
    #QUOTE_PRICE_DECIMAL = 8   #BTC
    QUOTE_PRICE_DECIMAL = 6  # EOS

    #BASE_TRADE_DECIMAL = 1   #EOS
    BASE_TRADE_DECIMAL = 0  # ETH


    #MID_PRICE_DECIMAL = 3     #USDT
    MID_PRICE_DECIMAL = 8  # BTC

    #QUOTE_TRADE_DECIMAL = 5  #BTC
    QUOTE_TRADE_DECIMAL = 4  # EOS

    # ----------------------货币精度、限制设置区----------------------





    def __init__(self):

        #初始化日志模块
        self.logger = logging.getLogger('main')

        self.logfile = "ll-{0}-{1}_{2}_arbitrage.log".format(self.base_cur,self.mid_cur,self.quote_cur)
        self.rotateHandler = ConcurrentRotatingFileHandler(self.logfile, "a", 2 * 1024 * 1024, 100)
        self.formatter = logging.Formatter("%(asctime)s - %(filename)s[line:%(lineno)d] - %(levelname)s: %(message)s")
        self.rotateHandler.setFormatter(self.formatter)

        self.logger.addHandler(self.rotateHandler)

        # 日志级别，可设置
        self.logger.setLevel(logging.DEBUG)

        self.tax = 0.001  # 0.3%
        #self.tax = 0  # 0.3%

        #三种货币的账户余额
        self.bal_mid_cur=0
        self.bal_quote_cur=0
        self.bal_base_cur=0

        #三种交易对的depth
        self.quote_mid_market_sell = dict()
        self.quote_mid_market_buy = dict()
        self.base_quote_market_sell = dict()
        self.base_quote_market_buy = dict()
        self.base_mid_market_sell = dict()
        self.base_mid_market_buy = dict()


        #三种交易对的depth中的第一档数据
        # a1/aq1为quote--mid的depth
        # b1/bq1为base--quote的depth
        # c1/cq1为base--mid的depth
        self.a1=0
        self.aq1=0
        self.a2 = 0
        self.aq2 = 0
        self.b1=0
        self.bq1=0
        self.b2 = 0
        self.bq2 = 0
        self.c1=0
        self.cq1=0
        self.c2 = 0
        self.cq2 = 0


        #bigone的api调用
        self.client = Client(self.big_one_api_key)

        #首次获取用户的所有账户余额
        self.get_user_balance()



    def get_user_balance(self):

        try:
            #account = self.client.get_account('BTC')
            #print(account)

            accounts = self.client.get_accounts()
            for i in range(len(accounts)):
                if accounts[i]['account_type'] == self.quote_cur:
                    self.bal_quote_cur=float(accounts[i]['active_balance']) * self.BAL_QUOTE_RATIO

                if accounts[i]['account_type'] == self.base_cur:
                    self.bal_base_cur=float(accounts[i]['active_balance']) * self.BAL_BASE_RATIO

                if accounts[i]['account_type'] == self.mid_cur:
                    self.bal_mid_cur=float(accounts[i]['active_balance']) * self.BAL_MID_RATIO



            #for test use
            #self.bal_mid_cur = 10000
            #self.bal_quote_cur = 3
            #self.bal_base_cur = 0.3

            self.logger.info("{0} is {1},{2} is {3},{4} is {5}".format(self.mid_cur, self.bal_mid_cur, self.quote_cur,
                                                                       self.bal_quote_cur, self.base_cur,
                                                                       self.bal_base_cur))
            return
        except:
            self.logger.error(traceback.format_exc())


    def get_depth_quote_mid(self,re_output):

        try:
            depth_return = self.client.get_order_book(self.quote_cur+'-'+self.mid_cur)

            # btc_idr的卖出价格depth------ask
            self.quote_mid_market_sell = dict()
            self.quote_mid_market_sell = depth_return.get("asks")
            self.a1 = float(self.quote_mid_market_sell[0]['price'])
            self.aq1 = float(self.quote_mid_market_sell[0]['amount'])

            # btc_idr的买入价格depth-----bid
            self.quote_mid_market_buy = dict()
            self.quote_mid_market_buy = depth_return.get("bids")
            self.a2 = float(self.quote_mid_market_buy[0]['price'])
            self.aq2 = float(self.quote_mid_market_buy[0]['amount'])

            self.logger.debug("a1:{0},aq1:{1}".format(self.a1, self.aq1))
            self.logger.debug("a2:{0},aq2:{1}".format(self.a2, self.aq2))

            arr_re = dict()

            arr_re["quote_mid_market_sell"] = self.quote_mid_market_sell[0:10]
            arr_re["quote_mid_market_buy"] = self.quote_mid_market_buy[0:10]

            arr_re["a1"] = self.a1
            arr_re["aq1"] = self.aq1
            arr_re["a2"] = self.a2
            arr_re["aq2"] = self.aq2

            re_output.put(arr_re)
        except:
            self.logger.error(traceback.format_exc())


    def get_depth_base_quote(self,re_output):

        try:
            depth_return = self.client.get_order_book(self.base_cur+'-'+self.quote_cur)

            # eos_btc的卖出价格depth------ask
            self.base_quote_market_sell = dict()
            self.base_quote_market_sell = depth_return.get("asks")
            self.b1 = float(self.base_quote_market_sell[0]['price'])
            self.bq1 = float(self.base_quote_market_sell[0]['amount'])

            # eos_btc的买入价格depth-----bid
            self.base_quote_market_buy = dict()
            self.base_quote_market_buy = depth_return.get("bids")
            self.b2 = float(self.base_quote_market_buy[0]['price'])
            self.bq2 = float(self.base_quote_market_buy[0]['amount'])

            self.logger.debug("b1:{0},bq1:{1}".format(self.b1, self.bq1))
            self.logger.debug("b2:{0},bq2:{1}".format(self.b2, self.bq2))

            arr_re = dict()
            arr_re["base_quote_market_sell"] = self.base_quote_market_sell[0:10]
            arr_re["base_quote_market_buy"] = self.base_quote_market_buy[0:10]
            arr_re["b1"] = self.b1
            arr_re["bq1"] = self.bq1
            arr_re["b2"] = self.b2
            arr_re["bq2"] = self.bq2

            re_output.put(arr_re)
        except:
            self.logger.error(traceback.format_exc())


    def get_depth_base_mid(self,re_output):

        try:
            depth_return = self.client.get_order_book(self.base_cur+'-'+self.mid_cur)

            # eos_idr的卖出价格depth------ask
            self.base_mid_market_sell = dict()
            self.base_mid_market_sell = depth_return.get("asks")
            self.c1 = float(self.base_mid_market_sell[0]['price'])
            self.cq1 = float(self.base_mid_market_sell[0]['amount'])

            # eos_idr的买入价格depth-----bid
            self.base_mid_market_buy = dict()
            self.base_mid_market_buy = depth_return.get("bids")
            self.c2 = float(self.base_mid_market_buy[0]['price'])
            self.cq2 = float(self.base_mid_market_buy[0]['amount'])

            self.logger.debug("c1:{0},cq1:{1}".format(self.c1, self.cq1))
            self.logger.debug("c2:{0},cq2:{1}".format(self.c2, self.cq2))

            arr_re = dict()
            arr_re["base_mid_market_sell"] = self.base_mid_market_sell[0:10]
            arr_re["base_mid_market_buy"] = self.base_mid_market_buy[0:10]
            arr_re["c1"] = self.c1
            arr_re["cq1"] = self.cq1
            arr_re["c2"] = self.c2
            arr_re["cq2"] = self.cq2

            re_output.put(arr_re)
        except:
            self.logger.error(traceback.format_exc())



    def get_depth_info(self):

        try:

            re_output_p1 = multiprocessing.Queue()
            re_output_p2 = multiprocessing.Queue()
            re_output_p3 = multiprocessing.Queue()
            #re_output_p4 = multiprocessing.Queue()

            p1 = multiprocessing.Process(target=self.get_depth_quote_mid, args=(re_output_p1,))

            p2 = multiprocessing.Process(target=self.get_depth_base_quote, args=(re_output_p2,))

            p3 = multiprocessing.Process(target=self.get_depth_base_mid, args=(re_output_p3,))

            #p4 = multiprocessing.Process(target=self.get_user_balance, args=(re_output_p4,))

            p1.start() #process of get_depth_quote_mid
            p2.start() #process of get_depth_base_quote
            p3.start() #process of get_depth_base_mid
            #p4.start() #process of get_user_balance

            p1.join(timeout=self.process_timeout)
            p2.join(timeout=self.process_timeout)
            p3.join(timeout=self.process_timeout)
            #p4.join(timeout=self.process_timeout)


            if p1.is_alive():
                self.logger.warning("p1(get_depth_quote_mid) timeout, now kill that....")
                p1.terminate()
                p1.join()
                self.logger.warning("p1(get_depth_quote_mid) timeout, already killed!")

            if p2.is_alive():
                self.logger.warning("p2(get_depth_base_quote) timeout, now kill that....")
                p2.terminate()
                p2.join()
                self.logger.warning("p2(get_depth_base_quote) timeout, already killed!")

            if p3.is_alive():
                self.logger.warning("p3(get_depth_base_mid) timeout, now kill that....")
                p3.terminate()
                p3.join()
                self.logger.warning("p3(get_depth_base_mid) timeout, already killed!")



            if not re_output_p1.empty():
                arr_re_p1 = re_output_p1.get(True)
                self.a1 = arr_re_p1["a1"]
                self.aq1 = arr_re_p1["aq1"]
                self.a2 = arr_re_p1["a2"]
                self.aq2 = arr_re_p1["aq2"]
                self.quote_mid_market_sell = arr_re_p1["quote_mid_market_sell"]
                self.quote_mid_market_buy = arr_re_p1["quote_mid_market_buy"]
            else:
                # TODO 增加错误的处理
                self.logger.error("error!")
                self.err_amt = self.err_amt + 1

            if not re_output_p2.empty():
                arr_re_p2 = re_output_p2.get(True)
                self.b1 = arr_re_p2["b1"]
                self.bq1 = arr_re_p2["bq1"]
                self.b2 = arr_re_p2["b2"]
                self.bq2 = arr_re_p2["bq2"]
                self.base_quote_market_sell = arr_re_p2["base_quote_market_sell"]
                self.base_quote_market_buy = arr_re_p2["base_quote_market_buy"]
            else:
                # TODO 增加错误的处理
                self.logger.error("error!")
                self.err_amt = self.err_amt + 1

            if not re_output_p3.empty():
                arr_re_p3 = re_output_p3.get(True)
                self.c1 = arr_re_p3["c1"]
                self.cq1 = arr_re_p3["cq1"]
                self.c2 = arr_re_p3["c2"]
                self.cq2 = arr_re_p3["cq2"]
                self.base_mid_market_sell = arr_re_p3["base_mid_market_sell"]
                self.base_mid_market_buy = arr_re_p3["base_mid_market_buy"]
            else:
                # TODO 增加错误的处理
                self.logger.error("error!")
                self.err_amt = self.err_amt + 1


        except:
            self.logger.error(traceback.format_exc())




    def check_auto_quit(self):
        if os.path.isfile(self.AUTO_QUIT_FILENAME):
            self.logger.info("found quit name:{0},now delete and quit!".format(self.AUTO_QUIT_FILENAME))
            os.remove(self.AUTO_QUIT_FILENAME)
            exit()

    def is_number(self,s):
        try:
            float(s)
            return True
        except ValueError:
            return False

        return False

    def decimal_accuracy(self,dest_number,decimal_val,mode=1):
        #mode: 1,floor; 2,round; 3,ceil
        if not self.is_number(dest_number):
            return False


        ten_number=1
        for i in range(decimal_val):
            ten_number = ten_number * 10

        if mode == 1:
            return math.floor(dest_number * ten_number) / ten_number
        if mode == 2:
            return math.round(dest_number * ten_number) / ten_number
        if mode == 3:
            return math.ceil(dest_number * ten_number) / ten_number






    def cal_profit(self):

        try:

            old_bal_mid_cur = self.bal_mid_cur
            old_bal_quote_cur = self.bal_quote_cur
            old_bal_base_cur = self.bal_base_cur
            self.get_user_balance()

            gap_bal_mid_cur = self.bal_mid_cur - old_bal_mid_cur
            gap_bal_quote_cur = self.bal_quote_cur - old_bal_quote_cur
            gap_bal_base_cur = self.bal_base_cur - old_bal_base_cur

            gap_est_profit = gap_bal_mid_cur + gap_bal_quote_cur * self.a2 + gap_bal_base_cur * self.c2

            self.logger.info("套利后各账户余额如下:{0} is {1},{2} is {3},{4} is {5}".format(self.mid_cur, self.bal_mid_cur, self.quote_cur,
                                                                       self.bal_quote_cur, self.base_cur,
                                                                       self.bal_base_cur))
            self.logger.info(
                "各账户差值如下:{0}:{1},{2}:{3},{4}:{5}".format(self.mid_cur, gap_bal_mid_cur, self.quote_cur,
                                                         gap_bal_quote_cur, self.base_cur, gap_bal_base_cur))


            self.logger.info("粗略计算profit为:{0} {1}".format(gap_est_profit,self.mid_cur))

        except:
            self.logger.error(traceback.format_exc())


    def invoke_create_order(self, retry_numer,symbol, side, price, amount):

        re_order={'status':False,'order_result':None}

        if retry_numer == self.MAX_TRADE_TIMES:
            self.logger.error(
                "ERROR!MAX try time:{0} for {1}:{2} with {3}_{4}".format(retry_numer, symbol, side, price, amount))
            re_order['status']=False
            return re_order
        else:
            self.logger.warning(
                "now try time:{0} for {1}:{2} with {3}_{4}".format(retry_numer, symbol, side, price, amount))

        try:
            self.logger.warning("invoke_create_order:{0}_{1}".format(symbol, side))
            re_order['order_result']=self.client.create_order(symbol, side, price, amount)
        except BigoneAPIException as e:
            #如果错误码为10001，bigone的Internal Server Error，需要重试
            if str(e.code) == '10001':
                self.logger.warning(
                    "[need retry]Internal Server Error happen on try time:{0} for {1}:{2} with {3}_{4}".format(
                        retry_numer, symbol, side, price, amount))

                retry_numer += 1
                time.sleep(1)
                return self.invoke_create_order(retry_numer, symbol, side, price, amount)
            else:
                #对于其他错误码，暂时不需要重试
                self.logger.warning(
                    "其他的错误码，暂时不需要重试,detail:status:{0},response:{1}".format(e.status_code, e.response))
                re_order['status'] = True
                return re_order

        else:
            #print("succeed")
            re_order['status'] = True
            return re_order


    def process_order(self,symbol, side, price, amount):

        re_order=self.invoke_create_order(1, symbol, side, price, amount)

        #重试了MAX次数后，也没有成功
        if re_order['status'] == False:
            self.logger.error('ERROR!{0}_{1}线程处理失败!'.format(symbol,side))
            return
        else:
            #订单处理成功后的后处理
            '''
            #订单成功处理的返回样例，需要判断里面是否已经全部处理完毕
            '{'order_market': 'ETH-EOS', 'order_side': 'BID', 'user_id': '12f1c302-0314-4eb2-a66e-4f9ada35d3bf',
             'order_type': 'LIMIT', 'order_id': '03bcc2e6-512b-4b5b-b1ea-cdd8b8316eff', 'price': '98.20000000',
             'created_at': '2018-02-17T16:08:30.631269472Z', 'type': 'order', 'amount': '0.15000000',
             'order_state': 'open', 'updated_at': '2018-02-17T16:08:30.631269472Z', 'filled_amount': '0.00000000'}
             '''

            if re_order == None:
                # 如果订单的返回数据中没有order_id，表示含有其他的错误
                self.logger.warning("{0}_{1}:订单返回值为None!".format(symbol, side))
                return
            elif not 'order_id' in re_order['order_result']:
                #如果订单的返回数据中没有order_id，表示含有其他的错误
                self.logger.warning("{0}_{1}:订单返回中没有order_id, detail:{2}".format(symbol,side,re_order))
                return
            else:

                # 根据order_id判断订单的处理状态
                order_id = re_order['order_result']['order_id']

                while(1):
                    order_info = self.client.get_order(order_id)

                    if order_info['order_state'] == 'filled':
                        #订单已经全部处理完毕
                        self.logger.info('{0}_{1},order_id:{2},已经全部处理完毕!'.format(symbol,side,order_id))
                        return True
                    else:
                        self.logger.info('{0}_{1},order_id:{2}还没有处理完毕，等待再次处理!'.format(symbol, side, order_id))
                        time.sleep(1)




    def check_tri(self):

        try:

            # get all depth data using for check trigger condition
            self.get_depth_info()
            # time.sleep(0.3)

            tri_pos_ratio = self.c2 / (self.a1 * self.b1 * (1 + self.tax) / (1 - self.tax))
            tri_nag_ratio = self.a2 * self.b2 / (self.c1 * (1 + self.tax) / (1 - self.tax))

            self.logger.debug("pos tri is {0}".format(tri_pos_ratio))
            self.logger.debug("nag tri is {0}".format(tri_nag_ratio))

            base_amt_pos = min(self.aq1 / self.b1, self.bq1, self.cq2, self.bal_base_cur, self.bal_quote_cur / self.b1,
                              self.bal_mid_cur / self.a1 / self.b1 / (1 + self.tax),self.MAX_BASE_AMT_TRADE)
            #est_profit_pos = base_amt_pos * self.c2 * (1 - self.tax) - base_amt_pos * self.b1 * self.a1 * (1 + self.tax)
            est_profit_pos = base_amt_pos * self.c2 * (1 - self.tax) - base_amt_pos * self.b1 * self.a1 / (
            1 - self.tax) / (1 - self.tax)

            base_amt_nag = min(self.aq2 / self.b2, self.bq2, self.cq1, self.bal_base_cur, self.bal_quote_cur / self.b2,
                              self.bal_mid_cur / self.c1 / (1 + self.tax),self.MAX_BASE_AMT_TRADE)
            #est_profit_nag = base_amt_nag * self.b2 * self.a2 * (1 - self.tax) - base_amt_nag * self.c1 * (1 + self.tax)
            est_profit_nag = base_amt_nag * self.b2 * self.a2 * (1 - self.tax) * (
            1 - self.tax) - base_amt_nag * self.c1 / (1 - self.tax)
            self.logger.debug("pos tri is {0},base_amt_pos is {1},esti profit is {2}".format(tri_pos_ratio,base_amt_pos, float(est_profit_pos)))
            self.logger.debug("nag tri is {0},base_amt_nag is {1},esti profit is {2}".format(tri_nag_ratio,base_amt_nag, float(est_profit_nag)))

            #self.logger.debug("{0}-{1}-{2}-{3}-{4}-{5}".format(self.quote_mid_market_sell,self.quote_mid_market_buy,self.base_quote_market_sell,self.base_quote_market_buy,self.base_mid_market_sell,self.base_mid_market_buy))




            #if (tri_pos_ratio > self.AMT_TRI_POS):       #根据百分比触发
            if (est_profit_pos > self.PROFIT_AMT_TRI_POS) and (base_amt_pos >= self.MIN_BASE_CUR_AMT):   #根据利润触发
                # 正向套利条件符合，计算eos_amt
                self.logger.info("trigger pos!")
                self.logger.info("quote_mid_market_sell a1 depth data:{0}".format(self.quote_mid_market_sell))
                self.logger.info("quote_mid_market_buy a2 depth data:{0}".format(self.quote_mid_market_buy))
                self.logger.info("base_quote_market_sell b1 depth data:{0}".format(self.base_quote_market_sell))
                self.logger.info("base_quote_market_buy b2 depth data:{0}".format(self.base_quote_market_buy))
                self.logger.info("base_mid_market_sell c1 depth data:{0}".format(self.base_mid_market_sell))
                self.logger.info("base_mid_market_buy c2 depth data:{0}".format(self.base_mid_market_buy))
                self.logger.info(
                    "套利前各账户余额如下:{0} is {1},{2} is {3},{4} is {5}".format(self.mid_cur, self.bal_mid_cur, self.quote_cur,
                                                                         self.bal_quote_cur, self.base_cur,
                                                                         self.bal_base_cur))


                base_amt = base_amt_pos

                #保证eos的amt的精度为小数点后一位
                base_amt = self.decimal_accuracy(base_amt,self.BASE_TRADE_DECIMAL,1)
                #just for test
                #base_amt = 5

                est_profit = base_amt * self.c2 * (1 - self.tax) - base_amt * self.b1 * self.a1 * (1 + self.tax)
                self.logger.info("warning!base_amt_pos is {0},esti profit is {1}".format(base_amt, est_profit))

                self.logger.info("begin to pos hedging......")

                #base_cur = 'ETH'
                #quote_cur = 'EOS'
                #mid_cur = 'BTC'

                #改良的版本（try），按照1档的价格的90%or110%下单
                p2 = multiprocessing.Process(target=self.process_order, args=(
                    self.base_cur+'-'+self.quote_cur, "BID", str(self.decimal_accuracy(self.b1 * 1.01, self.QUOTE_PRICE_DECIMAL, 3)),
                    str(self.decimal_accuracy(base_amt / (1 - self.tax), self.BASE_TRADE_DECIMAL, 1))))

                p3 = multiprocessing.Process(target=self.process_order, args=(
                    self.base_cur+'-'+self.mid_cur, "ASK", str(self.decimal_accuracy(self.c2 * 0.99, self.MID_PRICE_DECIMAL, 3)),
                    str(base_amt)))

                p1 = multiprocessing.Process(target=self.process_order, args=(
                    self.quote_cur+'-'+self.mid_cur, "BID", str(self.decimal_accuracy(self.a1 * 1.01, self.MID_PRICE_DECIMAL, 3)), str(
                        self.decimal_accuracy(base_amt / (1 - self.tax) / (1 - self.tax) * self.b1,
                                              self.QUOTE_TRADE_DECIMAL, 3))))


                p2.start() #process of btc_idr-buy
                #time.sleep(0.1)
                p3.start() #process of eos_btc-buy
                #time.sleep(0.1)
                p1.start() #process of eos_idr-sell


                p2.join(timeout=self.process_timeout)
                p3.join(timeout=self.process_timeout)
                p1.join(timeout=self.process_timeout)

                if p1.is_alive():
                    self.logger.warning("p1("+self.quote_cur+"_"+self.mid_cur+"-buy) timeout, now kill that....")
                    p1.terminate()
                    p1.join()
                    self.logger.warning("p1("+self.quote_cur+"_"+self.mid_cur+"-buy) timeout, already killed!")

                if p2.is_alive():
                    self.logger.warning("p2("+self.base_cur+"_"+self.quote_cur+"-buy) timeout, now kill that....")
                    p2.terminate()
                    p2.join()
                    self.logger.warning("p2("+self.base_cur+"_"+self.quote_cur+"-buy) timeout, already killed!")

                if p3.is_alive():
                    self.logger.warning("p3("+self.base_cur+"_"+self.mid_cur+"-sell) timeout, now kill that....")
                    p3.terminate()
                    p3.join()
                    self.logger.warning("p3("+self.base_cur+"_"+self.mid_cur+"-sell) timeout, already killed!")

                self.logger.info("finish pos hedging!")
                self.suc_amt = self.suc_amt + 1
                time.sleep(10)
                self.cal_profit()
                return

            #if (tri_nag_ratio > self.AMT_TRI_NAG):      #根据百分比触发
            if (est_profit_nag > self.PROFIT_AMT_TRI_NAG) and (base_amt_nag >= self.MIN_BASE_CUR_AMT):    #根据利润触发
                # 逆向套利条件符合，计算eos_amt
                self.logger.info("trigger nag!")
                self.logger.info("quote_mid_market_sell a1 depth data:{0}".format(self.quote_mid_market_sell))
                self.logger.info("quote_mid_market_buy a2 depth data:{0}".format(self.quote_mid_market_buy))
                self.logger.info("base_quote_market_sell b1 depth data:{0}".format(self.base_quote_market_sell))
                self.logger.info("base_quote_market_buy b2 depth data:{0}".format(self.base_quote_market_buy))
                self.logger.info("base_mid_market_sell c1 depth data:{0}".format(self.base_mid_market_sell))
                self.logger.info("base_mid_market_buy c2 depth data:{0}".format(self.base_mid_market_buy))
                self.logger.info(
                    "套利前各账户余额如下:{0} is {1},{2} is {3},{4} is {5}".format(self.mid_cur, self.bal_mid_cur, self.quote_cur,
                                                                         self.bal_quote_cur, self.base_cur,
                                                                         self.bal_base_cur))

                base_amt = base_amt_nag

                #保证eos的amt的精度为小数点后一位
                base_amt = self.decimal_accuracy(base_amt, self.BASE_TRADE_DECIMAL, 1)

                #just for test
                #base_amt = 5


                est_profit = base_amt * self.b2 * self.a2 * (1 - self.tax) - base_amt * self.c1 * (1 + self.tax)
                self.logger.info("warning!base_amt_nag is {0},esti profit is {1}".format(base_amt, est_profit))

                self.logger.info("begin to nag hedging......")

                p2 = multiprocessing.Process(target=self.process_order, args=(
                    self.base_cur+'-'+self.quote_cur, "ASK", str(self.decimal_accuracy(self.b2 * 0.98, self.QUOTE_PRICE_DECIMAL, 3)),
                    str(base_amt)))

                p3 = multiprocessing.Process(target=self.process_order, args=(
                    self.base_cur+'-'+self.mid_cur, "BID", str(self.decimal_accuracy(self.c1 * 1.01, self.MID_PRICE_DECIMAL, 3)),
                    str(self.decimal_accuracy(base_amt / (1 - self.tax), self.BASE_TRADE_DECIMAL, 1))))

                p1 = multiprocessing.Process(target=self.process_order, args=(
                    self.quote_cur+'-'+self.mid_cur, "ASK", str(self.decimal_accuracy(self.a2 * 0.98, self.MID_PRICE_DECIMAL, 3)),
                    str(self.decimal_accuracy(base_amt * self.b2 * (1 - self.tax), self.QUOTE_TRADE_DECIMAL, 3))))

                p2.start() #process of btc_idr-sell
                #time.sleep(0.1)
                p3.start() #process of eos_btc-sell
                #time.sleep(0.1)
                p1.start() #process of eos_idr-buy


                p2.join(timeout=self.process_timeout)
                p3.join(timeout=self.process_timeout)
                p1.join(timeout=self.process_timeout)

                if p1.is_alive():
                    self.logger.warning("p1("+self.quote_cur+"_"+self.mid_cur+"-sell) timeout, now kill that....")
                    p1.terminate()
                    p1.join()
                    self.logger.warning("p1("+self.quote_cur+"_"+self.mid_cur+"-sell) timeout, already killed!")

                if p2.is_alive():
                    self.logger.warning("p2("+self.base_cur+"_"+self.quote_cur+"-sell) timeout, now kill that....")
                    p2.terminate()
                    p2.join()
                    self.logger.warning("p2("+self.base_cur+"_"+self.quote_cur+"-sell) timeout, already killed!")

                if p3.is_alive():
                    self.logger.warning("p3("+self.base_cur+"_"+self.mid_cur+"-buy) timeout, now kill that....")
                    p3.terminate()
                    p3.join()
                    self.logger.warning("p3("+self.base_cur+"_"+self.mid_cur+"-buy) timeout, already killed!")

                self.logger.info("finish nag hedging!")
                self.suc_amt = self.suc_amt + 1
                time.sleep(10)
                self.cal_profit()
                return

        except:
            self.logger.error(traceback.format_exc())




'''
'''

if __name__ == "__main__":

    a_bitcoin=arbitrage_bitcoin()

    i=0
    a_bitcoin.get_user_balance()
    while True:
        i+=1
        a_bitcoin.check_tri()
        #exit()

        if (a_bitcoin.err_amt > a_bitcoin.err_limit):
            a_bitcoin.logger.error("[ERROR]重大错误超出阈值，请检查程序!")
            exit()

        if (a_bitcoin.suc_amt >= a_bitcoin.suc_limit):
            a_bitcoin.logger.info("[EXIT]满足成功次数条件:{0},退出".format(a_bitcoin.suc_amt))
            exit()

        #统计代理使用情况，并定期清除代理使用数据记录
        if (i % 5)==0:
            #a_bitcoin.proxy_stat()
            a_bitcoin.check_auto_quit()

        #exit()


        time.sleep(0)





