import argparse
import dimod
import numpy as np
import pandas as pd


def add_general_argument(parser: argparse.ArgumentParser):
    parser.add_argument("-v", "--verbose", action='store_true')
    parser.add_argument("--targets", nargs='+', type=int, help="The list of target logical states to keep track of.")
    parser.add_argument("--tf", type=float, help="The anneal time for a simple annealing schedule.", default=20.0)
    parser.add_argument("--schedule", nargs='+', help="Anneal schedule specification ")
    parser.add_argument("-n", "--num-reads", type=int, default=64,
                        help="Number of solution readouts per repetition")
    parser.add_argument("--reps", type=int, default=1,
                        help="Number of repetitions of data collection")
    parser.add_argument("-R", "--rand-gauge", action='store_true',
                        help="Use a random gauge (spin reversal transformation) every repetition")
    parser.add_argument("--rev-init", type=int,
                        help="Initial state for reverse annealing")
    parser.add_argument("--scale-j", type=float, default=1.0,
                        help="Rescale all biases and couplings as J / scale_J")
    parser.add_argument("problem",
                        help="A cell problem, specified in a text file with three columns with the adjacency list")
    parser.add_argument("output", help="Prefix for output data")


def save_cell_results(raw_results: dimod.SampleSet, sched, args, additional_columns=None):
    """
    Save the results of a SampleSet where the outcomes can be labeled a 'blabel' integer column
    :param raw_results:
    :param sched:
    :param args:
    :return:
    """
    from .util import ising_to_intlabel
    all_results = raw_results.aggregate()
    sample = all_results.record.sample
    n_arr = ising_to_intlabel(sample)
    all_results = dimod.append_data_vectors(all_results, blabel=n_arr)

    df: pd.DataFrame = all_results.to_pandas_dataframe() \
        .sort_values("blabel", kind='mergesort') \
        .sort_values("energy", kind='mergesort')
    if additional_columns is None:
        additional_columns = []
    df2 = df[["blabel", "num_occurrences", "energy"] + additional_columns]
    if args.verbose:
        print(df[:11][["blabel", "num_occurrences", "energy"]])
    csv_path = f"{args.output}_samps.csv"
    sched_path = f"{args.output}_sched.csv"
    with open(csv_path, 'w') as f:
        df2.to_csv(f, index=False)

    if sched is not None:
        sched_arr = np.asarray(sched)
    else:
        sched_arr = np.asarray([[0.0, 0.0], [args.tf, 1.0]])
    np.savetxt(sched_path, sched_arr)


def profile(dw_sampler, bqm):
    from .pqubit import PegasusCellEmbedding
    print("Profiling cell embedding...")
    import pstats, cProfile
    cProfile.runctx("PegasusCellEmbedding(16, dw_sampler, cache=False)", globals(), locals(), "Profile.prof")
    s = pstats.Stats("Profile.prof")
    s.strip_dirs().sort_stats("cumulative").print_stats()

    print("Profiling sampling...")
    cProfile.runctx("cell_sampler.sample(bqm, num_spin_reversal_transforms=1, num_reads=args.num_reads).aggregate()",
                    globals(), locals(), "samp.prof")
    s = pstats.Stats("samp.prof")
    s.strip_dirs().sort_stats("cumulative").print_stats()
