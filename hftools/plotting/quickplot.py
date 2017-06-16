#!/usr/bin/env python

import ROOT
ROOT.gROOT.SetBatch(True)
import yaml
from brewer2mpl import qualitative
import itertools
import click
import os
from .. import utils as hfutils
from ..utils.parsexml import parse
from .. import fitting as hffit

import logging
log = logging.getLogger(__name__)


logging.basicConfig()

def get_workspace(rootfile,workspace):
    click.secho('getting workspace',fg = 'green')
    ws = rootfile.Get(str(workspace))
    if not ws:
        raise click.ClickException('Could not find workspace in file')
    return ws

def get_weighted_histos(ws,channel,obs,components,filename):

    return_data = {
        'data':None,
        'model':{}
    }

    return_data['data'] = hfutils.extract_data(ws,channel,obs)
    for component in components:
        return_data['model'][component] = hfutils.extract(ws,channel,obs,component)

    return return_data

def getlegend(*args, **kwargs):
  legend = ROOT.TLegend(*args)
  legend.SetShadowColor(kwargs.get('shadow',0))
  legend.SetFillColor(kwargs.get('fill',0))
  legend.SetFillStyle(kwargs.get('fillstyle',4000))
  legend.SetLineColor(kwargs.get('line',0))
  legend.SetTextFont(kwargs.get('font',43))
  legend.SetTextColor(kwargs.get('fontcolor',ROOT.kBlack))
  legend.SetTextSize(kwargs.get('fontsize',20))
  return legend

def plot(ws,channel,obs,components,filename,title,xaxis,yaxis,singlebin,dimensions,logy):
    weighted_hists = get_weighted_histos(ws,channel,obs,components,filename)

    stack = ROOT.THStack()
    colormap = qualitative.Paired.get(len(components),None)
    if not colormap:
        colormap = qualitative.Paired['max']
    colors = colormap.hex_colors

    comphists = []
    for color,component in zip(itertools.cycle(colors),components):
        plotcomp = weighted_hists['model'][component].Clone()
        plotcomp.SetFillColor(ROOT.TColor.GetColor(color))
        plotcomp.SetLineColor(ROOT.kBlack)
        log.info('adding to stack',component,plotcomp.GetSumOfWeights())
        comphists += [(component,plotcomp)]
        stack.Add(plotcomp)

    width,height = map(int,dimensions.split('x'))
    c = ROOT.TCanvas('c','c',width,height)
    datahist = weighted_hists['data']
    datahist.SetMarkerStyle(20);
    datahist.SetLineColor(ROOT.kBlack)


    frame = datahist.Clone()
    frame.Reset('ICE')
    frame.SetTitle(title or '')
    frame.GetYaxis().SetRangeUser(0,datahist.GetMaximum()*1.5)
    frame.GetYaxis().SetTitleOffset(1.4)


    frame.GetXaxis().SetRangeUser(0,500)

    frame.GetYaxis().SetTitle(yaxis or '')

    if singlebin:
        frame.GetXaxis().SetBinLabel(1,xaxis or '')
        frame.GetXaxis().SetTitle('')
    else:
        frame.GetXaxis().SetTitle(xaxis or '')

    if logy:
        c.SetLogy()

    frame.Draw()
    ROOT.gStyle.SetOptStat(0)
    stack.Draw('histsame')
    datahist.Draw('sameE0')

    x, y, linewidth = 0.7, 0.7, 0.03

    l = getlegend(x,y,x+0.1,y+linewidth*(len(comphists)+1), fontsize = 15)
    l.AddEntry(datahist,'data','pl')
    for comp,h in reversed(comphists):
        l.AddEntry(h,comp,'f')

    l.Draw()
    c.SaveAs(filename)

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

def get_path(basedir,relpath):
    return '{}/{}'.format(basedir,relpath.split('./',1)[-1])


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
    plot(ws,channel,observable,complist,output,title,xaxis,yaxis,singlebin,dimensions,logy)


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
    save_pars(ws,output,False)


if __name__=='__main__':
  toplevel()
