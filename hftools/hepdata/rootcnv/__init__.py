#!/usr/bin/env python

import itertools
import formatters

def _get_maxdim(histo):
    classname = histo.ClassName()
    maxdim = 1 if 'TH1' in classname else 2 if 'TH2' in classname else 3
    return maxdim

def _extract_values_bin(histo,x,y,z,maxdim):
    global_binnr = histo.GetBin(x,y,z)
    value_data = {'value':histo.GetBinContent(global_binnr),
                'error_plus':histo.GetBinErrorUp(*[x,y,z][0:maxdim]),
                'error_minus':histo.GetBinErrorLow(*[x,y,z][0:maxdim])}
    return value_data

def _get_dep_info(inputsdict,indep_tag):
    ndim = len(indep_tag)
    x,y,z = list(indep_tag)+([1]*(3-ndim))
    dep_vals = {k:_extract_values_bin(h,x,y,z,ndim) for k,h in inputsdict.iteritems()}
    return dep_vals

def _get_indep_info(rep):
    ndim = _get_maxdim(rep)
    bin_ranges = [range(1,n+1) for n in [rep.GetNbinsX(),rep.GetNbinsY(),rep.GetNbinsZ()]]
    tag_list = []
    indep_list = []
    for x,y,z in itertools.product(*bin_ranges):
        indep_storage = []
    for axis,axisbin in [(rep.GetXaxis(),x),(rep.GetYaxis(),y),(rep.GetZaxis(),z)]:
        low = axis.GetBinLowEdge(axisbin)
        width = axis.GetBinWidth(axisbin)
        indep_storage += [{'low':low,'width':width}]
    indep_list += [indep_storage[0:ndim]]
    tag_list+=[(x,y,z)[0:ndim]]
    return (indep_list,tag_list)

def convertROOT(table_definition):
  #representative input for x values is first input of first data
    xrep = table_definition['dependent_variables'][0]['conversion']['inputs'].values()[0]
    indep_values,taglist = _get_indep_info(xrep)

    indep_val_lists = zip(*indep_values)
    for indep_def,val_list in zip(table_definition['independent_variables'],indep_val_lists):
        standard_conversion = {'formatter':formatters.bin_format}
        conversion = indep_def.pop('conversion') if 'conversion' in indep_def else standard_conversion
        indep_def['values'] = list(conversion['formatter'](x,**conversion.get('formatter_args',{})) for x in val_list)
  
    for col_def in table_definition['dependent_variables']:
        conversion = col_def.pop('conversion')
        column_data = [_get_dep_info(conversion['inputs'],indep_tag) for indep_tag in taglist]
        formatter = conversion.pop('formatter',formatters.standard_format)
        formatter_args = conversion.pop('formatter_args',{})
        col_def['values'] = list(formatter(x,**formatter_args) for x in column_data)
  
    return table_definition