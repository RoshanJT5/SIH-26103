import numpy as np
import pandas as pd
import pytest

from ml.training.pipeline import (
    MIN_ELIGIBLE_SAMPLES,
    TrainingUnavailableError,
    classification_metrics,
    create_group_safe_split,
)


def test_group_safe_split_is_reproducible_stratified_and_disjoint():
    labels = pd.Series(([0, 1] * 60), dtype="int8")
    project_ids = list(range(120))

    first = create_group_safe_split(labels, project_ids, seed=42)
    second = create_group_safe_split(labels, project_ids, seed=42)

    assert np.array_equal(first.train, second.train)
    assert np.array_equal(first.validation, second.validation)
    assert np.array_equal(first.test, second.test)
    assert (len(first.train), len(first.validation), len(first.test)) == (72, 24, 24)
    assert set(first.train).isdisjoint(first.validation)
    assert set(first.train).isdisjoint(first.test)
    assert set(first.validation).isdisjoint(first.test)
    for indices in (first.train, first.validation, first.test):
        assert set(labels.iloc[indices]) == {0, 1}


def test_split_reports_unavailable_for_insufficient_data_or_classes():
    with pytest.raises(TrainingUnavailableError, match=str(MIN_ELIGIBLE_SAMPLES)):
        create_group_safe_split(pd.Series([0, 1] * 10), list(range(20)))

    labels = pd.Series(([0] * 95) + ([1] * 5), dtype="int8")
    with pytest.raises(TrainingUnavailableError, match="Both classes"):
        create_group_safe_split(labels, list(range(100)))


def test_metrics_include_discrimination_confusion_and_calibration():
    metrics = classification_metrics(
        pd.Series([0, 0, 1, 1]),
        np.asarray([0.1, 0.4, 0.6, 0.9]),
    )

    assert metrics["precision"] == 1.0
    assert metrics["recall"] == 1.0
    assert metrics["f1"] == 1.0
    assert metrics["roc_auc"] == 1.0
    assert metrics["pr_auc"] == 1.0
    assert metrics["confusion_matrix"] == [[2, 0], [0, 2]]
    assert metrics["calibration"]["brier_score"] > 0
    assert metrics["undefined_metrics"] == []


def test_metrics_explain_undefined_single_class_auc():
    metrics = classification_metrics(pd.Series([0, 0]), np.asarray([0.2, 0.3]))

    assert metrics["roc_auc"] is None
    assert metrics["pr_auc"] is None
    assert metrics["undefined_metrics"] == ["roc_auc", "pr_auc"]
