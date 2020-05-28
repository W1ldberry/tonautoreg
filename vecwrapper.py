import os
import subprocess
import json

class ValidatorEngineConsole:
    TIMEOUT = 60

    def __init__(self, program_path, client_key, server_key, server_addr):
        self.program_path = program_path
        self.client_key = client_key
        self.server_key = server_key
        self.server_addr = server_addr


    def _evaluate(self, args):
        '''
        Run /validator-engine-console program
        :param args:
        :return: return value and stdout
        '''
        try:
            a = []
            for i in args:
                a.append('-c')
                a.append(i)
            params = [self.program_path] + ['-k', self.client_key, '-p', self.server_key, '-a', self.server_addr] + a + ['-c', 'quit']
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
            retcode = 1
            out = 'Cmd: %s (TIMEOUT %d)\n' % (params, self.TIMEOUT)
            out += str(e)
        return retcode, out

    def getconfig(self):
        '''
        downloads current config
        '''
        retcode, out = self._evaluate(['getconfig'])
        if retcode != 0:
            return False, out
        try:
            ms = '---------'
            substr = out[out.find(ms)+len(ms):-9]
            obj = json.loads(substr)
            return True, obj
        except Exception as e:
            return False, 'Output parsing error: ' + str(e) + '\nCmd output: ' + out

    def newkey(self):
        '''
        generates new key pair on server
        '''
        retcode, out = self._evaluate(['newkey'])
        if retcode != 0:
            return False, out
        try:
            ms = 'created new key '
            key = out[out.find(ms)+len(ms):-1]
            return True, key
        except Exception as e:
            return False, 'Output parsing error: ' + str(e) + '\nCmd output: ' + out

    def exportpub(self, key):
        '''
        exports public key by key hash
        :param key: private key in HEX
        :return: public key in base64
        '''
        retcode, out = self._evaluate(['exportpub ' + key])
        if retcode != 0:
            return False, out
        try:
            ms = 'got public key: '
            key = out[out.find(ms)+len(ms):-1]
            return True, key
        except Exception as e:
            return False, 'Output parsing error: ' + str(e) + '\nCmd output: ' + out

    def sign(self, key, data):
        '''
        signs bytestring with privkey
        '''
        retcode, out = self._evaluate(['sign ' + key + ' ' + data])
        if retcode != 0:
            return False
        try:
            ms = 'got signature '
            sign = out[out.find(ms) + len(ms):-1]
            return True, sign
        except Exception as e:
            return False, 'Output parsing error: ' + str(e) + '\nCmd output: ' + out

    def addpermkey(self, permkey, start, expire):
        '''
        add validator permanent key
        '''
        retcode, out = self._evaluate(['addpermkey ' + permkey + ' ' + str(start) + ' ' + str(expire)])
        if retcode != 0 or 'success' not in out:
            print(out)
            return False
        return True

    def delpermkey(self, key):
        '''
        force del unused validator permanent key
        '''
        retcode, out = self._evaluate(['delpermkey ' + key])
        if retcode != 0 or 'success' not in out:
            print(out)
            return False
        return True

    def addtempkey(self, permkey, tempkey, expire):
        '''
        add validator temp key
        '''
        retcode, out = self._evaluate(['addtempkey ' + permkey + ' ' + tempkey + ' ' + str(expire)])
        if retcode != 0:
            print(out)
            return False
        return True

    def deltempkey(self, permkey, key):
        '''
        force del unused validator temp key
        '''
        retcode, out = self._evaluate(['deltempkey ' + permkey + ' ' + key])
        if retcode != 0 or 'success' not in out:
            print(out)
            return False
        return True

    def addvalidatoraddr(self, permkey, key, expire):
        '''
        add validator ADNL addr
        '''
        retcode, out = self._evaluate(['addvalidatoraddr ' + permkey + ' ' + key + ' ' + str(expire)])
        if retcode != 0 or 'success' not in out:
            print(out)
            return False
        return True

    def delvalidatoraddr(self, permkey, key):
        '''
        force del unused validator ADNL addr
        '''
        retcode, out = self._evaluate(['delvalidatoraddr ' + permkey + ' ' + key])
        if retcode != 0 or 'success' not in out:
            print(out)
            return False
        return True

    def addadnl(self, key, category=0):
        '''
        use key as ADNL addr
        '''
        retcode, out = self._evaluate(['addadnl ' + key + ' ' + str(category)])
        if retcode != 0 or 'success' not in out:
            print(out)
            return False
        return True

    def deladnl(self, key):
        '''
        del unused ADNL addr
        '''
        retcode, out = self._evaluate(['deladnl ' + key])
        if retcode != 0:
            print(out)
            return False
        return True
