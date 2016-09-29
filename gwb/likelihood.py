from __future__ import division, print_function

# Third-party
import astropy.units as u
import numpy as np

# Project
from .coords import get_tangent_basis

pc_mas_yr_to_km_s = (1*u.pc * u.mas/u.yr).to(u.km/u.s,u.dimensionless_angles()).value

def get_y(d, star):
    d = np.atleast_1d(d)
    y = np.stack([d * star._parallax*1E-3 - 1.,
                  d * star._pmra * pc_mas_yr_to_km_s,
                  d * star._pmdec * pc_mas_yr_to_km_s,
                  np.atleast_1d(star._rv)], axis=1)
    return y

def get_M(star):
    ra = np.atleast_1d(star._ra)
    dec = np.atleast_1d(star._dec)
    M0 = np.zeros((3,) + ra.shape)
    M_vel = get_tangent_basis(ra, dec)
    return np.hstack((M0, M_vel)).T[None]

def get_Cinv(d, star):
    Cinv = star.get_sub_cov_inv()
    Cinv[:3,:3] /= d**2
    return Cinv[None]

def get_A_nu_Delta(d, M, Cinv, y, Vinv):
    if Cinv.ndim > 2:
        n = Cinv.shape[0]
    else:
        n = 1

    # using ji vs. ij does the transpose of M
    # TODO: is A is actually the inverse of what you think it is?
    Ainv = np.einsum('...ji,...jk,...ks->...is', M, Cinv, M) + Vinv
    A = np.linalg.inv(Ainv)

    # using ji vs. ij does the transpose
    Bb = np.einsum('...ji,...jk,...k->...i', M, Cinv, y)
    nu = np.einsum('...ij,...j->...i', A, Bb)

    # do the right thing when Cinv[3,3] == 0
    idx = np.isclose(Cinv[...,3,3], 0)

    log_detCinv = np.zeros(n)
    _,log_detCinv[idx] = np.linalg.slogdet(Cinv[idx,:3,:3]/(2*np.pi))
    _,log_detCinv[~idx] = np.linalg.slogdet(Cinv[~idx]/(2*np.pi))

    sgn,log_detVinv = np.linalg.slogdet(Vinv/(2*np.pi))

    yT_Cinv_y = np.einsum('...i,...ji,...j->...', y, Cinv, y)
    nuT_A_nu = np.einsum('...i,...ji,...j->...', nu, A, nu)
    Delta = -3*np.log(d) - 0.5*log_detCinv - 0.5*log_detVinv + 0.5*yT_Cinv_y - nuT_A_nu

    return A, nu, Delta

def ln_marg_likelihood_helper(d, data, Vinv):
    y = get_y(d, data)
    M = get_M(data)
    Cinv = get_Cinv(d, data)
    A,nu,Delta = get_A_nu_Delta(d, M, Cinv, y, Vinv)
    _,log_detA = np.linalg.slogdet(A/(2*np.pi))
    return -Delta + 0.5*log_detA # TODO: plus or minus? is A actually Ainv?
