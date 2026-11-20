"""Strict stage-3 configs, executed commands, saved raw draws, and provenance."""

from copy import deepcopy
from dataclasses import replace
import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from qwave.cli import main
from qwave.config import ConfigError, DisorderConfig, SensitivityConfig, load_config
from qwave.disorder_experiments import run_disorder, run_sensitivity


@pytest.fixture
def configs() -> tuple[DisorderConfig, SensitivityConfig]:
    """Smaller grids/draws for workflow checks, with the actual four gate profiles."""
    root=Path(__file__).resolve().parents[1]/'examples'
    disorder=json.loads((root/'disorder.json').read_text())
    model=disorder['model']
    model['scattering']['grid_points']=81
    model['scattering']['energy_points']=9
    model['disorder']['retained_modes']=3
    disorder['sample_count']=128
    sensitivity=json.loads((root/'sensitivity.json').read_text())
    sensitivity.update(model=deepcopy(model),steps_mev_sqrt_nm=[.1,.01,.001],selected_step_mev_sqrt_nm=.01,
                       disorder_scales=[0.,.1,1.],validation_samples=2)
    return DisorderConfig.from_mapping(disorder), SensitivityConfig.from_mapping(sensitivity)


def _audit(output: Path, config: DisorderConfig | SensitivityConfig) -> tuple[dict,dict]:
    """Verify actual archived artifacts and model settings, not just their filenames."""
    manifest=json.loads((output/'manifest.json').read_text())
    metrics=json.loads((output/'metrics.json').read_text())
    assert load_config(output/'config.json') == config
    assert manifest['config'] == config.to_dict()
    assert 'Var(z)=I' in manifest['mode_convention']
    for name,item in manifest['outputs'].items():
        assert hashlib.sha256((output/name).read_bytes()).hexdigest() == item['sha256']
    return manifest,metrics


def test_complete_examples_load() -> None:
    """The public defaults specify complete supported settings."""
    root=Path(__file__).resolve().parents[1]/'examples'
    assert isinstance(load_config(root/'disorder.json'),DisorderConfig)
    assert isinstance(load_config(root/'sensitivity.json'),SensitivityConfig)


def test_disorder_archive_replays_seeded_samples_and_variance(configs, tmp_path: Path) -> None:
    """Raw coefficients, all modes, and paired full/KL realizations remain recoverable."""
    config=configs[0]
    output=run_disorder(config,tmp_path/'disorder',plot=False)
    manifest,metrics=_audit(output,config)
    assert manifest['randomness']['seeds'] == [config.seed]
    with np.load(output/'arrays.npz',allow_pickle=False) as data:
        assert json.loads(str(data['provenance_json']))['config'] == config.to_dict()
        expected_z=np.random.Generator(np.random.PCG64(config.seed)).standard_normal(data['standard_normals'].shape)
        np.testing.assert_array_equal(data['standard_normals'],expected_z)
        np.testing.assert_allclose(data['eta_mev_sqrt_nm'] @ data['all_phi_per_sqrt_nm'].T,data['full_samples_mev'],atol=1e-13)
        weights=data['channel_weights_nm']
        assert np.dot(weights,np.diag(data['covariance_mev2'])) == pytest.approx(4*60)
        assert metrics['kl']['retained_variance_fraction'] < 1
        assert data['full_samples_mev'].shape == (128,61)
    with pytest.raises(FileExistsError):
        run_disorder(config,output,plot=False)


def test_sensitivity_archive_has_complex_derivatives_and_full_solve_comparisons(configs, tmp_path: Path) -> None:
    """Saved finite differences can be reconstructed; KL and Taylor errors remain distinct."""
    config=configs[1]
    output=run_sensitivity(config,tmp_path/'sensitivity',plot=False)
    manifest,metrics=_audit(output,config)
    assert manifest['randomness']['seed_roles'] == {'linearization_validation':config.validation_seed}
    assert metrics['conservation_passed']
    assert metrics['linearization'][0]['rms_complex_error'] == 0
    assert metrics['linearization'][-1]['kl_truncation_rms_error'] > 0
    assert metrics['selected_step_max_derivative_error'] < 1e-6
    with np.load(output/'arrays.npz',allow_pickle=False) as data:
        np.testing.assert_array_equal(data['dt_deta_finite_difference'],
            (data['t_plus']-data['t_minus'])/(2*data['steps_mev_sqrt_nm'][:,None,None]))
        assert np.iscomplexobj(data['full_solve_full_covariance_t'])
        assert data['first_order_t'].shape == (3,2,9)
        assert np.all(data['full_validation_disorder_mev'][:,abs(data['x_nm']) > 30] == 0)
        # This independent contraction checks the coefficient/eigenvalue convention through the export.
        gradient=data['dt_dV_node'][:,data['channel_indices']]
        exact=np.einsum('ei,ij,ej->e',gradient,data['kl_covariance_mev2'],gradient.conj()).real
        np.testing.assert_allclose(data['predicted_mean_squared_delta_t'],exact,rtol=2e-5,atol=1e-12)
    with pytest.raises(FileExistsError):
        run_sensitivity(config,output,plot=False)


@pytest.mark.parametrize('command,index,stems',[
    ('disorder',0,['gates','covariance_modes','disorder_samples','covariance_validation']),
    ('sensitivity',1,['gates','covariance_modes','sensitivity_maps','derivative_convergence','linearization_error']),
])
def test_commands_create_headless_plots(configs,tmp_path: Path,capsys,command: str,index: int,stems: list[str]) -> None:
    """Execute both user-facing commands and all figure exports."""
    config=configs[index]
    path=tmp_path/'config.json';path.write_text(json.dumps(config.to_dict()))
    assert main(['config-check',str(path)]) == 0
    output=tmp_path/'result'
    assert main([command,'--config',str(path),'--output',str(output)]) == 0
    assert 'Var(eta_k) = lambda_k' in capsys.readouterr().out
    for stem in stems:
        for extension in ('png','svg','pdf'):
            assert (output/f'{stem}.{extension}').stat().st_size > 1000
    _audit(output,config)


@pytest.mark.parametrize('change',[{'sample_count':2},{'seed':True},{'unit_system':'volts'},{'unknown_model':1}])
def test_bad_disorder_root_fields(configs,change: dict) -> None:
    """No implicit amplitude units, seeds, or unknown model switches."""
    with pytest.raises(ConfigError):
        DisorderConfig.from_mapping({**configs[0].to_dict(),**change})


@pytest.mark.parametrize('change',[
    {'sigma_mev':0.},{'correlation_length_nm':-1.},{'kernel':'white_noise'},
    {'boundary_taper_nm':31.},{'retained_modes':True},{'extra':1},
])
def test_bad_covariance_fields(configs,change: dict) -> None:
    """Unsupported covariance choices cannot silently select another physical model."""
    config=configs[0]
    model=deepcopy(config.model);model['disorder'].update(change)
    with pytest.raises(ConfigError):
        replace(config,model=model)


@pytest.mark.parametrize('change',[
    {'steps_mev_sqrt_nm':[.01,.1,1.]},{'selected_step_mev_sqrt_nm':.07},
    {'disorder_scales':[.1,1.,2.]},{'validation_seed':-1},{'validation_samples':1},
])
def test_bad_derivative_settings(configs,change: dict) -> None:
    """Steps, chosen baseline, validation scales, and random seed must be explicit and valid."""
    with pytest.raises(ConfigError):
        replace(configs[1],**change)


def test_other_config_cannot_run_as_disorder(tmp_path: Path,capsys) -> None:
    """No implicit gates or covariance are invented for a scattering-only request."""
    path=Path(__file__).resolve().parents[1]/'examples/barrier.json'
    output=tmp_path/'missing'
    assert main(['disorder','--config',str(path),'--output',str(output)]) == 2
    assert 'DisorderConfig' in capsys.readouterr().err
    assert not output.exists()
