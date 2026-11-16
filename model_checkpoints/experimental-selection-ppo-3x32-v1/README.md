# Experimental-selection PPO, three layers of 32

Published at the user’s explicit request with the research portal handoff.
Selected policy seed: **613**, by the highest recorded development score among
seeds 613–617 (12.6667 mean development hits). This is an inference checkpoint;
exact training resumption is not promised.

The selected policy averaged 12.20 new hits on the two already examined evaluation
targets; the reported five-policy average is 11.98. Neither establishes superiority
over the strongest heuristic or validity for live researchers.

Install Poetry 2.1.4 on Python 3.11, then:

```sh
poetry sync --with science,reporting,experimental-rl
```

Verify `publication.json` SHA-256 hashes before loading. `policy.zip` is an SB3
MaskablePPO checkpoint; load only this trusted repository artifact.
`source_parameters.npz` contains the matching 4,096-feature Ridge coefficients and
intercept. Use `experimental_rl.belief.encode` with the pinned context/chemistry
features, and the residual scale in `source_prior.json`. Policy observation order
and expert action order are in `policy_manifest.json` and the source environment.
The partition manifest records source and campaign membership without row outcomes.

See `docs/research-portal-implementation-handoff.md` before website integration.
The replay environment requires historical pool labels and must be adapted for
real delayed researcher feedback. No raw datasets or experiment ledgers are included.
