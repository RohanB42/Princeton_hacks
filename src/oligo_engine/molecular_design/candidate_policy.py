"""Shared molecular scorer; grammar actions marginalize legal completions.

No position-specific molecular logits. All features are label-free; only queried
history contains endpoint predictions. The policy prior is learned, not a call to
the frozen endpoint oracle. Administrative actions remain history-conditioned.
"""

import numpy as np
import torch
from sb3_contrib.common.maskable.distributions import MaskableDistribution
from sb3_contrib.common.maskable.policies import MaskableActorCriticPolicy
from torch import nn

from .policy import SearchEncoder


class CandidatePolicy(MaskableActorCriticPolicy):
    def __init__(self, *args, action_tokens: list[dict], **kwargs) -> None:
        self.action_tokens = action_tokens
        kwargs["features_extractor_class"] = SearchEncoder
        super().__init__(*args, **kwargs)

    def _build(self, lr_schedule) -> None:
        super()._build(lr_schedule)
        size = int(np.prod(self.observation_space["candidates"].shape[1:]))
        self.molecule = nn.Sequential(
            nn.Linear(size, 64), nn.GELU(), nn.Linear(64, 64), nn.GELU()
        )
        self.endpoint = nn.Linear(64, 2)
        self.query = nn.Linear(self.mlp_extractor.latent_dim_pi, 64)
        nn.init.normal_(self.query.weight, std=0.01)
        nn.init.zeros_(self.query.bias)
        administrative = [
            i
            for i, t in enumerate(self.action_tokens)
            if t["kind"] in {"STOP", "NEW", "CANCEL", "COMMIT", "PARENT", "EDIT"}
        ]
        self.register_buffer("administrative", torch.tensor(administrative))
        # Replace, rather than retain unused per-position parameters.
        self.action_net = nn.Linear(
            self.mlp_extractor.latent_dim_pi, len(administrative)
        )
        nn.init.normal_(self.action_net.weight, std=0.01)
        nn.init.zeros_(self.action_net.bias)
        self.optimizer = self.optimizer_class(
            self.parameters(), lr=lr_schedule(1), **self.optimizer_kwargs
        )

    def _get_constructor_parameters(self) -> dict:
        return {
            **super()._get_constructor_parameters(),
            "action_tokens": self.action_tokens,
        }

    def molecular_predictions(self, candidates: torch.Tensor) -> torch.Tensor:
        """Two uncalibrated logits: screen eligibility and objective utility."""
        return self.endpoint(self.molecule(candidates.flatten(-2)))

    def candidate_scores(self, obs: dict, latent_pi: torch.Tensor) -> torch.Tensor:
        features = self.molecule(obs["candidates"].flatten(-2))
        predictions = torch.sigmoid(self.endpoint(features))
        prior = 4 * predictions[..., 0] * predictions[..., 1]
        residual = (features * self.query(latent_pi)[:, None, :]).sum(-1) / 8
        return prior + residual

    def _distribution(
        self, obs: dict, latent_pi: torch.Tensor, action_masks=None
    ) -> MaskableDistribution:
        scores = self.candidate_scores(obs, latent_pi)
        available = obs["completion_mask"] * obs["candidate_mask"]
        # Stabilized marginalization; terminal observations may have no completions.
        masked = scores.masked_fill(available == 0, -1e8)
        weights = (masked - masked.max(dim=1, keepdim=True).values).exp() * available
        indices = obs["candidate_tokens"].long().flatten(1)
        mass = torch.zeros((len(scores), self.action_space.n), device=scores.device)
        mass = mass.scatter_add(
            1, indices, weights[..., None].expand(-1, -1, 5).flatten(1)
        )
        logits = mass.clamp_min(1e-30).log()
        admin = self.action_net(latent_pi)
        logits = logits.scatter(
            1, self.administrative[None, :].expand(len(scores), -1), admin
        )
        distribution = self.action_dist.proba_distribution(action_logits=logits)
        if action_masks is not None:
            distribution.apply_masking(action_masks)
        return distribution

    def forward(
        self, obs: dict, deterministic: bool = False, action_masks=None
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        pi, vf = self.mlp_extractor(self.extract_features(obs))
        dist = self._distribution(obs, pi, action_masks)
        actions = dist.get_actions(deterministic=deterministic)
        return actions, self.value_net(vf), dist.log_prob(actions)

    def evaluate_actions(
        self, obs: dict, actions: torch.Tensor, action_masks=None
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        pi, vf = self.mlp_extractor(self.extract_features(obs))
        dist = self._distribution(obs, pi, action_masks)
        return self.value_net(vf), dist.log_prob(actions), dist.entropy()

    def get_distribution(self, obs: dict, action_masks=None) -> MaskableDistribution:
        pi = self.mlp_extractor.forward_actor(self.extract_features(obs))
        return self._distribution(obs, pi, action_masks)
