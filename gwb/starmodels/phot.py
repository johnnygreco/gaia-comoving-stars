from astropy.io.votable import parse_single_table
import pandas as pd
import numpy as np

from .cfg import XMATCHFILE

xdf = None

def get_xdf():
    table = parse_single_table(XMATCHFILE)
    xdf = pd.DataFrame(np.array(table.array))

    # make G mag uncertainties
    xdf['phot_g_mean_mag_error'] = 2.5 * np.log10(1 + xdf.phot_g_mean_flux_error / xdf.phot_g_mean_flux)
    xdf.index = xdf.source_id
    return xdf

def get_photometry(source_id):
    """Returns dictionary of photometry
    """
    global xdf
    if xdf is None:
        xdf = get_xdf()

    s = xdf.ix[source_id]
    d = dict(G=(s.phot_g_mean_mag, s.phot_g_mean_mag_error),
             J=(s.j_m, s.j_msigcom),
             H=(s.h_m, s.h_msigcom),
             K=(s.ks_m, s.ks_msigcom),
             W1=(s.w1mpro, s.w1mpro_error),
             W2=(s.w2mpro, s.w2mpro_error),
             W3=(s.w2mpro, s.w2mpro_error),
             parallax=(s.parallax, s.parallax_error))
    
    systematics = dict(G=0.005, J=0.01, H=0.01, K=0.01, W1=0.01, W2=0.01, W3=0.01,
                      parallax=0.3)
    
    for k,v in systematics.items():
        val, unc = d[k]
        d[k] = (val, np.sqrt(unc**2 + v**2))
    
    return d