# -*- coding: utf-8 -*-
from __future__ import division
from __future__ import print_function

import os
import sys

import unittest

import numpy as np
from sklearn.model_selection import train_test_split

from sklearn.tree import DecisionTreeClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.neighbors import KNeighborsClassifier

from sklearn.datasets import load_breast_cancer
# noinspection PyProtectedMember
from sklearn.utils.testing import assert_allclose
from sklearn.utils.testing import assert_array_less
from sklearn.utils.testing import assert_equal
from sklearn.utils.testing import assert_greater
from sklearn.utils.testing import assert_greater_equal
from sklearn.utils.testing import assert_less_equal
from sklearn.utils.testing import assert_raises
from sklearn.utils.testing import assert_true

from sklearn.metrics import roc_auc_score
from sklearn.metrics import accuracy_score
from scipy.stats import rankdata

# temporary solution for relative imports in case  combo is not installed
# if  combo is installed, no need to use the following line
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from combo.models.classifier_comb import BaseClassifierAggregator
from combo.models.classifier_comb import SimpleClassifierAggregator


# Check sklearn\tests\test_base
# A few test classes
# noinspection PyMissingConstructor,PyPep8Naming
class MyEstimator(BaseClassifierAggregator):

    def __init__(self, l1=0, empty=None):
        self.l1 = l1
        self.empty = empty

    def fit(self, X, y=None):
        pass

    def predict(self, X):
        pass

    def predict_proba(self, X):
        pass


# noinspection PyMissingConstructor
class K(BaseClassifierAggregator):
    def __init__(self, c=None, d=None):
        self.c = c
        self.d = d

    def fit(self, X, y=None):
        pass

    def predict(self, X):
        pass

    def predict_proba(self, X):
        pass


# noinspection PyMissingConstructor
class T(BaseClassifierAggregator):
    def __init__(self, a=None, b=None):
        self.a = a
        self.b = b

    def fit(self, X, y=None):
        pass

    def predict(self, X):
        pass

    def predict_proba(self, X):
        pass


# noinspection PyMissingConstructor
class ModifyInitParams(BaseClassifierAggregator):
    """Deprecated behavior.
    Equal parameters but with a type cast.
    Doesn't fulfill a is a
    """

    def __init__(self, a=np.array([0])):
        self.a = a.copy()

    def fit(self, X, y=None):
        pass

    def predict(self, X):
        pass

    def predict_proba(self, X):
        pass


# noinspection PyMissingConstructor
class VargEstimator(BaseClassifierAggregator):
    """scikit-learn estimators shouldn't have vargs."""

    def __init__(self, *vargs):
        pass

    def fit(self, X, y=None):
        pass

    def predict(self, X):
        pass

    def predict_proba(self, X):
        pass


class TestBase(unittest.TestCase):
    def test_repr(self):
        # Smoke test the repr of the base estimator.
        my_estimator = MyEstimator()
        repr(my_estimator)
        test = T(K(), K())
        assert_equal(
            repr(test),
            "T(a=K(c=None, d=None), b=K(c=None, d=None))"
        )

        some_est = T(a=["long_params"] * 1000)
        assert_equal(len(repr(some_est)), 415)

    def test_str(self):
        # Smoke test the str of the base estimator
        my_estimator = MyEstimator()
        str(my_estimator)

    def test_get_params(self):
        test = T(K(), K())

        assert_true('a__d' in test.get_params(deep=True))
        assert_true('a__d' not in test.get_params(deep=False))

        test.set_params(a__d=2)
        assert_true(test.a.d == 2)
        assert_raises(ValueError, test.set_params, a__a=2)


class TestAverage(unittest.TestCase):
    def setUp(self):
        self.roc_floor = 0.9
        self.accuracy_floor = 0.9

        random_state = 42
        X, y = load_breast_cancer(return_X_y=True)

        self.X_train, self.X_test, self.y_train, self.y_test = \
            train_test_split(X, y, test_size=0.4, random_state=random_state)

        classifiers = [DecisionTreeClassifier(random_state=random_state),
                       LogisticRegression(random_state=random_state),
                       KNeighborsClassifier(),
                       RandomForestClassifier(random_state=random_state),
                       GradientBoostingClassifier(random_state=random_state)]

        self.clf = SimpleClassifierAggregator(classifiers, method='average')
        self.clf.fit(self.X_train, self.y_train)

    def test_parameters(self):
        assert_true(hasattr(self.clf, 'classifiers') and
                    self.clf.classifiers is not None)

    def test_train_scores(self):
        y_train_predicted = self.clf.predict(self.X_train)
        assert_equal(len(y_train_predicted), self.X_train.shape[0])

        # check performance
        assert_greater(accuracy_score(self.y_train, y_train_predicted),
                       self.accuracy_floor)

    def test_prediction_scores(self):
        y_test_predicted = self.clf.predict(self.X_test)
        assert_equal(len(y_test_predicted), self.X_test.shape[0])

        # check performance
        assert_greater(accuracy_score(self.y_test, y_test_predicted),
                       self.accuracy_floor)

    def test_prediction_proba(self):
        y_test_predicted = self.clf.predict_proba(self.X_test)
        assert_greater_equal(y_test_predicted.min(), 0)
        assert_less_equal(y_test_predicted.max(), 1)

        # check performance
        assert_greater(roc_auc_score(self.y_test, y_test_predicted[:, 1]),
                       self.roc_floor)

        # check shape of integrity
        n_classes = len(np.unique(self.y_train))
        assert_equal(y_test_predicted.shape, (self.X_test.shape[0], n_classes))

        # check probability sum is 1
        y_test_predicted_sum = np.sum(y_test_predicted, axis=1)
        assert_allclose(np.ones([self.X_test.shape[0], ]),
                        y_test_predicted_sum)

    def tearDown(self):
        pass


class TestWeightedAverage(unittest.TestCase):
    def setUp(self):
        self.roc_floor = 0.9
        self.accuracy_floor = 0.9

        random_state = 42
        X, y = load_breast_cancer(return_X_y=True)

        self.X_train, self.X_test, self.y_train, self.y_test = \
            train_test_split(X, y, test_size=0.4, random_state=random_state)

        clf_weights = np.array([0.1, 0.4, 0.1, 0.2, 0.2])

        classifiers = [DecisionTreeClassifier(random_state=random_state),
                       LogisticRegression(random_state=random_state),
                       KNeighborsClassifier(),
                       RandomForestClassifier(random_state=random_state),
                       GradientBoostingClassifier(random_state=random_state)]

        self.clf = SimpleClassifierAggregator(classifiers, method='average',
                                              weights=clf_weights)
        self.clf.fit(self.X_train, self.y_train)

    def test_parameters(self):
        assert_true(hasattr(self.clf, 'classifiers') and
                    self.clf.classifiers is not None)

        # print clf details
        self.clf

        # set parameters
        self.clf.set_params()

    def test_train_scores(self):
        y_train_predicted = self.clf.predict(self.X_train)
        assert_equal(len(y_train_predicted), self.X_train.shape[0])

        # check performance
        assert_greater(accuracy_score(self.y_train, y_train_predicted),
                       self.accuracy_floor)

    def test_prediction_scores(self):
        y_test_predicted = self.clf.predict(self.X_test)
        assert_equal(len(y_test_predicted), self.X_test.shape[0])

        # check performance
        assert_greater(accuracy_score(self.y_test, y_test_predicted),
                       self.accuracy_floor)

    def test_prediction_proba(self):
        y_test_predicted = self.clf.predict_proba(self.X_test)
        assert_greater_equal(y_test_predicted.min(), 0)
        assert_less_equal(y_test_predicted.max(), 1)

        # check performance
        assert_greater(roc_auc_score(self.y_test, y_test_predicted[:, 1]),
                       self.roc_floor)

        # check shape of integrity
        n_classes = len(np.unique(self.y_train))
        assert_equal(y_test_predicted.shape, (self.X_test.shape[0], n_classes))

        # check probability sum is 1
        y_test_predicted_sum = np.sum(y_test_predicted, axis=1)
        assert_allclose(np.ones([self.X_test.shape[0], ]),
                        y_test_predicted_sum)

    def tearDown(self):
        pass


if __name__ == '__main__':
    unittest.main()