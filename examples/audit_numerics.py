"""Independent, reproducible numerical audit; all figures use the saved arrays.

Run: python examples/audit_numerics.py --output results/independent-audit
References live in independent_transport_oracles.py and never import qwave.
These numerical checks do not establish robustness of an optimized device.
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import importlib.metadata
import json
import platform
from pathlib import Path

import numpy as np
from scipy.linalg import cholesky
from scipy.stats import chi2

from independent_transport_oracles import (exponential_packet_exact, impurity_amplitudes,
    kinetic_coefficient, rectangular_matching, recurrence_scattering)
from qwave.disorder import covariance_matrix, covariance_modes, sample_disorder
from qwave.experiment_support import invocation_git_identity
from qwave.potentials import sample_potential
from qwave.provenance import sha256_file, source_identity
from qwave.scattering import ScatteringError, solve_scattering
from qwave.sensitivity import derivative_study, transmission_gradient
from qwave.wavepackets import DelaySearch, analyze_packet

MASS_RATIO = .067
COVARIANCE_SEEDS = [935001, 935002]  # Audit only, not optimization or evaluation draws.


def check(name: str, observed: float, limit: float, reason: str) -> dict:
    """A numerical regression criterion, with its interpretation stated explicitly."""
    return dict(check=name, observed=float(observed), limit=float(limit),
                passed=bool(np.isfinite(observed) and observed <= limit), reason=reason)


def scattering_checks() -> tuple[list[dict], dict]:
    """Full S-matrix, independent recurrence, translation phase, and continuum limit."""
    x = np.linspace(-15, 15, 61)
    energy = np.array([9., 17., 31., 59.])
    potential = 10*np.exp(-((x+3)/3)**2)+6*np.exp(-((x-5)/2)**2)
    left = solve_scattering(x, potential, energy, effective_mass_ratio=MASS_RATIO, right_lead_mev=4.)
    right = solve_scattering(x, potential[::-1], energy, effective_mass_ratio=MASS_RATIO, left_lead_mev=4.)
    ref_t, ref_r, condition = recurrence_scattering(x, potential, energy, mass_ratio=MASS_RATIO, right=4.)
    s = np.empty((len(energy), 2, 2), complex)
    s[:, 0, 0], s[:, 0, 1], s[:, 1, 0], s[:, 1, 1] = left.r, right.t, left.t, right.r
    unitary_error = np.max(abs(s.conj().transpose(0, 2, 1) @ s-np.eye(2)))
    # 2e-10 is a regression guard for small, conditioned systems, not physical accuracy.
    checks = [check('two_sided_unitarity', unitary_error, 2e-10, 'S^dagger S including cross-channel complex products'),
              check('reciprocity_complex_t', np.max(abs(left.t-right.t)), 2e-10, 'time reversal, unequal propagating leads'),
              check('independent_recurrence_t_r', max(np.max(abs(left.t-ref_t)), np.max(abs(left.r-ref_r))),
                    2e-10, 'independent 2x2 boundary matching; condition recorded; no opaque-barrier use')]
    compact = np.zeros(len(x)); compact[23:30] = [2, 4, 6, 8, 6, 4, 2]
    a = solve_scattering(x, compact, energy, effective_mass_ratio=MASS_RATIO)
    b = solve_scattering(x, np.roll(compact, 5), energy, effective_mass_ratio=MASS_RATIO)
    q = np.arccos(1-energy*(x[1]-x[0])**2/(2*kinetic_coefficient(MASS_RATIO)))
    checks.append(check('translation_phase', max(np.max(abs(a.t-b.t)), np.max(abs(b.r-a.r*np.exp(10j*q)))),
                        2e-10, 'same lead planes: t unchanged, r multiplied by exp(2ik displacement)'))
    hopping = kinetic_coefficient(MASS_RATIO)/(x[1]-x[0])**2
    rejected = 0
    for forbidden in [-1., 0., 4*hopping, 4*hopping+1]:
        try:
            solve_scattering(x, compact, [forbidden], effective_mass_ratio=MASS_RATIO)
        except ScatteringError:
            rejected += 1
    checks.append(check('forbidden_energy_acceptances', 4-rejected, 0, 'negative/threshold/upper-edge/above-band rejected'))
    benchmark_energy = np.array([7., 18., 30., 47., 75.])
    expected_t, expected_r = rectangular_matching(benchmark_energy, height=30., width=8., plane_distance=40., mass_ratio=MASS_RATIO)
    spacing, errors, t_values, r_values = [], [], [], []
    for count in [161, 321, 641, 1281]:
        grid = np.linspace(-20, 20, count)
        barrier = sample_potential(grid, dict(kind='rectangular', height_mev=30., width_nm=8., center_nm=0., offset_mev=0.))
        actual = solve_scattering(grid, barrier, benchmark_energy, effective_mass_ratio=MASS_RATIO)
        spacing.append(grid[1]-grid[0])
        t_values.append(actual.t); r_values.append(actual.r)
        errors.append(max(np.max(abs(actual.t-expected_t)), np.max(abs(actual.r-expected_r))))
    orders = np.log2(np.array(errors[:-1])/errors[1:])
    checks.extend([
        check('rectangular_complex_finest_error', errors[-1], 2e-4, '4x4 continuum matching below/at/above barrier; assess with measured order'),
        check('rectangular_order_shortfall', max(0., 1.7-float(min(orders))), 0., 'second-order model; order >=1.7 across these cell-averaged grids'),
    ])
    return checks, dict(scatter_x_nm=x, scatter_energy_mev=energy, scatter_potential_mev=potential,
        scatter_t=left.t, scatter_r=left.r, scatter_oracle_t=ref_t, scatter_oracle_r=ref_r,
        scatter_S=s, recurrence_condition=condition, rectangle_energy_mev=benchmark_energy,
        rectangle_spacing_nm=np.array(spacing), rectangle_complex_error=np.array(errors), rectangle_orders=orders,
        rectangle_t=np.array(t_values), rectangle_r=np.array(r_values),
        rectangle_oracle_t=expected_t, rectangle_oracle_r=expected_r)


def sensitivity_checks() -> tuple[list[dict], dict]:
    """Nonzero single-site impurity identity independently tests phase derivatives."""
    x = np.arange(41.)*2
    energy = np.array([5., 22., 65.])
    site, height = 17, 40.
    potential = np.zeros(len(x)); potential[site] = height
    t, r, derivative_u = impurity_amplitudes(energy, height=height, spacing=2., count=len(x), site=site, mass_ratio=MASS_RATIO)
    response = transmission_gradient(x, potential, energy, effective_mass_ratio=MASS_RATIO)
    shape = np.zeros((len(x), 1)); shape[site, 0] = 1/np.sqrt(2.)
    derivative_eta = derivative_u/np.sqrt(2.)
    steps = np.array([2., 1., .5, .01, 1e-12])
    study = derivative_study(x, potential, energy, shape, steps, effective_mass_ratio=MASS_RATIO)
    fd_error = np.max(abs(study.finite_difference[:, :, 0]-derivative_eta), axis=1)
    strengths = np.array([.125, .25, .5, 1., 4., 16.])
    errors, full = [], []
    for delta in strengths:
        perturbed = potential+delta*shape[:, 0]
        actual = solve_scattering(x, perturbed, energy, effective_mass_ratio=MASS_RATIO)
        full.append(actual.t)
        errors.append(np.max(abs(actual.t-t-delta*derivative_eta)))
    orders = np.log2(np.array(errors[1:4])/errors[:3])
    checks = [
        check('single_impurity_t_r', max(np.max(abs(response.baseline.t-t)), np.max(abs(response.baseline.r-r))), 2e-11,
              'exact lattice identity at nonzero impurity height'),
        check('single_impurity_analytic_derivative', np.max(abs(response.dt_dpotential_per_mev[:, site]-derivative_u)), 2e-12,
              'independent analytic dt/dU, without production amplitude in expected value'),
        check('central_difference_best_error', min(fd_error), 2e-9, 'eta derivative; steps carry meV sqrt(nm)'),
        check('central_difference_order_shortfall', max(0., 1.9-float(min(np.log2(fd_error[:2]/fd_error[1:3])))), 0.,
              'second-order central differences before cancellation'),
        check('taylor_order_shortfall', max(0., 1.9-float(min(orders))), 0., 'small-disorder Taylor remainder must be quadratic'),
    ]
    return checks, dict(impurity_x_nm=x, impurity_potential_mev=potential, impurity_energy_mev=energy,
        impurity_t=response.baseline.t, impurity_r=response.baseline.r, impurity_oracle_t=t,
        impurity_oracle_r=r, impurity_oracle_dt_deta=derivative_eta,
        impurity_implicit_dt_deta=response.dt_dpotential_per_mev@shape,
        derivative_steps_mev_sqrt_nm=steps, derivative_error=fd_error,
        derivative_finite_difference=study.finite_difference,
        taylor_eta_mev_sqrt_nm=strengths, taylor_complex_error=np.array(errors), taylor_full_t=np.array(full),
        taylor_small_orders=orders)


def covariance_checks() -> tuple[list[dict], dict]:
    """Separate Cholesky draws and Gaussian sampling intervals test weighted KL."""
    x = np.linspace(0., 20., 21)
    sigma, ell, count = 3., 1.2, 6000
    target = sigma**2*np.exp(-.5*((x[:, None]-x[None, :])/ell)**2)
    production = covariance_matrix(x, sigma_mev=sigma, correlation_length_nm=ell)
    modes = covariance_modes(x, production, retained_modes=8)
    kl = sample_disorder(modes, sample_count=count, seed=COVARIANCE_SEEDS[0]).full_mev
    independent = np.random.default_rng(COVARIANCE_SEEDS[1]).standard_normal((count, len(x))) @ cholesky(target, lower=True).T
    covariances = np.array([np.cov(kl, rowvar=False), np.cov(independent, rowvar=False)])
    # Exact marginal chi-square law; Bonferroni accounts for all 42 variance tests.
    tail = .001/(2*2*len(x))
    interval = chi2.ppf([tail, 1-tail], count-1)/(count-1)
    ratios = np.diagonal(covariances, axis1=1, axis2=2)/sigma**2
    se = np.sqrt((target**2+np.outer(np.diag(target), np.diag(target)))/(count-1))
    z = (covariances-target)/se
    # Cholesky fields projected onto quadrature-orthonormal shapes must have Var(eta)=lambda.
    projected = independent @ (modes.weights_nm[:, None]*modes.shapes_per_sqrt_nm)
    modal_ratio = np.var(projected, axis=0, ddof=1)/modes.eigenvalues_mev2_nm
    modal_interval = chi2.ppf([.001/(2*len(x)), 1-.001/(2*len(x))], count-1)/(count-1)
    checks = [check('covariance_formula', np.max(abs(production-target)), 1e-13, 'separately written Gaussian covariance formula'),
              check('covariance_variance_interval_violations', np.sum((ratios<interval[0]) | (ratios>interval[1])), 0,
                    'exact chi-square marginal variance law, family alpha=.001 by Bonferroni'),
              check('covariance_entry_standard_errors', np.max(abs(z)), 6.,
                    'Gaussian Wishart entry variance; conservative diagnostic, not a simultaneous exact CI'),
              check('independent_projected_mode_variance_violations', np.sum((modal_ratio<modal_interval[0]) | (modal_ratio>modal_interval[1])),
                    0., 'Cholesky sampler projected onto weighted KL: Var(eta)=lambda')]
    return checks, dict(covariance_x_nm=x, covariance_target_mev2=target, covariance_sample_mev2=covariances,
        covariance_kl_samples_mev=kl, covariance_cholesky_samples_mev=independent,
        covariance_eigenvalues_mev2_nm=modes.eigenvalues_mev2_nm, covariance_modal_variance_ratio=modal_ratio,
        covariance_retained_variance_fraction=np.array(sum(modes.retained_eigenvalues)/sum(modes.eigenvalues_mev2_nm)),
        covariance_variance_interval=interval, covariance_projected_variance_interval=modal_interval,
        covariance_sigma_mev=np.array(sigma), covariance_ell_nm=np.array(ell), covariance_seeds=np.array(COVARIANCE_SEEDS))


def packet_checks() -> tuple[list[dict], dict]:
    """Closed-form non-Gaussian spectral integrals check complex overlap and lag."""
    expected = np.array(exponential_packet_exact(40., .015, .08))
    counts = [41, 81, 161, 321, 641]
    values = []
    for count in counts:
        energy = np.linspace(10., 50., count)
        incoming = np.ones(count)/np.sqrt(40.)
        t = np.exp((-.015+.055j)*(energy-10))
        target = np.exp(-.025j*(energy-10))
        result = analyze_packet(energy, incoming, t, target,
            delay=DelaySearch(min_ps=-.1, max_ps=.1, grid_points=101, xatol_ps=1e-10))
        values.append([result.p_transmitted, result.raw_fidelity, result.aligned_fidelity, result.estimated_delay_ps])
    values = np.array(values)
    errors = abs(values-expected)
    orders = np.log2(errors[:-1, :3]/errors[1:, :3])
    global_phase = analyze_packet(energy, incoming, t*np.exp(1.234j), target)
    tiny = analyze_packet(energy, incoming, t*1e-7, target)
    checks = [check('packet_analytic_probability_and_fidelities', np.max(errors[-1, :3]), 2e-6,
                    'independent closed integrals; synthetic uniform spectrum, not a device result'),
              check('packet_quadrature_order_shortfall', max(0., 1.95-float(np.min(orders))), 0.,
                    'trapezoidal second-order convergence for this smooth spectral test'),
              check('packet_delay_ps', errors[-1, 3], 2e-7, 'analytic bounded lag hbar*(b-c); amplitude distortion remains'),
              check('global_phase_fidelity', abs(global_phase.raw_fidelity-result.raw_fidelity), 2e-14, 'complex normalized overlap'),
              check('tiny_transmission_hidden', int(not tiny.low_transmission), 0., 'conditional fidelity must not remove low-throughput flag'),
              check('tiny_probability_scaling', abs(tiny.p_transmitted/(1e-14*result.p_transmitted)-1), 2e-14,
                    'amplitude factor squared in probability; no display renormalization')]
    return checks, dict(packet_counts=np.array(counts), packet_values=values, packet_exact=expected,
        packet_errors=errors, packet_orders=orders, packet_energy_mev=energy,
        packet_incoming_per_sqrt_mev=incoming, packet_transmission=t, packet_target=target)


def save_figures(output: Path, data: dict) -> None:
    """Plot saved measurements, with units and reference distinctions visible."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(2, 2, figsize=(11, 8), constrained_layout=True)
    ax = axes[0, 0]
    ax.loglog(data['rectangle_spacing_nm'], data['rectangle_complex_error'], 'o-')
    ax.set(xlabel='Spatial spacing (nm)', ylabel='Max complex amplitude error (1)', title='Continuum rectangular matching: t and r')
    ax = axes[0, 1]
    ax.loglog(data['derivative_steps_mev_sqrt_nm'], data['derivative_error'], 'o-')
    ax.set(xlabel=r'Coefficient step (meV $\sqrt{\mathrm{nm}}$)', ylabel=r'Max derivative error (meV$^{-1}$ nm$^{-1/2}$)', title='Analytic single-impurity derivative')
    ax = axes[1, 0]
    for index, label in enumerate(['P transmitted', 'Raw conditional fidelity', 'Aligned conditional fidelity']):
        ax.loglog(40/(data['packet_counts']-1), data['packet_errors'][:, index], 'o-', label=label)
    ax.set(xlabel='Energy spacing (meV)', ylabel='Absolute error (1)', title='Synthetic spectral integral; independent exact values')
    ax.legend(fontsize=8)
    ax = axes[1, 1]
    ax.plot(data['covariance_x_nm'], np.diag(data['covariance_target_mev2']), label='Target')
    for cov, label in zip(data['covariance_sample_mev2'], ['KL sampler', 'Independent Cholesky sampler']):
        ax.plot(data['covariance_x_nm'], np.diag(cov), label=label)
    ax.set(xlabel='Position (nm)', ylabel=r'Potential variance (meV$^2$)', title='6,000 draws per sampler; fixed audit seeds')
    ax.legend(fontsize=8)
    for suffix in ['png', 'svg', 'pdf']:
        fig.savefig(output/f'independent_checks.{suffix}', dpi=180)
    plt.close(fig)


def main() -> int:
    """Save raw arrays, criteria, source identity and figures without overwriting."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    checks, arrays = [], {}
    for function in [scattering_checks, sensitivity_checks, covariance_checks, packet_checks]:
        group, data = function()
        checks.extend(group); arrays.update(data)
    np.savez_compressed(args.output/'arrays.npz', **arrays)
    (args.output/'checks.json').write_text(json.dumps(checks, indent=2, allow_nan=False)+'\n')
    with (args.output/'checks.csv').open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(checks[0]))
        writer.writeheader(); writer.writerows(checks)
    save_figures(args.output, arrays)
    (args.output/'figure_description.md').write_text(
        'Numerical validation only. Top left: complex t and r convergence toward independent continuum boundary matching. '
        'Top right: centered derivative step refinement and cancellation against a lattice impurity identity. '
        'Bottom left: exact synthetic spectral integrals. Bottom right: independently sampled covariance variance. '
        'Every point comes from arrays.npz; tests and criteria are in checks.csv. No optimized-device conclusion.\n')
    metadata = dict(created_utc=datetime.now(timezone.utc).isoformat(), project='Phaseward',
        status='completed' if all(row['passed'] for row in checks) else 'failed_checks',
        scope='Independent numerical audit; not a research robustness trial',
        mass_ratio=MASS_RATIO, units=dict(position='nm', energy='meV', delay='ps', eta='meV sqrt(nm)'),
        configuration='All grids, spectra, potentials, steps and seeds are stored in arrays.npz; constants and criteria are in audit sources.',
        approximations=['constant mass, coherent elastic 1D finite difference', 'finite lead band, open channels only',
                        'cell-averaged rectangular potential; continuum extrapolation tested',
                        'Gaussian covariance on finite grid; 8 retained modes, full draws checked',
                        'packet check is a synthetic uniform energy spectrum with exponential attenuation and phase'],
        seeds=COVARIANCE_SEEDS, source=source_identity(), invocation_git=invocation_git_identity(),
        verification_sources={p.name: sha256_file(p) for p in [Path(__file__), Path(__file__).with_name('independent_transport_oracles.py')]},
        versions={name: importlib.metadata.version(name) for name in ['qwave', 'numpy', 'scipy', 'matplotlib']},
        hardware=dict(platform=platform.platform(), machine=platform.machine(), python=platform.python_version()),
        outputs={p.name: sha256_file(p) for p in sorted(args.output.iterdir()) if p.is_file()})
    (args.output/'manifest.json').write_text(json.dumps(metadata, indent=2, allow_nan=False)+'\n')
    print(json.dumps(dict(status=metadata['status'], checks=len(checks), failed=[r['check'] for r in checks if not r['passed']], output=str(args.output))))
    return 0 if metadata['status']=='completed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
