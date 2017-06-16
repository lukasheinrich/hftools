import ROOT
import numpy as np
import math
from brewer2mpl import qualitative
import itertools
from .. import utils as hfutils

import logging
log = logging.getLogger(__name__)

def combine_graphs(graphs,positionhist):
    '''
    return combined band of bands summed in quadrature for each bin

    :param graphs: list of TGraph objects
    :param positionhist: Histogram that controls the y-position of resulting graph
    :return: combined TGraph object
    '''
    result = graphs[0].Clone()
    for i in range(result.GetN()):
        x,y = np.array([0],dtype = float),np.array([0],dtype = float)
        result.GetPoint(i,x,y)

        total_widths = [g.GetErrorYhigh(i)+g.GetErrorYlow(i) for g in graphs]
        total_error = math.sqrt(sum(w**2 for w in total_widths))
    
        position = positionhist.GetBinContent(positionhist.FindBin(x))

        result.SetPoint(i,x,position)
        result.SetPointEYhigh(i,total_error/2.0)
        result.SetPointEYlow(i,total_error/2.0)
    return result

def _getlegend(*args,**kwargs):
    legend = ROOT.TLegend(*args)
    legend.SetShadowColor(kwargs.get('shadow',0))
    legend.SetFillColor(kwargs.get('fill',0))
    legend.SetFillStyle(kwargs.get('fillstyle',4000))
    legend.SetLineColor(kwargs.get('line',0))
    legend.SetTextFont(kwargs.get('font',43))
    legend.SetTextColor(kwargs.get('fontcolor',ROOT.kBlack))
    legend.SetTextSize(kwargs.get('fontsize',20))
    return legend

def quickplot(ws,channel,obs,components,filename,title,xaxis,yaxis,singlebin,dimensions,logy):
    '''
    :param ws: a HistFactory workspace
    :return: None
    '''
    weighted_hists = {
        'data': hfutils.extract_data(ws,channel,obs),
        'model':{c: hfutils.extract(ws,channel,obs,c) for c in components}
    }

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

    l = _getlegend(x,y,x+0.1,y+linewidth*(len(comphists)+1), fontsize = 15)
    l.AddEntry(datahist,'data','pl')
    for comp,h in reversed(comphists):
        l.AddEntry(h,comp,'f')

    l.Draw()
    c.SaveAs(filename)