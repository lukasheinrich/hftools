#!/usr/bin/env python

import ROOT
ROOT.gROOT.SetBatch(True)
import yaml
import click
import os
from ..utils.parsexml import parse
from .. import fitting as hffit
from .. import plotting as hfplot
from .. import utils as hfutils

import logging
log = logging.getLogger(__name__)


logging.basicConfig()

def get_workspace(rootfile,workspace):
    click.secho('getting workspace',fg = 'green')
    ws = rootfile.Get(str(workspace))
    if not ws:
        raise click.ClickException('Could not find workspace in file')
    return ws



def save_pars(ws,output,justvalues = False):
    mc = ws.obj('ModelConfig')

    parpoint = {}
    def write(v):
        if justvalues:
            parpoint[v.GetName()] = v.getVal()
        else:
            parpoint[v.GetName()] = {'min':v.getMin(),'max':v.getMax(),'val':v.getVal(),'err': v.getError()}

    nuis = mc.GetNuisanceParameters()
    if nuis:
        nuisit = nuis.iterator()
        v = nuisit.Next()


        while v:
            write(v)
            v = nuisit.Next()

    v = mc.GetParametersOfInterest().iterator().Next()
    write(v)

    with open(output,'w') as results:
        results.write(yaml.dump(parpoint,default_flow_style = False))

@click.group()
def toplevel():
    pass

@toplevel.command()
@click.argument('toplvlxml')
@click.argument('output')
def dump_information(toplvlxml,output):
    parsed_data = parse(toplvlxml,os.getcwd())
    with open(output,'w') as f:
        f.write(yaml.safe_dump(parsed_data,default_flow_style = False))


@toplevel.command()
@click.argument('rootfile')
@click.argument('workspace')
@click.argument('channel')
@click.argument('observable')
@click.argument('parpointfile')
@click.option('--logy/--no-logy',default = False)
@click.option('-c','--components',default = 'all')
@click.option('-o','--output',default = 'plot.pdf')
@click.option('-t','--title',default = None)
@click.option('-x','--xaxis',default = None)
@click.option('-y','--yaxis',default = None)
@click.option('--singlebin/--no-single-bin',default = False)
@click.option('-d','--dimensions',default = '600x600')
def plot_channel(rootfile,workspace,channel,observable,components,parpointfile,output,title,xaxis,yaxis,singlebin,dimensions,logy):
    f = ROOT.TFile.Open(rootfile)
    ws = get_workspace(f,workspace)

    parpoint_data = yaml.load(open(parpointfile))

    hfutils.set_pars2(ws,parpoint_data)
    complist = hfutils.samples(ws,channel) if components == 'all' else components.split(',')
    print hfplot
    hfplot.quickplot(ws,channel,observable,complist,output,title,xaxis,yaxis,singlebin,dimensions,logy)


@toplevel.command()
@click.argument('rootfile')
@click.argument('workspace')
@click.argument('output')
def write_vardef(rootfile,workspace,output):
  f = ROOT.TFile.Open(rootfile)
  ws = get_workspace(f,workspace)
  save_pars(ws,output)


@toplevel.command()
@click.argument('rootfile')
@click.argument('workspace')
@click.argument('output')
def fit(rootfile,workspace,output):
    f = ROOT.TFile.Open(rootfile)
    ws = get_workspace(f,workspace)
    result = hffit.fit(ws)
    assert result
    save_pars(ws,output,False)


if __name__=='__main__':
  toplevel()
