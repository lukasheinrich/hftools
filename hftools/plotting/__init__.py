import numpy as np
import math
def combine_graphs(graphs,positionhist):
    '''return combined band of bands summed in quadrature for each bin'''
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
