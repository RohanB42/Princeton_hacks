"""Attention over full target and query history; stock masked PPO distribution."""

import torch
from gymnasium import spaces
from stable_baselines3.common.torch_layers import BaseFeaturesExtractor
from torch import nn


class SearchEncoder(BaseFeaturesExtractor):
    """All target positions/history rows are visible; learned pooling is lossy.

    No claim that this learned representation is a sufficient Markov statistic.
    Four construction-conditioned attention queries summarize each complete input.
    """

    def __init__(self, observation_space: spaces.Dict, features_dim: int = 128) -> None:
        super().__init__(observation_space, features_dim)
        width = 32
        self.target = nn.Sequential(
            nn.Conv1d(7, width, 5, padding=2),
            nn.GELU(),
            nn.Conv1d(width, width, 3, padding=1),
            nn.GELU(),
        )
        self.history = nn.Linear(observation_space["history"].shape[-1] + 1, width)
        self.current = nn.Linear(observation_space["construction"].shape[0], width)
        self.queries = nn.Parameter(torch.randn(4, width) * 0.02)
        self.target_attention = nn.MultiheadAttention(width, 4, batch_first=True)
        self.history_attention = nn.MultiheadAttention(width, 4, batch_first=True)
        self.empty_history = nn.Parameter(torch.zeros(1, 1, width))
        shape = observation_space["patterns"].shape
        self.pattern = nn.Linear(shape[0] * shape[1] * shape[2], width)
        self.context = nn.Linear(observation_space["context"].shape[0], width)
        self.output = nn.Sequential(nn.Linear(width * 11, features_dim), nn.Tanh())

    def forward(self, observations: dict[str, torch.Tensor]) -> torch.Tensor:
        target = observations["target"]
        current = self.current(observations["construction"])
        query = self.queries[None, :, :] + current[:, None, :]
        target_values = self.target(target.transpose(1, 2)).transpose(1, 2)
        target_summary, _ = self.target_attention(
            query,
            target_values,
            target_values,
            key_padding_mask=target[:, :, :5].sum(dim=-1) == 0,
            need_weights=False,
        )
        history = observations["history"]
        positions = torch.linspace(0, 1, history.shape[1], device=history.device)
        positions = positions[None, :, None].expand(history.shape[0], -1, -1)
        values = self.history(torch.cat([history, positions], dim=-1))
        values = torch.cat(
            [self.empty_history.expand(history.shape[0], -1, -1), values], dim=1
        )
        mask = torch.cat(
            [
                torch.zeros((history.shape[0], 1), device=history.device),
                1 - observations["history_mask"],
            ],
            dim=1,
        ).bool()
        history_summary, _ = self.history_attention(
            query, values, values, key_padding_mask=mask, need_weights=False
        )
        return self.output(
            torch.cat(
                [
                    current,
                    target_summary.flatten(1),
                    history_summary.flatten(1),
                    self.pattern(observations["patterns"].flatten(1)),
                    self.context(observations["context"]),
                ],
                dim=1,
            )
        )
