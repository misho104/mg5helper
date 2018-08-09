#!env python3
# -*- coding: utf-8 -*-
# Time-Stamp: <2018-08-09 23:11:51>

"""mg5_helper.py: a wrapper module for MadGraph 5."""

import os
import pathlib
import shutil
import textwrap
from typing import Mapping, Union, Optional, List, Tuple

import mg5helper.exceptions as exceptions
import mg5helper.utility as utility
from mg5helper.utility import logger

__version__ = '2.0.0alpha1'
__date__ = '9 Aug 2018'
__author__ = 'Sho Iwamoto / Misho'
__license__ = 'MIT'
__status__ = 'Development'


class MG5():
    PATH = None                                          # type: Union[pathlib.Path, None]
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

    def __init__(self, mg5bin: Union[pathlib.Path, str, None]=None, output_force: Optional[bool]= None)->None:
        mg5bin = shutil.which(str(mg5bin)) if mg5bin else None
        self.mg5bin = pathlib.Path(mg5bin) if mg5bin else self.__mg5bin_default()  # type: Optional[pathlib.Path]
        self.output_force = output_force                                           # type: Optional[bool]

    def run_command(self, cmd: str)->Tuple[str, str]:
        with utility.shell_cmd('{} <<_EOF_'.format(self.mg5bin)) as f:
            f.stdin.write(cmd)
            f.stdin.write('\n_EOF_\n')
            stdout = f.run()
        return stdout

    def output(self, *args, **kwargs):
        obj = MG5Output(*args, **kwargs)
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
               cards: Optional[Mapping[str, 'MG5Card']]=dict(),
               name: str='',
               laststep: str = '',
               options: str='--multicore')->None:

        for k, v in cards.items():
            output.set_card(k, v)
        self.run_command('launch {dir} {name_tag} {last_tag} {options} -f'.format(
            dir=output.path,
            name_tag='--name='+name if name else '',
            last_tag='--laststep='+laststep if laststep else '',
            options=options
        ))


class MG5Output:
    def __init__(self,
                 process: Union[str, List[str]],
                 path: Union[str, pathlib.Path],
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
    def path(self, path: Union[pathlib.Path, str])->None:
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

    def set_card(self, card_name: str, card: 'MG5Card')->None:
        if not self.path.is_dir():
            raise exceptions.OutputNotPreparedError

        if card_name in utility.cards_abbrev:
            card_name = utility.cards_abbrev[card_name]
        destination = self.path / card_name

        with open(card.path) as fi:
            template = fi.read()
        text = template % card.replace_pattern
        with open(destination) as fo:
            fo.write(text)

    def launch(self,
               cards: Optional[Mapping[str, 'MG5Card']]=dict(),
               name: str='',
               laststep: str = '',
               options: str='--multicore')->None:
        if self.mg5 is None:
            logger.debug('New mg5 instance is created.')
            self.mg5 = MG5()
        self.mg5.launch(output=self, cards=cards, name=name, laststep=laststep, options=options)


class MG5Card:
    def __init__(self, path: Union[str, pathlib.Path], replace_pattern: Optional[Mapping] = None)->None:
        self.path = path
        self.replace_pattern = replace_pattern

    @property
    def path(self)->pathlib.Path:
        return self._path

    @path.setter
    def path(self, path: Union[pathlib.Path, str])->None:
        self._path = pathlib.Path(path)
        if not self._path.is_file():
            raise FileNotFoundError(self._path)
