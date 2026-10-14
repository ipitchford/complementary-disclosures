# Optimal exposure disclosure under clearing uncertainty

13 October 2026

**Status.** Analytical solution of the model specified here, accompanied by executed exact-rational tests and exact-real solver checks. Publication novelty has not been established. This is not a claim about the resilience of any actual bank. The proofs are not formalised in a proof assistant, and the solver outputs are not independently checked proof traces.

## 1. Question and scope

Problem 6 in the supplied list asks which additional financial-exposure disclosures most reduce uncertainty about contagion losses, given aggregate assets and liabilities. It proposes fixing a clearing mechanism, default costs and an external shock. It supplies no numerical portfolio, disclosure menu, costs, prior distribution or unique loss metric.

We fix one-period Eisenberg–Noe proportional clearing, zero bankruptcy costs, known post-shock external assets and known nominal interbank asset and liability totals. Every bank has strictly positive outside debt. The loss is the payment shortfall to creditors outside the modelled banking network. This avoids adding the same chain of unpaid interbank claims to the outside-creditor loss. It is not a welfare-loss measure, a probability of default, or a model of dissipative amplification.

The objective is to minimise the **worst-case width of the loss interval remaining after the requested reports arrive**. Reports are truthful; they do not change contracts, behaviour or the shock. The initial main result concerns a finite menu of affine reports with declared costs. Later results cover a bespoke linear aggregate, concentration reports and bounded reporting error.

All empirical figures below are synthetic. Monetary quantities are in a common arbitrary unit; homogeneous rescaling can assign a currency unit.

## 2. Model and well-posedness

Let L_ij >= 0 be the nominal liability of bank i to bank j, with L_ii=0. The observed row totals are r_i, column totals a_i, outside liabilities b_i>0, and post-shock external assets x_i>=0. Put bar p_i=r_i+b_i. The feasible set F is a nonempty closed set described by rational linear equalities and inequalities, including

\[
\sum_jL_{ij}=r_i,\qquad \sum_iL_{ij}=a_j.
\]

Known zeros, individual exposures and exposure bounds can be included. Nonnegativity and fixed finite row totals make F compact. A failure of feasibility must be reported, not repaired silently.

Clearing payments solve

\[
p_i(L)=\min\left\{\bar p_i,x_i+\sum_j L_{ji}\frac{p_j(L)}{\bar p_j}\right\}.
\tag{1}
\]

Define recovery u_i=p_i/bar p_i and outside-creditor loss

\[
\ell(L)=\sum_i b_i(1-u_i(L)).
\tag{2}
\]

### Lemma 1: unique, continuous clearing

Put Pi_ij=L_ij/bar p_i. The right-hand side T_L of (1) maps the payment box into itself, and

\[
\|T_L(p)-T_L(q)\|_1\leq\gamma\|p-q\|_1,
\qquad
\gamma=\max_i\frac{r_i}{r_i+b_i}<1.
\]

Indeed, coordinatewise clipping is nonexpansive, and the induced 1-norm of Pi^T is its largest column sum, namely gamma. The contraction theorem gives a unique clearing vector. This contraction constant is uniform over F. For L and M in F,

\[
\|p(L)-p(M)\|_1
\leq\frac{\|(L-M)^Tu(M)\|_1}{1-\gamma},
\]

which proves continuity. Therefore ell is continuous, and all maxima and minima below exist. This proof uses the stated positive outside-debt assumption; it does not assert uniqueness for every possible clearing system.

## 3. The exact disclosure-selection theorem

Let Q_1,...,Q_d be candidate continuous reports. Initially take them to be affine functions of L. A bilateral exposure and a counterparty-category sum are examples. For S subset {1,...,d}, write Q_S for the vector of selected reports. The set remaining after report y is

\[
F(S,y)=\{L\in F:Q_S(L)=y\}.
\]

For feasible y its sharp bounding interval has width

\[
w(S,y)=\max_{L\in F(S,y)}\ell(L)-\min_{L\in F(S,y)}\ell(L).
\]

For affine reports and convex F, continuity also implies that the entire interval is attained. With nonlinear reports the identified set can be disconnected; the endpoints still define sharp bounds.

Define the ex-ante minimax residual width

\[
R(S)=\sup_{y\in Q_S(F)}w(S,y).
\tag{3}
\]

### Theorem 1: indistinguishable-pair formula

\[
\boxed{R(S)=\max\{\ell(L)-\ell(M):L,M\in F,\ Q_S(L)=Q_S(M)\}.}
\tag{4}
\]

**Proof.** Networks that agree on Q_S lie in the same report set, so their loss difference is bounded by its width. Conversely, the maximum- and minimum-loss networks in any report set form an admissible pair in (4). Compactness of the closed pair set gives attainment. The pair set is symmetric, so one could equivalently maximise the absolute difference. QED.

The optimal budget-constrained report set is consequently

\[
S_B^*\in\arg\min_{\sum_{q\in S}c_q\leq B}R(S).
\tag{5}
\]

This objective also solves minimax point estimation: the midpoint of each reported loss interval achieves worst-case absolute error R(S)/2, and no estimator based only on those reports can do better. Two endpoint losses separated by w cannot both lie within less than w/2 of a single estimate.

### Theorem 2: minimum-cost disclosure is a bad-pair hitting problem

For a target epsilon>=0 and a pair with ell(L)-ell(M)>epsilon, define

\[
D(L,M)=\{q:Q_q(L)\ne Q_q(M)\}.
\]

Then R(S)<=epsilon if and only if S intersects D(L,M) for every such pair. Thus the minimum disclosure cost is the exact 0–1 problem

\[
\min\sum_qc_qz_q,\quad z_q\in\{0,1\},\qquad
\sum_{q\in D(L,M)}z_q\geq1
\quad\text{for every bad pair}.
\tag{6}
\]

**Proof.** A pair not separated by any selected report remains observationally indistinguishable and violates (4). If every bad pair is separated, no feasible same-report pair has gap above epsilon, so (4) gives the desired bound. QED.

Although there are continuously many network pairs, there are at most 2^d different sets D(L,M). This gives an exact finite witness-cut algorithm:

1. Solve the minimum-cost hitting problem for the bad-pair sets collected so far.
2. Search for two feasible clearing networks that agree on the selected reports but have loss gap greater than epsilon.
3. If none exist, return the selected reports: they are feasible and globally minimum-cost.
4. Otherwise retain the pair and add its distinguishing-report set as a new constraint.

Every new pair has a distinguishing set not hit by the current solution, whereas all previous constraints are hit. Therefore its constraint is new and the procedure terminates after finitely many different sets. An empty distinguishing set proves that the entire candidate menu is insufficient. A master problem with no solution under a budget proves that budget insufficient.

Optimality at termination follows because the finite master constraints are necessary for every valid policy. The returned policy satisfies the full problem, while its cost is no larger than that of any full-problem feasible policy.

This is a specialised application of a general information-separation principle, not a claim that hitting-set methods themselves are new.

## 4. Exact clearing oracle

Each network copy can be represented using its liability variables and recovery variables u_i. Set

\[
h_i=x_i+\sum_jL_{ji}u_j.
\]

Impose

\[
0\leq u_i\leq1,\qquad \bar p_i u_i\leq h_i,
\qquad (u_i=1)\ \lor\ (\bar p_i u_i=h_i).
\tag{7}
\]

These conditions are exactly equivalent to (1). When recovery is below one, the bank pays its available resources. At recovery one, available resources must cover nominal debt. The positive outside-debt assumption makes this solution unique.

Duplicate (7), enforce the same report values, and require ell(L)-ell(M)>epsilon. For rational linear observations and affine reports this is a quantifier-free polynomial real-arithmetic feasibility problem of degree at most two. In particular, fixing a default set does **not** turn uncertain-network clearing into a linear program: the products L_ji u_j remain.

A complete real-algebraic decision method supplies the oracle needed for finite theoretical termination. Exact optimal widths are real algebraic numbers when all coefficients are rational: projection of the compact semialgebraic feasible set onto the objective axis is semialgebraic over the rationals, so its finite endpoints are algebraic. Quantifier elimination and real-root isolation can obtain them. Enumerating the finitely many budget-admissible report sets then solves (5) exactly. This is a decidability result, not an efficient large-network complexity guarantee.

The included implementation solves the threshold problem using Z3 and an exhaustive finite master. It supports fixed row and column totals, structural zeros, rational edge bounds and affine report menus. It rejects unknown/timeout responses and independently verifies each returned rational counterexample using Fraction arithmetic. The stored UNSAT outputs are solver checks, not proof-assistant certificates or independently replayed formal proof traces.

## 5. A fully solved six-bank example

There are banks A,B,C,D,E,F. Every bank owes 1 to outside creditors. The only allowed interbank liabilities are

| Debtor | Creditor | Liability |
|---|---|---:|
| A | C | x |
| A | D | 1-x |
| B | C | 1-x |
| B | D | x |
| C | E | y |
| C | F | 1-y |
| D | E | 1-y |
| D | F | y |

Here x,y range independently over [0,1]. Every allowed matrix has row totals (1,1,1,1,0,0) and column totals (0,0,1,1,1,1). Thus all nominal bank-level assets and liabilities are unchanged across the family.

Post-shock external assets are (0,2,1,1,0,1). Before the shock they were (2,2,1,1,0,1), when every bank paid in full. The shock destroys 2 external-asset units at A.

Write f(x,y)=xy+(1-x)(1-y)=1-x-y+2xy. Exact clearing gives

\[
p_A=0,\quad p_B=2,\quad p_C=2-x,\quad p_D=1+x,\quad
p_E=1-\tfrac12f(x,y),\quad p_F=1.
\]

Therefore

\[
\boxed{\ell(x,y)=\frac32+\frac12f(x,y)
=\frac74+\frac14(2x-1)(2y-1).}
\tag{8}
\]

The loss ranges from 3/2 to 2. A's direct outside-creditor loss is the constant 1; subtracting it to isolate secondary outside-creditor shortfalls leaves all disclosure rankings unchanged.

### Individual exposure reports

Any exposure in the first 2-by-2 block determines x; any exposure in the second determines y. Revealing x=a leaves realised interval width

\[
w(\{x\},a)=\tfrac12|2a-1|.
\]

Consequently,

\[
R(\varnothing)=R(\{x\})=R(\{y\})=\tfrac12,
\qquad R(\{x,y\})=0.
\tag{9}
\]

For x=1/2 a single report identifies the loss, so the assertion is about the worst possible report, not every realised report. No probability distribution is assumed.

Define the guaranteed information gain G(S)=R(empty)-R(S). Then G({x})=G({y})=0, but G({x,y})=1/2. Hence G is not submodular: the marginal value of revealing y increases after x has been revealed.

### Theorem 3: an optimal single linear aggregate

Suppose one published scalar may be any nonconstant affine function of x and y. The minimum possible worst-case residual width is 1/4, attained by revealing x+y or x-y.

For s=x+y, feasible x lies in [max(0,s-1),min(1,s)]. Along this set,

\[
f=1-s+2x(s-x).
\]

Its maximum is 1-s+s^2/2, attained at x=s/2. Its minimum is |1-s|, attained at a feasible endpoint. Therefore

\[
w(\{x+y\},s)=\tfrac14\min(s,2-s)^2,
\qquad R(\{x+y\})=\tfrac14.
\tag{10}
\]

For optimality, constants and nonzero rescaling of a report do not change its information. Swapping x and y and replacing one coordinate by its complement preserve loss widths. Thus a report with two nonzero coefficients may be written x+t y, with 0<t<=1. Consider its report value 1, for which x=1-t y and 0<=y<=1. The varying part of f is

\[
g_t(y)=(1+t)y-2ty^2,
\]

with minimum zero at y=0. If t<=1/3, its maximum is 1-t, giving loss width at least (1-t)/2>=1/3. If t>=1/3, the maximum is (1+t)^2/(8t), giving width at least

\[
\frac{(1+t)^2}{16t}\geq\frac14.
\]

A report with one zero coefficient is an individual report and has width 1/2. The lower bound thus applies to all nonconstant affine scalar reports, and (10) attains it. QED.

This result concerns disclosure bandwidth. Computing an aggregate of two liabilities may cost more to collect or verify than obtaining one bilateral exposure; a cost-aware application must charge accordingly. It is a bespoke cross-bank exposure sum, not automatically an existing regulatory counterparty category.

### Concentration reports cannot substitute for orientation

The interbank Herfindahl concentration indices of the two blocks are

\[
H_x=x^2+(1-x)^2,\qquad H_y=y^2+(1-y)^2.
\]

They reveal the magnitudes of 2x-1 and 2y-1, but not their signs. After both concentrations are known, the feasible losses are generally the two points

\[
\frac74\ \pm\ \frac14\sqrt{(2H_x-1)(2H_y-1)}.
\]

At H_x=H_y=1 the full original width 1/2 remains. Thus even all these row-level concentration summaries do not guarantee a reduction. Counterparty labels and directions contain information the concentration indices discard.

## 6. Arbitrarily high-order complementarity

### Theorem 4: layered construction and optimal bilateral budget rule

For every integer m>=1, a 2(m+1)-bank network with fixed nominal balance sheets has m independent hidden switches t_1,...,t_m and loss

\[
\boxed{\ell_m(t)=2-2^{-m}+2^{-m}\prod_{j=1}^m(2t_j-1).}
\tag{11}
\]

For unit-cost bilateral disclosures, every proper subset of stages has worst-case residual width 2^(1-m), and observing one exposure from every stage identifies the loss. Therefore the exact optimum with at most k disclosures is

\[
R_k^*=\begin{cases}2^{1-m},&k<m,\\0,&k\geq m.\end{cases}
\tag{12}
\]

**Construction.** Arrange banks in m+1 layers of two banks. Every bank owes 1 outside. Between layers j-1 and j the interbank liability block is

\[
T(t_j)=\begin{pmatrix}t_j&1-t_j\\1-t_j&t_j\end{pmatrix}.
\]

There are no other interbank liabilities. Sources have post-shock external assets (0,2); intermediate layers each have (1,1); final banks have (0,1). Before the shock replace the first source's zero by 2. Every bank then pays in full, and all row and column totals are independent of t.

**Proof of (11).** Let d_0=(1,0)^T be source recovery deficits. At intermediate layer j,

\[
d_j=\tfrac12T(t_j)^Td_{j-1}.
\]

The matrices have common eigenvectors (1,1)^T and (1,-1)^T with eigenvalues 1 and 2t_j-1. The first final bank's outside shortfall is consequently

\[
2^{-m}\left(1+\prod_j(2t_j-1)\right).
\]

The source and intermediate outside shortfalls sum to 1+sum_{j=1}^{m-1}2^{-j}=2-2^(1-m). Adding gives (11).

For a proper selected set S and actual reported switch values t_S, the unknown factors can make their product attain both -1 and 1. Hence

\[
w(S,t_S)=2^{1-m}\left|\prod_{j\in S}(2t_j-1)\right|.
\tag{13}
\]

An adversary can choose all observed factors to have absolute value one; therefore every proper S has the original worst-case width. Observing every stage determines the product. This proves (12). QED.

Adaptive selection does not improve this worst-case guarantee. At an endpoint network, every revealed switch is 0 or 1. As long as one stage remains unrevealed, changing that stage preserves the full transcript and reverses the product's sign. Randomising the selection cannot help on these endpoint networks when the realised policy uses fewer than m stages.

### Greedy gain can be arbitrarily poor

Take the m=2 module, of width 1/2, and an independent m=1 module scaled by delta, whose loss is delta(1+z) and whose width is delta. Let the report menu be x,y,z, all of cost one, and the budget two. Then

\[
R(S)=\tfrac12\mathbf1_{\{x,y\}\not\subseteq S}
+\delta\mathbf1_{z\notin S}.
\tag{14}
\]

If 0<delta<1/2, a greedy algorithm that maximises current guaranteed gain chooses z first, because its gain is delta while the individual gains of x and y are zero. One remaining query cannot complete the pair, so greedy reduces uncertainty by only delta. Choosing x and y reduces it by 1/2. The ratio of achieved gains is 2delta, which tends to zero.

For delta=1/100, initial width is 51/100, greedy residual width is 1/2, and the optimum is 1/100. The achieved gains are 1/100 and 1/2 respectively: greedy captures 2% of the optimum. This is a ratio of uncertainty reductions, not a claim about a standard multiplicative approximation ratio for residual width.

## 7. Robustness and sensitivity

### Strictly positive allowed exposures

Restrict every switch to [a,1-a], with 0<a<1/2. Let h=1-2a. The initial width in (11) becomes 2^(1-m)h^m. For any proper S, the worst-case observed product has magnitude h^|S| and the remaining product ranges between plus and minus h^(m-|S|). The worst-case residual width remains exactly 2^(1-m)h^m. Thus complementarity does not depend on edges disappearing at zero exposure.

### Positive initial equity and a fixed default set

In the six-bank example take x,y in [1/10,9/10]. Give every bank additional external assets kappa=1/100 before the shock. After the shock A has zero assets, so the destroyed amount is 2+kappa; the other external-asset increments remain. Every bank has strictly positive initial equity. The defaulting banks are always A,C,D,E throughout the permitted square.

More generally, if kappa<a and 3kappa/2<a(1-a), direct clearing gives

\[
\ell(x,y)=\frac74-\frac52\kappa+\frac14(2x-1)(2y-1).
\tag{15}
\]

The constant changes, but the disclosure widths do not. With a=1/10 and kappa=1/100, the loss range is [313/200,377/200]=[1.565,1.885], width 8/25=0.32. Each individual disclosure still has worst-case residual width 0.32, and both together have zero width. Therefore the phenomenon does not require a change in the default set or zero pre-shock equity.

### Bounded-error reports

Suppose report q has arbitrary independent error bounded by eta_q, so its reported value lies within eta_q of Q_q(L). Two networks admit a common report vector exactly when

\[
|Q_q(L)-Q_q(M)|\leq2\eta_q\quad\text{for every selected q}.
\]

Replace equality in (4) by these inequalities. The same proof gives the exact minimax residual width. The hitting-set formulation uses the separating set {q:|Q_q(L)-Q_q(M)|>2eta_q}. This result is for independent bounded-error intervals; it is not automatically the formula for deterministic rounding into fixed bins. The code provided implements exact reports, not this extension.

### Alternative decision targets

For a fixed binary stress-test decision, define bad pairs as networks with different decisions rather than losses differing by more than epsilon. The same separating-set theorem characterises reports that identify the decision. A different prior, welfare objective, clearing mechanism or cost model can select different reports.

## 8. Sanity checks and execution record

Summing bank balance sheets after clearing gives

\[
\sum_i e_i=\sum_i x_i-\sum_i b_iu_i,
\qquad
\ell=\sum_i b_i-\sum_i x_i+\sum_i e_i.
\tag{16}
\]

All included rational cases verify this identity exactly. In the base six-bank example, (x,y)=(0,0) gives payments (0,2,2,1,1/2,1), outside receipts 4 and shortfall 2. At (0,1), payments are (0,2,2,1,1,1), outside receipts 9/2 and shortfall 3/2. These networks have the same x report, the same balance-sheet totals and the same two concentration indices, yet their losses differ by 1/2. The original destroyed asset amount was 2, so neither example manufactures losses in excess of that amount.

Executed verification comprised:

- 408 exact-rational clearing cases, checked using both a fictitious-default linear-system calculation and separate acyclic forward propagation;
- 252 endpoint witness checks covering every selected-stage set through six stages, with unrestricted and strictly positive allowed exposures;
- 31 full-variable-network Z3 checks: global upper bounds or attainment witnesses for the base, positive-capital, aggregate-report and greedy examples;
- witness-cut optimisation proving the two-disclosure optimum, plus a budget-impossibility run ruling out a residual width below 0.01 with two reports in the combined example.

The solver was Z3 4.13.3.0. Every SAT witness used in these runs was rational and was independently checked by the Fraction clearing implementation. Finite samples do not prove the infinite family; the proof in section 6 does. The independently written computational formulations share model assumptions and do not replace independent human review.

## 9. Relation to prior work and remaining boundaries

Eisenberg and Noe (2001) supply the proportional clearing foundation. Gandy and Veraart (2017) reconstruct networks conditional on totals and observed individual liabilities. Feinstein et al. (2018) study clearing sensitivity to bilateral-liability errors. Ahn et al. (2024) develop robust default-risk and capital-requirement calculations and analyse incomplete information structures. Hu et al. (2024) optimise expected losses over networks with common aggregate balance-sheet information.

A targeted source search on 13 October 2026 verified these topics from publisher abstracts and bibliographic records. It did not inspect all full texts or establish exhaustive novelty. Robust network-loss bounds are therefore not claimed as a new general idea. The mathematical contribution developed here is the explicit minimax report-separation formulation, its exact threshold-selection implementation, the closed-form one-scalar linear-report optimum, and the high-order complementarity family. Whether any of these results are unpublished requires a separate full-text prior-art review.

The solution holds under the declared one-period clearing and reporting assumptions. It does not account for fire sales, strategic public disclosure, seniority differences, multiple maturities or recovery costs. No real-world reporting data were supplied or inferred. A successful fit of reconstructed networks or agreement between code outputs would not establish that the adopted model describes an actual financial system.

## Sources

### Clearing, reconstruction and sensitivity

Eisenberg, L., & Noe, T. H. (2001). Systemic risk in financial systems. *Management Science, 47*(2), 236–249. https://doi.org/10.1287/mnsc.47.2.236.9835

Gandy, A., & Veraart, L. A. M. (2017). A Bayesian methodology for systemic risk assessment in financial networks. *Management Science, 63*(12), 4428–4446. https://doi.org/10.1287/mnsc.2016.2546

Feinstein, Z., Pang, W., Rudloff, B., Schaanning, E., Sturm, S., & Wildman, M. (2018). Sensitivity of the Eisenberg–Noe clearing vector to individual interbank liabilities. *SIAM Journal on Financial Mathematics, 9*(4), 1286–1325. https://doi.org/10.1137/18M1171060

### Robust incomplete-network analysis

Ahn, D., Chen, N., & Kim, K.-K. (2024). Robust risk quantification via shock propagation in financial networks. *Operations Research, 72*(1), 1–18. https://doi.org/10.1287/opre.2020.0722

Hu, F., Mitchell, D., & Tompaidis, S. (2024). Robust financial networks. *Operations Research, 72*(5), 1827–1842. https://doi.org/10.1287/opre.2022.0272

### Computation

Z3 Project. (n.d.). *Arithmetic*. Online Z3 Guide. Retrieved October 13, 2026, from https://microsoft.github.io/z3guide/docs/theories/Arithmetic/
