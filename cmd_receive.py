import sys
sys.path.append("/usr/local/lib/python3.6/dist-packages")
from flask import Flask, request
app = Flask(__name__)

@app.route('/')
def index():
    return 'hzp, hello world!'

class flaskConfig(object):
    def __init__(self):
        self.stop_singal_from_client=False
        self.change_ratio_singal_from_client=False
        self.ratio_no_trendency=0.25#随着仓位增加网格利率以0.25递增
        self.ratio_up_or_down=0.5 #随着仓位增加网格利率以0.5递增
        self.every_time_trade_share = 100 # 33 测试环境下要求小数点后面3位精度，买10u的话只要0.000304左右，四舍五入就是0.000了，这样买不上
        self.leverage = 20

fc = flaskConfig()
@app.route('/grid/stop')
def grid_stop():
    fc.stop_singal_from_client=True
    return 'hzp, /grid/stop!'

@app.route('/grid/change/params', methods=['GET'])
def grid_change_params():

    # data = request.get_json()
    param1 = str(request.args.get('ratio_up_or_down'))
    param2 = str(request.args.get('ratio_no_trendency'))
    if param1:
        fc.ratio_no_trendency = float(param1)
    if param2:
        fc.ratio_up_or_down = float(param2)
    if param1 or param2:
        fc.change_ratio_singal_from_client = True
    return 'hzp, /change/params, ratio_up_or_down:' + param1 + ', ratio_no_trendency:' + param2

@app.route('/grid/change/trade_share', methods=['GET'])
def grid_change_trade_share():

    # data = request.get_json()
    every_time_trade_share = str(request.args.get('every_time_trade_share'))
    if every_time_trade_share:
        fc.every_time_trade_share = float(every_time_trade_share)
    return 'hzp, /change/trade_share, every_time_trade_share:' + every_time_trade_share

@app.route('/grid/change/leverage', methods=['GET'])
def grid_change_leverage():

    # data = request.get_json()
    leverage = str(request.args.get('leverage'))
    if leverage:
        fc.leverage = int(leverage)
    return 'hzp, /change/leverage, leverage:' + leverage

@app.route('/grid/start')
def grid_start():

    #todo
    # error_raw = ''
    # try:
    #     config.loads('../config.json')
    #     # dynamicConfig.loads('./config.json')
    #
    #     hengedGrid = HengedGrid()
    #     receiver_thread = threading.Thread(target=hengedGrid.open_receiver)
    #     receiver_thread.start()
    #     exit_thread = threading.Thread(target=hengedGrid.normal_exit)
    #     exit_thread.start()
    #     hengedGrid.run()
    #     receiver_thread.join()
    #     exit_thread.join()
    #
    # except Exception as e:
    #     print('出现异常了:' + str(e))
    #     error_raw = '出现异常了:' + str(e)
    # except BaseException as be:
    #     if isinstance(be, KeyboardInterrupt):
    #         print('ctrl + c 程序中断了')
    #         error_raw = 'ctrl + c 程序中断了' + str(be)
    # finally:
    #     if error_raw:
    #         error_info = "报警：币种{coin},服务停止.错误原因{info}".format(coin=config.symbol, info=str(error_raw))
    #         Message.dingding_warn(str(error_info))
    return 'hzp, /grid/start!'

if __name__ == '__main__':
    app.run(host='104.225.143.245',
            port=5000,
            debug=True)