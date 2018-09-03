#!env python3
# -*- coding: utf-8 -*-
# Time-Stamp: <2018-09-03 16:59:42>

"""mg5_helper.py: a wrapper module for MadGraph 5."""

import os
import pathlib
import re
import shutil
import textwrap
from typing import Mapping, Union, Optional, List

import mg5helper.exceptions as exceptions
import mg5helper.utility as utility
from mg5helper.utility import logger

__version__ = '2.0.0alpha1'
__date__ = '9 Aug 2018'
__author__ = 'Sho Iwamoto / Misho'
__license__ = 'MIT'
__status__ = 'Development'

ProcessType = Union[str, List[str]]
PathType = Union[pathlib.Path, str]
CardDictType = Mapping[str, 'MG5Card']


class MG5():
    PATH = None                                          # type: Optional[pathlib.Path]
    SEARCH_PATHS = [os.environ.get('HEP_MG5', ''), '.']  # type: List[str]

    @classmethod
    def __mg5bin_default(cls)->Optional[pathlib.Path]:
        if cls.PATH and shutil.which(str(cls.PATH)):
            cls.PATH = pathlib.Path(cls.PATH)
            return cls.PATH
        for path in [''] + [p + '/bin' for p in cls.SEARCH_PATHS if p]:
            m = shutil.which('mg5_aMC', path=path or None)
            if m:
                return pathlib.Path(m)
        return None

    def __init__(self, mg5bin: Optional[PathType]=None, output_force: Optional[bool]= None)->None:
        mg5bin = shutil.which(str(mg5bin)) if mg5bin else None
        self.mg5bin = pathlib.Path(mg5bin) if mg5bin else self.__mg5bin_default()  # type: Optional[pathlib.Path]
        self.output_force = output_force                                           # type: Optional[bool]

    def run_command(self, cmd: str)->List[str]:
        with utility.shell_cmd('{} <<_EOF_'.format(self.mg5bin)) as f:
            f.stdin.write(cmd)
            f.stdin.write('\n_EOF_\n')
            stdout = f.run()
        return stdout

    def output(self, *args, **kwargs)->'MG5Output':
        return self._output(MG5Output(*args, **kwargs))

    def _output(self, obj: 'MG5Output')->'MG5Output':
        obj.mg5 = self
        if obj.path.exists():
            if not obj.path.is_dir():
                logger.warning('Path [{}] exists as non-directory; output interrupted.'.format(obj.path))

            force = obj.force
            if force is None:
                yn = utility.timeout_input('Path [{}] exists. Overwrite? [y/N] (3 sec)\n > '.format(obj.path))
                force = (yn.lower() == 'y')
            if force:
                shutil.rmtree(str(obj.path))
            else:
                logger.warning('Path [{}] exists; output interrupted as requested.'.format(obj.path))
                return obj
        self.run_command(obj.to_output_command())
        return obj

    def launch(self,
               output: 'MG5Output',
               cards: Optional[CardDictType]=None,
               name: str='',
               laststep: str = '',
               options: str='--multicore')->'MG5Launch':

        if cards:
            for k, v in cards.items():
                output.set_card(k, v)
        stdout = self.run_command(textwrap.dedent("""\
                set automatic_html_opening False
                launch {dir} {name_tag} {last_tag} {options} -f
            """.format(
            dir=output.path,
            name_tag='--name='+name if name else '',
            last_tag='--laststep='+laststep if laststep else '',
            options=options
        )))
        launch = MG5Launch.parse_output(stdout)
        launch.path = output.path
        return launch


class MG5Output:
    def __init__(self,
                 process: ProcessType,
                 path: PathType,
                 model: str='sm',
                 extra_code: Union[str, List[str]]=list(),
                 force: Optional[bool]=None,
                 )->None:
        self.process = [process] if isinstance(process, str) else process              # type: List[str]
        self.path = path
        self.model = model                                                             # type: str
        self.extra_code = [extra_code] if isinstance(extra_code, str) else extra_code  # type: List[str]
        self.force = force
        self.mg5 = None  # type: Optional[MG5]

    @property
    def path(self)->pathlib.Path:
        return self._path

    @path.setter
    def path(self, path: PathType)->None:
        self._path = pathlib.Path(path)
        if self._path.is_absolute():
            raise exceptions.AbsolutePathSpecifiedError

    def to_output_command(self)->str:
        return textwrap.dedent("""\
                import model {model}
                {extra_code}
                {generate}
                output {output_path} -f
            """.format(
            model=self.model,
            extra_code='\n'.join(self.extra_code),
            generate='generate ' + '\nadd process '.join(self.process),
            output_path=self.path,
        ))

    def output(self):
        if self.mg5 is None:
            logger.debug('New mg5 instance is created.')
            self.mg5 = MG5()
        return self.mg5._output(self)

    def set_card(self, card_name: str, card: 'MG5Card')->None:
        if not self.path.is_dir():
            raise exceptions.OutputNotPreparedError

        if card_name in utility.cards_abbrev:
            card_name = utility.cards_abbrev[card_name]
        if not re.match(r'[\w\d\.]+', card_name):
            raise ValueError(card_name)
        destination = self.path / 'Cards' / card_name

        with open(card.path) as fi:
            text = fi.read()
        if card.replace_pattern:
            text = text % card.replace_pattern
        with open(destination, 'w') as fo:
            fo.write(text)

    def launch(self,
               cards: Optional[CardDictType]=None,
               name: str='',
               laststep: str='',
               options: str='--multicore')->'MG5Launch':
        if self.mg5 is None:
            logger.debug('New mg5 instance is created.')
            self.mg5 = MG5()
        return self.mg5.launch(output=self, cards=cards, name=name, laststep=laststep, options=options)


class MG5Card:
    def __init__(self, path: PathType, replace_pattern: Optional[Mapping]=None)->None:
        self.path = path
        self.replace_pattern = replace_pattern

    @property
    def path(self)->pathlib.Path:
        return self._path

    @path.setter
    def path(self, path: PathType)->None:
        self._path = pathlib.Path(path)
        if not self._path.is_file():
            raise FileNotFoundError(self._path)


class MG5Launch:
    def __init__(self, **kwargs):
        self.run = kwargs.get('run', '')      # type: str
        # not use tag name because the output from MG5-launch seems unreliable...
        # self.tag = kwargs.get('tag', '')    # type: str
        self.xs = kwargs.get('xs', -1)        # type: float   # fb
        self.xserr = kwargs.get('xserr', -1)  # type: float   # fb
        self.nev = kwargs.get('nev', -1)      # type: int

        self.path = None                      # type: Optional[pathlib.Path]

    re_summary_line_1 = re.compile(r'\s+===\s+Results Summary for\s+run:\s+(.*?)\s+tag:\s+(.*?)\s+===')
    re_summary_line_2 = re.compile(r'\s+Cross-section:\s+([\d.de+-]+)\s+(\+- ([\d.de+-]+)\s+)(pb|fb)', re.I)
    re_summary_line_3 = re.compile(r'\s+Nb of events:\s+(\d+)', re.I)

    @classmethod
    def parse_output(cls, output: List[str])->'MG5Launch':
        obj = cls()
        for i, line in enumerate(output):
            match = cls.re_summary_line_1.match(line)
            if match:
                obj.run = match.group(1)
                # obj.tag = match.group(2)
                break
        for j in range(i+1, i+10):
            match = cls.re_summary_line_2.match(output[j])
            if match:
                if match.group(4) == 'fb':
                    normalization = 1.0
                elif match.group(4) == 'pb':
                    normalization = 1e-3
                else:
                    raise RuntimeError
                obj.xs = float(match.group(1)) * normalization
                obj.xserr = float(match.group(3)) * normalization if match.group(2) else -1
                continue
            match = cls.re_summary_line_3.match(output[j])
            if match:
                obj.nev = int(match.group(1))
                continue
        return obj

    @property
    def event_dir(self)->Optional[pathlib.Path]:
        if self.run and self.path and (self.path / 'Events').is_dir():
            event_dir = self.path / 'Events' / self.run
            decay_dirs = [f for f in (self.path / 'Events').glob(f'{self.run}*')
                          if f.is_dir() and f.name.startswith(f'{self.run}_decayed_')]
            if decay_dirs:
                return max(decay_dirs)
            elif event_dir.is_dir():
                return event_dir
        else:
            return None
