#!env python3
# -*- coding: utf-8 -*-
# Time-Stamp: <2017-01-21 14:26:24>

"""mg5_helper.py: a wrapper module for MadGraph 5."""

from __future__ import absolute_import, division, print_function, unicode_literals

import os
import sys
import shutil
import time
import textwrap
import select
import tempfile
import subprocess

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
    def timeout_input(cls, prompt="", timeout=3):
        print(prompt, end="")
        sys.stdout.flush()
        i, o, e = select.select([sys.stdin], [], [], timeout)
        return sys.stdin.readline().strip() if i else ""


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

                cards : ""     => cards in current directory are used.
                        STRING => interpreted as a prefix. i.e. "STRING_run_card.dat" etc.
                        HASH   => {'param' => 'param_card.dat',
                                   'run'   => 'run_card.dat',
                                   'plot'  => 'plot_card.dat, ... }
                                  [param,run,pythia,pgs,delphes,plot,grid,...]
                                    any keys are accepted.
                                  Card names can be an array [TEMPLATE, rules],
                                    where rules is a manipulation rule (array or hash).

                        OR
                             {'prefix' => 'xxx', 'suffix' => 'yyy'}
                             is equivalent to the STRING case.

                runname  ||= 'run_XX'"""))

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
            mg5cmd.append("{cmd} {proc} @ {i}".format(
                cmd=("generate" if i == 1 else "add process"),
                proc=proc,
                i=i + 1))  # i is zero-origin
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
        pass

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


# sub move_cards{
#   my ($dir, $cards) = @_;
#   my %c = find_cards($cards);
#   foreach(keys(%c)){
#     my $card = get_card_name($_);
#     my $output = "$dir/Cards/$card";
#
#     unlink($output) if -e $output;
#
#     my $msg;
#     if(ref($c{$_}) eq 'ARRAY' and @{$c{$_}} == 2){
#       my ($template, $rules) = @{$c{$_}};
#       manipulate_card($template, $output, $rules);
#       $msg = "$template with " . manipulate_card_rules_to_text($rules);
#     }elsif(ref($c{_}) eq ''){
#       my $cmd = "cp -Lf " . $c{$_} . " $output";
#       system($cmd) unless $c{$_} eq "-";
#       if($?){
#         error("fail in moving a card. the command tried to execute is:\n\t".$cmd);
#       }
#       $msg = $c{$_};
#     }else{
#       error("invalid card options");
#     }
#     info(uc($card)." : $msg");
#   }
# }
#
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
# # Card manipulation                                                            #
# #==============================================================================#
# sub find_cards{
#   my $cards = $_[0] || "";
#   my %c = ();
#   my $mode = "";
#   my ($prefix, $suffix) = ("", "");
#
#   if(ref($cards) eq 'HASH'){
#     foreach(keys(%$cards)){
#       my $a = lc($_);
#       if($a eq 'prefix' or $a eq 'suffix'){
#         error('invalid cards specified.') if $mode eq 'HASH';
#         $mode = 'STRING';
#         $prefix = $cards->{'prefix'} if $a eq 'prefix';
#         $suffix = $cards->{'suffix'} if $a eq 'suffix';
#       }else{
#         error('invalid cards specified.') if $mode eq 'STRING';
#         $mode = 'HASH';
#       }
#     }
#   }elsif(ref($cards) eq ''){
#     ($mode, $prefix, $suffix) = ('STRING', $cards, "");
#   }else{
#     error('invalid cards specified.');
#   }
#
#   if($mode eq 'HASH'){
#     foreach(keys(%$cards)){
#       my $fn = ref($cards->{$_}) eq 'ARRAY' ? $cards->{$_}->[0] : $cards->{$_};
#       my $c = get_card_name($_);
#       error  ("invalid card name ${_}.") unless $c;
#       error  (uc($c)." [$fn] not found.") unless $fn eq "-" or -f $fn;
#     }
#     %c = %$cards;
#   }else{
#     my $p = $prefix !~ /[\/_-]$/ ? $prefix : $prefix."_";
#     my $s = $suffix ? "_$suffix.dat" : ".dat";
#     foreach(`ls $p*$s 2>/dev/null`){
#       chomp;
#       next unless $_ =~ /^$p(.*)$s/;
#       my $key = ($1 eq 'delphes_trigger') ? 'trigger' : ($1 =~ /^([a-z]+)_card$/) ? $1 : "";
#
#       my $card = get_card_name($key);
#       unless($card){
#         warning("file [$_] cannot be recognized and ignored.");
#         next;
#       }
#       warning("file [$_] found. so used as ".uc($card).".");
#       $c{$key} = $_;
#     }
#   }
#   return %c;
# }
#
# sub get_card_name{
#   my $c = lc($_[0]||"");
#   if($c =~ /^(param|run|pythia|pgs|delphes|grid|plot)$/){
#     return "${c}_card.dat";
#   }elsif($c eq 'trigger'){
#     return "delphes_trigger.dat";
#   }
#   return "";
# }
#
# sub manipulate_card{
#   my ($in, $out, @args) = @_;
#   open(my $out_fh, ">$out");
#   manipulate_card_sub($in, $out_fh, manipulate_card_rules(@args));
#   close($out_fh);
# }
#
# sub manipulate_card_sub{
#   my ($in, $out_fh, $rules) = @_;
#   my $in_fh;
#   if($in =~ /^\*\w+::DATA$/){
#     $in_fh = $in;
#   }else{
#     open($in_fh, $in) || die "$in not found";
#   }
#   foreach(<$in_fh>){
#     s/<<<+%([\w\-\.]+) *>>>+/
#       if(exists($rules->{$1})){
#         my $v = $rules->{$1};
#         my $spacing = length($&) - length($v);
#         $spacing = 0 if $spacing < 0;
#         print "Replacing ::  %$1 => $v\n";
#         (" "x$spacing).$v;
#       }else{
#         error("Cannot replace $&");
#       }
#     /eg;
#     print $out_fh $_;
#   }
#   close($in_fh);
# }
#
# sub generate_temporal_card{
#   my ($in, @args) = @_;
#   my ($fh, $filename) = tempfile("tmp_XXXX", SUFFIX => '.dat');
#   manipulate_card_sub($in, $fh, manipulate_card_rules(@args));
#   close $fh;
#   return $filename;
# }
#
# sub manipulate_card_rules{
#   if(@_ == 1 and ref($_[0]) eq 'HASH'){
#     return $_[0];
#   }
#   my @rule_list = (@_ == 1 and ref($_[0]) eq 'ARRAY') ? @{$_[0]} : @_;
#   foreach(@rule_list){
#     if(ref($_)){
#       error("Invalid replace rule. Rule should be a hash, an array, or a list of scalar values.");
#     }
#   }
#   my $rules = {};
#   for(0..$#rule_list){
#     $rules->{1+$_} = $rule_list[$_];
#   }
#   return $rules;
# }
#
# sub manipulate_card_rules_to_text{
#   my $rules = manipulate_card_rules($_[0]);
#   return '{' . join(", ", map{"$_ => $rules->{$_}"} sort keys %$rules) . "}";
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
