#!/usr/bin/python
import datetime
from numpy import pi, sqrt
from functions import setupROOT
from myon import MyonData, prepareGraph
from ROOT import TCanvas, TLegend, TMath # @UnresolvedImport
from fitter import Fitter
from txtfile import TxtFile
from data import DataErrors
from asyncore import write


def langaufun(x, par):
    """Convoluted Landau and Gaussian Fitting Function
    source: https://root.cern.ch/root/html/tutorials/fit/langaus.C.html
    translated to python by Benjamin Rottler (benjamin@dierottlers.de)

    parameters:
    par[0] = Width (scale) parameter of Landau density
    par[1] = Most Probable (MP, location) parameter of Landau density
    par[2] = Total area (integral -inf to inf, normalization constant)
    par[3] = Width (sigma) of convoluted Gaussian function

    In the Landau distribution (represented by the CERNLIB approximation), 
    the maximum is located at x=-0.22278298 with the location parameter=0.
    This shift is corrected within this function, so that the actual
    maximum is identical to the MP parameter.
    """
    # numeric constants
    invsq2pi = (2 * pi) ** (-1 / 2)
    mpshift = -0.22278298  # Landau maximum location

    # control constants
    np = 500  # number of convolution steps
    sc = 5    # convolution extends to +-sc Guassion sigmas

    # mp shift correction
    mpc = par[1] - mpshift * par[0]

    # range of convolution integral
    xlow, xupp = x[0] - sc * par[3], x[0] + sc * par[3]

    # Convolution integral of Landau and Gaussion by sum
    i = 1
    step = (xupp - xlow) / np
    s = 0
    while i <= np / 2:
        xx = xlow + (i - 0.5) * step
        fland = TMath.Landau(xx, mpc, par[0]) / par[0]
        s += fland * TMath.Gaus(x[0], xx, par[3])

        xx = xupp - (i - 0.5) * step
        fland = TMath.Landau(xx, mpc, par[0]) / par[0]
        s += fland * TMath.Gaus(x[0], xx, par[3])
        i += 1

    return (par[2] * step * s * invsq2pi / par[3])


def evalFlythroughSpectrum(name, xmin, xmax):
    data = MyonData.fromPath('../data/%s.TKA' % name)
    data.convertToCountrate()

    c = TCanvas('c_%s' % name, '', 1280, 720)
    g = data.makeGraph('g_%s' % name, 'channel c', 'countrate n / (1/s)')
    prepareGraph(g)
    g.GetXaxis().SetRangeUser(0, 700)
    g.GetYaxis().SetTitleOffset(1.2)
    g.Draw('APX')  # don't draw error bars => fit function in front

    maxY = data.getByY(data.getMaxY())[0]
    area = g.Integral(xmin, xmax)

    print('start fitting %s' % name)
    t1 = datetime.datetime.now()
    fit = Fitter('fit_%s' % name, langaufun, (xmin, xmax, 4))
    fit.setParam(0, 's', 1)
    fit.setParam(1, 'm', maxY)
    fit.setParam(2, 'A', area)
    fit.setParam(3, '#sigma', 30)
    fit.fit(g, xmin, xmax, 'RBO')
    t2 = datetime.datetime.now()
    delta = t2 - t1
    print('fitted in %d s' % int(delta.total_seconds()))
    fit.saveData('../fit/%s.txt' % name)
    
    if not name == "energiekalibration_100":
        l = TLegend(0.5, 0.55, 0.85, 0.85)
    else:
        l = TLegend(0.15, 0.55, 0.5, 0.85)
    l.SetTextSize(0.03)
    l.AddEntry(g, 'flight through with %s%% energy' % name.split('_')[1], 'p')
    l.AddEntry(fit.function, 'fit with n(c) =', 'l')
    l.AddEntry(None, '(landau(m, s) * gaus(0, #sigma))(c)', '')
    fit.addParamsToLegend(l, (('%.2f', '%.2f'), ('%.2f', '%.2f'), ('%.3f', '%.3f'), ('%.2f', '%.2f')), chisquareformat='%.2f', lang='en')
    l.Draw()

    g.Draw('P')  # redraw points with error bars
    c.Update()
    c.Print('../img/%s.pdf' % name, 'pdf')

    return ((fit.params[1]['value'], fit.params[1]['error']), (fit.params[3]['value'], fit.params[3]['error']))


def evalPedestal():
    name = 'pedestal'
    data = MyonData.fromPath('../data/%s.TKA' % name)
    data.convertToCountrate()
    c = TCanvas('c_ped', '', 1280, 720)
    g = data.makeGraph('g_ped', 'channel c', 'countrate n / (1/s)')
    g.SetLineColor(1)
    g.SetLineWidth(1)
    g.GetXaxis().SetRangeUser(0, 20)
    g.Draw('APX')
    
    fit = Fitter('fit_%s' % name, 'gaus(0)')
    fit.setParam(0, 'A', 30)
    fit.setParam(1, 'x', 6)
    fit.setParam(2, '#sigma', 3)
    fit.setParamLimits(2, 0, 100)
    fit.fit(g, 3.5, 10.5)
    fit.saveData('../fit/%s.txt' % name)
    
    l = TLegend(0.55, 0.6, 0.85, 0.85)
    l.SetTextSize(0.03)
    l.AddEntry(g, 'pedestal', 'p')
    l.AddEntry(fit.function, 'fit with n(c) = A gaus(c; x, #sigma)', 'l')
    fit.addParamsToLegend(l, (('%.2f', '%.2f'), ('%.3f', '%.3f'), ('%.3f', '%.3f')), chisquareformat='%.2f', units=('1/s', '', ''), lang='en')
    l.Draw()

    g.Draw('P')
    c.Update()
    c.Print('../img/%s.pdf' % name, 'pdf')
    
    return (fit.params[1]['value'], fit.params[1]['error'])

def evalEnergyCalibration(peaks, percents):
    maxenergy = 1.95 * 0.87 * 84
    smaxenergy = maxenergy * sqrt((0.05/1.95) ** 2 + (0.01/0.87) ** 2 + (5/84) ** 2 )
    channels = list(list(zip(*peaks))[0])
    schannels = list(list(zip(*peaks))[1])
    energies = list(map(lambda x:x/100*maxenergy, percents))
    senergies = list(map(lambda x:x/100*smaxenergy, percents))
    print(energies)
    print(senergies)
    
    with TxtFile('../src/tab_energycalibration.tex', 'w') as f:
        f.write2DArrayToLatexTable(list(zip(*[percents, channels, schannels, energies, senergies])),
                                   ['\% energy', '$c$', '$s_c$', '$E$ / MeV', '$s_E$ / MeV'], 
                                   ['%d', '%.3f', '%.3f', '%.1f', '%.1f'], 
                                   "Channels of fitted peaks and their theoretical energy for the energy calibration.", "tab:ecal")
    
    data = DataErrors.fromLists(channels, energies, schannels, senergies)
    c = TCanvas('c_energycalibration', '', 1280, 720)
    g = data.makeGraph('g_energycalibration', 'channel c', 'energy E / MeV')
    g.Draw('AP')
    
    fit = Fitter('fit_energycalibration', 'pol1(0)')
    fit.function.SetNpx(1000)
    fit.setParam(0, 'a', 0)
    fit.setParam(1, 'b', 1/3)
    fit.fit(g, 0, max(channels) + 5)
    fit.saveData('../fit/energyCalibration.txt')
    
    l = TLegend(0.15, 0.6, 0.575, 0.85)
    l.SetTextSize(0.03)
    l.AddEntry(g, 'Peaks of flight through spectra / pedestal', 'p')
    l.AddEntry(fit.function, 'fit with E(c) = a + b * c', 'l')
    fit.addParamsToLegend(l, (('%.2f', '%.2f'), ('%.3f', '%.3f')), chisquareformat='%.2f', units=('MeV', 'MeV / channel'), lang='en')
    l.Draw()
    
    c.Update()
    c.Print('../img/energyCalibration.pdf', 'pdf')
    
    with TxtFile('../calc/energyCalibration.txt', 'w') as f:
        f.writeline('\t', str(fit.params[0]['value']), str(fit.params[0]['error']))
        f.writeline('\t', str(fit.params[1]['value']), str(fit.params[1]['error']))
        f.writeline('\t', str(fit.getCovMatrixElem(0, 1)))

def main():
    peak100, sigma100 = evalFlythroughSpectrum('energiekalibration_100', 275, 600)
    peak050, sigma050 = evalFlythroughSpectrum('energiekalibration_50', 120, 400)
    peak035, sigma035 = evalFlythroughSpectrum('energiekalibration_35', 75, 240)
    peak000 = evalPedestal()
    evalEnergyCalibration([peak000, peak035, peak050, peak100], [0, 35, 50, 100])
    with TxtFile('../calc/ecal_sigmas.txt', 'w') as f:
        for d in [[peak035, sigma035], [peak050, sigma050], [peak100, sigma100]]:
            f.writeline('\t', *map(str,  [item for sublist in d for item in sublist]))

if __name__ == "__main__":
    setupROOT()
    main()
