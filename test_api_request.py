# coding=utf-8

#from bigone.client import Client
#from bigone.exceptions import BigoneAPIException, BigoneRequestException
from client import Client

import exceptions

#import pytest
#import requests_mock
import time


api_key='xxxxxxx'

client = Client(api_key)

#ts=time.time()

#print(client.get_market('ETH-BTC'))


#print(client.get_account('CANDY'))

#depth = client.get_order_book('EOS-USDT')
#trades = client.get_market_trades('ETH-BTC')

#accounts= client.get_accounts()

#order = client.create_order('BTC-USDT', 'ASK', '8002', '0.01367')
#order_info=client.get_order('df318996-fdf0-4229-8d94-911640a5b7dc')
#o=client.cancel_order('c4993fc8-3a27-43aa-8b6d-a7393eeb057d')
print(client.get_orders('ETH-BTC'))


class interl_error(Exception):
    pass


class BigoneAPIException(Exception):

    def __init__(self, response):
        print("doing something with json_res")
        self.code=1001

    def __str__(self):
        return 'cwj'


def _handle_re(bool):
    if bool:
        return
    else:
        raise BigoneAPIException(bool)
        #raise "error"


def _request(retry_numer):
    print("_request 1")
    if retry_numer==3:
        return _handle_re(True)
    else:
        return _handle_re(False)


def _post(retry_numer):
    _request(retry_numer)

def create_order(retry_numer):
    if retry_numer==4:
        print("already retry 3 times,now back")
        return False
    else:
        print("now do the time:{0} try".format(retry_numer))

    print("doing")

    try:
        _post(retry_numer)
    except BigoneAPIException as e:
        print("2")
        print("code is {}".format(e.code))
        retry_numer+=1
        create_order(retry_numer)
    else:
        print("succeed")
        return True



#create_order(1)





