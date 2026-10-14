# Complementary disclosures in financial networks

Anonymous · version 2.0.0-candidate · 14 October 2026

A mathematical candidate about what specified disclosures identify in a one-period
proportional-clearing model. Synthetic networks only; no actual institution data.
Read [the manuscript](paper/paper.md), [status](STATUS.md),
[provenance](PROVENANCE.md), and [AI index](AI_INDEX.md).

## Results and scope

Several disclosures can jointly identify outside-creditor shortfall even when
each proper subset leaves the worst-case range unchanged. The paper separates
multiplicative transmission in a layered family from accounting coupling and a
restricted report menu in a one-layer affine construction.

The revision corrects the prior-dependent submodularity criterion at zero factors,
specifies which uncertainty is averaged, and derives affine-simplex residual
width formulas using standard LP duality. Exact and bounded-error reports admit
primal/dual certificates. These results do not solve generic nonlinear clearing
or arbitrary minimum-cost report selection.

Abstract complementarity, clearing theory, loss conservation and LP duality are
not claimed as new. See [citation audit](CITATION_AUDIT.md),
[research gates](RESEARCH_GATES.json), and the attributed unpublished predecessor.

## Fast read-only checks

Python 3.10 or newer and z3-solver suffice for these checks; NumPy/SciPy are not
required. The portable checker environment pins `z3-solver==4.15.4.0` in
`requirements-checks.txt`; the full study used Homebrew Z3 5.1.0, recorded
separately. Run from the package root:

```sh
python3 -B code/verify_extensions.py
python3 -B -O code/verify_extensions.py
python3 -B code/verify_assurance.py --results results/fresh-full
python3 -B -O code/verify_assurance.py --results results/fresh-full
python3 -B code/check_manifest.py
```

Extension checks cover rational affine primal/dual certificates, corrected prior
conditions, one-layer clearing, heterogeneous noise and semantic negative controls.
Assurance checks exercise solver-status handling and independently re-clear retained
rational witnesses. They do not regenerate the expensive solver search.
The frozen replay receipt records actual execution and environment.

## Regenerate the study

Run in a fresh working copy. Preserve prior outputs by choosing a new directory:

```sh
python3 -B code/study_random.py --historical-suite --timeout 40 --workers 2 --outdir results/NEW_DIRECTORY
```

This uses the original 44-instance design. Solver outcomes and timings can differ
across machines. UNKNOWN, timeouts and failed witness validations remain unresolved.
The study is exploratory, not a prevalence estimate or scalability claim.

## Rebuild the reading copy

The checked PDF is supplied. To rebuild with Pandoc and Tectonic, work in
`paper/` in a disposable copy (generated files need not be byte-identical across
typesetting versions):

```sh
pandoc paper.md --from markdown+tex_math_single_backslash+autolink_bare_uris --standalone --to latex --include-in-header header.tex -o paper.tex
tectonic paper.tex
```

Keep `figure_layered.pdf` beside the source. This is a multi-file document;
a single-file compiler that cannot access the figure cannot reproduce it.

## Evidence map

- `paper/paper.md`, `paper/paper.pdf`: canonical manuscript and typeset reading copy.
- `code/netinfo.py`: rational clearing, pair queries and witness validation.
- `code/verify_extensions.py`, `code/verify_assurance.py`: exact and regression checks.
- `results/fresh-full/`: fresh query, outcome and witness records.
- `results/historical-study-audit.json`: corrections and limitations of supplied study.
- Other supplied `results/`, `logs/`, `replay/`: historical evidence, not
  retrospectively upgraded to fresh certificates.
- `provenance/companion-2026-10-13.md`: exact unpublished predecessor, not the current paper.
- `SHA256SUMS`: final shipped file hashes except the manifest itself.

Other supplied scripts remain available for the layered, saturation, Bayesian,
noisy-report and criteria-divergence constructions. Historical logs do not imply
all scripts were freshly executed for this revision; the replay receipt states
fresh scope.

## Assurance boundary

Continuous-domain theorems rely on written proofs. Finite exact checks cover
specified cases. Rational witnesses are validated separately from solver SAT.
Algebraic SAT without a validated rational witness is not promoted to a certified
lower bound. UNSAT remains solver evidence unless a separately checked proof
certificate is supplied. UNKNOWN and timeout are not UNSAT.

No external peer-review acceptance, proof-assistant verification, independent
reproduction, empirical validation or official REF rating is claimed.
Original prose/data: CC0-1.0. Original code: MIT. See [licences](LICENSES.md).
