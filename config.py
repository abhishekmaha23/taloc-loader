import yaml

config = None

with open('config.yml', 'r') as f:
    config = yaml.safe_load(f)

# import configparser

# config = configparser.ConfigParser()
# config.read('config.ini')
