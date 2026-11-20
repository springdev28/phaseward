"""Independent references live outside qwave and never call its solver."""

import importlib.util
import json
from pathlib import Path
import sys

import pytest
import numpy as np
from scipy.integrate import trapezoid


@pytest.fixture(scope='module')
def audit():
    """Load the executable audit without changing which installed qwave is tested."""
    examples = Path(__file__).parents[1]/'examples'
    for name in ['independent_transport_oracles', 'audit_numerics']:
        spec = importlib.util.spec_from_file_location(name, examples/f'{name}.py')
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize('group', ['scattering_checks', 'sensitivity_checks', 'covariance_checks', 'packet_checks'])
def test_independent_numerical_checks(audit, group) -> None:
    """Expected values come from separate matching, analytic identities or sampling laws."""
    checks, _ = getattr(audit, group)()
    assert checks
    assert all(row['passed'] for row in checks), [row for row in checks if not row['passed']]


def test_optimization_clean_feasibility_from_independent_amplitudes(audit) -> None:
    """Recalculate P, complex overlap and all physical bounds outside the evaluator."""
    from qwave.optimization import CandidateEvaluator, prepare_problem
    from qwave.optimization_config import OptimizeConfig
    from qwave.potentials import sample_potential
    config = json.loads((Path(__file__).parents[1]/'examples/optimize_quick.json').read_text())
    config['model']['scattering']['grid_points'] = 81
    problem = prepare_problem(OptimizeConfig.from_mapping(config))
    x, energy = problem.device.x_nm, problem.device.energy_mev
    target, _, _ = audit.recurrence_scattering(x, sample_potential(x, config['target_potential']), energy,
                                              mass_ratio=config['model']['scattering']['effective_mass_ratio'])
    a = problem.packet.amplitude
    floor = .99
    results = []
    for u in [np.zeros(4), np.full(4, 25.)]:
        evaluator = CandidateEvaluator(problem, 'B_clean', floor, np.empty((0, len(x))))
        row = evaluator.evaluate(u)
        t, _, _ = audit.recurrence_scattering(x, problem.potential(u), energy,
                                             mass_ratio=config['model']['scattering']['effective_mass_ratio'])
        probability = trapezoid(abs(a*t)**2, energy)
        p_target = trapezoid(abs(a*target)**2, energy)
        fidelity = abs(trapezoid((a*target).conj()*(a*t), energy))**2/(p_target*probability)
        assert row['p_transmitted'] == pytest.approx(probability, abs=2e-10)
        assert row['raw_fidelity'] == pytest.approx(fidelity, abs=2e-10)
        profile = problem.device.gates.shapes@u
        independently_feasible = (probability >= floor and fidelity >= config['constraints']['minimum_clean_fidelity']
            and np.all(u >= problem.bounds[:, 0]) and np.all(u <= problem.bounds[:, 1])
            and max(abs(profile)) <= config['model']['gates']['total_abs_bound_mev']
            and max(abs(np.diff(profile)/np.diff(x))) <= config['constraints']['max_gate_gradient_mev_per_nm'])
        assert row['feasible'] == independently_feasible
        results.append(row['feasible'])
    assert results == [True, False]


def test_physical_opaque_impurity_cannot_hide_behind_conditional_fidelity(audit) -> None:
    """Real lossless scattering can have high conditional F and unusable throughput."""
    from qwave.scattering import solve_scattering
    from qwave.wavepackets import analyze_packet
    x, energy = np.arange(41.)*2, np.linspace(39.9, 40.1, 101)
    potential = np.zeros(41); potential[17] = 1e9
    actual = solve_scattering(x, potential, energy, effective_mass_ratio=.067)
    reference, _, _ = audit.impurity_amplitudes(energy, height=0., spacing=2., count=41, site=17, mass_ratio=.067)
    expected, _, _ = audit.impurity_amplitudes(energy, height=1e9, spacing=2., count=41, site=17, mass_ratio=.067)
    np.testing.assert_allclose(actual.t, expected, atol=1e-18, rtol=2e-10)
    metrics = analyze_packet(energy, np.ones(101)/np.sqrt(energy[-1]-energy[0]), actual.t, reference)
    assert metrics.raw_fidelity > .999
    assert metrics.low_transmission and metrics.p_transmitted < 1e-10
