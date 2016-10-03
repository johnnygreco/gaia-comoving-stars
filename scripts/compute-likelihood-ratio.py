# Standard library
import os
import sys

# Third-party
from astropy.io import fits
from astropy import log as logger
import astropy.units as u
import h5py
import numpy as np
import six
from schwimmbad import choose_pool

# Project
from gwb.data import TGASData, TGASStar
from gwb.fml import ln_H1_FML, ln_H2_FML

class Worker(object):

    def __init__(self, Vinv, v_scatter, n_distance_samples, output_filename):
        self.Vinv = np.array(Vinv)
        self.v_scatter = v_scatter
        self.n_distance_samples = n_distance_samples
        self.output_filename = output_filename

    def work(self, i, star1, star2):
        h1 = ln_H1_FML(star1, star2, Vinv=self.Vinv, v_scatter=self.v_scatter,
                       n_dist_samples=self.n_distance_samples)
        h2 = ln_H2_FML(star1, star2, Vinv=self.Vinv, v_scatter=self.v_scatter,
                       n_dist_samples=self.n_distance_samples)
        return i, h1, h2

    def __call__(self, task):
        i, star1, star2 = task
        return self.work(i, star1, star2)

    def callback(self, result):
        if result is None:
            pass

        else:
            i,h1,h2 = result
            with h5py.File(self.output_filename, 'a') as f:
                f['lnH1'][i] = h1
                f['lnH2'][i] = h2

def main(pool, stacked_tgas_path, pair_indices_path, signal_to_noise_cut,
         output_path="../data", seed=42, overwrite=False):

    # MAGIC NUMBERs
    n_distance_samples = 128
    v_scatter = 1. # km/s
    Vinv = np.diag(np.full(3, 1/25)**2) # 3x3 inverse variance matrix for disk stars

    if not os.path.exists(pair_indices_path):
        raise IOError("Path to pair indices file '{}' does not exist!".format(pair_indices_path))

    output_file = '{}-likelihood-ratio.h5'.format(os.path.splitext(pair_indices_path)[0])

    # load the pair indices
    pair_idx = fits.getdata(pair_indices_path, 0)

    if os.path.exists(output_file) and not overwrite:
        with h5py.File(output_file, 'a') as f:
            if len(f['lnH1']) != len(pair_idx):
                raise ValueError("Cache file dataset has wrong shape ({} vs {})."
                                 .format(len(f['lnH1']), len(pair_idx)))
    else:
        with h5py.File(output_file, 'w') as f:
            f.create_dataset('lnH1', dtype='f8', shape=(len(pair_idx),))
            f.create_dataset('lnH2', dtype='f8', shape=(len(pair_idx),))

    # read in TGAS data
    tgas = TGASData(os.path.abspath(stacked_tgas_path))
    tgas = tgas[tgas.parallax_snr > signal_to_noise_cut]

    if len(tgas) < pair_idx.max():
        raise ValueError("Number of surviving stars after S/N cut and pair indices "
                         "are not consistent!")

    all_pairs = [[k,tgas[i],tgas[j]] for k,(i,j) in enumerate(pair_idx)]
    all_pairs = all_pairs[:8] # HACK: testing

    worker = Worker(Vinv=Vinv, v_scatter=v_scatter, n_distance_samples=n_distance_samples,
                    output_filename=output_file)

    worker.callback(worker(all_pairs[0]))

    pool.map(worker, all_pairs, callback=worker.callback)
    pool.close()

if __name__ == "__main__":
    from argparse import ArgumentParser
    import logging

    # Define parser object
    parser = ArgumentParser(description="")

    vq_group = parser.add_mutually_exclusive_group()
    vq_group.add_argument('-v', '--verbose', action='count', default=0, dest='verbosity')
    vq_group.add_argument('-q', '--quiet', action='count', default=0, dest='quietness')

    parser.add_argument("-o", "--overwrite", dest="overwrite", default=False,
                        action="store_true", help="Overwrite any existing data.")

    parser.add_argument("-s", "--seed", dest="seed", default=None, type=int,
                        help="Random number seed")

    group = parser.add_mutually_exclusive_group()
    group.add_argument("--procs", dest="n_procs", default=1,
                       type=int, help="Number of processes.")
    group.add_argument("--mpi", dest="mpi", default=False,
                       action="store_true", help="Run with MPI.")

    parser.add_argument("--tgas-file", dest="stacked_tgas_path", required=True,
                        type=str, help="Path to stacked TGAS data file.")
    parser.add_argument("--pairs-file", dest="pair_indices_path", required=True,
                        type=str, help="Path to pair indices file.")
    parser.add_argument("--snr-cut", dest="signal_to_noise_cut", default=8,
                        type=float, help="Minimum signal-to-noise ratio in parallax.")
    parser.add_argument("--output-path", dest="output_path", default="../data/",
                        type=str, help="Path to write output.")

    args = parser.parse_args()

    # Set logger level based on verbose flags
    if args.verbosity != 0:
        if args.verbosity == 1:
            logger.setLevel(logging.DEBUG)
        else: # anything >= 2
            logger.setLevel(1)

    elif args.quietness != 0:
        if args.quietness == 1:
            logger.setLevel(logging.WARNING)
        else: # anything >= 2
            logger.setLevel(logging.ERROR)

    else: # default
        logger.setLevel(logging.INFO)

    pool_kwargs = dict(mpi=args.mpi, processes=args.n_procs)
    pool = choose_pool(**pool_kwargs)
    logger.debug("Using pool: {}".format(pool.__class__))

    # use a context manager so the prior samples file always gets deleted
    main(pool, args.stacked_tgas_path, args.pair_indices_path, args.signal_to_noise_cut,
         output_path=args.output_path, seed=args.seed, overwrite=args.overwrite)
