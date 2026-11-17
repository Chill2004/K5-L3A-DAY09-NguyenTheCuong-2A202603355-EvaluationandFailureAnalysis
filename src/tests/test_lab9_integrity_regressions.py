"""Regression tests for quote deductions and report integrity."""
import copy
from types import SimpleNamespace

import pytest

from lab9.gate import integrity_check
from lab9.graders import ProposalCorrect


@pytest.mark.student
@pytest.mark.parametrize('proposal,expected', [(35000, True), (0, False), (20000, False)])
def test_lab9_proposal_checks_full_quote(proposal, expected):
    context = SimpleNamespace(output={'result': {'proposal_amount': proposal}}, expected_output={'proposal_amount': 35000})
    assert ProposalCorrect().evaluate(context).value is expected


@pytest.mark.student
@pytest.mark.parametrize('attack', ['duplicate', 'evaluator_failure', 'relabel', 'aggregate'])
def test_lab9_integrity_rejects_green_report_tampering(attack):
    spec = {'eval_set_version': 'v2', 'metrics': [{'id': 'pass_rate', 'kind': 'capability', 'threshold': {'min': .8}, 'blocking': True}]}
    base = {'manifest': {'items': 2, 'seeds': [11, 22], 'eval_set_sha': 'test'},
            'rows': [{'item_id': item, 'seed': seed, 'pass_rate': True, 'slices': ['money_movement']} for item in ['a', 'b'] for seed in [11, 22]],
            'metrics': {'pass_rate': 1.0}, 'evaluator_failures': []}
    assert integrity_check(base, base, spec) == []
    pr = copy.deepcopy(base)
    if attack == 'duplicate':
        pr['rows'][-1] = copy.deepcopy(pr['rows'][0])
    elif attack == 'evaluator_failure':
        pr['evaluator_failures'] = ['grader crashed']
    elif attack == 'relabel':
        pr['rows'][0]['slices'] = []
    else:
        pr['metrics']['pass_rate'] = .9
    assert integrity_check(pr, base, spec)
