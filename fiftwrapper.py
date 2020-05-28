import os
import subprocess
import json
import tempfile

class Fift:
    TIMEOUT = 60

    def __init__(self, program_path, includes):
        self.program_path = program_path
        self.includes = includes

    def _evaluate(self, args):
        '''
        Run fift
        :param args:
        :return: return value and stdout
        '''
        try:
            params = [self.program_path, '-I', self.includes] + args
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

    def run(self, contract, *args):
        a = ['-s', contract] + list(args)
        retcode, out = self._evaluate(a)
        return retcode == 0, out

    def get_tempfile_name(self, id):
        return os.path.join(tempfile.gettempdir(), next(tempfile._get_candidate_names()) + "_" + id)
