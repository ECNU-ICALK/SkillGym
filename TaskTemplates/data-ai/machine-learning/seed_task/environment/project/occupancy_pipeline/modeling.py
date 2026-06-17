from __future__ import annotations

import random

import numpy as np
import torch
from torch import nn


class PhaseSequenceClassifier(nn.Module):
    """Model scaffold for room-occupancy phase sequence classification."""

    def __init__(self, input_dim: int, hidden_dim: int, num_layers: int, num_classes: int, dropout: float) -> None:
        super().__init__()
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers
        self.num_classes = num_classes
        self.dropout = dropout

    def forward(self, x: torch.Tensor, lengths: torch.Tensor) -> torch.Tensor:
        raise NotImplementedError("Implement a variable-length sequence classifier.")


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.use_deterministic_algorithms(True)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False


def compute_standardization(valid_sequences: list[np.ndarray]) -> tuple[np.ndarray, np.ndarray]:
    """Compute deterministic feature-wise preprocessing statistics."""
    raise NotImplementedError("Implement preprocessing statistics.")


def softmax(logits: np.ndarray) -> np.ndarray:
    """Convert logits into normalized probabilities."""
    raise NotImplementedError("Implement probability normalization.")
