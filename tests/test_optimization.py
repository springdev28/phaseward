"""Independent objective identities, feasibility, budgets, and derivatives."""

from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path

import numpy as np
import pytest

from qwave.optimization import (CandidateEvaluator, NumericalFailure, ScatteringCache, WorkBudgetExceeded,
    bounded_jacobian, disorder_draws, gate_jacobian, gate_step_check, initializations, prepare_problem, run_multistart)
from qwave.optimization_config import OptimizeConfig


@pytest.mark.parametrize('fault', ['nan_gradient', 'response_residual', 'phase_mismatch', 'forward_residual'])
def test_invalid_response_cannot_be_cached_or_selected(problem, monkeypatch, fault) -> None:
    """Fault injection: conservation alone does not validate a complex derivative."""
    import qwave.optimization as module
    original = module.transmission_gradient

    def invalid(*args, **kwargs):
        response = original(*args, **kwargs)
        if fault == 'nan_gradient':
            gradient = response.dt_dpotential_per_mev.copy()
            gradient[0, 0] = np.nan
            return replace(response, dt_dpotential_per_mev=gradient)
        if fault == 'response_residual':
            return replace(response, max_response_solve_residual=1e-2)
        if fault == 'phase_mismatch':
            return replace(response, max_reassembled_t_difference=1e-2)
        residual = response.baseline.relative_residual.copy()
        residual[0] = 1e-2
        return replace(response, baseline=replace(response.baseline, relative_residual=residual))

    monkeypatch.setattr(module, 'transmission_gradient', invalid)
    evaluator = CandidateEvaluator(problem, 'D_sensitivity', .85, np.empty((0, len(problem.device.x_nm))))
    with pytest.raises(NumericalFailure, match='numerical|response|residual'):
        evaluator.evaluate(np.array([4., 6.]))
    assert not evaluator.cache.cache and not evaluator.records
    assert evaluator.cache.work == 3  # Failed work is still charged.


def test_candidate_gate_vector_rejects_complex_values(problem) -> None:
    """An imaginary potential cannot be silently changed to a real gate setting."""
    evaluator = CandidateEvaluator(problem, 'B_clean', .85, np.empty((0, len(problem.device.x_nm))))
    with pytest.raises(ValueError, match='real'):
        evaluator.evaluate(np.array([4.+1j, 6.]))
    assert evaluator.cache.work == 0


def small_config() -> dict:
    """Small actual two-gate device with the complete production schema."""
    config=json.loads((Path(__file__).parents[1]/"examples/optimize_quick.json").read_text())
    model=config["model"]
    model["scattering"].update(grid_points=81,energy_min_mev=20,energy_max_mev=60,energy_points=17)
    config["packet"]["bandwidth_mev"]=10
    model["gates"]["profiles"]=model["gates"]["profiles"][1:3]
    for profile,u in zip(model["gates"]["profiles"],[4.,6.]):
        profile["amplitude_mev"]=u
        profile["bounds_mev"]=[-15.,15.]
    model["disorder"].update(sigma_mev=1.,retained_modes=3)
    config["optimizer"].update(forward_work_budget=90,starts=2,maxiter=15)
    config["diagnostics"]["mode_steps_mev_sqrt_nm"]=[.1,.001,1e-8]
    config["ensembles"].update(training_samples=2,validation_samples=3,heldout_samples=4)
    return config


@pytest.fixture
def optimization_config() -> dict:
    """Independent mutable configuration for each numerical test."""
    return small_config()


@pytest.fixture
def problem(optimization_config: dict):
    """Production scientific setup, not invented transmission values."""
    return prepare_problem(OptimizeConfig.from_mapping(optimization_config))


def test_objective_matches_independent_free_born_and_covariance_contraction(problem) -> None:
    """KL objective has exactly one lambda and a normalized energy measure."""
    clean,response=problem.cache().solve(problem.potential(np.zeros(2)),response=True)
    raw,normalized,derivative=problem.sensitivity(response)
    phi=problem.device.embedded_shapes
    q=clean.k_left_per_nm*clean.spacing_nm
    independent=(-1j*clean.t/(2*clean.hopping_mev*np.sin(q)))[:,None]*phi.sum(axis=0)
    weight=problem.packet.weights_mev*problem.importance_density
    expected=np.sum(weight[:,None]*problem.device.modes.retained_eigenvalues*abs(independent)**2)
    np.testing.assert_allclose(derivative,independent,atol=2e-13,rtol=2e-12)
    assert raw==pytest.approx(expected,rel=3e-12)
    covariance=(phi*problem.device.modes.retained_eigenvalues)@phi.T
    gradient=response.dt_dpotential_per_mev
    nodal=np.einsum('ei,ij,ej->e',gradient,covariance,gradient.conj())
    assert raw==pytest.approx(np.dot(weight,nodal).real,rel=2e-12)
    assert normalized==pytest.approx(raw/problem.config.model['disorder']['sigma_mev']**2)
    assert sum(weight)==pytest.approx(1.,abs=1e-15)


def test_normalization_removes_nominal_sigma_squared(optimization_config: dict) -> None:
    """Scaling sigma changes J, not J/sigma² or the deterministic model."""
    first=prepare_problem(OptimizeConfig.from_mapping(optimization_config))
    changed=deepcopy(optimization_config);changed['model']['disorder']['sigma_mev']=2.
    second=prepare_problem(OptimizeConfig.from_mapping(changed))
    values=[]
    for p in [first,second]:
        _,response=p.cache().solve(p.potential(np.array([4.,6.])),response=True)
        values.append(p.sensitivity(response)[:2])
    assert values[1][0]==pytest.approx(4*values[0][0],rel=1e-12)
    assert values[1][1]==pytest.approx(values[0][1],rel=1e-12)


def test_uniform_weight_energy_refinement(optimization_config: dict) -> None:
    """Normalized quadrature does not grow with energy sample count."""
    values=[]
    optimization_config['objective']['weighting']='uniform_energy'
    for count in [17,33,65]:
        cfg=deepcopy(optimization_config);cfg['model']['scattering']['energy_points']=count
        p=prepare_problem(OptimizeConfig.from_mapping(cfg))
        assert np.allclose(p.importance_density,1/40)
        _,response=p.cache().solve(p.potential(np.zeros(2)),response=True)
        values.append(p.sensitivity(response)[0])
    ratio=abs(values[0]-values[1])/abs(values[1]-values[2])
    assert 3.8 < ratio < 4.2


def test_normalized_objective_spatial_refinement_with_smooth_disorder_boundary() -> None:
    """Fixed physical covariance and weighted modes give converging J, not node-count scaling."""
    cfg=json.loads((Path(__file__).parents[1]/'examples/optimize_quick.json').read_text())
    cfg['model']['disorder']['boundary_taper_nm']=5
    values=[]
    for count in [81,161,321]:
        current=deepcopy(cfg);current['model']['scattering']['grid_points']=count
        p=prepare_problem(OptimizeConfig.from_mapping(current))
        _,response=p.cache().solve(p.potential(np.zeros(4)),response=True)
        values.append(p.sensitivity(response)[1])
    ratio=abs(values[0]-values[1])/abs(values[1]-values[2])
    assert 3.7 < ratio < 4.3


def test_objective_normalization_and_optional_gradient_constraint(optimization_config: dict) -> None:
    """Changing objective units does not silently remove lambda or enable a slope limit."""
    optimization_config['model']['disorder']['sigma_mev']=2
    optimization_config['objective']['normalization']='none'
    optimization_config['constraints']['max_gate_gradient_mev_per_nm']=None
    p=prepare_problem(OptimizeConfig.from_mapping(optimization_config))
    row=CandidateEvaluator(p,'D_sensitivity',.85,disorder_draws(p,2,42001)[2]).evaluate(p.device.gates.amplitudes_mev)
    assert row['objective']==row['sensitivity_J']
    assert row['objective']==pytest.approx(4*row['sensitivity_J_per_mev2'])
    assert row['constraint_residuals']['gradient_mev_per_nm'] is None


def test_bounded_jacobian_polynomial_central_and_one_sided() -> None:
    """Known analytic Jacobian checks signs, units and both boundary stencils."""
    bounds=np.array([[-2.,2.],[-3.,3.]])
    def f(u):return np.array([u[0]**2+3*u[1]**2,u[0]*u[1]])
    for u in [np.array([.3,.7]),np.array([-2.,3.]),np.array([2.,-3.])]:
        expected=np.array([[2*u[0],6*u[1]],[u[1],u[0]]])
        np.testing.assert_allclose(bounded_jacobian(f,u,bounds,.01),expected,atol=5e-12,rtol=0)
    with pytest.raises(NumericalFailure,match='representable'):
        bounded_jacobian(f,np.array([1.,1.]),bounds,1e-30)


def test_potential_roundoff_cannot_create_false_zero_gradient(optimization_config: dict) -> None:
    """Representable small u does not imply its perturbation survives the background."""
    optimization_config['model']['scattering']['potential']['offset_mev']=5.
    optimization_config['diagnostics']['gate_steps_mev']=[.01,.005,1e-30]
    p=prepare_problem(OptimizeConfig.from_mapping(optimization_config))
    evaluator=CandidateEvaluator(p,'D_sensitivity',.85,disorder_draws(p,2,42001)[2])
    with pytest.raises(NumericalFailure,match='gate-potential'):
        gate_jacobian(evaluator,np.zeros(2),1e-30)
    check=gate_step_check(evaluator,np.zeros(2))
    assert check['passed'] and check['unresolved_step_errors'][-1] is not None
    assert check['jacobians_objective_P_F_per_mev'][-1] is None


def test_cache_exact_keys_response_cost_and_no_model_collisions(problem) -> None:
    """No rounded keys or hidden response discount; every physical setting matters."""
    cache=problem.cache();potential=problem.potential(np.array([4.,6.]))
    first,_=cache.solve(potential)
    assert cache.solve(potential.copy())[0] is first
    assert cache.work==1 and cache.hits==1
    cache.solve(potential,response=True)
    assert cache.work==4 and cache.forward_sweeps==2 and cache.response_rhs_sweeps==2
    cache.solve(potential,response=True)
    assert cache.work==4
    for kind in ['potential','grid','energy','mass','lead','source','tolerance']:
        x=problem.device.x_nm.copy();energy=problem.device.energy_mev.copy();args=problem.arguments.copy()
        v=potential.copy();context=problem.context;tol=problem.device.scatter.conservation_tolerance
        if kind=='potential':v[30]=np.nextafter(v[30],np.inf)
        if kind=='grid':x=x*1.01
        if kind=='energy':energy=energy+.001
        if kind=='mass':args['effective_mass_ratio']*=1.01
        if kind=='lead':args['right_lead_mev']=1.
        if kind=='source':context+='changed code'
        if kind=='tolerance':tol*=2
        other=ScatteringCache(x,energy,args,context=context,tolerance=tol)
        assert other.key(v)!=cache.key(potential)
    with pytest.raises(ValueError,match='real'):cache.solve(potential.astype(complex))
    with pytest.raises(TypeError):cache.arguments['effective_mass_ratio']=1.
    with pytest.raises(ValueError):first.t[0]=0


def test_budget_and_lru_eviction(problem) -> None:
    """No solve begins after the cap; eviction triggers counted recomputation."""
    cache=ScatteringCache(problem.device.x_nm,problem.device.energy_mev,problem.arguments,context=problem.context,entries=1)
    a=problem.potential(np.array([4.,6.]));b=problem.potential(np.array([5.,6.]))
    cache.solve(a);cache.solve(b);cache.solve(a)
    assert cache.work==3 and cache.evictions==2
    cache.work_limit=3
    with pytest.raises(WorkBudgetExceeded):cache.solve(b)
    assert cache.work==3


def test_mc_direct_average_and_other_methods_ignore_training_draws(problem) -> None:
    """C uses physical P/F; B and D are independent of supplied disorder samples."""
    training=disorder_draws(problem,2,42001)[2]
    u=problem.device.gates.amplitudes_mev
    evaluator=CandidateEvaluator(problem,'C_monte_carlo',.85,training)
    row=evaluator.evaluate(u)
    direct=np.mean([problem.clean_loss(problem.packet_metrics(t)) for t in evaluator.data[0]['training_t']])
    assert row['objective']==pytest.approx(direct,abs=1e-15)
    assert evaluator.cache.work==3
    retained=evaluator.training.copy()
    training[:]=0
    np.testing.assert_array_equal(evaluator.training,retained)
    with pytest.raises(ValueError):evaluator.training[0,0]=0
    assert evaluator.candidate_context!=CandidateEvaluator(problem,'C_monte_carlo',.85,training).candidate_context
    training=retained.copy()
    for method in ['B_clean','D_sensitivity']:
        a=CandidateEvaluator(problem,method,.85,training).evaluate(u)
        b=CandidateEvaluator(problem,method,.85,training*100).evaluate(u)
        assert a['objective']==b['objective']


def test_negligible_throughput_is_infeasible_despite_high_conditional_fidelity(problem) -> None:
    """A normalized conditional state cannot bypass a minimum probability."""
    metrics={'p_transmitted':1e-30,'raw_fidelity':1.}
    raw,scaled=problem.residuals(np.zeros(2),metrics,.85)
    assert raw['transmission']<0 and min(scaled)<0
    assert problem.clean_loss(metrics)==pytest.approx(.5)
    metrics={'p_transmitted':0.,'raw_fidelity':None}
    assert problem.clean_loss(metrics)==1.
    assert problem.residuals(np.zeros(2),metrics,.85)[0]['fidelity']<0
    raw,_=problem.residuals(np.array([30.,-30.]),{'p_transmitted':1.,'raw_fidelity':1.},.85)
    assert min(raw['upper_gate_mev'])<0 and min(raw['lower_gate_mev'])<0


def test_unconditional_overlap_survives_undefined_conditional_state(problem) -> None:
    """Synthetic attenuation tests direct overlap; no artificial zero replaces a tiny physical probability."""
    from qwave.optimization_experiments import _ensemble_statistics
    t=problem.target_t*1e-155
    assert problem.packet_metrics(t)['raw_fidelity'] is None
    summary,rows=_ensemble_statistics(problem,np.stack([t,t]),problem.target_t)
    assert summary['undefined_fidelity_count']==2
    assert np.all(np.isnan(rows[:,1]))
    assert 0 < summary['mean_probability_times_fidelity'] < 1e-308
    assert summary['mean_probability_times_fidelity']==pytest.approx(1e-310,rel=1e-4,abs=0)


def test_spatial_gradient_constraint_has_physical_nm_scaling(problem) -> None:
    u=np.array([14.,-14.])
    raw,scaled=problem.residuals(u,{'p_transmitted':1.,'raw_fidelity':1.},.85)
    expected=problem.config.constraints['max_gate_gradient_mev_per_nm']-max(abs(np.diff(problem.device.gates.shapes@u)/np.diff(problem.device.x_nm)))
    assert raw['gradient_mev_per_nm']==pytest.approx(expected)
    assert scaled[-1]==pytest.approx(expected/problem.config.constraints['max_gate_gradient_mev_per_nm'])


def test_budgeted_slsqp_selects_only_feasible_observed_candidates(problem) -> None:
    """Physical free-target example checks the optimizer and all recorded constraints."""
    training=disorder_draws(problem,2,42001)[2]
    check=CandidateEvaluator(problem,'B_clean',.85,training,phase='test')
    initial=check.evaluate(problem.device.gates.amplitudes_mev)
    assert gate_step_check(check,problem.device.gates.amplitudes_mev)['passed']
    evaluator=CandidateEvaluator(problem,'B_clean',.85,training)
    result=run_multistart(evaluator,initializations(problem),scale=initial['objective'],preflight_passed=True)
    assert result['selected']['feasible']
    assert result['selected']['objective'] <= initial['objective']
    assert result['cost']['forward_work'] <= problem.config.optimizer['forward_work_budget']
    assert result['selected'] in evaluator.records
    assert all(row['used_forward_work']<=row['allocated_forward_work'] for row in result['runs'])
    assert all('constraint_residuals' in row and 'objective' in row for row in evaluator.records)


def test_failed_preflight_and_infeasibility_do_not_manufacture_winners(problem) -> None:
    training=disorder_draws(problem,2,42001)[2]
    evaluator=CandidateEvaluator(problem,'D_sensitivity',.85,training)
    result=run_multistart(evaluator,initializations(problem),scale=1.,preflight_passed=False)
    assert result['selected'] is None and result['cost']['forward_work']==0
    fixed=CandidateEvaluator(problem,'A_fixed',1.,training)
    result=run_multistart(fixed,initializations(problem),scale=1.,preflight_passed=True)
    assert result['selected'] is None and not fixed.records[0]['feasible']


@pytest.mark.parametrize('change',[
    {'unknown':1},
    {'objective':{'weighting':'bad','normalization':'none','transmission_weight':.5}},
    {'ensembles':{'representation':'retained_kl','training_samples':2,'validation_samples':3,'heldout_samples':4,
                  'training_seed':1,'validation_seed':1,'heldout_seed':2}},
    {'optimizer':{'method':'SLSQP','starts':2,'initialization_seed':True,'forward_work_budget':90,'maxiter':15,
                  'ftol':1e-7,'gate_step_mev':.01,'cache_entries':128}},
])
def test_strict_config(optimization_config: dict,change: dict) -> None:
    with pytest.raises(ValueError):OptimizeConfig.from_mapping({**optimization_config,**change})

