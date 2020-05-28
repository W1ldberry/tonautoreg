from tonoscliwrapper import TonosCli
from vecwrapper import ValidatorEngineConsole
import base64
import json
from fiftwrapper import Fift
import os
import utils
from datetime import datetime
import time
import sys
from version import VERSION


def printl(*args):
    print(datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S:'), *args, flush=True)

if __name__ == '__main__':
    printl('TON Autoreg version %s started with args %s' % (VERSION, sys.argv))

    if len(sys.argv) >= 2:
        config_file = sys.argv[1]
    else:
        config_file = 'config.json'

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

    path_conf, user_conf, notify_conf, email_conf = utils.check_config(config)
    if path_conf is None:
        exit(1)

    try_num = 100

    t = TonosCli(path_conf['tonos-cli'])

    v = ValidatorEngineConsole(path_conf['validator-engine-console'],
                               path_conf['client_key'],
                               path_conf['server_pub_key'],
                               path_conf['server_url'])

    fift = Fift(path_conf['fift'], path_conf['fift_includes'])


    printl('Checking for elector address')
    elector_addr = utils.get_elector_address(t)
    if elector_addr is None:
        printl('Cannot get elector address')
        exit(1)
    else:
        printl('Got %s' % elector_addr)

    # check for unconfirmed transactions
    printl('Checking for unconfirmed transactions')
    transactions = utils.get_awaiting_transactions(t, user_conf['msig_addr'], elector_addr, path_conf['abi'])
    if transactions is None:
        printl('Cannot get transaction list for %s' % user_conf['msig_addr'])
        exit(1)
    if len(transactions) > 0:
        printl('There are unconfirmed transactions from %s to elector: %s' % (user_conf['msig_addr'], str(transactions)))
        exit(0)
    else:
        printl('No unconfirmed transactions')

    #
    msig_addr_hex = '0x' + user_conf['msig_addr'][3:]
    msig_addr_int = int(msig_addr_hex, 0)

    # some reward?
    printl('Checking for reward')
    res, out = t.runget(elector_addr, 'compute_returned_stake', msig_addr_hex)
    if not res:
        printl(out)
        printl('Cannot get returned stake for %s' % msig_addr_hex)
        exit(1)
    try:
        returned_stake = int(out[0], 0)
    except:
        printl('Bad compute_returned_stake answer')
        exit(1)

    if returned_stake > 0:
        printl('Found stake to return: %d' % returned_stake)

        # check for wallet balance
        printl('Checking for balance on %s' % user_conf['msig_addr'])
        res, out = t.account(user_conf['msig_addr'])
        if not res:
            printl(out)
            printl('Cannot get account state for %s' % user_conf['msig_addr'])
            exit(1)
        if not out['active']:
            printl('Wallet not active')
            exit(0)
        if out['balance'] <= 1000000000:  # 1 ton, but fees???
            printl('Not enough tokens to take reward. Have %d, min needed %d' % (out['balance'], 1000000000))

            msg = 'Not enough tokens to take reward. Have %d, min needed %d' % (out['balance'], 1000000000)
            utils.notify_owner(msg, notify_conf, email_conf)

            exit(0)

        printl('Requesting for reward')
        trans_id = utils.request_reward(t, fift, path_conf['recover-stake'], user_conf['msig_addr'], elector_addr, path_conf['abi'], user_conf['keyfile'])
        if trans_id is None:
            printl('Cannot send request for reward for %s' % user_conf['msig_addr'])
            exit(1)
        # check for unconfirmed transactions
        printl('Checking for unconfirmed transactions')
        transactions = utils.get_awaiting_transactions(t, user_conf['msig_addr'], elector_addr, path_conf['abi'])
        if transactions is None:
            printl('Cannot get transaction list for %s' % user_conf['msig_addr'])
            exit(1)
        if len(transactions) > 0:
            printl('There are unconfirmed transactions from %s to elector: %s' % (user_conf['msig_addr'], str(transactions)))

            # есть неподтверждённые транзакции, уведомим кастодианов
            custodians = utils.get_custodians(t, user_conf['msig_addr'], path_conf['abi'])
            if custodians is None:
                printl('Cannot get custodians for %s' % user_conf['msig_addr'])
                exit(1)

            msg = 'Need your confirmation for transactions: %s' % str(transactions)

            utils.notify_custodians(custodians, msg, notify_conf, email_conf)

            printl('Custodians notified for transactions: %s' % str(transactions))
            exit(0)
    else:
        printl('No reward')


    printl('Checking for active election')
    res, out = t.runget(elector_addr, 'active_election_id')
    if not res:
        printl(out)
        printl('Cannot get active election id')
        exit(1)
    try:
        active_election_id = int(out[0], 0)
    except:
        printl('Bad active election id')
        exit(1)

    if active_election_id != 0:
        printl('Current election %d' % active_election_id)

    if active_election_id != 0:
        election_file = path_conf['election_folder'] + '/' + str(active_election_id) + '.json'

        try:
            with open(election_file, 'r') as f:
                election_obj = json.load(f)
        except:
            election_obj = None

        if election_obj is None:
            printl('No saved election info')
        else:
            printl('Loaded saved election info from %s' % election_file)

        if election_obj is None:
            # Election parameters
            printl('Get config15')
            res, out = t.getconfig(15)
            if not res:
                printl(out)
                printl('Cannot get config15')
                exit(1)

            # {'elections_end_before': 8192, 'elections_start_before': 32768, 'stake_held_for': 32768, 'validators_elected_for': 65536}
            try:
                elections_start_tm = active_election_id - out['elections_start_before']
                elections_end_tm = active_election_id - out['elections_end_before']
                validator_since_tm = active_election_id
                validator_until_tm = active_election_id + out['validators_elected_for']
                stake_held_for_tm = validator_until_tm + out['stake_held_for']
                expire = stake_held_for_tm + 1000
            except:
                printl('Bad config15')
                exit(1)

            # Validator stake parameters
            printl('Get config17')
            res, out = t.getconfig(17)
            if not res:
                printl(out)
                printl('Cannot get config17')
                exit(1)

            try:
                # {'max_stake': '10000000000000000', 'max_stake_factor': 196608, 'min_stake': '10000000000000', 'min_total_stake': '100000000000000'}
                max_stake = int(out['max_stake'])
                min_stake = int(out['min_stake'])
                max_stake_factor = int(out['max_stake_factor']) / 65536.0
            except:
                printl('Bad config17')
                exit(1)

            min_stake += 1000000000

            # check for wallet balance
            printl('Checking for balance on %s' % user_conf['msig_addr'])
            res, out = t.account(user_conf['msig_addr'])
            if not res:
                printl(out)
                printl('Cannot get account state for %s' % user_conf['msig_addr'])
                exit(1)
            if not out['active']:
                printl('Wallet not active')
                exit(0)
            if out['balance'] <= min_stake + 1000000000: # min stake + fees
                printl('Not enough tokens for elections. Have %d, min needed %d' % (out['balance'], min_stake + 1000000000))

                msg = 'Not enough tokens for elections. Have %d, min needed %d' % (out['balance'], min_stake + 1000000000)
                utils.notify_owner(msg, notify_conf, email_conf)

                exit(0)
            our_balance = out['balance']
            printl('Our balance is %d' % our_balance)

            # stack and factor checks
            our_stake_factor = min(max_stake_factor, user_conf['stake_factor'])
            our_stake_factor = max(our_stake_factor, 1)

            if user_conf['stake_value'] == 'all':
                our_stake_value = our_balance - 1000000000 # 1 ton for fees
            elif user_conf['stake_value'] == 'min':
                our_stake_value = min_stake
            else:
                our_stake_value = user_conf['stake_value']

            # ограничиваем сверху максимальной ставкой и нашим балансом
            our_stake_value = min(max_stake, our_stake_value)
            our_stake_value = min(our_balance - 1000000000, our_stake_value)
            # ограничиваем снизу минимальной ставкой
            our_stake_value = max(min_stake, our_stake_value)

            printl('Election stake %d' % our_stake_value)

            res, config = v.getconfig()
            if not res:
                printl(config)
                printl('Cannot get validator node config')
                exit(1)

            # check if keys for election already installed and delete them
            try:
                for el in config['validators']:
                    if el['election_date'] == active_election_id:
                        # deleting keys
                        for i in el['adnl_addrs']:
                            v.delvalidatoraddr(base64.b64decode(el['id']).hex(), base64.b64decode(i['id']).hex())
                        for i in el['temp_keys']:
                            v.deltempkey(base64.b64decode(el['id']).hex(), base64.b64decode(i['key']).hex())
                        v.delpermkey(base64.b64decode(el['id']).hex())
            except:
                pass

            res, private_key = v.newkey()
            if not res:
                printl(private_key)
                printl('Cannot generate key')
                exit(1)
            res, public_key = v.exportpub(private_key)
            if not res:
                printl(public_key)
                printl('Cannot export pubkey')
                exit(1)
            res, adnl_key = v.newkey()
            if not res:
                printl(adnl_key)
                printl('Cannot generate key')
                exit(1)

            fn = fift.get_tempfile_name('validator-to-sign.bin')
            res, out = fift.run(path_conf['validator-elect-req'], user_conf['msig_addr'], str(active_election_id), str(our_stake_factor), adnl_key, fn)
            if not res:
                printl(out)
                printl('Cannot generate transaction')
                exit(1)
            try:
                with open(fn, 'rb') as f:
                    validator_request = f.read().hex().upper()
                os.remove(fn)
            except:
                printl('Cannot generate transaction')
                exit(1)

            res, sign = v.sign(private_key, validator_request)
            if not res:
                printl(sign)
                printl('Cannot sign transaction')
                exit(1)

            fn = fift.get_tempfile_name('validator-query.boc')
            res, out = fift.run(path_conf['validator-elect-signed'], user_conf['msig_addr'], str(active_election_id), str(our_stake_factor), adnl_key, public_key,  sign, fn)
            if not res:
                printl(out)
                printl('Cannot generate query')
                exit(1)
            try:
                with open(fn, 'rb') as f:
                    validator_query = f.read()
                os.remove(fn)
            except:
                printl('Cannot generate query')
                exit(1)

            election_obj = {
                'election_id': active_election_id,
                'state': 'created',
                'elections_start': datetime.utcfromtimestamp(elections_start_tm).strftime('%Y-%m-%d %H:%M:%S UTC'),
                'elections_start_tm': elections_start_tm,
                'elections_end': datetime.utcfromtimestamp(elections_end_tm).strftime('%Y-%m-%d %H:%M:%S UTC'),
                'elections_end_tm': elections_end_tm,
                'validator_since': datetime.utcfromtimestamp(validator_since_tm).strftime('%Y-%m-%d %H:%M:%S UTC'),
                'validator_since_tm': validator_since_tm,
                'validator_until': datetime.utcfromtimestamp(validator_until_tm).strftime('%Y-%m-%d %H:%M:%S UTC'),
                'validator_until_tm': validator_until_tm,
                'stake_held_for': datetime.utcfromtimestamp(stake_held_for_tm).strftime('%Y-%m-%d %H:%M:%S UTC'),
                'stake_held_for_tm': stake_held_for_tm,
                'expire': expire,
                'max_stake': max_stake,
                'min_stake': min_stake,
                'max_stake_factor': max_stake_factor,
                'our_stake_value': our_stake_value,
                'our_stake_factor': our_stake_factor,
                'elector_addr': elector_addr,
                'private_key': private_key,
                'public_key': public_key,
                'public_key_hex': base64.b64decode(public_key).hex().upper()[8:],
                'adnl_key': adnl_key,
                'validator_query_hex': validator_query.hex().upper(),
                'validator_query_base64': base64.b64encode(validator_query).decode("utf-8"),
                'transIds': []
            }
            res = utils.save_atomic(election_file, json.dumps(election_obj, indent=4))
            if not res:
                printl('Cannot save %s' % election_file)
                exit(1)
            else:
                printl('Saved election info to %s' % election_file)

        if election_obj['state'] == 'confirmed':
            printl('Already registered in election %d' % active_election_id)
            exit(0)

        # проверим, сконфигурирована ли нода на эти выборы

        # Get validator keys
        res, config = v.getconfig()
        if not res:
            printl(config)
            printl('Cannot get validator node config')
            exit(1)

        # search for key
        validator_configured = False
        try:
            for el in config['validators']:
                if el['election_date'] == active_election_id and base64.b64decode(el['id']).hex().upper() == election_obj['private_key']:
                    validator_configured = True
                    break
        except:
            pass

        if not validator_configured:
            # Configuring node from zero
            res = v.addpermkey(election_obj['private_key'], election_obj['election_id'], election_obj['expire'])
            if not res:
                printl('Cannot addpermkey')
                exit(1)
            res = v.addtempkey(election_obj['private_key'], election_obj['private_key'], election_obj['expire'])
            if not res:
                printl('Cannot addtempkey')
                exit(1)
            res = v.addadnl(election_obj['adnl_key'])
            if not res:
                printl('Cannot addadnl')
                exit(1)
            res = v.addvalidatoraddr(election_obj['private_key'], election_obj['adnl_key'], election_obj['expire'])
            if not res:
                printl('Cannot addvalidatoraddr')
                exit(1)

        # сначала посмотрим, есть ли мы в списке участников
        validator_public_key_int = int(election_obj['public_key_hex'], 16)

        printl('Checking our public key %s in participant list' % (election_obj['public_key_hex']))
        stake = utils.check_participant_list(t, election_obj['elector_addr'], validator_public_key_int)
        if stake is None:
            printl('Cannot get participant list')
            exit(1)
        if stake > 0:
            printl('Found our public key %s in participant list with stake = %d' % (election_obj['public_key_hex'], stake))

            election_obj['state'] = 'confirmed'
            res = utils.save_atomic(election_file, json.dumps(election_obj, indent=4))
            if not res:
                printl('Cannot save %s' % election_file)
                exit(1)

            msg = 'Successfully registered in elections %d with stake %d' % (election_obj['election_id'], election_obj['our_stake_value']/1000000000)
            utils.notify_owner(msg, notify_conf, email_conf)

            exit(0)
        else:
            printl('Not found our public key %s in participant list' % (election_obj['public_key_hex']))

        # сформируем транзакцию к контракту электора!
        sended = False
        for i in range(try_num):
            printl('TRY %d Sending transaction from %s to %s with stake %d and payload %s' % (i+1, user_conf['msig_addr'], election_obj['elector_addr'], election_obj['our_stake_value'], election_obj['validator_query_base64']))
            res, out = t.transfer(user_conf['msig_addr'], election_obj['elector_addr'], election_obj['our_stake_value'], False, False, election_obj['validator_query_base64'], path_conf['abi'], user_conf['keyfile'])
            if not res or 'transId' not in out:
                printl('Failed')
                continue
            else:
                sended = True
                printl('Sended')
                break

        if not sended:
            msg = 'Cannot send transaction for elections participation'
            utils.notify_owner(msg, notify_conf, email_conf)
            exit(1)

        election_obj['transIds'].append(out['transId'])
        election_obj['state'] = 'unconfirmed'
        res = utils.save_atomic(election_file, json.dumps(election_obj, indent=4))
        if not res:
            printl('Cannot save %s' % election_file)
            exit(1)

        # проверим, есть ли транзакции к электору в ожидании подтверждения
        printl('Checking for unconfirmed transactions')
        transactions = utils.get_awaiting_transactions(t, user_conf['msig_addr'], election_obj['elector_addr'], path_conf['abi'])
        if transactions is None:
            printl('Cannot get transaction list for %s' % user_conf['msig_addr'])
            exit(1)

        if len(transactions) > 0:
            printl('There are unconfirmed transactions from %s to elector: %s' % (user_conf['msig_addr'], str(transactions)))

            # да, есть неподтверждённые транзакции, уведомим кастодианов
            custodians = utils.get_custodians(t, user_conf['msig_addr'], path_conf['abi'])
            if custodians is None:
                printl('Cannot get custodians for %s' % user_conf['msig_addr'])
                exit(1)

            msg = 'Need your confirmation for transactions: %s' % str(transactions)

            utils.notify_custodians(custodians, msg, notify_conf, email_conf)

            printl('Custodians notified for transactions: %s' % str(transactions))
            exit(0)
        else:
            # транзакция уже прошла, проверим, попали ли мы в списки участников
            printl('Checking our public key %s in participant list' % (election_obj['public_key_hex']))
            stake = utils.check_participant_list(t, election_obj['elector_addr'], validator_public_key_int)
            if stake is None:
                printl('Cannot get participant list')
                exit(1)
            if stake > 0:
                printl('Found our public key %s in participant list with stake = %d' % (election_obj['public_key_hex'], stake))

                election_obj['state'] = 'confirmed'
                res = utils.save_atomic(election_file, json.dumps(election_obj, indent=4))
                if not res:
                    printl('Cannot save %s' % election_file)
                    exit(1)

                msg = 'Successfully registered in elections %d with stake %d' % (election_obj['election_id'], election_obj['our_stake_value']/1000000000)
                utils.notify_owner(msg, notify_conf, email_conf)

                exit(0)
            else:
                printl('Not found our public key %s in participant list' % (election_obj['public_key_hex']))
                exit(1)

    else:
        # no elections
        printl('No current elections')
        exit(0)
