# AI index — complementary disclosures

## Read first

- [Status and boundaries](STATUS.md): mathematical candidate, not empirical banking advice or external peer-review acceptance.
- [Canonical manuscript](paper/paper.md): definitions, hypotheses, theorem statements, proofs and limitations. The PDF is generated from this source.
- [Provenance](PROVENANCE.md) and [component licences](LICENSES.md): Anonymous creator, supplied predecessor and review contributions, internal revision roles.

## Mathematical objects

The feasible objects are nonnegative liability matrices with fixed row/column totals and positive outside debts. Clearing is proportional, with no bankruptcy cost. The scalar target is outside-creditor payment shortfall under a specified shock. Reports come from a declared finite affine menu.

Minimax width maximises the target difference over two feasible networks with identical reports. Expected width averages the full accounting-fibre width over report values; it is not generally posterior-support width or expected utility. The layered constructions have exact multiplicative formulas. The one-layer affine construction distinguishes accounting coupling and report availability from nonlinear propagation. The affine simplex calculation uses standard LP duality; its scope does not extend automatically to generic cyclic clearing.

## Evidence and replay

- [Main library](code/netinfo.py): rational clearing and pair-query encoding. Distinguish solver SAT from checked rational witness evidence.
- [Fresh study](results/fresh-full/): records for the planned 44-instance design, retaining unresolved outcomes alongside resolved cases. Read-only witness validation and fresh solver regeneration are different operations; completion must be established by the summary and checker, not directory existence.
- [Historical results](results/): original aggregate records are not retrospectively upgraded to witness certificates. [Historical audit](results/historical-study-audit.json) records their limitations.
- [Claim map](CLAIMS.md), [assurance](ASSURANCE.md), [replay record](REPLAY.md) and [environment](ENVIRONMENT.json): precise scopes, limitations and execution identities.
- [Research gates](RESEARCH_GATES.json) and [citation audit](CITATION_AUDIT.md): contribution/dependency assessment and bounded prior-art checking, not a novelty guarantee.
- [Extension checker](code/verify_extensions.py), [assurance checker](code/verify_assurance.py) and [manuscript checker](code/crosscheck_paper.py): exact finite checks and explicit semantic negative controls, including optimized Python execution.
- [Historical companion](provenance/companion-2026-10-13.md): exact unpublished predecessor, with [context](provenance/README.md).
- [README](README.md): final runnable commands and environment requirements.

Inspect the final replay receipt and exact manifest before relying on a reported execution. A successful finite test is not a proof of the continuous-domain theorem. An UNSAT answer remains solver evidence unless an independently checked proof certificate is supplied. UNKNOWN and timeouts do not establish infeasibility. No proof-assistant verification is claimed.

## Safe reuse

Preserve the report menu, fixed-total constraints, positive-outside-debt assumption and the distinction between a fixed-parameter result and a parameter-dependent existence construction. In particular, adding a directly informative report can eliminate complementarity. Do not quote prospective REF judgements as official assessments or treat more computation as stronger significance.
