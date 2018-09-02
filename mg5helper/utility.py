import logging
import os
import select
import subprocess
import sys
from typing import List, Union

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger('mg5helper')

cards_abbrev = {
    'param': 'param_card.dat',
    'run': 'run_card.dat',
    'pythia': 'pythia_card.dat',
    'pythia8': 'pythia8_card.dat',
    'pgs': 'pgs_card.dat',
    'delphes': 'delphes_card.dat',
    'shower': 'shower_card.dat',
    'plot': 'plot_card.dat',
    'madspin': 'madspin_card.dat',
    'reweight': 'reweight_card.dat',
}


def timeout_input(prompt='', timeout=3)->str:
    logger.debug('timeout_input prompted: {}'.format(prompt))
    print(prompt, end='')
    sys.stdout.flush()
    i, o, e = select.select([sys.stdin], [], [], timeout)
    answer = sys.stdin.readline().strip() if i else ''
    logger.debug('timeout_input answerted: {}'.format(answer))
    return answer


class shell_cmd:
    SHELL = os.environ.get('SHELL', '/bin/sh')  # type: str
    SHELL_ARGS = ['-l']                         # type: List[str]

    def __init__(self, commands: Union[str, List[str]], **kwargs)->None:
        self.output = []  # type: List[str]
        self.proc = subprocess.Popen([self.SHELL] + self.SHELL_ARGS,   # type: ignore
                                     stdin=subprocess.PIPE,
                                     stdout=subprocess.PIPE,
                                     encoding='utf-8',
                                     env=dict(),
                                     **kwargs)
        for i in ([commands] if isinstance(commands, str) else commands):
            self.proc.stdin.write('{}\n'.format(i))

    def __enter__(self, **kwargs):
        self.stdin = self.proc.stdin
        return self

    def run(self)->List[str]:
        self.proc.stdin.close()
        while True:
            line = self.proc.stdout.readline()
            if line:
                self.output.append(line)
                print(line, end='')
            if self.proc.poll() is not None:
                break
        self.proc.wait(1)
        return self.output

    def __exit__(self, *args, **kwargs):
        return self.proc.__exit__(*args, **kwargs)
