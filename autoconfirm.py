from tonoscliwrapper import TonosCli
import json
import utils
from datetime import datetime
import time
import sys
from version import VERSION

def printl(*args):
    print(datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S:'), *args, flush=True)

if __name__ == '__main__':
    printl('TON Autoconfirm version %s started with args %s' % (VERSION, sys.argv))

    if len(sys.argv) >= 2:
        config_file = sys.argv[1]
    else:
        config_file = 'config.custodian.json'

    printl('Using %s' % config_file)

    try:
        with open(config_file, 'r') as f:
            _config = f.read()
    except:
        printl('Cannot read %s' % config_file)
        exit(1)

    try:
        config = json.loads(_config)
    except Exception as e:
        printl('Cannot parse %s: %s' % (config_file, str(e)))
        exit(1)

    path_conf, user_conf, notify_conf, email_conf = utils.check_config(config, True)
    if path_conf is None:
        exit(1)

    t = TonosCli(path_conf['tonos-cli'])

    confirmed, unconfirmed = utils.confirm_transactions_to_elector(t, user_conf['msig_addr'], user_conf['keyfile'], path_conf['abi'], 100, printl)
    printl('Confirmed: %s Unconfirmed: %s' % (str(confirmed), str(unconfirmed)))

    if len(confirmed) > 0:
        msg = 'Confirmed transactions: %s' % confirmed
        utils.notify_owner(msg, notify_conf, email_conf)

    if len(unconfirmed) > 0:
        msg = 'Cannot confirm transactions: %s' % unconfirmed
        utils.notify_owner(msg, notify_conf, email_conf)

    exit(len(unconfirmed))
