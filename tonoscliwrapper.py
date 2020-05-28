import os
import subprocess
import json

class TonosCli:
    TIMEOUT = 320

    def __init__(self, program_path='tonos-cli'):
        self.program_path = program_path

    def get_int(self, string):
        return int(string, 0)

    def _evaluate(self, args):
        '''
        Run tonos-cli program
        :param args: args to tonos-cli
        :return: return value and stdout of tonos-cli
        '''
        try:
            params = [self.program_path] + args
            out = subprocess.check_output(params, timeout=self.TIMEOUT).decode("utf-8")
            retcode = 0
        except subprocess.CalledProcessError as e:
            retcode = e.returncode
            out = 'Cmd: %s (TIMEOUT %d)\n' % (params, self.TIMEOUT)
            out += e.output.decode("utf-8")
        except subprocess.TimeoutExpired as e:
            retcode = 2
            out = 'Cmd: %s (TIMEOUT %d)\n' % (params, self.TIMEOUT)
            out += e.output.decode("utf-8")
        except Exception as e:
            retcode = -1
            out = 'Cmd: %s (TIMEOUT %d)\n' % (params, self.TIMEOUT)
            out += str(e)
        return retcode, out

    def getconfig(self, index):
        '''
        Get global config
        :param index: index if config
        :return: (success, obj)
        '''
        retcode, out = self._evaluate(['getconfig', str(index)])
        if retcode != 0:
            return False, out
        try:
            ms = 'Config p%d: ' % index
            substr = out[out.find(ms)+len(ms):]
            obj = json.loads(substr)
            return True, obj
        except Exception as e:
            return False, 'Output parsing error: ' + str(e) + '\nCmd output: ' + out

    def account(self, addr):
        retcode, out = self._evaluate(['account', addr])
        if retcode != 0:
            return False, out
        res = {
            'active': False,
            'balance': 0
        }
        try:
            for l in out.split('\n'):
                if l.startswith('acc_type:'):
                    if 'Active' in l:
                        res['active'] = True
                elif l.startswith('balance:'):
                    res['balance'] = int(l[8:].replace(' ', ''))
            return True, res
        except Exception as e:
            return False, 'Output parsing error: ' + str(e) + '\nCmd output: ' + out

    def runget(self, addr, method, *params):
        '''
        tonos-cli runget <address> <method> [<params>...]
        '''
        retcode, out = self._evaluate(['runget', addr, method] + list(params))
        if retcode != 0 or not 'Succe' in out:
            return False, out
        try:
            ms = 'Result: '
            substr = out[out.find(ms)+len(ms):]
            obj = json.loads(substr)
            return True, obj
        except Exception as e:
            return False, 'Output parsing error: ' + str(e) + '\nCmd output: ' + out

    def call(self, addr, method, abi, sign, *params):
        '''
        tonos-cli call --abi contract.abi.json --sign contract_keys.json <raw_address> methodName {<method_args>}
        '''
        p = ['call', '--abi', abi, addr, method] + list(params)
        if sign is not None:
            p += ['--sign', sign]
        retcode, out = self._evaluate(p)
        if retcode != 0 or not 'Succe' in out:
            return False, out
        if 'Succe' in out and not 'Result:' in out:
            return True, {}
        try:
            ms = 'Result: '
            substr = out[out.find(ms)+len(ms):]
            obj = json.loads(substr)
            return True, obj
        except Exception as e:
            return False, 'Output parsing error: ' + str(e) + '\nCmd output: ' + out

    def run(self, addr, method, abi, sign, *params):
        '''
        tonos-cli run [--abi <abi_file>] <address> <method> <params>
        '''
        p = ['run', '--abi', abi, addr, method] + list(params)
        if sign is not None:
            p += ['--sign', sign]
        retcode, out = self._evaluate(p)
        if retcode != 0 or not 'Succe' in out:
            return False, out
        if 'Succe' in out and not 'Result:' in out:
            return True, {}
        try:
            ms = 'Result: '
            substr = out[out.find(ms)+len(ms):]
            obj = json.loads(substr)
            return True, obj
        except Exception as e:
            return False, 'Output parsing error: ' + str(e) + '\nCmd output: ' + out

    def transfer(self, src, dst, amount, bounce, all, payload, abi, sign):
        '''
        Transfers tokens from src to dst
        '''
        params = '{"dest":"%s","value":%d,"bounce":%s,"allBalance":%s,"payload":"%s"}' % (dst,
                                                                                          0 if all else amount,
                                                                                          'true' if bounce else 'false',
                                                                                          'true' if all else 'false',
                                                                                          "" if payload is None else payload)
        return self.call(src, 'submitTransaction', abi, sign, params)

    def confirmTransaction(self, src, trans_id, abi, sign):
        '''
        Runs confirmTransaction method
        '''
        params = '{"transactionId":"%s"}' % (trans_id)
        return self.call(src, 'confirmTransaction', abi, sign, params)

    def getTransactions(self, addr, abi):
        '''
        Runs getTransactions {} method
        '''
        return self.run(addr, 'getTransactions', abi, None, '{}')

    def getCustodians(self, addr, abi):
        '''
        Runs getCustodians {} method
        '''
        return self.run(addr, 'getCustodians', abi, None, '{}')

if __name__ == '__main__':
    t = TonosCli('/home/user/tonos-cli/tonos-cli')
    for i in range(1, 20):
        res, out = t.getconfig(i)
        print('Config %d: %s' % (i, str(out)))
