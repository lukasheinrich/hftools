# conventions for histogram formatters
# bin_info_dep is a dictionary of {'histoname':{'value':v,'error_plus':plus_error,'error_minus':minus_error}}
# indep_info is a dictionary {'low':low_edge,'width':bin_width}

def standard_format(dep_info,**kwargs):
  v = dep_info.values()[0]
  error_config = kwargs.get('error_config',None)
  error = {}
  if error_config == 'asymmetric':
    error = {'asymerror':{'minus':-v['error_minus'],'plus':v['error_plus']},'label':kwargs['label']}
  if error_config == 'symmetric':
    error = {'symerror':(v['error_plus']+v['error_minus'])/2,'label':kwargs['label']}
  data = {'value':v['value']}
  if error: data['errors'] = [error]
  return data

def nominal_with_variations_formatter(dep_info,**kwargs):
  nom,up,down = [dep_info[x]['value'] for x in ['nominal','up','down']]
  return {'value':nom,'errors':[
    {'asymerror':{'minus':down-nom,'plus':up-nom},
     'label':kwargs['label']}
   ]}
   
def bin_format(indep_info,**kwargs):
  style = kwargs.get('style',None)
  if style=='central_value':
    return {'value':(indep_info['low']+indep_info['width'])/2.}
  else:
    return {'low':indep_info['low'], 'high':indep_info['low']+indep_info['width']}