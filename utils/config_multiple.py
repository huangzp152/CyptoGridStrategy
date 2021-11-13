# -*- coding:utf-8 -*-
import json


class Config:

    def __init__(self):
        self.configs = []

    def loads(self, config_file=None):
        """ Load config file.

        Args:
            config_file: config json file.
        """
        configures = {}
        if config_file:
            try:
                with open(config_file) as f:
                    data = f.read()
                    configures = json.loads(data)
            except Exception as e:
                print(e)
                exit(0)
            if not configures:
                print("config json file error!")
                exit(0)
        self._update(configures)

    def _update(self, update_fields):
        """
        更新update fields.
        :param update_fields:
        :return: None

        """

        for k, v in update_fields.items():
            setattr(self, k, v)

class User:

    def __init__(self, cfg):
        self.user = cfg['user']
        self.markets = []
        if 'markets' in cfg:
            for mkt in cfg['markets']:
                self.markets.append(Market(mkt))

class Market:

    def __init__(self, detail):
        self.platform = detail['platform']
        self.api_key = detail['api_key']
        self.api_secret = detail['api_secret']
        self.products = []
        if 'products' in detail:
            for product in detail['products']:
                self.products.append(Product(product))
        # self.platform: str = "binance"  # 交易的平台
        # self.coin: str = "BUSD"  # 要进行仓位查询的币种
        # self.api_key: str = None
        # self.api_secret: str = None
        # self.quantity: float = 0.005
        # self.min_price = 0.0001
        # self.min_qty = 0.01
        # self.max_orders = 1
        # self.proxy_host = ""  # proxy host
        # self.proxy_port = 0  # proxy port
        # self.initial_price = 0
        # self.grid_number = 0
        # self.max_border_price = 0
        # self.min_border_price = 0
        # self.test: bool = False
        # self.spot_rising_ratio = 1
        # self.spot_falling_ratio = 1
        # self.future_rising_ratio = 1
        # self.future_falling_ratio = 1
        # self.spot_buy_price = 9999999
        # self.spot_sell_price = 0.0000001
        # self.spot_step = 0  # 步数/仓位数
        # self.record_spot_price = []
        # self.every_time_trade_share = 200  # 33是测试的 不然过不了精度 10.1 #每次交易的份额
        #
        # self.future_buy_price = 9999999
        # self.future_sell_price = 0.0000001
        # self.future_step = 0  # 步数/仓位数
        # self.record_future_price = []
        # self.long_bottom_position_price = []  # 记录做多的底仓的价格列表

class Product:

    def __init__(self, product):
        self.symbol = product['symbol']
        self.coin = product['coin']
        self.quantity = product['quantity'] if 'quantity' in product else 0
        self.every_time_trade_share = product['every_time_trade_share']
        self.long_bottom_position_share = product['long_bottom_position_share']
        self.spot_rising_ratio = 1
        self.spot_falling_ratio = 1
        self.future_rising_ratio = 1
        self.future_falling_ratio = 1
        self.spot_buy_price = 9999999
        self.spot_sell_price = 0.0000001
        self.spot_step = 0 #步数/仓位数

        self.future_buy_price = 9999999
        self.future_sell_price = 0.0000001
        self.future_step = 0 #步数/仓位数
        self.record_spot_price = []
        self.record_future_price = []
        self.long_bottom_position_price = []

config = Config()

# class DynamicConfig(object):
#
#     def __init__(self):
#         self.spot_rising_ratio = 1
#         self.spot_falling_ratio = 1
#         self.future_rising_ratio = 1
#         self.future_falling_ratio = 1
#         self.spot_buy_price = 9999999
#         self.spot_sell_price = 0.0000001
#         self.spot_step = 0 #步数/仓位数
#         self.record_spot_price = []
#         self.every_time_trade_share = 200 #33是测试的 不然过不了精度 10.1 #每次交易的份额
#
#         self.future_buy_price = 9999999
#         self.future_sell_price = 0.0000001
#         self.future_step = 0 #步数/仓位数
#         self.record_future_price = []
#         self.long_bottom_position_price = []# 记录做多的底仓的价格列表
#
#         # test
#         self.order_list = []
#         self.total_earn = 0
#         self.total_invest = 0
#         self.total_earn_grids = 0
#         self.total_steps = 0
#
#     def loads(self, config_file=None):
#         """ Load config file.
#
#         Args:
#             config_file: config json file.
#         """
#         configures = {}
#         if config_file:
#             try:
#                 with open(config_file) as f:
#                     data = f.read()
#                     configures = json.loads(data)
#             except Exception as e:
#                 print(e)
#                 exit(0)
#             if not configures:
#                 print("config json file error!")
#                 exit(0)
#         self._update(configures)
#
#     def _update(self, update_fields):
#         """
#         更新update fields.
#         :param update_fields:
#         :return: None
#
#         """
#
#         for k, v in update_fields.items():
#             setattr(self, k, v)

# dynamicConfig = DynamicConfig()