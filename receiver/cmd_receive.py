from flask import Flask

app = Flask(__name__)

@app.route('/')
def index():
    return 'hzp, hello world!'

class flaskConfig(object):
    def __init__(self):
        self.stop_singal_from_client=False

fc = flaskConfig()

@staticmethod
def set_stop_singal_from_client():
    pass


@app.route('/grid/stop')
def grid_stop():
    fc.stop_singal_from_client=True
    return 'hzp, /grid/stop!'


if __name__ == '__main__':
    app.run(host='104.225.143.245',
            port=5000,
            debug=True)