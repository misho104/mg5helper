import logging
import os
import select
import subprocess
import sys
from typing import List, Union, Tuple

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
        self.output = []
        self.proc = subprocess.Popen([self.SHELL] + self.SHELL_ARGS,
                                     stdin=subprocess.PIPE,
                                     stdout=subprocess.PIPE,
                                     encoding='utf-8',
                                     env={},
                                     **kwargs)
        for i in ([commands] if isinstance(commands, str) else commands):
            self.proc.stdin.write('{}\n'.format(i))

    def __enter__(self, **kwargs):
        self.stdin = self.proc.stdin
        return self

    def run(self)->str:
        self.proc.stdin.close()
        while True:
            line = self.proc.stdout.readline()
            if line:
                self.output.append(line)
                print(line, end='')
            if self.proc.poll() is not None:
                break
        self.proc.wait(1)
        return ''.join(self.output)

    def __exit__(self, *args, **kwargs):
        return self.proc.__exit__(*args, **kwargs)

# class MG5Output:
#    def __init__(self, dir: Union[str, pathlib.Path, None]=None, model: Optional[str]=None):
#        self.dir = dir
#        self.model = model
    #           def __init__(self, mg5, dir_name):
    #       dir_name = os.path.normpath(os.path.expanduser(dir_name))
    #       if os.path.isabs(dir_name):
    #           raise AbsolutePathSpecifiedException
    #       if not (os.path.lexists(dir_name) and os.path.isdir(dir_name)):
    #           raise MG5OutputNotFoundError(dir_name)
#
#        self.mg5 = mg5
#        self.dir_name = dir_name

#    def move_cards(self, cards):
#        if is_str(cards):
#            prefix, suffix = cards, ''
#            self.find_and_move_all_cards(prefix, suffix)
#        elif isinstance(cards, dict) and ('prefix' in cards or 'suffix' in cards):
#            prefix, suffix = cards.pop('prefix', ''), cards.pop('suffix', '')
#            if len(cards) != 0:
#                raise CardSpecificationError()
#            self.find_and_move_all_cards(prefix, suffix)
#        elif isinstance(cards, dict):
#            for k, v in cards.items():
#                MG5Card(k, v).write(os.path.join(self.dir_name, 'Cards'))
#        else:
#            raise CardSpecificationError()
#        print()
#
#    def find_and_move_all_cards(self, prefix, suffix):
#        if not re.match(r'.*[/_-]'):
#            prefix = prefix + '_'
#        if suffix:
#            suffix = '_' + suffix + '.dat'
#        else:
#            suffix = '.dat'
#
#        for k in ['param_card', 'run_card', 'pythia_card', 'pythia8_card', 'pgs_card',
#                  'delphes_card', 'grid_card', 'plot_card', 'delphes_trigger']:
#            source = prefix + k + suffix
#            target = os.path.join(self.dir_name, 'Cards', k + '.dat')
#            if os.path.isfile(source):
#                shutil.copy(source, target)
#                MG5Helper.notice('Card: {} -> {}'.format(source, target))
#
#    def launch(self, laststep='parton', cards=None, run_name=''):
#        laststep = laststep.lower()
#        if not (laststep in self.LASTSTEPS):
#            raise InvalidLaunchError
#        self.move_cards(cards)
#
#        mg5cmd = ['set automatic_html_opening False']
#        # ----------------
#        # Apr 4 2016 SI: MSSM process seems to prefer 'launch' even for
#        #                decay? so, 'generate_events' only for non-MSSM models?
#        # if self.is_process_decay():
#        if False:
#            # ----------------
#            mg5cmd.append('generate_events -f --multicore')
#            program = os.path.join(self.dir_name, 'bin', 'madevent')
#        else:
#            mg5cmd.append('launch {dir_name} {run_name} -f --multicore --laststep={laststep}'.format(
#                dir_name=self.dir_name,
#                run_name='--name=' + run_name if run_name else '',
#                laststep=laststep))
#            program = self.mg5.mg5bin
#
#        with tempfile.NamedTemporaryFile(mode='w', prefix='tmp.mg5lnc.', dir='.', delete=False) as f:
#            f.write('\n'.join(mg5cmd))
#
#        cmd = [program, os.path.basename(f.name)]  # fine because tmpfile is at '.'
#        MG5Helper.info('EXEC: ' + ' '.join(cmd))
#        output = subprocess.Popen(cmd, env=dict(os.environ, LANG='C'), stdout=subprocess.PIPE)
#
#        log = []
#        while True:
#            line = output.stdout.readline()
#            if not line:
#                break
#            print(line, end='')
#            log.append(line)
#
#        # TODO: Is there any way to check if the launch succeeds?
#
#        os.remove(f.name)
#        return ''.join(log)
#
#
# sub is_process_decay{
# my ($dir) = shift;
##   open(PROC, "$dir/Cards/proc_card_mg5.dat");
# foreach(<PROC>){
# print $_;
# if (/^\s*generate\s*(.*?)\s*>\s*(.*)/i){
# return ($1 !~ / /);
# }
# }
# close(PROC);
##   error("fail detecting the process.");
# }
##
## #==============================================================================#
## # Output scrape                                                                #
## #==============================================================================#
# sub cs_fb{
# my ($cs_fb, $cserr_fb) = (-1, -1);
# foreach(@_){
# if(/^\s*cross.section\s*:\s*([0-9\.e\+\-]*) \+- ([0-9\.e\+\-]*)\s+(pb|fb)\s*$/i){
# if($cs_fb != -1){
##         warning("Cross section line might appear twice.");
# }
# ($cs_fb, $cserr_fb) = ($1, $2);
# if($3 =~ /pb/i){
# $cs_fb    *= 1000;
# $cserr_fb *= 1000;
# }
# }
# }
# if($cs_fb == -1){
##     warning("Cross section line cannot be found.");
# }
# return ($cs_fb, $cserr_fb);
# }
#
#
# class MG5BinNotFoundError(FileNotFoundError):
#    def __init__(self, mg5bin='', is_default=True):
#        self.message = 'MG5 executable, {} value "{}", not found.'.format(
#            'default' if is_default else 'specified',
#            mg5bin)
#
#    def __str__(self):
#        return self.message
#
#    pass
#
#
# class MG5OutputNotFoundError(FileNotFoundError):
#    def __init__(self, dir_name):
#        self.message = 'Directory {} not found.'.format(dir_name)
#
#    def __str__(self):
#        return self.message
#
#
# class AbsolutePathSpecifiedException(ValueError):
#    def __str__(self):
#        return 'Output directory must be a relative path for safety.'
#
#
# class InvalidLaunchError(ValueError):
#    def __str__(self):
#        return 'Invalid launch options are specified.'
#
#
# class CardSpecificationError(ValueError):
#    def __init__(self, message=None):
#        self.message = ' ({})'.format(message) if message else ''
#
#    def __str__(self):
#        return 'Invalid card specification{}.'.format(self.message)
#
#
# class CardReplaceKeyError(KeyError):
#    def __init__(self, keyerror, filename):
#        self.message = 'Card {} has an undefined key: {}'.format(filename, keyerror.message)
#
#    def __str__(self):
#        return self.message
#
#
# class MG5Error(BaseException):
#    def __init__(self, message, cmd=None):
#        self.message = message
#        if isinstance(cmd, list):
#            self.cmd = '\n'.join(cmd)
#        else:
#            self.cmd = cmd
#
#    def __str__(self):
#        s = self.message
#        if self.cmd:
#            s = s + ' The command was:\n' + self.cmd
#        return s.replace('\n', '\n    ')
#
#
# class MG5Helper:
#    @classmethod
#    def warning(cls, message):
#        print('{yellow}[Warning] {m}{end}'.format(yellow='\033[93m', m=message, end='\033[0m'))
#
#    @classmethod
#    def info(cls, message):
#        print('{green}[info] {m}{end}'.format(green='\033[92m', m=message, end='\033[0m'))
#
#    @classmethod
#    def notice(cls, message):
#        print('{blue}[info] {m}{end}'.format(blue='\033[94m', m=message, end='\033[0m'))
#
#    @classmethod
# class MG5Card:
#    def __init__(self, key, specification):
#        self.key = key
#        if is_str(specification):
#            self.file = specification
#            self.rules = dict()
#        elif isinstance(specification, tuple):
#            try:
#                self.file, rules = specification
#            except ValueError:
#                raise CardSpecificationError('string or two-valued tuple')
#
#            if isinstance(rules, dict):
#                self.rules = rules
#            elif isinstance(rules, list):
#                self.rules = dict((str(i), v) for i, v in enumerate(rules))
#            else:
#                raise CardSpecificationError('invalid replace rules')
#        self.replaces = 0
#
#    VAR_REGEX = re.compile('<<<+%(,+?)>>>+')
#
#    def __replacement(self, key):
#        self.replaces += 1
#        try:
#            value = self.rules[key]
#        except KeyError as e:
#            raise CardReplaceKeyError(e, self.file)
#        if isinstance(value, float) or isinstance(value, int):
#            value = str(value)
#        return value
#
#    def _read(self):
#        # TODO: error handling?
#        with open(self.file) as f:
#            raw = f.read()
#        return re.sub(self.VAR_REGEX, lambda m: self.__replacement(m.group(1)), raw)
#
#    def card_name(self):
#        return 'delphes_trigger.dat' if self.key == 'trigger' else '{}_card.dat'.format(self.key)
#
#    def write(self, dir_name):
#        target = os.path.join(dir_name, self.card_name())
#
#        if self.file == '-':
#            if os.path.exists(target):
#                os.remove(target)
#            MG5Helper.notice('Card: removed {} '.format(target))
#            return ''
#
#        data = self._read()
#        f = open(target, 'w')  # TODO: error handling?
#        f.write(data)
#        f.close()
#        MG5Helper.notice('Card: {} -> {} ({} replacements)'.format(self.file, target, self.replaces))
#        return target
#################
