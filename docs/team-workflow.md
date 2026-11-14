# Team workflow

The disjoint ownership plan and dependencies are in
[IMPLEMENTATION_TASKS.md](IMPLEMENTATION_TASKS.md). No contributors or worktrees
have been assigned yet. The current integrator owns the initial contracts, fixture
runner, shared docs/configs and source verification.

Use short branches and PRs into `main`. The integrator coordinates metadata,
lockfiles, configs and interface changes; other owners propose those edits. Preserve
the executable pipeline. Suggested protection: review plus repository-health CI;
hosting settings are not changed here. A research task needs tested code, reproducible
config, results and an honest interpretation before closure.
