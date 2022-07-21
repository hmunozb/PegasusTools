import argparse
import numpy as np
import pandas as pd
import dimod

from pegasustools.app import add_general_arguments, add_qac_arguments, run_sampler, save_cell_results
from pegasustools.qac import PegasusQACEmbedding
from pegasustools.nqac import PegasusNQACEmbedding, PegasusK4NQACGraph
from pegasustools.util.adj import read_ising_adjacency, read_mapping
from pegasustools.util.sched import interpret_schedule
from dwave.preprocessing import ScaleComposite
from dwave.system import DWaveSampler, EmbeddingComposite


def main(args=None):
    parser = argparse.ArgumentParser()
    add_general_arguments(parser)
    add_qac_arguments(parser)
    parser.add_argument("--qac-mapping", type=str, default=None,
                        help="Topology mapping to QAC graph")
    parser.add_argument("--qubo", action='store_true')
    parser.add_argument("--minor-embed", action='store_true',
                        help="Minor-embed the instance to the QAC graph")
    parser.add_argument("--chain-strength", type=float, default=None,
                        help="Chain strength for minor-embed")
    parser.add_argument("--format", default=None)
    args = parser.parse_args(args)

    problem_file = args.problem
    tf = args.tf
    sep = ',' if args.format == 'csv' else None
    bqm = read_ising_adjacency(problem_file, 1.0, sep, args.qubo)
    bqm = dimod.BQM(bqm)  # ensure dict-based BQM
    if args.qac_mapping is not None:
        n2l, l2n = read_mapping(args.qac_mapping)
        mapping = {k: n for (k, n) in l2n.items() if k in bqm.linear}
        mapping_n2l = {n: k for (n, k) in n2l.items() if k in bqm.linear}
        bqm.relabel_variables(mapping)
    else:
        mapping_n2l = None

    dw_sampler = DWaveSampler()

    # Interpret and construct the annealing schedule
    if args.schedule is not None:
        sched = interpret_schedule(args.tf, *args.schedule)
        print(sched)
        dw_sampler.validate_anneal_schedule(sched)
    else:
        print(f"tf={args.tf}")
        sched = None
    if args.verbose:
        print(f"QAC Penalty: {args.qac_penalty}")
        print(f"QAC Problem scale: {args.qac_scale}")
    qac_args = {
        "qac_penalty_strength": args.qac_penalty,
        "qac_problem_scale": args.qac_scale,
        "qac_decoding": args.qac_mode
    }
    sched_kwags = {"anneal_schedule": sched} if sched is not None else {"annealing_time": args.tf}
    dw_kwargs = {"num_spin_reversal_transforms": 1 if args.rand_gauge else 0,
                 "num_reads": args.num_reads,
                 "auto_scale": False}
    if args.qac_method == "qac":
        qac_sampler = PegasusQACEmbedding(16, dw_sampler)
    elif args.qac_method == "k4":
        qac_graph = PegasusK4NQACGraph.from_sampler(16, dw_sampler)
        qac_sampler = PegasusNQACEmbedding(16, dw_sampler, qac_graph)
    else:
        raise RuntimeError(f"Invalid method {args.qac_method}")

    if args.minor_embed:
        qac_sampler = EmbeddingComposite(qac_sampler)
        emb_kwargs = {
            'chain_strength': args.chain_strength
        }
    else:
        qac_sampler.validate_structure(bqm)
        emb_kwargs = {}
    sampler = ScaleComposite(qac_sampler)
    aggr_results = run_sampler(sampler, bqm, args, aggregate=False, run_gc=True, scalar=1.0/args.scale_j,
                               **emb_kwargs, **qac_args, **dw_kwargs, **sched_kwags)
    all_results: dimod.SampleSet = dimod.concatenate(aggr_results)
    if mapping_n2l is not None:
        all_results.relabel_variables(mapping_n2l)
    lo = all_results.lowest()
    lo_df: pd.DataFrame = lo.to_pandas_dataframe()
    if args.qac_method == "qac" and args.qac_mode == "qac":
        print(lo_df.loc[:, ['energy', 'error_p', 'rep', 'num_occurrences']])
    else:
        print(lo_df.loc[:, ['energy', 'rep', 'num_occurrences']])
    num_gs = np.sum(lo.record.num_occurrences)
    total_reads = np.sum(all_results.record.num_occurrences)
    print(f"The lowest energy appears in {num_gs}/{total_reads} samples")
    # samps_df = df = pd.DataFrame(all_results.record.sample, columns=all_results.variables)
    num_vars = len(all_results.variables)

    df = all_results.to_pandas_dataframe()
    df_samples = df.iloc[:, :num_vars].astype("int8")
    df_properties = df.iloc[:, num_vars:]
    h5_file = args.output+".h5"
    store = pd.HDFStore(h5_file, mode='w', complevel=5)
    store.append("samples", df_samples)
    store.append("info", df_properties)
    store.close()
    #df_samples.to_hdf(h5_file, key="samples", mode='a', complevel=5, format="table")
    #df_properties.to_hdf(h5_file, key="info", mode='a', complevel=5, format="table")


if __name__ == "__main__":
    main()
