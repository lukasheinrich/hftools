#!/usr/bin/env python

import ROOT
ROOT.gROOT.SetBatch(True)
import yaml
from brewer2mpl import qualitative
import itertools
import click
import os
import re
from xml.etree import ElementTree as etree

def get_workspace(rootfile,workspace):
    click.secho('getting workspace',fg = 'green')
    ws = rootfile.Get(str(workspace))
    if not ws:
        print workspace
        print rootfile.ls()
        raise click.ClickException('Could not find workspace in file')
    return ws

def get_all_comps(funcs,obs,channel):
    it = funcs.iterator()
    regex = re.compile('L_{}_(.*)_{}_overallSyst'.format(obs,channel))
    allcomps = []
    for i in range(funcs.getSize()):
        v = it.Next()
        m = regex.match(v.GetName())
        if m:
            allcomps += [m.group(1)]
    return allcomps

def get_funcname(funcs,obs,component,channel):
    it = funcs.iterator()
    funcname = None
    print 'number of funcs',funcs.getSize()
    for i in range(funcs.getSize()):
        v = it.Next()
        if v.GetName().startswith('L_{}_{}_{}'.format(obs,component,channel)):
            funcname = v.GetName()
            return funcname
    return funcname

def get_datahist(data,obsvar,channel):
    reduced = data.reduce('channelCat == channelCat::{}'.format(channel))
    varlist = ROOT.RooArgList()
    varlist.add(obsvar)
    datahist = obsvar.createHistogram('data_{}'.format(channel))
    datahist = reduced.fillHistogram(datahist,varlist)
    datahist.Sumw2(0)
    datahist.SetMarkerStyle(20);
    datahist.SetLineColor(ROOT.kBlack)
    return datahist

def diff_hist(lhs,rhs):
    result.one.Clone()
    result.Add(rhs,-1)

def get_weighted_histos(ws,channel,obs,components,filename):
    obsname='obs_{}_{}'.format(obs,channel)
    obsobj = ws.var(obsname)
    binwidth = obsobj.getBinWidth(1) #assume equally spaced histos

    return_data = {
        'data':None,
        'model':{}
    }


    frame = obsobj.frame()

    data = ws.data('obsData')
    reduced = data.reduce('channelCat == channelCat::{}'.format(channel))

    funcs = ws.allFunctions()

    datahist = get_datahist(data,obsobj,channel)
    return_data['data'] = datahist

    for component in components:
        funcname=get_funcname(funcs,obs,component,channel)
        function = ws.function(funcname)
        histogram = function.createHistogram(obsname)
        histogram.Scale(1./binwidth)
        print 'sow',component,':',histogram.GetSumOfWeights()
        return_data['model'][component] = histogram

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
        print 'adding to stack',component,plotcomp.GetSumOfWeights()
        comphists += [(component,plotcomp)]
        stack.Add(plotcomp)

    width,height = map(int,dimensions.split('x'))
    c = ROOT.TCanvas('c','c',width,height)
    datahist = weighted_hists['data']
    frame = datahist.Clone()
    frame.Reset('ICE')
    frame.SetTitle(title or '')
    frame.GetYaxis().SetRangeUser(100,datahist.GetMaximum()*1.5)
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
    it = mc.GetNuisanceParameters().iterator()
    v = it.Next()
    parpoint = {}

    def write(v):
        if justvalues:
            parpoint[v.GetName()] = v.getVal()
        else:
            parpoint[v.GetName()] = {'min':v.getMin(),'max':v.getMax(),'defval':v.getVal()}

    while v:
        write(v)
        v = it.Next()

    v = mc.GetParametersOfInterest().iterator().Next()
    print "POI: {}".format(v)
    write(v)

    with open(output,'w') as results:
        results.write(yaml.dump(parpoint,default_flow_style = False))

def get_path(basedir,relpath):
    return '{}/{}'.format(basedir,relpath.split('./',1)[-1])

def parse_histfactory_xml(toplvlxml):
    dirname = os.path.abspath(os.path.dirname(toplvlxml))
    histfithome = dirname.split('/config')[0]

    p = etree.parse(toplvlxml)
    channels =  [etree.parse(open(get_path(histfithome,inpt.text))).findall('.')[0] for inpt in p.findall('Input')]

    parsed_data = {
        'Combination':{
            'Prefix':p.findall('.')[0].attrib['OutputFilePrefix'].split('./',1)[-1],
            'Measurements':[ {'name':x.attrib['Name'] for x in p.findall('Measurement')}]
        }
    }

    channel_info = []
    for input_tag in p.findall('Input'):
        channel_xml = etree.parse(open(get_path(histfithome,input_tag.text)))
        channel_name = channel_xml.findall('.')[0].attrib['Name']
        sample_names = [x.attrib['Name'] for x in channel_xml.findall('Sample')]
        channel_info += [{'name':channel_name,'samples':sample_names}]

    parsed_data['Combination']['Inputs'] = channel_info
    return parsed_data


@click.group()
def toplevel():
    pass

@toplevel.command()
@click.argument('toplvlxml')
@click.argument('output')
def dump_information(toplvlxml,output):
    parsed_data = parse_histfactory_xml(toplvlxml)
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
    for name,val in parpoint_data.iteritems():
        ws.var(name).setVal(val)

    complist = get_all_comps(ws.allFunctions(),observable,channel) if components == 'all' else components.split(',')
    print complist
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
    ws.pdf('simPdf').fitTo(ws.data('obsData'),
        ROOT.RooFit.Extended(True),
        ROOT.RooFit.Save(True),
        ROOT.RooFit.Minimizer("Minuit","Migrad"),
        ROOT.RooFit.Offset(True)
    )
    save_pars(ws,output,True)


if __name__=='__main__':
  toplevel()
