#!env python3
# -*- coding: utf-8 -*-
# Time-Stamp: <2017-07-18 23:00:45>

"""mg5_helper.py: a wrapper module for MadGraph 5."""

from __future__ import absolute_import, division, print_function, unicode_literals

import os
import re
import sys
import shutil
import time
import textwrap
import select
import tempfile
import subprocess
import glob

__version__ = "1.0.1"
__date__ = "21 Jan 2017"
__author__ = "Sho Iwamoto"
__license__ = "MIT"
__status__ = "Development"

# Python 2 <-> 3 #####################################################
try:
    FileNotFoundError
except NameError:
    FileNotFoundError = IOError

if sys.version_info[0] == 3:
    def is_str(obj):
        return isinstance(obj, str)
else:
    def is_str(obj):
        return isinstance(obj, basestring)


######################################################################

class MG5BinNotFoundError(FileNotFoundError):
    def __init__(self, mg5bin="", is_default=True):
        self.message = 'MG5 executable, {} value "{}", not found.'.format(
            'default' if is_default else 'specified',
            mg5bin)

    def __str__(self):
        return self.message

    pass


class MG5OutputNotFoundError(FileNotFoundError):
    def __init__(self, dir_name):
        self.message = 'Directory {} not found.'.format(dir_name)

    def __str__(self):
        return self.message


class AbsolutePathSpecifiedException(ValueError):
    def __str__(self):
        return "Output directory must be a relative path for safety."


class InvalidLaunchError(ValueError):
    def __str__(self):
        return "Invalid launch options are specified."


class CardSpecificationError(ValueError):
    def __init__(self, message=None):
        self.message = ' ({})'.format(message) if message else ""

    def __str__(self):
        return 'Invalid card specification{}.'.format(self.message)


class CardReplaceKeyError(KeyError):
    def __init__(self, keyerror, filename):
        self.message = 'Card {} has an undefined key: {}'.format(filename, keyerror.message)

    def __str__(self):
        return self.message


class MG5Error(BaseException):
    def __init__(self, message, cmd=None):
        self.message = message
        if isinstance(cmd, list):
            self.cmd = '\n'.join(cmd)
        else:
            self.cmd = cmd

    def __str__(self):
        s = self.message
        if self.cmd:
            s = s + ' The command was:\n' + self.cmd
        return s.replace('\n', '\n    ')


class MG5Helper:
    @classmethod
    def warning(cls, message):
        print('{yellow}[Warning] {m}{end}'.format(yellow='\033[93m', m=message, end='\033[0m'))

    @classmethod
    def info(cls, message):
        print('{green}[info] {m}{end}'.format(green='\033[92m', m=message, end='\033[0m'))

    @classmethod
    def notice(cls, message):
        print('{blue}[info] {m}{end}'.format(blue='\033[94m', m=message, end='\033[0m'))

    @classmethod
    def timeout_input(cls, prompt="", timeout=3):
        print(prompt, end="")
        sys.stdout.flush()
        i, o, e = select.select([sys.stdin], [], [], timeout)
        return sys.stdin.readline().strip() if i else ""


class MG5Card:
    def __init__(self, key, specification):
        self.key = key
        if is_str(specification):
            self.file = specification
            self.rules = dict()
        elif isinstance(specification, tuple):
            try:
                self.file, rules = specification
            except ValueError:
                raise CardSpecificationError("string or two-valued tuple")

            if isinstance(rules, dict):
                self.rules = rules
            elif isinstance(rules, list):
                self.rules = dict((str(i), v) for i, v in enumerate(rules))
            else:
                raise CardSpecificationError("invalid replace rules")
        self.replaces = 0

    VAR_REGEX = re.compile('<<<+%(,+?)>>>+')

    def __replacement(self, key):
        self.replaces += 1
        try:
            value = self.rules[key]
        except KeyError as e:
            raise CardReplaceKeyError(e, self.file)
        if isinstance(value, float) or isinstance(value, int):
            value = str(value)
        return value

    def _read(self):
        # TODO: error handling?
        with open(self.file) as f:
            raw = f.read()
        return re.sub(self.VAR_REGEX, lambda m: self.__replacement(m.group(1)), raw)

    def card_name(self):
        return "delphes_trigger.dat" if self.key == "trigger" else '{}_card.dat'.format(self.key)

    def write(self, dir_name):
        target = os.path.join(dir_name, self.card_name())

        if self.file == '-':
            if os.path.exists(target):
                os.remove(target)
            MG5Helper.notice("Card: removed {} ".format(target))
            return ""

        data = self._read()
        f = open(target, "w")  # TODO: error handling?
        f.write(data)
        f.close()
        MG5Helper.notice("Card: {} -> {} ({} replacements)".format(self.file, target, self.replaces))
        return target


class MG5Run:
    """MG5Run main class"""  # TODO: more to write

    @classmethod
    def __mg5bin_default(cls):
        """Return the 'default' value of MG5 executable, looking the
        environmental variable ``PATH``, then ``HEP_MG5``"""

        try:
            m = shutil.which('mg5_aMC')
        except AttributeError:  # python 2.7 does not have 'which'
            out, err = subprocess.Popen(['which', 'mg5_aMC'], stdout=subprocess.PIPE).communicate()
            m = out.strip()
        if m:
            return m
        directory = os.environ.get('HEP_MG5', '.')
        return os.path.join(directory, 'bin', 'mg5_aMC')

    @classmethod
    def help(cls):
        print(textwrap.dedent("""\
            This code is used as a module!

            Usage: output(process(es), directory, [model])
                   launch(directory, [laststep], [cards], [runname])

            process can be an ARRAY.
            model    ||= 'sm'
            laststep ||= 'parton'  [auto|parton|pythia|pgs|delphes]
            runname  ||= 'run_XX'

            two manipulation modes are prepared:
              - In prefix-suffix mode, all known cards with specified suffix/prefix are copied.
                This mode is called if a string is specified, which is regarded as a prefix,
                or a dict with "prefix" and/or "suffix" is specified.

              - If a dict like
                  { 'param' = (template, rules),
                    'run'   = (template, rules), ... }
                is specified, the templates are copied after the rules are applied.
                For a dict rule, <<<%key>>> is replaced to the value.
                For a list rule, <<<%n>>> is replaced to the n-th element.
                rules can be a string, for which no rules are applied.
                If template is '-', the corresponding card is removed.
        """))

    """
        Properties:
            mg5bin       : str
            output_force : bool
    """

    def __init__(self, mg5bin=None, output_force=False):
        self.mg5bin = os.path.normpath(os.path.expanduser(mg5bin or self.__mg5bin_default()))
        self.output_force = output_force or False
        if not (os.path.isfile(self.mg5bin) and os.access(self.mg5bin, os.X_OK)):
            raise MG5BinNotFoundError(self.mg5bin, is_default=(self.mg5bin != mg5bin))
        return

    def output(self, process, dir_name, model=None, extra_code=None, force=None):
        def to_list(obj):
            return obj if isinstance(obj, list) else [obj]

        def assert_is_str(obj, name):
            if not is_str(obj):
                raise TypeError('Invalid "{}" for output.'.format(name))

        assert_is_str(dir_name, "dir_name")
        if os.path.isabs(dir_name):
            raise AbsolutePathSpecifiedException

        if force is None:
            force = self.output_force
        if os.path.lexists(dir_name):
            if not force:
                yn = MG5Helper.timeout_input('Path [{}] exists. Overwrite? [y/N] (3 sec)\n > '.format(dir_name))
                if yn.lower() == 'y':
                    force = True
            if force:
                shutil.rmtree(dir_name)
            else:
                print()
                MG5Helper.info("Output prevented.")
                time.sleep(1)
                return MG5Output(mg5=self, dir_name=dir_name)

        mg5cmd = []
        if model:
            assert_is_str(model, "model")
            mg5cmd.append("import model {}".format(model))
        if extra_code:
            for line in to_list(extra_code):
                assert_is_str(line, "extra_code")
                mg5cmd.append(line)
        for i, proc in enumerate(to_list(process)):
            assert_is_str(proc, "process")
            mg5cmd.append("{cmd} {proc} @ {n}".format(
                cmd=("generate" if i == 0 else "add process"),
                proc=proc,
                n=i+1))  # i is zero-origin
        mg5cmd.append("output {} -f".format(dir_name))
        with tempfile.NamedTemporaryFile(mode='w', prefix='tmp.mg5out.', dir='.', delete=False) as f:
            f.write('\n'.join(mg5cmd))

        cmd = [self.mg5bin, os.path.basename(f.name)]  # fine because tmpfile is at '.'
        MG5Helper.info('EXEC: ' + ' '.join(cmd))
        retval = subprocess.call(cmd, env=dict(os.environ, LANG='C'))

        if retval or not (os.path.isdir(dir_name)):  # NOTE: MG5 only return '0' even if it failed.
            raise MG5Error('MG5 output seems failed.', mg5cmd)

        os.remove(f.name)
        return MG5Output(mg5=self, dir_name=dir_name)

    def launch(self, dir_name, laststep='parton', cards=None, run_name=""):
        MG5Output(mg5=self, dir_name=dir_name).launch(laststep=laststep, cards=cards, run_name=run_name)


class MG5Output:
    """
    Properties:
            mg5      : MG5Run
            dir_name : str
    """

    LASTSTEPS = ['auto', 'parton', 'pythia', 'pgs', 'delphes']

    def __init__(self, mg5, dir_name):
        if not is_str(dir_name):
            raise TypeError('Invalid "dir_name" for MG5Output.__init__.')
        dir_name = os.path.normpath(os.path.expanduser(dir_name))
        if os.path.isabs(dir_name):
            raise AbsolutePathSpecifiedException
        if not (os.path.lexists(dir_name) and os.path.isdir(dir_name)):
            raise MG5OutputNotFoundError(dir_name)

        self.mg5 = mg5
        self.dir_name = dir_name

    def move_cards(self, cards):
        if is_str(cards):
            prefix, suffix = cards, ""
            self.find_and_move_all_cards(prefix, suffix)
        elif isinstance(cards, dict) and ("prefix" in cards or "suffix" in cards):
            prefix, suffix = cards.pop("prefix", ""), cards.pop("suffix", "")
            if len(cards) != 0:
                raise CardSpecificationError()
            self.find_and_move_all_cards(prefix, suffix)
        elif isinstance(cards, dict):
            for k, v in cards.items():
                MG5Card(k, v).write(os.path.join(self.dir_name, 'Cards'))
        else:
            raise CardSpecificationError()
        print()

    def find_and_move_all_cards(self, prefix, suffix):
        if not re.match(r'.*[/_-]'):
            prefix = prefix + "_"
        if suffix:
            suffix = "_" + suffix + ".dat"
        else:
            suffix = ".dat"

        for k in ["param_card", "run_card", "pythia_card", "pythia8_card", "pgs_card",
                  "delphes_card", "grid_card", "plot_card", "delphes_trigger"]:
            source = prefix + k + suffix
            target = os.path.join(self.dir_name, 'Cards', k + ".dat")
            if os.path.isfile(source):
                shutil.copy(source, target)
                MG5Helper.notice("Card: {} -> {}".format(source, target))

    def launch(self, laststep='parton', cards=None, run_name=""):
        laststep = laststep.lower()
        if not (laststep in self.LASTSTEPS):
            raise InvalidLaunchError
        self.move_cards(cards)

        mg5cmd = ['set automatic_html_opening False']
        # ----------------
        # Apr 4 2016 SI: MSSM process seems to prefer 'launch' even for
        #                decay? so, 'generate_events' only for non-MSSM models?
        # if self.is_process_decay():
        if False:
            # ----------------
            mg5cmd.append('generate_events -f --multicore')
            program = os.path.join(self.dir_name, 'bin', 'madevent')
        else:
            mg5cmd.append('launch {dir_name} {run_name} -f --multicore --laststep={laststep}'.format(
                dir_name=self.dir_name,
                run_name='--name=' + run_name if run_name else '',
                laststep=laststep))
            program = self.mg5.mg5bin

        with tempfile.NamedTemporaryFile(mode='w', prefix='tmp.mg5lnc.', dir='.', delete=False) as f:
            f.write('\n'.join(mg5cmd))

        cmd = [program, os.path.basename(f.name)]  # fine because tmpfile is at '.'
        MG5Helper.info('EXEC: ' + ' '.join(cmd))
        output = subprocess.Popen(cmd, env=dict(os.environ, LANG='C'), stdout=subprocess.PIPE)

        log = []
        while True:
            line = output.stdout.readline()
            if not line:
                break
            print(line, end="")
            log.append(line)

        # TODO: Is there any way to check if the launch succeeds?

        os.remove(f.name)
        return ''.join(log)


# sub is_process_decay{
#   my ($dir) = shift;
#   open(PROC, "$dir/Cards/proc_card_mg5.dat");
#   foreach(<PROC>){
#     print $_;
#     if (/^\s*generate\s*(.*?)\s*>\s*(.*)/i){
#       return ($1 !~ / /);
#     }
#   }
#   close(PROC);
#   error("fail detecting the process.");
# }
#
# #==============================================================================#
# # Output scrape                                                                #
# #==============================================================================#
# sub cs_fb{
#   my ($cs_fb, $cserr_fb) = (-1, -1);
#   foreach(@_){
#     if(/^\s*cross.section\s*:\s*([0-9\.e\+\-]*) \+- ([0-9\.e\+\-]*)\s+(pb|fb)\s*$/i){
#       if($cs_fb != -1){
#         warning("Cross section line might appear twice.");
#       }
#       ($cs_fb, $cserr_fb) = ($1, $2);
#       if($3 =~ /pb/i){
#         $cs_fb    *= 1000;
#         $cserr_fb *= 1000;
#       }
#     }
#   }
#   if($cs_fb == -1){
#     warning("Cross section line cannot be found.");
#   }
#   return ($cs_fb, $cserr_fb);
# }


if __name__ == '__main__':
    MG5Run.help()
    sys.exit(1)
