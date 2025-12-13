"""
Regime Detection for Trading MCTS.

Provides Hidden Markov Model (HMM) based regime detection:
- Bull, Bear, High-Volatility, Low-Volatility states
- Transition probability tracking
- Regime trigger mechanism for batch recomputation
"""

from reasoning_trading.regime.hmm import (
    HiddenMarkovModel,
    HMMConfig,
    RegimeState,
    TransitionMatrix,
)
from reasoning_trading.regime.detector import (
    RegimeDetector,
    RegimeDetectorConfig,
    RegimeClassification,
    RegimeHistory,
)
from reasoning_trading.regime.features import (
    RegimeFeatureExtractor,
    RegimeFeatures,
)

__all__ = [
    "HiddenMarkovModel",
    "HMMConfig",
    "RegimeState",
    "TransitionMatrix",
    "RegimeDetector",
    "RegimeDetectorConfig",
    "RegimeClassification",
    "RegimeHistory",
    "RegimeFeatureExtractor",
    "RegimeFeatures",
]
