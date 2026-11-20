# Equation → implementation → test → generated figure

The machine-readable source of this table is [code-map.json](code-map.json).
`check_package.py` verifies equation anchors, callable names, test definitions,
and (when `--results` is supplied) every named generated figure and manifest hash.

Figure paths are relative to the output folder passed to `run_notebooks.py`.
They are **illustrations** of the corresponding checks, not independent proofs.
Each PNG also has SVG/PDF counterparts, raw arrays and a description in its
notebook directory. See [the validation record](../validation_stage7.md) for this run's figures.

| Equation / concept | Implementation | Verification test | Figure relative to output |
| --- | --- | --- | --- |
| [M1](01-tools.md#eq-m1); [M3](01-tools.md#eq-m3) | [qwave.wavepackets.quadrature_weights](../../src/qwave/wavepackets.py) | [test_positive_quadrature_matches_scipy_and_integrates_linear_function](../../tests/test_wavepackets.py) | `02_packets/packet-checks.png` |
| [M2](01-tools.md#eq-m2) | [qwave.wavepackets.analyze_packet](../../src/qwave/wavepackets.py) | [test_identical_reference_and_global_phase](../../tests/test_wavepackets.py) | `02_packets/packet-checks.png` |
| [M4](01-tools.md#eq-m4) | [qwave.disorder.covariance_modes](../../src/qwave/disorder.py) | [test_weighted_kl_orthogonality_covariance_reconstruction_and_variance_fraction](../../tests/test_disorder.py) | `03_covariance/covariance-modes.png` |
| [S1](02-model.md#eq-s1); [S2](02-model.md#eq-s2); [S3](02-model.md#eq-s3) | [qwave.scattering.solve_scattering](../../src/qwave/scattering.py) | [test_free_channel_complex_phase_and_flux](../../tests/test_scattering.py) | `01_scattering/scattering.png` |
| [S4](03-scattering.md#eq-s4) | [qwave.scattering.solve_scattering](../../src/qwave/scattering.py) | [test_unequal_lead_flux_normalization_against_discrete_step](../../tests/test_scattering.py); [test_free_channel_complex_phase_and_flux](../../tests/test_scattering.py) | `01_scattering/scattering.png` |
| [S5](03-scattering.md#eq-s5); [S6](03-scattering.md#eq-s6) | [qwave.scattering.solve_scattering](../../src/qwave/scattering.py) | [test_free_phase_converges_to_continuum](../../tests/test_scattering.py); [test_forbidden_discrete_lead_energies_rejected](../../tests/test_scattering.py) | `01_scattering/scattering-convergence.png` |
| [S7](03-scattering.md#eq-s7) | [qwave.scattering.solve_scattering](../../src/qwave/scattering.py) | [test_opaque_barrier_has_no_transfer_matrix_overflow](../../tests/test_scattering.py); [test_closed_right_channel_is_explicitly_unsupported](../../tests/test_scattering.py) | `01_scattering/scattering.png` |
| [S8](03-scattering.md#eq-s8) | [qwave.references.rectangular_transmission_amplitude](../../src/qwave/references.py); [qwave.references.rectangular_probability](../../src/qwave/references.py); [qwave.references.continuum_ode_reference](../../src/qwave/references.py) | [test_barrier_above_below_and_at_top_converges](../../tests/test_scattering.py); [test_gaussian_matches_independent_continuum_ode](../../tests/test_scattering.py) | `01_scattering/scattering-convergence.png` |
| [P1](04-packets.md#eq-p1); [P2](04-packets.md#eq-p2); [P8](04-packets.md#eq-p8) | [qwave.wavepackets.reconstruct_lead_packet](../../src/qwave/wavepackets.py) | [test_discrete_lead_jacobian_gives_spatial_parseval_norm](../../tests/test_wavepackets.py); [test_energy_to_k_jacobian_matches_analytic_position_gaussian](../../tests/test_wavepackets.py) | `02_packets/packets.png` |
| [P3](04-packets.md#eq-p3) | [qwave.wavepackets.gaussian_packet](../../src/qwave/wavepackets.py) | [test_truncated_gaussian_is_a_normalized_amplitude](../../tests/test_wavepackets.py) | `02_packets/packets.png` |
| [P4](04-packets.md#eq-p4); [P5](04-packets.md#eq-p5) | [qwave.wavepackets.analyze_packet](../../src/qwave/wavepackets.py) | [test_constant_loss_retains_conditional_fidelity_but_flags_throughput](../../tests/test_wavepackets.py); [test_zero_or_underflowing_transmission_has_no_fabricated_state](../../tests/test_wavepackets.py) | `02_packets/packets.png` |
| [P6](04-packets.md#eq-p6) | [qwave.wavepackets.analyze_packet](../../src/qwave/wavepackets.py); [qwave.wavepackets.DelaySearch](../../src/qwave/wavepackets.py) | [test_linear_phase_has_analytic_raw_fidelity_and_signed_delay](../../tests/test_wavepackets.py); [test_bounded_alignment_reports_boundary_and_residual_distortion](../../tests/test_wavepackets.py) | `02_packets/packet-checks.png` |
| [P7](04-packets.md#eq-p7) | [qwave.wavepackets.analyze_packet](../../src/qwave/wavepackets.py) | [test_quadratic_phase_distorts_state_without_changing_probability](../../tests/test_wavepackets.py); [test_amplitude_filter_changes_both_throughput_and_fidelity](../../tests/test_wavepackets.py); [test_quadrature_refinement_converges_to_independent_adaptive_integral](../../tests/test_wavepackets.py) | `02_packets/packet-checks.png` |
| [G1](05-disorder.md#eq-g1) | [qwave.gates.build_gates](../../src/qwave/gates.py) | [test_gate_contributions_bounds_and_lead_exclusion](../../tests/test_disorder.py) | `04_sensitivity_objective/gates-objective.png` |
| [D1](05-disorder.md#eq-d1) | [qwave.disorder.covariance_matrix](../../src/qwave/disorder.py) | [test_kernel_variance_length_scale_and_positive_semidefiniteness](../../tests/test_disorder.py); [test_boundary_taper_changes_covariance_explicitly](../../tests/test_disorder.py) | `03_covariance/covariance-samples.png` |
| [D2](05-disorder.md#eq-d2); [D4](05-disorder.md#eq-d4) | [qwave.disorder.covariance_modes](../../src/qwave/disorder.py) | [test_weighted_kl_orthogonality_covariance_reconstruction_and_variance_fraction](../../tests/test_disorder.py); [test_covariance_eigenvalues_converge_with_physical_grid_weights](../../tests/test_disorder.py) | `03_covariance/covariance-modes.png` |
| [D3](05-disorder.md#eq-d3) | [qwave.disorder.sample_disorder](../../src/qwave/disorder.py); [qwave.disorder.covariance_statistics](../../src/qwave/disorder.py) | [test_seeded_covariance_scaling_and_statistical_error](../../tests/test_disorder.py); [test_covariance_amplitude_scaling_is_not_sample_normalization](../../tests/test_disorder.py) | `03_covariance/covariance-samples.png` |
| [L1](06-sensitivity.md#eq-l1) | [qwave.sensitivity.validate_linearization](../../src/qwave/sensitivity.py) | [test_taylor_remainder_convergence_and_separate_truncation_error](../../tests/test_sensitivity.py) | `04_sensitivity_objective/sensitivity-objective.png` |
| [L2](06-sensitivity.md#eq-l2) | [qwave.sensitivity.derivative_study](../../src/qwave/sensitivity.py) | [test_centered_complex_derivative_converges_quadratically_before_roundoff](../../tests/test_sensitivity.py); [test_unresolvable_small_steps_are_reported](../../tests/test_sensitivity.py) | `04_sensitivity_objective/sensitivity-objective.png` |
| [L3](06-sensitivity.md#eq-l3) | [qwave.sensitivity.transmission_gradient](../../src/qwave/sensitivity.py) | [test_free_channel_gradient_matches_independent_discrete_born_result](../../tests/test_sensitivity.py); [test_implicit_local_response_matches_independent_site_perturbations](../../tests/test_sensitivity.py) | `04_sensitivity_objective/sensitivity-objective.png` |
| [L4](06-sensitivity.md#eq-l4) | [qwave.optimization.OptimizationProblem.sensitivity](../../src/qwave/optimization.py) | [test_modal_variance_matches_direct_covariance_contraction](../../tests/test_sensitivity.py) | `04_sensitivity_objective/sensitivity-objective.png` |
| [O1](07-objective.md#eq-o1) | [qwave.optimization.OptimizationProblem.sensitivity](../../src/qwave/optimization.py) | [test_objective_matches_independent_free_born_and_covariance_contraction](../../tests/test_optimization.py); [test_normalization_removes_nominal_sigma_squared](../../tests/test_optimization.py) | `04_sensitivity_objective/gates-objective.png` |
| [O2](07-objective.md#eq-o2); [O3](07-objective.md#eq-o3) | [qwave.wavepackets.analyze_packet](../../src/qwave/wavepackets.py); [qwave.sensitivity.transmission_gradient](../../src/qwave/sensitivity.py) | [test_documented_projection_identity_and_probability_bound](../../tests/test_derivation_package.py); [test_documented_projected_taylor_coefficient](../../tests/test_derivation_package.py); [test_global_phase_surrogate_is_not_fidelity_loss](../../tests/test_derivation_package.py) | `02_packets/packets.png`; `04_sensitivity_objective/gates-objective.png` |
| [O4](07-objective.md#eq-o4) | [qwave.optimization.OptimizationProblem.residuals](../../src/qwave/optimization.py); [qwave.optimization.run_multistart](../../src/qwave/optimization.py) | [test_negligible_throughput_is_infeasible_despite_high_conditional_fidelity](../../tests/test_optimization.py); [test_budgeted_slsqp_selects_only_feasible_observed_candidates](../../tests/test_optimization.py) | `04_sensitivity_objective/gates-objective.png` |

## Interpretation limits

- S1, S2, S3: S1 is an assumed physical model. The test verifies its discrete stationary implementation, not the truth of quantum mechanics or a transient PDE integrator.
- O2, O3: The new tests verify O2 and the exact probability-change inequality. Markov's inequality is derived in O3; no real-world probability bound is implemented or claimed. Figures illustrate the distinct metrics.
- O4: The notebook evaluates a fixed design and saves residuals; it does not rerun or rank optimizers.

## Additional convergence and experiment checks

The notebooks are small mathematical checks. The larger library suites cover
spatial spacing, energy quadrature, mode truncation, derivative steps, and
sample count separately. Run the prespecified convergence preset when needed:

```sh
qwave experiment convergence-study --output results/learning-convergence-01
```

See [experiments.md](../experiments.md) for preset scope and costs. Increasing
the sample count cannot fix biased scattering. Seed-isolation checks live in
[test_experiment_suite.py](../../tests/test_experiment_suite.py), including
`test_all_cases_freeze_before_any_evaluation_and_training_is_isolated`.
