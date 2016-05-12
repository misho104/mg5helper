#!/usr/bin/perl
### Time-Stamp: <2016-04-04 21:50:47 misho>

package mg5;
use strict;
use warnings;
if($0 eq __FILE__){ help(); }

use File::Temp qw/ tempfile /;

our $MG5BIN       = "$ENV{'HEP_MG5'}/bin/mg5_aMC";
our $OUTPUT_FORCE = 0;

#==============================================================================#
# Executions                                                                   #
#==============================================================================#
sub output{
  my ($process, $dir, $model, $extra, $force_mode) = @_;

  help() unless $process and $dir;
  $model      ||= "";
  $extra      ||= "";
  $force_mode ||= 0;

  if(-d $dir){
    unless($OUTPUT_FORCE || $force_mode){
      print "Directory [$dir] exists. Overwrite? [y/N] (3 sec)\n  > ";
      my $input = timeout_input(3);
      if($input =~ /^\s*y\s*$/i){ $force_mode = 1; }
    }
    if($OUTPUT_FORCE or $force_mode){
      `rm -rf $dir`;
    }else{
      print "\nOutput prevented.\n\n";
      sleep 1;
      return;
    }
  }

  my ($fh, $filename) = tempfile("tmp.XXXX");

  print $fh "import model $model\n" if $model;

  if (ref($extra) eq 'ARRAY'){
    foreach(@$extra){
      print $fh $_, "\n";
    }
  }else{
    print $fh $extra, "\n" if $extra;
  }

  if (ref($process) eq 'ARRAY') {
    my $i = 0;
    foreach(@$process){
      print $fh (++$i == 1 ? "generate" : "add process") . " $_ " . '@' . "$i\n";
    }
  }else{
    print $fh "generate $process\n";
  }
  print $fh "output $dir -f\n";
  close $fh;
  system("LANG=C $MG5BIN $filename");
  unlink($filename);
}

sub move_cards{
  my ($dir, $cards) = @_;
  my %c = find_cards($cards);
  foreach(keys(%c)){
    my $card = get_card_name($_);
    my $output = "$dir/Cards/$card";

    unlink($output) if -e $output;

    my $msg;
    if(ref($c{$_}) eq 'ARRAY' and @{$c{$_}} == 2){
      my ($template, $rules) = @{$c{$_}};
      manipulate_card($template, $output, $rules);
      $msg = "$template with " . manipulate_card_rules_to_text($rules);
    }elsif(ref($c{_}) eq ''){
      my $cmd = "cp -Lf " . $c{$_} . " $output";
      system($cmd) unless $c{$_} eq "-";
      if($?){
        error("fail in moving a card. the command tried to execute is:\n\t".$cmd);
      }
      $msg = $c{$_};
    }else{
      error("invalid card options");
    }
    info(uc($card)." : $msg");
  }
}

sub launch{
  my($dir, $laststep, $cards, $runname) = @_;

  help() unless $dir;
  error("Directory $dir not found.") unless -d $dir;

  $laststep = $laststep ? lc($laststep) : "auto";
  help() unless $laststep =~ /^(auto)|(parton)|(pythia)|(pgs)|(delphes)$/;
  $laststep = is_process_decay($dir) ? "" : "--laststep=$laststep";
  $runname = $runname ? "--name=$runname" : "";

  move_cards($dir, $cards);

  # --- launch
  my ($cmd, $program);
# Apr 4 2016 SI: MSSM process seems to prefer 'launch' even for decay? 'generate_events' for other models?
#   if(is_process_decay($dir)){
#     $cmd = <<_EOC_;
# set automatic_html_opening False
# generate_events -f --multicore
# _EOC_
#     $program = "$dir/bin/madevent";
#   }else{
    $cmd = <<_EOC_;
set automatic_html_opening False
launch $dir --force $runname --multicore $laststep
_EOC_
    $program = $MG5BIN;
#   }
  my ($fh,  $filename)    = tempfile("tmp.XXXX");
  print $fh $cmd;
  close $fh;

  open LAUNCH, "LANG=C $program $filename |" or die $!;
  my @launch_log;
  while(<LAUNCH>){
    print $_;
    push(@launch_log, $_);
  }
  unlink($filename);
  return @launch_log;
}

sub is_process_decay{
  my ($dir) = shift;
  open(PROC, "$dir/Cards/proc_card_mg5.dat");
  foreach(<PROC>){
    print $_;
    if (/^\s*generate\s*(.*?)\s*>\s*(.*)/i){
      return ($1 !~ / /);
    }
  }
  close(PROC);
  error("fail detecting the process.");
}

#==============================================================================#
# Card manipulation                                                            #
#==============================================================================#
sub find_cards{
  my $cards = $_[0] || "";
  my %c = ();
  my $mode = "";
  my ($prefix, $suffix) = ("", "");

  if(ref($cards) eq 'HASH'){
    foreach(keys(%$cards)){
      my $a = lc($_);
      if($a eq 'prefix' or $a eq 'suffix'){
        error('invalid cards specified.') if $mode eq 'HASH';
        $mode = 'STRING';
        $prefix = $cards->{'prefix'} if $a eq 'prefix';
        $suffix = $cards->{'suffix'} if $a eq 'suffix';
      }else{
        error('invalid cards specified.') if $mode eq 'STRING';
        $mode = 'HASH';
      }
    }
  }elsif(ref($cards) eq ''){
    ($mode, $prefix, $suffix) = ('STRING', $cards, "");
  }else{
    error('invalid cards specified.');
  }

  if($mode eq 'HASH'){
    foreach(keys(%$cards)){
      my $fn = ref($cards->{$_}) eq 'ARRAY' ? $cards->{$_}->[0] : $cards->{$_};
      my $c = get_card_name($_);
      error  ("invalid card name ${_}.") unless $c;
      error  (uc($c)." [$fn] not found.") unless $fn eq "-" or -f $fn;
    }
    %c = %$cards;
  }else{
    my $p = $prefix !~ /[\/_-]$/ ? $prefix : $prefix."_";
    my $s = $suffix ? "_$suffix.dat" : ".dat";
    foreach(`ls $p*$s 2>/dev/null`){
      chomp;
      next unless $_ =~ /^$p(.*)$s/;
      my $key = ($1 eq 'delphes_trigger') ? 'trigger' : ($1 =~ /^([a-z]+)_card$/) ? $1 : "";

      my $card = get_card_name($key);
      unless($card){
        warning("file [$_] cannot be recognized and ignored.");
        next;
      }
      warning("file [$_] found. so used as ".uc($card).".");
      $c{$key} = $_;
    }
  }
  return %c;
}

sub get_card_name{
  my $c = lc($_[0]||"");
  if($c =~ /^(param|run|pythia|pgs|delphes|grid|plot)$/){
    return "${c}_card.dat";
  }elsif($c eq 'trigger'){
    return "delphes_trigger.dat";
  }
  return "";
}

sub manipulate_card{
  my ($in, $out, @args) = @_;
  open(my $out_fh, ">$out");
  manipulate_card_sub($in, $out_fh, manipulate_card_rules(@args));
  close($out_fh);
}

sub manipulate_card_sub{
  my ($in, $out_fh, $rules) = @_;
  my $in_fh;
  if($in =~ /^\*\w+::DATA$/){
    $in_fh = $in;
  }else{
    open($in_fh, $in) || die "$in not found";
  }
  foreach(<$in_fh>){
    s/<<<+%([\w\-\.]+) *>>>+/
      if(exists($rules->{$1})){
        my $v = $rules->{$1};
        my $spacing = length($&) - length($v);
        $spacing = 0 if $spacing < 0;
        print "Replacing ::  %$1 => $v\n";
        (" "x$spacing).$v;
      }else{
        error("Cannot replace $&");
      }
    /eg;
    print $out_fh $_;
  }
  close($in_fh);
}

sub generate_temporal_card{
  my ($in, @args) = @_;
  my ($fh, $filename) = tempfile("tmp_XXXX", SUFFIX => '.dat');
  manipulate_card_sub($in, $fh, manipulate_card_rules(@args));
  close $fh;
  return $filename;
}

sub manipulate_card_rules{
  if(@_ == 1 and ref($_[0]) eq 'HASH'){
    return $_[0];
  }
  my @rule_list = (@_ == 1 and ref($_[0]) eq 'ARRAY') ? @{$_[0]} : @_;
  foreach(@rule_list){
    if(ref($_)){
      error("Invalid replace rule. Rule should be a hash, an array, or a list of scalar values.");
    }
  }
  my $rules = {};
  for(0..$#rule_list){
    $rules->{1+$_} = $rule_list[$_];
  }
  return $rules;
}

sub manipulate_card_rules_to_text{
  my $rules = manipulate_card_rules($_[0]);
  return '{' . join(", ", map{"$_ => $rules->{$_}"} sort keys %$rules) . "}";
}

#==============================================================================#
# Output scrape                                                                #
#==============================================================================#
sub cs_fb{
  my ($cs_fb, $cserr_fb) = (-1, -1);
  foreach(@_){
    if(/^\s*cross.section\s*:\s*([0-9\.e\+\-]*) \+- ([0-9\.e\+\-]*)\s+(pb|fb)\s*$/i){
      if($cs_fb != -1){
        warning("Cross section line might appear twice.");
      }
      ($cs_fb, $cserr_fb) = ($1, $2);
      if($3 =~ /pb/i){
        $cs_fb    *= 1000;
        $cserr_fb *= 1000;
      }
    }
  }
  if($cs_fb == -1){
    warning("Cross section line cannot be found.");
  }
  return ($cs_fb, $cserr_fb);
}

#==============================================================================#
# Logs, Messages, Small tools                                                  #
#==============================================================================#
sub log_and_err{
  if(-f "MG5_PM_LOG"){
    open(LOG, ">>MG5_PM_LOG"); print LOG $_[0]; close(LOG);
  }
  print STDERR $_[0];
}

sub error   { die "[ERROR] $_[0]"; }
sub warning { log_and_err("[WARNING] $_[0]\n"); }
sub info    { log_and_err("[INFO] $_[0]\n"); }

sub timeout_input{
  my $limit = $_[0];
  my $input_string = "";
  eval {
    local $SIG{ALRM} = sub { die "timeout" };
    alarm $limit;
    $input_string = <STDIN>;
    alarm 0;
    chomp $input_string;
  };
  if ($@) {
    if ($@ =~ /timeout/) {
      return "";
    } else {
      alarm 0;
      die $@;
    }
  }
  return $input_string;
}

sub help{
  die <<_HELP_;

Usage: output(process(es), directory, [model])
       launch(directory, [laststep], [cards], [runname])

       process can be an ARRAY.

       model    ||= 'sm'
       laststep ||= 'auto'  [auto|parton|pythia|pgs|delphes]

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

       runname  ||= 'run_XX'

_HELP_
}

1;
