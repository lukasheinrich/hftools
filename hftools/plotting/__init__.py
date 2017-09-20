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


def make_band_root(up,down,nominal,binmin = 0,binmax = 1):
    '''
    creates a TGraph error band from three histograms

    :param up: the upward variation
    :param down: the downward variation
    :param nominal: the nominal histogram, used to position the band vertically
    :return: the TGraph band
    '''
    g = ROOT.TGraphAsymmErrors(nominal.GetNbinsX())
    for i in range(1,nominal.GetNbinsX()+1):
        x_nom = nominal.GetBinCenter(i)
        x_lo = nominal.GetBinLowEdge(i)
        x_hi = nominal.GetBinLowEdge(i)+nominal.GetBinWidth(i)
        assert x_nom

        y_nom,y_up,y_down = [x.GetBinContent(i) for x in [nominal,up,down]]

        binwidth = x_hi-x_lo
        center = x_lo + binwidth*(binmax-binmin)/2.0
        left   = x_lo + binwidth*binmin
        right  = x_lo + binwidth*binmax

        g.SetPoint(i-1,center,y_nom)
        g.SetPointEXhigh(i-1,right-center)
        g.SetPointEXlow(i-1,center-left)
        g.SetPointEYhigh(i-1,y_up-y_nom)
        g.SetPointEYlow(i-1,y_nom-y_down)
    return g

def quickplot(ws,channel,obs,components,filename,title,xaxis,yaxis,singlebin,dimensions,logy):
    '''
    :param ws: a HistFactory workspace
    :param channel: a channel name
    :param obs: an observable name
    :param components: a list of components to plots (plot will respect order given here)
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


    # frame.GetXaxis().SetRangeUser(0,500)

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