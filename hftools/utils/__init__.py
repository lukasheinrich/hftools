import ROOT
import math
import logging
log = logging.getLogger(__name__)

### Naming Conventions

def dataName():
    return "obsData"

def simulPdfName():
    return 'simPdf'

def binwidthname(obs,channel,componentindex):
    return 'binWidth_{}_{}'.format(obsname(obs,channel),componentindex)

def obsname(obs,channel):
    name='obs_{}_{}'.format(obs,channel)
    return name

def totalpdfname(channel):
    name = '{}_model'.format(channel)
    return name

def shapeGaussVarNames(sysname,binnr):
    gamma =  'gamma_{}_bin_{}'.format(sysname,binnr)
    sigma =  'gamma_{}_bin_{}_sigma'.format(sysname,binnr)
    return gamma,sigma

def shapePoissonVarNames(sysname,binnr):
    gamma =  'gamma_{}_bin_{}'.format(sysname,binnr)
    tau =  'gamma_{}_bin_{}_tau'.format(sysname,binnr)
    return gamma,tau

def isComponentFunc(channel,name,component = None):
    if component:
        return 'L_x_{}_{}'.format(component,channel) in name
    else:
        return name.startswith('L_x') and name.split('_')[3] == channel

### End Naming Conventions

def set_pars(ws,parpoint,reference_snapshot):
    ws.loadSnapshot(reference_snapshot)
    for name,val in parpoint.iteritems():
        ws.var(name).setVal(val)

def set_pars2(ws,parpoint_data):
    for name,value_data in parpoint_data.iteritems():
        try:
            ws.var(name).setVal(value_data['val'])
        except:
            log.exception('could not get variable %s',)

def samples(ws,channel):
    allfuncs = ws.allFunctions()
    it = allfuncs.iterator()
    v = it.Next()
    samples = []
    while v:
        name =  v.GetName()
        if isComponentFunc(channel,name):
            samples += [name.split('_')[2]]
        v = it.Next()
    return samples

def binwidth(ws,obs,channel,component):
    for i,s in enumerate(samples(ws,channel)):
        if s==component:
            return ws.var(binwidthname(obs,channel,i)).getVal()

def extract_total(ws,channel,obs):
    oname=obsname(obs,channel)
    totalpdf = ws.pdf(totalpdfname(channel))
    h = totalpdf.createHistogram(oname)
    h.Scale(1./ws.var(binwidthname(obs,channel,0)).getVal())
    return h

def extract(ws,channel,obs,component = None):
    if not component:
        return extract_total(ws,channel,obs)
    oname=obsname(obs,channel)

    allfuncs = ws.allFunctions()
    it = allfuncs.iterator()

    v = it.Next()
    while v:
        name =  v.GetName()
        if isComponentFunc(channel,name,component):
            break
        v = it.Next()

    histo = v.createHistogram(oname)
    histo.SetDirectory(0)
    histo.Scale(binwidth(ws,obs,channel,component))
    return histo

def extract_with_pars(ws,channel,observable,component,pars,reference_snapshot = "NominalParamValues"):
    set_pars(ws,pars,reference_snapshot)
    return extract(ws,channel,observable,component)

def extract_data(ws,channel,observable,name = None):
    data = ws.data(dataName())
    reduced = data.reduce('channelCat == channelCat::{}'.format(channel))

    obsvar = ws.var(obsname(observable,channel))

    varlist = ROOT.RooArgList()
    varlist.add(obsvar)

    datahist = obsvar.createHistogram(name if name else 'data_{}'.format(channel))
    datahist = reduced.fillHistogram(datahist,varlist)
    datahist.Sumw2(0)
    return datahist

def get_shapesys_pars(ws,observable,sysname,constraint_type):
    allpars = pardict_up, pardict_nom, pardict_dn = {}, {}, {}
    for binnr in range(observable.getBinning().numBins()):
        gamma_name = 'gamma_{}_bin_{}'.format(sysname,binnr)

        mean_val,sigma_val = 0,0
        if constraint_type == 'Gaussian':
            gamma_name, gamma_sigma_name = shapeGaussVarNames(sysname,binnr)
            sigma_val = ws.obj(gamma_sigma_name).getVal()
            mean_val = ws.var(gamma_name).getVal()

        if constraint_type == 'Poisson':
            gamma_name, gamma_tau_name = shapePoissonVarNames(sysname,binnr)
            mean_val = ws.var(gamma_name).getVal()
            sigma_val = 1./math.sqrt((ws.function(gamma_tau_name).getVal()))

        pardict_up.update(**{gamma_name:mean_val+sigma_val})
        pardict_nom.update(**{gamma_name:mean_val})
        pardict_dn.update(**{gamma_name:mean_val-sigma_val})
    return allpars

def getsys_pars_from_fit(sysname,systype):
    raise NotImplementedError

def getsys_pars(sysname,systype,**kwargs):
    if systype in ['OverallSys','HistoSys']:
        constraintvar = 'alpha_{}'.format(sysname)
        return [{constraintvar:value} for value in [1.0,0.0,-1.0]]
    if systype in ['ShapeSys']:
        workspace       = kwargs['workspace']
        observable      = kwargs['observable']
        constraint_type = kwargs['constraint_type']
        assert constraint_type
        assert observable
        raise NotImplementedError
    if systype in ['Lumi']:
        workspace      = kwargs['workspace']
        return [{'Lumi':v} for v in getParFromConstraint(workspace,'lumiConstraint','Lumi')]

def getParFromConstraint(ws,constraintname,var):
    # import scipy.stats
    # pvals = [scipy.stats.norm.cdf(x) for x in [1,0,-1]]
    # no need for a scipy dependence for just three numbers
    # for +1,0,-1 sigma pvalues
    pvals = [0.84134474606854293, 0.5, 0.15865525393145707]

    varobj = ws.var(var)
    argset = ROOT.RooArgSet()
    argset.add(varobj)
    constraint = ws.pdf(constraintname)
    cdf = constraint.createCdf(argset)

    x = up,nom,dn = [cdf.findRoot(varobj,varobj.getMin(),varobj.getMax(),pval) for pval in pvals]

    return x

def make_band_root(up,down,nominal,binmin = 0,binmax = 1):
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
