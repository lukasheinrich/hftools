#!/usr/bin/env python

import rootcnv as hfrootcnv
import hftools.utils as hfutils
import logging
log = logging.getLogger(__name__)

def nominal_with_all_systs(dep_info,**kwargs):
    nominal_key = [k for k in dep_info.keys() if 'nominal' in k][0]
    sysnames = [k.split('_')[1] for k in dep_info.keys() if 'systhist' in k and 'up' in k]

    nom_val = dep_info[nominal_key]['value']

    errors = []
    for sys in sysnames:
        up_val = dep_info['systhist_{}_up'.format(sys)]['value']
        dn_val = dep_info['systhist_{}_down'.format(sys)]['value']
        errors += [{'asymerror':{'minus':dn_val-nom_val,'plus':up_val-nom_val},'label':sys}]


    outdata = {'value':nom_val}
    if errors: outdata.update(errors = errors)
    return outdata

def format_column_for_hepdata(ws,channel,observable,component,systematics,fitresult = None):
    log.warning('preparing HepData column for sample %s',component)
    loaded_param_sets = {}
    x = ws.var(hfutils.obsname(observable,channel))
    for name,defin in systematics.iteritems():
        loaded_param_sets[name] = hfutils.getsys_pars(defin['HFname'],defin['HFtype'],
                                                      workspace = ws, observable = x,
                                                      **(defin.get('additional_args',{})))
        if fitresult:
            hfutils.getsys_pars_from_fit(defin['HFname'],defin['HFtype'],workspace = ws, observable = x)

    log.info('working with parameter set: %s',loaded_param_sets)

    firstnom = None
    syst_hists = []
    for name,paramset in loaded_param_sets.iteritems():
        up,nom,down = [hfutils.extract_with_pars(ws,channel,observable,component,pardict) for pardict in paramset]

        for h,tag in zip([up,down],['up','down']):
            h.SetName('systhist_{}_{}'.format(name,tag))

        if not firstnom:
            firstnom = nom

        syst_hists += [up,down]

    if not loaded_param_sets:
        #just take reference parameter set
        firstnom = hfutils.extract_with_pars(ws,channel,observable,component,{})

    firstnom.SetName("nominal_{}".format(channel))

    nom_systs = {h.GetName():h for h in [firstnom] + syst_hists}

    column_data = {
     'header': {'name': component},
     'conversion':{
       'formatter': nominal_with_all_systs,
       'inputs': nom_systs
      },
    }

    return column_data


def hepdata_table(ws,channel,observable,sampledef,fitresult = None):
    compcols = []
    for sample,sampledef in sampledef:
        compcols += [format_column_for_hepdata(ws,channel,observable,sample,sampledef['systs'],fitresult)]

    datacol = {
     'header': {'name': 'Data'},
     'conversion':{
       'formatter': hfrootcnv.formatters.standard_format,
       'formatter_args': {},
       'inputs': {'histo': hfutils.extract_data(ws,channel,observable)}
      },
    }

    allcols = [datacol] + compcols

    to_convert = {
      'name': 'Channel {}'.format(channel),
      'dependent_variables': allcols,
      'independent_variables':
      [
        {'header': {'name': observable}}
      ],
    }
    hepdata_formatted = hfrootcnv.convertROOT(to_convert)
    return hepdata_formatted

