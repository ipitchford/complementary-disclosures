# Replay record and commands

## Completed finite checks, 14 October 2026

Run from the repository root, with Python 3.14.7 and Z3 5.1.0 on macOS arm64:

```sh
python3 -B code/verify_extensions.py
python3 -B -O code/verify_extensions.py
python3 -B code/verify_assurance.py
python3 -B -O code/verify_assurance.py
```

All four commands returned PASS. Normal and optimized modes agreed on substantive results:

| Extension check | Count |
|---|---:|
| Exact affine primal/dual certificates | 70 |
| Prior parameter vectors | 775 |
| Failures of the original unqualified pair-sum criterion | 302 |
| Heterogeneous noise configurations | 155 |
| Product-polytope vertices evaluated | 11,154 |
| One-layer rational clearing cases | 375 |
| Proper-menu endpoint pairs | 78 |
| Extension negative/regression controls | 7 |
| Assurance self-tests | 16 |

The assurance commands above had no `--results`: they checked zero retained study records. Their PASS is not a full-study replay. The extension enumerations are finite diagnostics supporting, not replacing, written proofs.

Final checker hashes at strict replay:

```text
2bf49b35f69b0793e9535d628e8e754a8b95d1df3a286b89fdc4c19890aa0973  code/verify_extensions.py
362dc6c47f245fbb4bc1e6094e260aa1ce3cf98b39f0cbb08c353dedf0bbe654  code/verify_assurance.py
a873ac23370d67abcdc84f9efd20a8f7a43a618db6115c30690f5418f43fbfb7  code/netinfo.py
239e1bff9c246020592f416562fa98f3c9a692583add1695b60b972177e88f60  results/fresh-study-aggregation.json
```

## Completed fresh study and strict portable replay

The repaired run in `results/fresh-full/` retained all 44 planned inputs: 29 completed every width bracket, 14 remain unresolved and one has zero shock. The 1,878 queries contain 657 exact rational witnesses, 1,207 solver UNSAT and 14 UNKNOWN, with no algebraic-only SAT. Of 28 selection attempts, seven were optimal and 21 infeasible for the declared menu and threshold. Accounting screening covered 91 reports on 29 completed instances: 24 accounting-fixed and 67 variable with witnesses. Recorded two-worker makespan was 3006.902408 seconds, not the sum of individual query times.

The following retained-evidence commands were personally repeated in Python 3.13.5 with PyPI `z3-solver==4.15.4.0`, both PASS with strict 44/44 coverage. Both extension-check modes also passed again with the final hashes above. Machine-readable receipts are `logs/assurance-final-normal.json`, `logs/assurance-final-optimized.json`; aggregation and input hashes are in `results/fresh-study-aggregation.json`.

```sh
python3 -B code/verify_assurance.py --results results/fresh-full
python3 -B -O code/verify_assurance.py --results results/fresh-full
```

The revised `verify_assurance.py` validates planned-design coverage and requires complete study records by default; `--allow-incomplete` is an interim diagnostic option, not used for these results. Nested selection histories are bound to the retained query trace. The supplied historical study is not relabelled as this fresh run.

The portable replay environment differs from full-study generation above, whose Z3 library is 5.1.0 without corresponding pip distribution metadata. Rechecking retained rational witnesses is not rerunning all original solver searches under a second solver version. Package integrity can separately be checked with `python3 -B code/check_manifest.py` and its `-O` counterpart against the release manifest.

To rerun the expensive study, use a new output directory:

```sh
python3 -B code/study_random.py --historical-suite --timeout 40 --workers 2 --outdir results/NEW_DIRECTORY
```

Runtime and solver verdicts can vary. Read-only retained rational witness checks recalculate feasibility and clearing; retained UNSAT is a recorded solver result, not a replayed proof certificate. Manifest integrity cannot establish mathematical correctness.
