# tri_-arbitrage_bigone
triangle arbitrage for cryptocurrency at BigOne 在bigone上的加密货币的三角套利程序

************作用************
用于在BigOne平台上进行三种交易对的三角套利
doing triangle arbitrage with 3 trading-pair at BigOne

************文件说明************
1）client.py
BigOne的API借口封装文件 interface file for BigOne API

2) exceptions.py
自定义的错误类型 define customization error exception

3) press_test.py
用于测试BigOne平台的API并发调用限制 for testing limit of API invoke at BigOne

4) test_api_request.py
用于测试API借口的测试文件 for testing API interface file

5) tri-arbitrage-EOS-ETH-BTC.py
针对EOS-ETH-BTC的三角套利主程序 Main process for triangle arbitrage among EOS-ETH-BTC

6) tri-arbitrage-IDT-ETH-BTC.py
针对IDT-ETH-BTC的三角套利主程序 Main process for triangle arbitrage among IDT-ETH-BTC

****TODO  5) 6)会简化成基于一个类的调用，初始化时给予不同的交易对变量
in the future, there will be a remend base on a Class for 5) and 6), impart different trading pair while initilize




