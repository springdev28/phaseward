"""Audit already frozen designs without searching, tuning or drawing new disorder.

Re-evaluate clean feasibility against independent recurrence amplitudes and
refine space/energy for the same frozen gate vectors. These are numerical
diagnostics, not fresh held-out evidence or a design-selection rule.
"""

from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path

import numpy as np
from scipy.integrate import trapezoid

from independent_transport_oracles import recurrence_scattering
from qwave.experiment_support import invocation_git_identity, write_table
from qwave.gui_results import load_bundle
from qwave.optimization import prepare_problem
from qwave.optimization_config import OptimizeConfig
from qwave.potentials import sample_potential
from qwave.provenance import sha256_file, source_identity
from qwave.scattering import solve_scattering
from qwave.units import physical_constants
from qwave.diagnostics import cpu_environment, software_versions


def spectral_metrics(energy, incoming, t, target):
    """Independent SciPy quadrature of normalized complex spectral overlaps."""
    probability = float(trapezoid(abs(incoming*t)**2, energy))
    target_probability = float(trapezoid(abs(incoming*target)**2, energy))
    fidelity = float(abs(trapezoid((incoming*target).conj()*(incoming*t), energy))**2/(probability*target_probability))
    return probability, fidelity


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    bundle = load_bundle(args.run.resolve(), args.run.resolve().parent)
    summary = bundle.json('summary.json')
    frozen = bundle.json('frozen_candidates.json')
    assert not frozen['evaluation_draws_generated']
    candidates = {row['run_id']: row for row in frozen['candidates']}
    args.output.mkdir(parents=True, exist_ok=False)
    rows, arrays, checks = [], {}, []
    for run in summary['runs']:
        saved = candidates[run['run_id']]
        if saved['u_mev'] is None:
            checks.append(dict(run_id=run['run_id'], status='no_frozen_candidate'))
            continue
        u = np.array(saved['u_mev'])
        original = bundle.manifest['resolved_cases'][run['case']]
        base = prepare_problem(OptimizeConfig.from_mapping(original))
        device = base.device
        t, r, condition = recurrence_scattering(device.x_nm, base.potential(u), device.energy_mev,
            mass_ratio=device.scatter.effective_mass_ratio, left=device.scatter.left_lead_mev, right=device.scatter.right_lead_mev)
        target, _, _ = recurrence_scattering(device.x_nm, sample_potential(device.x_nm, original['target_potential']),
            device.energy_mev, mass_ratio=device.scatter.effective_mass_ratio,
            left=device.scatter.left_lead_mev, right=device.scatter.right_lead_mev)
        probability, fidelity = spectral_metrics(device.energy_mev, base.packet.amplitude, t, target)
        original_metrics = run['reported_candidate']
        metric_error = max(abs(probability-original_metrics['p_transmitted']), abs(fidelity-original_metrics['raw_fidelity']))
        assert metric_error < 2e-9, 'independent coarse-grid metric mismatch'
        arrays[run['run_id']+'_recurrence_t'] = t
        arrays[run['run_id']+'_recurrence_r'] = r
        checks.append(dict(run_id=run['run_id'], independent_metric_error=metric_error,
                           max_reference_condition=float(max(condition)), status='independent_metrics_passed'))
        for axis in ['space', 'energy']:
            for factor in [1, 2, 4]:
                config = deepcopy(original)
                key = 'grid_points' if axis=='space' else 'energy_points'
                config['model']['scattering'][key] = factor*(original['model']['scattering'][key]-1)+1
                problem = prepare_problem(OptimizeConfig.from_mapping(config))
                d = problem.device
                result = solve_scattering(d.x_nm, problem.potential(u), d.energy_mev, **problem.arguments)
                p, f = spectral_metrics(d.energy_mev, problem.packet.amplitude, result.t, problem.target_t)
                residuals, scaled = problem.residuals(u, dict(p_transmitted=p, raw_fidelity=f), run['minimum_clean_transmission'])
                feasible = bool(min(scaled) >= -config['constraints']['feasibility_tolerance'] and p >= 1e-8)
                if factor == 1:
                    assert feasible == saved['feasible'], 'frozen feasibility mismatch'
                prefix = run['run_id']+f'_{axis}_{factor}'
                arrays.update({prefix+'_t': result.t, prefix+'_r': result.r, prefix+'_x_nm': d.x_nm,
                    prefix+'_potential_mev': problem.potential(u), prefix+'_energy_mev': d.energy_mev})
                rows.append(dict(run_id=run['run_id'], axis=axis, refinement=factor,
                    grid_points=len(d.x_nm), energy_points=len(d.energy_mev), p_transmitted=p, raw_fidelity=f,
                    transmission_residual=residuals['transmission'], fidelity_residual=residuals['fidelity'],
                    minimum_scaled_residual=float(min(scaled)), feasible=feasible,
                    max_conservation_error=float(max(result.conservation_error))))
    np.savez_compressed(args.output/'arrays.npz', **arrays)
    write_table(args.output/'clean_refinement.csv', rows)
    details = dict(independent_checks=checks, clean_refinement=rows,
        scope='Clean numerical refinement only. No disorder draws, searches, tuning or selection.',
        axes='Separate spatial and energy refinement, factors 1,2,4; neither substitutes for disorder/training replication.')
    (args.output/'checks.json').write_text(json.dumps(details, indent=2, allow_nan=False)+'\n')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5), constrained_layout=True)
    for axis, ax in zip(['space', 'energy'], axes):
        for run_id in candidates:
            selected = [r for r in rows if r['run_id']==run_id and r['axis']==axis]
            if not selected:
                continue
            reference = selected[-1]
            errors = [max(abs(r['p_transmitted']-reference['p_transmitted']),
                          abs(r['raw_fidelity']-reference['raw_fidelity'])) for r in selected[:-1]]
            ax.plot([r['refinement'] for r in selected[:-1]], errors, 'o-', label=run_id.replace('declared_device_', ''))
        ax.set(xlabel=f'{axis.capitalize()} resolution factor (1)', ylabel='Max |P or raw F − finest| (1)',
               title=f'Frozen clean designs: {axis} refinement')
        ax.set_yscale('symlog', linthresh=1e-13)
        ax.legend(fontsize=6)
    for extension in ['png', 'svg', 'pdf']:
        fig.savefig(args.output/f'frozen_clean_refinement.{extension}', dpi=180)
    plt.close(fig)
    (args.output/'figure_description.md').write_text('Clean metrics for every frozen gate vector, compared with its fourfold-refined value. This tests neither global optimizer optimality nor held-out disorder robustness. Infeasible fixed baselines remain in the tables and figure.\n')
    manifest = dict(manifest_version=1, project='Phaseward', status='completed',
        created_utc=datetime.now(timezone.utc).isoformat(), run=str(args.run.resolve()),
        original_manifest_sha256=bundle.fingerprint, source=source_identity(),
        invocation_git=invocation_git_identity(), constants_SI=physical_constants(),
        software_versions=software_versions(), hardware=cpu_environment(),
        config=dict(resolved_cases=bundle.manifest['resolved_cases'], frozen_candidates=frozen,
                    refinement_factors=[1, 2, 4], axes=['space', 'energy'], newly_drawn_seeds=[]),
        units=dict(position='nm', energy='meV', amplitudes='dimensionless', P_and_F='dimensionless'),
        approximations='Same discrete physics and phase planes; gate peak sampling follows each declared grid; no disorder generated.',
        verification_sources={p.name: sha256_file(p) for p in [Path(__file__), Path(__file__).with_name('independent_transport_oracles.py')]},
        outputs={p.name: dict(sha256=sha256_file(p), size_bytes=p.stat().st_size) for p in args.output.iterdir() if p.is_file()})
    (args.output/'manifest.json').write_text(json.dumps(manifest, indent=2, allow_nan=False)+'\n')
    print(json.dumps(dict(status='completed', designs=len(checks), clean_refinement_rows=len(rows),
        max_independent_metric_error=max(c.get('independent_metric_error',0) for c in checks), output=str(args.output))))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
