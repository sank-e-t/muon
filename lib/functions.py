#!/usr/bin/python2.7
"""some useful functions which dont fit in any class"""

__author__ = "Benjamin Rottler (benjamin@dierottlers.de)"
import numpy as np
from ROOT import gROOT, gStyle  #@UnresolvedImport
import os


def loadCSVToList(path, delimiter='\t'):
    """loads data in CSV-file to a list of lists.

    Arguments:
    path      -- relative path to file
    delimiter -- delimiter of file (default='\t')
    """
    if path:
        d = os.getcwd()
        p = os.path.abspath(os.path.join(d, path))
        data = []
        with open(p, 'r') as f:
            for line in f:
                try:
                    # remove \n, split by delimiter, convert to float
                    data.append(list(map(lambda x: float(x) if x else None, line.strip().split(delimiter))))
                except ValueError:
                    print('Warning: Could not convert %s' % line)
        return data


def avgerrors(values, errors):
    """calculates weighted average with error

    Arguments:
    values -- list of values
    errors -- list of errors
    """
    var = 1. / sum(map(lambda e: 1. / (e ** 2), errors))
    avg = sum(map(lambda v, e: v / (e ** 2), values, errors)) * var
    return avg, np.sqrt(var)


def setupROOT():
    """sets up ROOT """
    gROOT.Reset()
    gROOT.SetStyle('Plain')
    gStyle.SetPadTickY(1)
    gStyle.SetPadTickX(1)


def compare2Floats(a, b, rel_prec=1e-16):
    """compares 2 floats with relative precision treshold

    Arguments:
    a -- first float
    b -- second float
    rel_prec -- relative precision of error (default=1e-16)
    """
    return abs(a - b) <= rel_prec * max(abs(a), abs(b))
