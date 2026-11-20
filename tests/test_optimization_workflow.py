"""End-to-end CLI, frozen evaluation ordering, strict files, and infeasibility."""
from copy import deepcopy
import json
from pathlib import Path

import numpy as np
import pytest

from test_optimization import small_config
from qwave.cli import main
from qwave.config import load_config
from qwave.optimization import (CandidateEvaluator, disorder_draws, initializations, prepare_problem, run_multistart)
from qwave.optimization_config import OptimizeConfig
from qwave.optimization_experiments import run_optimization
from qwave.provenance import sha256_file


def test_full_cli_freezes_before_independent_draws_and_exports_raw_data(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Real CLI execution checks seed isolation, raw objective data, constraints and figures."""
    import qwave.optimization_experiments as experiments
    config=small_config()
    path=tmp_path/'config.json';path.write_text(json.dumps(config))
    output=tmp_path/'run'
    original=experiments.disorder_draws
    consumed=[]
    def observed(problem,count,seed):
        consumed.append(seed)
        if seed in [config['ensembles']['validation_seed'],config['ensembles']['heldout_seed']]:
            frozen=json.loads((output/'frozen_candidates.json').read_text())
            assert len(frozen['candidates'])==4
            assert all('u_mev' in row for row in frozen['candidates'])
        else:
            assert not (output/'frozen_candidates.json').exists()
        return original(problem,count,seed)
    monkeypatch.setattr(experiments,'disorder_draws',observed)
    assert main(['optimize','--config',str(path),'--output',str(output)])==0
    assert consumed==[config['ensembles'][name+'_seed'] for name in ['training','validation','heldout']]
    metrics=json.loads((output/'metrics.json').read_text())
    assert metrics['all_checks_passed']
    assert len(metrics['runs'])==4
    manifest=json.loads((output/'manifest.json').read_text())
    assert manifest['config']==config
    for name,expected in manifest['outputs'].items():
        assert sha256_file(output/name)==expected['sha256']
    assert manifest['frozen_candidates_sha256']==sha256_file(output/'frozen_candidates.json')
    with np.load(output/'arrays.npz',allow_pickle=False) as archive:
        data={key:archive[key] for key in archive.files}
    assert np.iscomplexobj(data['sweep0_D_sensitivity_dt_deta'])
    assert np.iscomplexobj(data['sweep0_C_monte_carlo_training_t'])
    np.testing.assert_allclose(data['training_eta_mev_sqrt_nm'],data['training_z']*np.sqrt(data['eigenvalues_mev2_nm'][:3]))
    np.testing.assert_allclose(data['training_potential_mev'],data['training_eta_mev_sqrt_nm']@data['retained_phi_per_sqrt_nm'].T)
    records=[json.loads(line) for line in (output/'candidates.jsonl').read_text().splitlines()]
    assert {'preflight','search','postflight'} <= {row['phase'] for row in records}
    for row in metrics['runs']:
        assert row['reported_candidate']['feasible']
        assert row['cost']['forward_work'] <= config['optimizer']['forward_work_budget']
        held=row['evaluation']['ensembles']['heldout']
        assert held['samples']==4 and held['undefined_fidelity_count']==0
        raw=data[row['run_id']+'_final_heldout_metrics_P_F_loss_PF_ownF_delta_t2']
        assert held['mean_transmission']==pytest.approx(np.mean(raw[:,0]))
        assert held['mean_loss']==pytest.approx(np.mean(raw[:,2]))
        if row['method']!='A_fixed':
            assert row['postflight']['passed']
            assert row['selected']['objective']==min(record['objective'] for record in records
                if record['run_id']==row['run_id'] and record['feasible'])
    for figure in ['optimization_tradeoffs','optimization_progress','optimization_costs','optimization_steps','optimized_potentials']:
        for extension in ['png','svg','pdf']:
            assert (output/(figure+'.'+extension)).stat().st_size>1000
    before=sha256_file(output/'manifest.json')
    with pytest.raises(FileExistsError):
        run_optimization(OptimizeConfig.from_mapping(config),output,plot=False)
    assert sha256_file(output/'manifest.json')==before


@pytest.mark.parametrize('method', ['B_clean', 'C_monte_carlo', 'D_sensitivity'])
def test_changing_evaluation_seeds_cannot_change_search(method: str) -> None:
    """Evaluation draws are neither constructed nor available to the search evaluator."""
    cfg=small_config();cfg['optimizer'].update(starts=1,forward_work_budget=36)
    outputs=[]
    for shift in [0,100]:
        current=deepcopy(cfg)
        current['ensembles']['validation_seed']+=shift
        current['ensembles']['heldout_seed']+=shift
        problem=prepare_problem(OptimizeConfig.from_mapping(current))
        training=disorder_draws(problem,2,current['ensembles']['training_seed'])[2]
        evaluator=CandidateEvaluator(problem,method,.85,training)
        initial=evaluator.evaluate(problem.device.gates.amplitudes_mev)
        result=run_multistart(evaluator,initializations(problem),scale=initial['objective'],preflight_passed=True)
        outputs.append([(row['u_mev'],row['objective'],row['constraint_residuals']) for row in evaluator.records])
    assert outputs[0]==outputs[1]


def test_infeasible_and_budget_starved_runs_are_saved_without_fake_winners(tmp_path: Path) -> None:
    cfg=small_config()
    cfg['optimizer']['forward_work_budget']=2
    cfg['constraints']['minimum_clean_transmission_values']=[1.]
    cfg['constraints']['minimum_clean_fidelity']=1.
    output=run_optimization(OptimizeConfig.from_mapping(cfg),tmp_path/'infeasible',plot=False)
    metrics=json.loads((output/'metrics.json').read_text())
    assert not metrics['all_checks_passed']
    assert all(row['selected'] is None for row in metrics['runs'])
    assert not metrics['runs'][0]['reported_candidate']['feasible']
    assert all(row['evaluation'] is None for row in metrics['runs'][1:])
    assert (output/'manifest.json').exists()


@pytest.mark.parametrize('name',['optimize.json','optimize_quick.json'])
def test_examples_are_strict_and_loadable(name: str) -> None:
    config=load_config(Path(__file__).parents[1]/'examples'/name)
    assert isinstance(config,OptimizeConfig)
    assert len(config.model['gates']['profiles'])==4


def test_optimize_rejects_other_experiment_without_creating_output(tmp_path: Path) -> None:
    demo=Path(__file__).parents[1]/'examples/demo.json'
    assert main(['optimize','--config',str(demo),'--output',str(tmp_path/'wrong')])==2
    assert not (tmp_path/'wrong').exists()

