# -*- coding:utf-8 -*-
import json


class Config:

    def __init__(self):

        self.platform: str = "binance_spot"  # 交易的平台
        self.symbol: str = "UNIUSDT"  # 交易对.
        self.coin: str = "UNI" # 要进行仓位查询的币种
        self.gap_percent: float = 0.01  # 网格变化交易的单位.
        self.api_key: str = None
        self.api_secret: str = None
        self.api_key_future: str = None
        self.api_secret_future: str = None
        self.api_key_future_testnet: str = None
        self.api_secret_future_testnet: str = None
        self.pass_phrase = None
        self.quantity:float = 0.02
        self.min_price =  0.0001
        self.min_qty = 0.01
        self.max_orders = 1
        self.proxy_host = ""  # proxy host
        self.proxy_port = 0  # proxy port
        self.initial_price = 0
        self.grid_number = 0
        self.max_border_price = 0
        self.min_border_price = 0
        self.test:bool = False


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

config = Config()

class DynamicConfig(object):

    def __init__(self):
        self.spot_rising_ratio = 1
        self.spot_falling_ratio = 1
        self.future_rising_ratio = 1
        self.future_falling_ratio = 1
        self.spot_buy_price = 9999999
        self.spot_sell_price = 0.0000001
        self.spot_step = 0 #步数/仓位数
        self.record_spot_price = []
        self.every_time_trade_share = 200 #33是测试的 不然过不了精度 10.1 #每次交易的份额

        self.future_buy_price = 9999999
        self.future_sell_price = 0.0000001
        self.future_step = 0 #步数/仓位数
        self.record_future_price = []
        self.long_bottom_position_price = []# 记录做多的底仓的价格列表

        # test
        self.order_list = []
        self.total_earn = 172
        self.total_invest = 0
        self.total_earn_grids = 0
        self.total_steps = 0

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

dynamicConfig = DynamicConfig()