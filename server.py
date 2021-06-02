import importlib
from flask import Flask
app = Flask(__name__)


@app.route('/')
def run_app():
    importlib.import_module('app')
    return 'Success!'

@app.route('/status')
def get_status():
    return 'Taloc-loader server is alive'


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
