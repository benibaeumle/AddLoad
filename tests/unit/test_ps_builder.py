"""Unit tests for PSBuilder."""

from __future__ import annotations

import os
import uuid

import numpy as np
import pandas as pd
import pytest

from src.generators.ps_builder import PSBuilder
from src.models.load_series import PSParameters
from src.models.ps_node import PSNode, PSNodeType


@pytest.fixture(scope="module")
def bdew_profiles():
    bdew_dir = os.path.join(
        os.path.dirname(__file__), "..", "..", "data", "bdew"
    )
    profiles = {}
    for name in ["H0", "G1"]:
        path = os.path.join(bdew_dir, f"{name}.csv")
        if os.path.exists(path):
            profiles[name] = pd.read_csv(path)
    return profiles


def _consumer(name="C", profile="H0", energy=3000.0) -> PSNode:
    return PSNode(
        node_id=str(uuid.uuid4()),
        node_type=PSNodeType.CONSUMER,
        name=name,
        profile_type=profile,
        annual_energy_kwh=energy,
    )


def _group(name="G", glf=1.0, children=None) -> PSNode:
    return PSNode(
        node_id=str(uuid.uuid4()),
        node_type=PSNodeType.GROUP,
        name=name,
        simultaneity_factor=glf,
        children=children or [],
    )


def test_single_consumer_shape(bdew_profiles):
    consumer = _consumer()
    params = PSParameters(root_node=consumer)
    result = PSBuilder.build(params, 2024, bdew_profiles)
    assert result.shape == (35040,)


def test_single_consumer_non_negative(bdew_profiles):
    consumer = _consumer()
    params = PSParameters(root_node=consumer)
    result = PSBuilder.build(params, 2024, bdew_profiles)
    assert np.all(result >= 0)


def test_group_with_glf(bdew_profiles):
    c1 = _consumer(energy=3000.0)
    c2 = _consumer(energy=3000.0)
    group = _group(glf=0.8, children=[c1, c2])
    params = PSParameters(root_node=group)
    result = PSBuilder.build(params, 2024, bdew_profiles)

    from src.generators.slp_generator import SLPGenerator
    from src.models.load_series import SLPParameters

    slp_params = SLPParameters(profile_type="H0", annual_energy_kwh=3000.0)
    s1 = SLPGenerator.generate(slp_params, 2024, bdew_profiles)
    s2 = SLPGenerator.generate(slp_params, 2024, bdew_profiles)
    expected = (s1 + s2) * 0.8
    np.testing.assert_allclose(result, expected, rtol=1e-5)


def test_consumer_no_profile_raises(bdew_profiles):
    consumer = PSNode(
        node_id=str(uuid.uuid4()),
        node_type=PSNodeType.CONSUMER,
        name="C",
        profile_type=None,
        annual_energy_kwh=1000.0,
    )
    params = PSParameters(root_node=consumer)
    with pytest.raises(ValueError, match="profile_type"):
        PSBuilder.build(params, 2024, bdew_profiles)


def test_zero_glf_raises(bdew_profiles):
    c = _consumer()
    group = _group(glf=0.0, children=[c])
    params = PSParameters(root_node=group)
    with pytest.raises(ValueError, match="Gleichzeitigkeitsfaktor"):
        PSBuilder.build(params, 2024, bdew_profiles)
