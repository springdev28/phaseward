"""Independent analytic gradients, complex finite differences, and Taylor remainder scaling."""

import numpy as np
import pytest

from qwave.scattering import solve_scattering
from qwave.sensitivity import derivative_study, transmission_gradient, validate_linearization
from qwave.wavepackets import quadrature_weights
from qwave.disorder import covariance_matrix, covariance_modes


def test_free_channel_gradient_matches_independent_discrete_born_result() -> None:
    """For any free site, dt/dV_j = -i t/(2 tau sin(q)); phases cannot be discarded."""
    x=np.linspace(-10,10,81)
    energy=np.array([10.,30.,80.])
    result=transmission_gradient(x,np.zeros(len(x)),energy,effective_mass_ratio=.067)
    q=result.baseline.k_left_per_nm*result.baseline.spacing_nm
    expected=-1j*result.baseline.t/(2*result.baseline.hopping_mev*np.sin(q))
    np.testing.assert_allclose(result.dt_dpotential_per_mev, np.broadcast_to(expected[:,None],(3,81)), atol=2e-14,rtol=0)
    assert result.max_reassembled_t_difference < 1e-12
    assert result.max_response_solve_residual < 1e-14


@pytest.mark.parametrize("right_lead", [0.,5.])
def test_implicit_local_response_matches_independent_site_perturbations(right_lead: float) -> None:
    """Cross-check complex gradients at endpoints and in the interior, including unequal velocities."""
    x=np.linspace(-20,20,161)
    potential=12*np.exp(-.5*((x-2)/3)**2)
    energy=np.array([8.,20.,50.])
    arguments=dict(effective_mass_ratio=.067,right_lead_mev=right_lead)
    response=transmission_gradient(x,potential,energy,**arguments)
    for site in [0,37,80,160]:
        delta=np.zeros_like(x);delta[site]=1e-3
        plus=solve_scattering(x,potential+delta,energy,**arguments).t
        minus=solve_scattering(x,potential-delta,energy,**arguments).t
        np.testing.assert_allclose((plus-minus)/.002,response.dt_dpotential_per_mev[:,site],atol=1e-9,rtol=0)


def test_centered_complex_derivative_converges_quadratically_before_roundoff() -> None:
    """Independent free-channel derivative detects differentiating |t| or phase instead of t."""
    x=np.linspace(-10,10,81)
    shape=np.ones((81,1))/np.sqrt(20)
    study=derivative_study(x,np.zeros(81),[10.,30.,80.],shape,[1.,.5,.25,.01],effective_mass_ratio=.067)
    error=np.max(abs(study.finite_difference-study.linear_response),axis=(1,2))
    assert np.all((error[:2]/error[1:3] > 3.9) & (error[:2]/error[1:3] < 4.1))
    assert error[-1] < 1e-8
    np.testing.assert_array_equal(study.finite_difference,
        (study.t_plus-study.t_minus)/(2*study.steps_mev_sqrt_nm[:,None,None]))
    assert study.max_conservation_error < 1e-10


def test_unresolvable_small_steps_are_reported() -> None:
    """An under-roundoff potential perturbation is flagged instead of trusted as a zero derivative."""
    x=np.linspace(-10,10,81)
    shapes=np.ones((81,1))/np.sqrt(20)
    study=derivative_study(x,np.ones(81)*5,[10.,30.,80.],shapes,[.1,.01,1e-30],effective_mass_ratio=.067)
    assert study.unresolved_perturbations[-1,0]
    assert np.all(study.finite_difference[-1] == 0)
    assert np.any(abs(study.linear_response) > 0)
    assert study.mode_rows[0]["small_step_error_growth_detected"]
    potential=np.ones(81)*5;potential[[0,-1]]=0
    partial=derivative_study(x,potential,[10.,30.,80.],shapes,[.1,.01,1e-30],effective_mass_ratio=.067)
    assert partial.unresolved_perturbations[-1,0]
    assert partial.potential_direction_relative_error[-1,0] == pytest.approx(1.)


def test_symmetry_protected_zero_derivative_uses_absolute_errors() -> None:
    """Odd potential perturbations about a mirror-symmetric device have zero first derivative."""
    x=np.linspace(-10,10,81)
    shape=x[:,None]/np.sqrt(np.dot(quadrature_weights(x),x*x))
    study=derivative_study(x,np.zeros(81),[10.,30.,80.],shape,[.1,.05,.01],effective_mass_ratio=.067)
    assert np.max(abs(study.linear_response)) < 1e-13
    assert np.max(abs(study.finite_difference)) < 1e-10


def test_taylor_remainder_convergence_and_separate_truncation_error() -> None:
    """Small-eta error is quadratic; omitted modes and nonunitary predictions remain visible."""
    x=np.linspace(-10,10,81)
    energy=np.linspace(10,60,11)
    shapes=np.ones((81,1))/np.sqrt(20)
    response=transmission_gradient(x,np.zeros(81),energy,effective_mass_ratio=.067)
    derivative=response.dt_dpotential_per_mev @ shapes
    eta=np.array([[1.],[-1.5]])
    full_disorder=eta @ shapes.T + .1*np.exp(-(x/3)**2)[None,:]
    result=validate_linearization(x,np.zeros(81),energy,shapes,eta,[0.,.05,.1,.2,2.],response.baseline.t,
                                   derivative,effective_mass_ratio=.067,full_disorder_mev=full_disorder)
    assert result.rows[0]["rms_complex_error"] == 0
    assert result.rows[0]["error_relative_to_full_change"] is None
    errors=np.array([row["rms_complex_error"] for row in result.rows[1:4]])
    assert np.all((errors[1:]/errors[:-1] > 3.9) & (errors[1:]/errors[:-1] < 4.1))
    assert result.rows[-1]["linearized_probability_above_one_count"] > 0
    assert result.rows[2]["kl_truncation_rms_error"] > 0
    assert result.max_conservation_error < 1e-10
    np.testing.assert_array_equal(result.linear_t[2],response.baseline.t+.1*(eta @ derivative.T))


def test_invalid_sensitivity_inputs_fail_explicitly() -> None:
    """Reject imaginary potentials, unordered steps, and coefficient dimension mistakes."""
    x=np.linspace(-10,10,41)
    for shapes,steps in [(np.ones((41,1),complex),[.1,.01,.001]),(np.ones((41,1)),[.01,.1,.001])]:
        with pytest.raises(ValueError):
            derivative_study(x,np.zeros(41),[10.,20.,30.],shapes,steps,effective_mass_ratio=.067)
    with pytest.raises(ValueError):
        validate_linearization(x,np.zeros(41),[10.,20.,30.],np.ones((41,2)),np.ones((2,1)),
                               [0.,1.,2.],np.ones(3),np.ones((3,2)),effective_mass_ratio=.067)


def test_modal_variance_matches_direct_covariance_contraction() -> None:
    """Lambda must appear once: modal variance equals J C_K J*, in physical nodal coordinates."""
    x=np.linspace(-10,10,41)
    modes=covariance_modes(x,covariance_matrix(x,sigma_mev=2.,correlation_length_nm=2.),retained_modes=5)
    gradient=transmission_gradient(x,5*np.exp(-(x/3)**2),[10.,20.,40.],effective_mass_ratio=.067).dt_dpotential_per_mev
    modal=gradient @ modes.retained_shapes
    modal_variance=np.sum(modes.retained_eigenvalues*abs(modal)**2,axis=1)
    nodal_variance=np.einsum('ei,ij,ej->e',gradient,modes.retained_covariance,gradient.conj())
    np.testing.assert_allclose(modal_variance,nodal_variance,rtol=2e-13,atol=1e-16)
