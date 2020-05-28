import os
import base64
from emailnotifier import EmailNotifier
from telegramnotifier import TelegramNotifier

def get_elector_address(t):
    # Elector address
    res, out = t.getconfig(1)
    if not res:
        print(out)
        return None
    elector_addr = '-1:' + out
    return elector_addr

def get_awaiting_transactions(t, msig_addr, dest, abi):
    '''
    Get transactions list
    '''
    res, out = t.getTransactions(msig_addr, abi)
    if not res:
        print(out)
        return None
    transactions = []
    try:
        for i in out['transactions']:
            if dest is None or i['dest'] == dest:
                transactions += [i['id']]
    except:
        return None

    return transactions

def confirm_transactions_to_elector(t, msig_addr, keyfile, abi, try_num=30, printl=print):
    elector_addr = get_elector_address(t)
    if elector_addr is None:
        return [], []

    # проверим, есть ли транзакции к электору в ожидании подтверждения
    transactions = get_awaiting_transactions(t, msig_addr, elector_addr, abi)
    if transactions is None:
        return [], []

    if len(transactions) == 0:
        return [], []

    printl('Found unconfirmed transactions: %s' % str(transactions))

    confirmed = []
    unconfirmed = []

    for i in transactions:
        for n in range(try_num):
            printl('Try %d Confirming %s' % (n+1, i))
            res, out = t.confirmTransaction(msig_addr, i, abi, keyfile)
            if res:
                printl('Success')
                confirmed.append(i)
                break
            else:
                printl(out)
        if i not in confirmed:
            printl('Failed')
            unconfirmed.append(i)

    return confirmed, unconfirmed


def request_reward(t, fift, recover_script, msig_addr, elector_addr, abi, keyfile, try_num=30):
    fn = fift.get_tempfile_name('recover-query.boc')
    res, out = fift.run(recover_script, fn)
    if not res:
        print(out)
        return None
    try:
        with open(fn, 'rb') as f:
            recover_request = base64.b64encode(f.read()).decode("utf-8")
        os.remove(fn)
    except:
        return None

    for n in range(try_num):
        res, out = t.transfer(msig_addr, elector_addr, 1000000000, True, False, recover_request, abi, keyfile)
        if not res or 'transId' not in out:
            print(out)
            continue
        return out['transId']
    return None

import tempfile

def save_atomic(filename, data):
    try:
        with tempfile.NamedTemporaryFile('w', dir=os.path.dirname(filename), delete=False) as tf:
            tf.write(data)
            tempname = tf.name
        os.rename(tempname, filename)
        return True
    except:
        return False

def notify_custodians(custodians, msg, notify_conf, email_conf):
    for c in custodians:
        if c in notify_conf:
            nn = notify_conf[c]
            if nn['type'] == 'telegram':
                try:
                    telegram = TelegramNotifier(nn['params']['token'], nn['params']['chat_ids'])
                    telegram.send(msg)
                except:
                    pass
            elif nn['type'] == 'email':
                try:
                    email = EmailNotifier(email_conf['login'], email_conf['password'], email_conf['smtp'],
                                          email_conf['port'])
                    email.send(nn['params']['address'], msg)
                except:
                    pass

def notify_owner(msg, notify_conf, email_conf):
    if not 'owner' in notify_conf:
        return
    nn = notify_conf['owner']
    if not 'type' in nn:
        return
    if nn['type'] == 'telegram':
        try:
            telegram = TelegramNotifier(nn['params']['token'], nn['params']['chat_ids'])
            telegram.send(msg)
        except:
            pass
    elif nn['type'] == 'email':
        try:
            email = EmailNotifier(email_conf['login'], email_conf['password'], email_conf['smtp'],
                                  email_conf['port'])
            email.send(nn['params']['address'], msg)
        except:
            pass


def check_participant_list(t, elector_addr, public_key):
    res, out = t.runget(elector_addr, 'participant_list')
    if not res:
        print(out)
        return None
    try:
        node = out[0]
        while True:
            participant = node[0]
            addr_int = int(participant[0], 0)
            if addr_int == public_key:
                stake = int(participant[1], 0)
                return stake
            if node[1] is None:
                break
            node = node[1]
    except Exception as e:
        pass

    return 0

def get_custodians(t, addr, abi):
    res, out = t.getCustodians(addr, abi)
    if not res or 'custodians' not in out:
        print(out)
        return None
    custodians = []
    for i in out['custodians']:
        if 'pubkey' not in i:
            continue
        custodians.append(i['pubkey'])

    return custodians


def make_and_check_path(path_conf, key, path):
    if key not in path_conf:
        path_conf[key] = path
    if not os.path.isfile(path_conf[key]):
        print('Cannot find key in %s' % path_conf[key])
        return False
    return True

def check_config(config, keymaybeseed=False):
    try:
        path_conf = config['path']
        user_conf = config['wallet']
        notify_conf = config['notifications']
        email_conf = config['email']
    except:
        return None, None, None, None

    if 'repo' in path_conf and os.path.isdir(path_conf['repo']):
        repo = path_conf['repo']
    else:
        print('Please specify correct repo path')
        return None, None, None, None

    if 'keysdir' in path_conf and os.path.isdir(path_conf['keysdir']):
        keysdir = path_conf['keysdir']
    else:
        print('Please specify correct ton-keys path')
        return None, None, None, None

    if not 'election_folder' in path_conf:
        path_conf['election_folder'] = './'

    if not make_and_check_path(path_conf, 'tonos-cli', repo + '/ton/build/utils/tonos-cli') or \
            not make_and_check_path(path_conf, 'validator-engine-console', repo + '/ton/build/validator-engine-console/validator-engine-console') or \
            not make_and_check_path(path_conf, 'client_key', keysdir + '/client') or \
            not make_and_check_path(path_conf, 'server_pub_key', keysdir + '/server.pub') or \
            not make_and_check_path(path_conf, 'fift', repo + '/ton/build/crypto/fift') or \
            not make_and_check_path(path_conf, 'abi', repo + '/configs/SafeMultisigWallet.abi.json'):
        return None, None, None, None

    if not keymaybeseed and not make_and_check_path(user_conf, 'keyfile', keysdir + '/msig.keys.json'):
        return None, None, None, None

    if not 'server_url' in path_conf:
        path_conf['server_url'] = '127.0.0.1:3030'

    if not 'fift_includes' in path_conf:
        path_conf['fift_includes'] = '%s/ton/crypto/fift/lib:%s/ton/crypto/smartcont' % (repo, repo)

    if not 'validator-elect-req' in path_conf:
        path_conf['validator-elect-req'] = 'validator-elect-req.fif'

    if not 'validator-elect-signed' in path_conf:
        path_conf['validator-elect-signed'] = 'validator-elect-signed.fif'

    if not 'recover-stake' in path_conf:
        path_conf['recover-stake'] = 'recover-stake.fif'

    if not 'msig_addr' in user_conf:
        import socket
        addr = keysdir + '/' + socket.gethostname() + '.addr'
        try:
            with open(addr, 'r') as f:
                user_conf['msig_addr'] = f.read().replace('\n', '')
        except:
            print('Cannot read %s' % addr)
            return None, None, None, None

    return path_conf, user_conf, notify_conf, email_conf
