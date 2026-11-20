# PROMPT 4 validation — constrained optimization

Validated on 2026-11-19 in Europe/Istanbul (the run manifests record UTC).
Phaseward is installed locally as **qwave 0.5.0**. This stage adds SLSQP
multi-start gate optimization, fixed/clean/Monte-Carlo/sensitivity comparisons,
numerical preflight/postflight, exact caches, complete trial logging and
frozen-design evaluation. The GUI remains outside this stage.

## Installed environment and source

The final runs used Python 3.13.0, NumPy 2.5.5, SciPy 1.18.1, Matplotlib 3.11.2
and pytest 9.2.0 on native Apple Silicon arm64, Darwin 25.6.0, 8 logical CPUs.
The runtime is CPU-only. No new dependency, cloud service, account, paid API,
Docker, notebook or device was required.

All 23 installed Python modules were compared byte-for-byte with the workspace
before testing. The final tests and commands used the installed package with
no PYTHONPATH override. Source code SHA-256 identity:

4925af030738247cc70c13b573b1c15e2baf2b01df384be2fb8eb26d60ebf8ee

The wheel is qwave-0.5.0-py3-none-any.whl, 85742 bytes, SHA-256:

35f8ff8d02e381810b2e2daacba3cf344cf879dbbda5c0cfc958bb22727b27a7

The repository has no commit to cite. Per-file hashes identify the code.
Only Python 3.13 was executed; Python 3.11 remains the declared minimum.
The existing regular-wheel workaround for this Mac's hidden editable .pth
issue is retained; see [stage 1](validation_stage1.md).

## Exact final build and run commands

Working directory: /Users/baharyuksel/Documents/ChatGPT/Phaseward.
Every experiment output directory was new. Reruns must use new folder names.
The comparison examples ran sequentially after the full tests finished, rather
than competing with another test/optimization run for CPU time.

~~~sh
set -e
mkdir -p results/stage4-release-logs
python3 -m pip wheel --no-deps --no-build-isolation --no-cache-dir --wheel-dir results/stage4-release-wheels . > results/stage4-release-logs/build.txt 2>&1
.venv/bin/python -m pip install --no-index --no-deps --force-reinstall results/stage4-release-wheels/qwave-0.5.0-py3-none-any.whl > results/stage4-release-logs/install.txt 2>&1
.venv/bin/python - <<'PY' > results/stage4-release-logs/source-audit.json
import json
from pathlib import Path
import qwave
from qwave.provenance import source_identity,sha256_file
installed=Path(qwave.__file__).parent
assert '.venv/lib/' in str(installed),installed
sources=sorted(Path('src/qwave').glob('*.py'))
for path in sources:
    assert path.read_bytes()==(installed/path.name).read_bytes(),path
wheel=Path('results/stage4-release-wheels/qwave-0.5.0-py3-none-any.whl')
print(json.dumps({'version':qwave.__version__,'installed_path':str(installed),'matching_python_modules':len(sources),
                  'source':source_identity(),'wheel_sha256':sha256_file(wheel),'wheel_size_bytes':wheel.stat().st_size},indent=2))
PY
~~~

~~~sh
source .venv/bin/activate
set -o pipefail
pytest | tee results/stage4-release-logs/pytest.txt
~~~

~~~sh
set -e
source .venv/bin/activate
export MPLCONFIGDIR="$PWD/results/.matplotlib-stage4"
qwave doctor --dev > results/stage4-release-logs/doctor.json
qwave config-check examples/optimize_quick.json > results/stage4-release-logs/optimize-quick-config-check.json
qwave config-check examples/optimize.json > results/stage4-release-logs/optimize-config-check.json
qwave optimize --config examples/optimize_quick.json --output results/stage4-release-optimize-quick > results/stage4-release-logs/optimize-quick.txt
qwave optimize --config examples/optimize.json --output results/stage4-release-optimize > results/stage4-release-logs/optimize.txt
python -m pip check > results/stage4-release-logs/pip-check.txt
~~~

~~~sh
set -e
source .venv/bin/activate
export MPLCONFIGDIR="$PWD/results/.matplotlib-stage4"
qwave config-check examples/demo.json > results/stage4-release-logs/demo-config-check.json
qwave demo --config examples/demo.json --output results/stage4-release-demo --plot > results/stage4-release-logs/demo.txt
~~~

All completed with exit status 0. Doctor reported runtime/development ready.
Pip check reported “No broken requirements found.” Pip's unwritable-cache warning
was nonblocking; no sudo or permission change was needed.

## Tests and numerical evidence

Exact final installed-package output:

~~~text
============================= test session starts ==============================
platform darwin -- Python 3.13.0, pytest-9.2.0, pluggy-1.7.0
rootdir: /Users/baharyuksel/Documents/ChatGPT/Phaseward
configfile: pyproject.toml
testpaths: tests
collected 191 items

tests/test_cli.py .......                                                [  3%]
tests/test_config.py ..........................                          [ 17%]
tests/test_demo.py ...........                                           [ 23%]
tests/test_disorder.py ...............                                   [ 30%]
tests/test_disorder_workflow.py .....................                    [ 41%]
tests/test_optimization.py ...................                           [ 51%]
tests/test_optimization_workflow.py ......                               [ 54%]
tests/test_packet_workflow.py ..............                             [ 62%]
tests/test_scatter_workflow.py ...................                       [ 72%]
tests/test_scattering.py ......................                          [ 83%]
tests/test_sensitivity.py .........                                      [ 88%]
tests/test_wavepackets.py ......................                         [100%]

============================= 191 passed in 29.86s =============================
~~~

The 25 new tests cover:

- The independent free-channel complex Born derivative and J, direct nodal
  covariance contraction, exactly one eigenvalue factor, sigma² normalization,
  and energy/spatial refinement.
- Analytic polynomial gate Jacobians with central and one-sided boundary stencils.
- Detection of a perturbation that is representable in u but disappears beneath
  the physical potential background; unusable tiny diagnostics do not invalidate
  a stable selected step.
- Exact cache keys for potential, grid, energy, mass, leads, source context and
  tolerance, response RHS cost, immutable results, eviction, and budget stops.
- Direct Monte Carlo loss averaging, disjoint seeds, unchanged search when only
  evaluation seeds change, and verification that evaluation draws are generated
  only after every design is frozen.
- Physical/scaled residuals, optional slope and normalization settings, negligible
  throughput rejection, infeasible/budget-starved runs without fabricated winners,
  strict schemas, CLI execution, hashes, raw complex arrays and all figure formats.

The earlier 166 tests passed too. They include stationary conservation,
analytical scattering references, phase, packets, covariance scaling and
complex derivatives. Those tests were rerun; the earlier standalone stage-1/2
validation scripts were not rerun in this stage.

A smooth-boundary spatial benchmark used 81, 161 and 321 nodes on the same
−40 to +40 nm domain, the quick example's six modes, a 5 nm disorder taper,
and zero gate amplitudes. Measured J/sigma² was 0.00726553307466,
0.00717146410797 and 0.00714834579220 meV⁻². The successive-difference ratio
was 4.0690, consistent with second-order convergence in that benchmark.
The separate uniform-energy integration test likewise checks approximately
fourfold reduction. These are numerical regression guards, not accuracy laws
for arbitrary gates, discontinuities or disorder kernels.

During development, one workflow test initially referenced an incorrect NPZ key
and left the archive unclosed after that assertion failed. The test was corrected
to the established retained_phi_per_sqrt_nm key and context-managed loading.
The actual CLI run had succeeded; no numerical result was modified to pass.
The corrected workflow subset reported 24 passed in 26.47s. A subsequent
final audit added direct unconditional target overlap at subnormal throughput
and immutable copies/hashes of training arrays. Its focused core tests passed
(19 passed in 1.61s), followed by the complete 191-test installed-package run above.
Development logs and the preliminary bundle remain in results, separate from
the installed-package evidence used here.

## Exact examples and normalization

Complete configurations:
[full comparison](../examples/optimize.json) and
[quick comparison](../examples/optimize_quick.json).
Their saved config.json files match exactly.

| Setting | Full example |
| --- | --- |
| Domain, channel | Domain [−40,40] nm; channel [−30,30] nm |
| Spatial grid | 201 domain nodes, dx=0.4 nm; channel endpoints on grid |
| Energy grid | 12–68 meV, 57 nodes |
| Mass and leads | Illustrative m*/m_e=0.067; both leads 0 meV |
| Incoming packet | Gaussian density center 40 meV, standard deviation 6 meV |
| Target | Free channel with identical grid, mass, leads and reference planes |
| Gates | Four Gaussian profiles at −18,−6,6,18 nm, width 4 nm |
| Fixed amplitudes | [8,15,12,6] meV |
| Bounds | Each [−25,25] meV; summed gate absolute bound 60 meV |
| Support/slope | 5 nm gate taper; maximum sampled gate slope 5 meV/nm |
| Disorder | Gaussian covariance sigma=2 meV, ell=5 nm, hard channel cutoff |
| KL | K=6; Var(eta)=lambda and Phi.T W Phi=I |
| Sensitivity | Incoming probability density weighting; minimize J/sigma²; raw J also saved |
| Clean/MC loss | 0.5(1−P)+0.5(1−F), raw conditional target fidelity |
| Constraints | Pmin sweep [0.85,0.98], Fmin=0.95, scaled feasibility tolerance 1e-7 |
| Search | SLSQP, 2 common starts, 360 RHS-equivalent work cap per method/floor |
| Local settings | maxiter=40, ftol=1e-7, selected gate step=0.01 meV |
| Gate diagnostic steps | 0.1,0.01,0.005,1e-7 meV |
| Mode diagnostic steps | 0.1,0.01,0.001,1e-6,1e-9 meV sqrt(nm) |
| Seeds | Initialization 41001; training 42001; validation 43001; held out 44001 |
| Ensemble sizes | Training 4; validation 8; held out 16 |

The quick example uses one floor (0.85), a 120-unit cap, maxiter=12, and
3/4/8 ensemble sizes. Other choices are unchanged. Its smaller ensembles share
the full example's streams, so the runs are not independent replications.
Both configurations were specified before the first example was evaluated.

The retained integrated variance fraction is **86.241119%**. This is
retained-KL disorder evaluation, not evidence about the discarded modes.
The default hard cutoff and finite grids remain explicit approximations.
The optional normalized objective removes nominal sigma² scaling; it does
not remove discretization or KL-truncation error.

## Derivative checks

All preflight and frozen-design postflight checks passed. At the common start,
the maximum selected-versus-half-step gate Jacobian difference was
6.1611e-10 in component-native units per meV. The configured numerical screen
is atol=1e-7 plus rtol=0.005 times the half-step component magnitude. Objective
and P/F component units differ; this is a numerical componentwise test, not
a physical error bound. The maximum is dominated by common clean constraints,
so the three maximum-error curves overlap; every objective component was
also checked and is saved separately.

The corresponding tiny gate step (1e-7 meV) gave 6.0739e-9 maximum discrepancy,
showing noise growth. The selected step was not retuned after seeing this.
At the frozen B/C/D designs, maximum half-step discrepancies were respectively
1.5515e-10, 2.7274e-10 and 4.4298e-11.

| Mode step (meV sqrt(nm)) | Maximum complex derivative error (1/(meV sqrt(nm))) |
| ---: | ---: |
| 0.1 | 2.33041e-06 |
| 0.01 | 2.33056e-08 |
| 0.001 | 2.3617e-10 |
| 1e-06 | 2.7959e-08 |
| 1e-09 | 3.18218e-05 |

Every retained mode met the 1e-7 absolute screen at a resolved step.
The smallest mode step had a represented-direction error of only 5.0716e-6,
so solve/subtraction noise mattered before the potential directions disappeared.
This supports the derivative of the discrete model, not arbitrary continuum
accuracy or a guarantee that first-order theory holds at finite disorder.

## Measured comparison and limitations

Both throughput-floor sweeps selected the same B/C/D vectors. Their clean
throughputs already exceeded 0.98, so the stricter constraint was inactive for
those selected designs. This is a measured coincident result, not an invented
Pareto frontier. A remained at its fixed vector and failed the stricter floor:
its P residual was −0.0126066962. It is plotted and reported as infeasible there.

Full-example values below use the 16 shared held-out realizations. P and F
are always separate; mean loss is the declared equal-weight combination.

| Method | Clean P | Clean F | Raw J | Held-out mean P | Held-out mean F | Held-out mean loss |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| A_fixed | 0.967393304 | 0.983757029 | 0.038283089 | 0.967297335 | 0.984562776 | 0.024069944 |
| B_clean | 0.999999998 | 1.000000000 | 0.031816918 | 0.999748142 | 0.999822293 | 0.000214783 |
| C_monte_carlo | 0.999959617 | 0.999909102 | 0.031324592 | 0.999617105 | 0.999670984 | 0.000355955 |
| D_sensitivity | 0.999349641 | 0.967873951 | 0.022521052 | 0.998640244 | 0.966766314 | 0.017296721 |

D reduced J relative to A by **41.172322%**, but that did not make it the best
target-state method. B had the highest held-out throughput and fidelity, and
the smallest mean held-out loss among these runs. D also had lower conditional
target fidelity than A while improving throughput. J measures a different
quantity, including global-phase sensitivity that F ignores.

The paired held-out difference in mean loss D−B was 0.0170819383, with sample
standard error 0.0003376082 over 16 paired draws. This is descriptive evidence
for this declared finite experiment, not a universal ranking or a claim about
fabricated devices. C's small training set and exhausted budget are limitations;
its result does not establish the general inferiority of Monte Carlo methods.

The selected gate vectors (meV) are:

| Method | Amplitudes u_j (meV) |
| --- | --- |
| A_fixed | [8, 15, 12, 6] |
| B_clean | [0.012665218, -0.00018496986, -0.014207437, 0.0088110355] |
| C_monte_carlo | [3.1378622, -10.048635, 1.4124146, 0.10181499] |
| D_sensitivity | [-25, -25, -25, -25] |

D hit the lower gate bounds and SLSQP reported success from both starts
(3 and 5 iterations). It used 216 of 360 allowed work units per floor.
B and C consumed all 360 units and stopped on work budget at both starts;
their returned designs are best feasible observed trials, not convergence claims.
The histories preserve 360 B trials, 72 C trials and 72 D trials per floor.
No extra work was spent to force an improvement or use unused D capacity.

## Measured cost

One work unit is a complete energy-grid RHS sweep. An implicit response costs
three units (one forward plus two response RHS), with actual factorization and
forward-solve counts also recorded. The table sums both floor sweeps plus
preflight, postflight and frozen-design evaluation; shared setup is separate.

| Method | Total work units | Forward energy solves | All energy RHS solves | Factorizations | Measured seconds |
| --- | ---: | ---: | ---: | ---: | ---: |
| A_fixed | 64 | 3420 | 3648 | 3534 | 0.163039 |
| B_clean | 879 | 49875 | 50103 | 49989 | 2.329403 |
| C_monte_carlo | 1267 | 71991 | 72219 | 72105 | 3.383325 |
| D_sensitivity | 830 | 20178 | 47310 | 33744 | 1.848176 |

Available search budgets were equal; actual totals and wall times were not.
Wall times are observations on this Mac, not portable performance claims.
The full bundle took 11.080371 seconds including setup, plotting and writing.
Metrics retain the separate phases and actual counts rather than hiding audits
or response solves outside a claimed total budget.

## Artifacts and remaining blockers

The final full and quick bundles each contain 27 hashed artifacts plus a manifest.
Every hash was recomputed, both configs match their examples, and source identity
matches the installed code. Candidate logs, raw complex amplitudes/derivatives,
training/evaluation z and eta, potentials, seeds and numerical settings are saved.
The frozen-selection hash is checked after evaluation. Results and virtual
environments remain Git-ignored.

- [Observed trade-offs](../results/stage4-release-optimize/optimization_tradeoffs.png)
- [Search progress and budget use](../results/stage4-release-optimize/optimization_progress.png)
- [All method costs by phase](../results/stage4-release-optimize/optimization_costs.png)
- [Derivative-step diagnostics](../results/stage4-release-optimize/optimization_steps.png)
- [Frozen potential profiles](../results/stage4-release-optimize/optimized_potentials.png)
- [Comparison table](../results/stage4-release-optimize/comparison.csv)
- [Paired held-out differences](../results/stage4-release-optimize/paired_heldout.csv)
- [Exact equations and conventions](optimization.md)
- [Architecture and file tree](architecture.md)

There are no unresolved execution blockers. The scientific limitations remain
finite resolution, omitted KL modes, small ensembles, local/budget-limited
searches, and the gap between a complex-amplitude sensitivity surrogate and
target-state fidelity. Clean feasibility does not guarantee robustness under
all disorder. No global-optimality, publication, novelty, or universal improvement
claim is made.

