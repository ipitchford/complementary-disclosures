# Computational entry points

The release checks require Python 3.10+ and `z3-solver`; the portable quick suite was tested on Python 3.13.5 with `z3-solver==4.15.4.0`. No NumPy or SciPy is needed for these entry points.

From the repository root, run `python3 -B code/verify_assurance.py --results results/fresh-full` and `python3 -B code/verify_extensions.py`, then repeat both with `-O`. These commands do not write files. Assurance replay checks retained rational matrices and trace consistency rather than rerunning the random study. By default it rejects an incomplete results directory; `--allow-incomplete` exists only for interim diagnostics. `check_manifest.py` checks the final recursive package inventory.

`study_random.py --historical-suite --timeout 40 --workers 2 --outdir results/NEW_DIRECTORY` reuses the 44 historical *input specifications* for a fresh witness-retaining study. It requires a new output directory and may take substantial time. UNKNOWN, solver-only algebraic SAT, solver UNSAT, and independently Fraction-rechecked rational SAT are distinct outcomes. UNSAT results are solver evidence, not formal proof certificates.

`verify_extensions.py` checks finite exact affine-simplex certificates, the corrected zero-prior criterion, heterogeneous/coarse-error product extrema and one-layer clearing examples. It does not establish the paper's universal statements by computation.

`python3 -B code/crosscheck_paper.py` (repeat with `-O`) is also read-only. It checks the ratio table, all six two-report package choices, the contextual noise examples and the six-report quantile against their formulas. Fraction half-up rounding and high-precision Decimal gamma-CDF inversion are used; no SciPy is required. This is specified numerical checking, not whole-manuscript proof verification.

The remaining scripts are optional original diagnostics. They may require NumPy/SciPy and write to isolated `results/fresh_optional_*` directories. They are not the release quick suite. `make_tables.py` audits historical inputs/results without conferring missing witness evidence on them. Historical result files and logs remain historical.
