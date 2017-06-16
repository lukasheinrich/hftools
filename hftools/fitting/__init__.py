import ROOT
import hftools.utils as hfutils

def fit(workspace):
    '''
	fit the model to the data.

	:param workspace: the workspace object
	:return: fit result object
	'''
    result = workspace.pdf(hfutils.simulPdfName()).fitTo(workspace.data(hfutils.dataName()),
        ROOT.RooFit.Extended(True),
        ROOT.RooFit.Save(True),
        ROOT.RooFit.Minimizer("Minuit","Migrad"),
        ROOT.RooFit.Offset(True)
    )
    assert result
    return result