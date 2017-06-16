#!/usr/bin/env python
import ROOT
import yaml
import os

from rootcnv import convertROOT, formatters
import click

@click.command()
@click.argument('inputfile')
@click.option('-d','--workdir',default = None, help = 'change working directory (relative to which inputs are defined)')
def converter(inputfile,workdir):
  
  files_cache,objects_cache = {},{}
  def get_root_object(identifiers):
    if identifiers in objects_cache:
      return objects_cache[identifiers]
    filename,path = identifiers.split(':',1)
    if filename in files_cache:
      obj = files_cache[filename].Get(path)
      if not obj: raise RuntimeError
      objects_cache[identifiers] = obj
      return get_root_object(identifiers)
    files_cache[filename] = ROOT.TFile.Open(filename)
    return get_root_object(identifiers)
  
  data = yaml.load(open(inputfile))

  original_dir = os.path.abspath(os.curdir)
  if workdir:
    os.chdir(os.path.abspath(workdir))

  converted_tables = []
  for table in data:
    #load files and formatters
    for dep in table['dependent_variables']:
      dep['conversion']['inputs']    = {k:get_root_object(v) for k,v in dep['conversion']['inputs'].iteritems()}
      if 'formatter' in dep['conversion']:
        dep['conversion']['formatter'] = getattr(formatters,dep['conversion']['formatter'])
    for indep in table['independent_variables']:
      if 'conversion' in indep:
        indep['conversion']['formatter'] = getattr(formatters,indep['conversion']['formatter'])

    converted_tables += [convertROOT(table)]
  
  os.chdir(original_dir)
  for i,data in enumerate(converted_tables):
    filename = 'data{}.yaml'.format(i)
    with open(filename,'w') as f:
      click.secho('writing {}'.format(filename), fg = 'green')
      f.write(yaml.safe_dump(data,default_flow_style = False))
