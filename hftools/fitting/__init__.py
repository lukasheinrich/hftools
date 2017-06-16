import ROOT
import hftools.utils as hfutils

def fit(workspace):
    result = workspace.pdf(hfutils.simulPdfName()).fitTo(workspace.data(hfutils.dataName()),
        ROOT.RooFit.Extended(True),
        ROOT.RooFit.Save(True),
        ROOT.RooFit.Minimizer("Minuit","Migrad"),
        ROOT.RooFit.Offset(True)
    )
    assert result
    return result