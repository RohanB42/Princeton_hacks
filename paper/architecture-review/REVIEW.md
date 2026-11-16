# Architecture figure: proposed replacement

Prepared in a side conversation at the user's explicit request. **Not integrated into the manuscript.** No communication with the main agent or subagent delegation took place; side conversations do not permit those operations.

## Assessment

The current figure repeats the surrounding prose as a list of data fields and process labels. Its main scientific distinction—predicted feedback versus purchased measured feedback—is useful, but the shared-foundation list and budget subtitles occupy disproportionate space. The arrows show only forward flow even though the important behavior is sequential decision-making.

## Recommended change

Replace it with the compact two-loop alternative in `decision-loops.svg` (preview: `decision-loops.png`). It removes the shared-foundation inventory, places the two tasks side by side, makes feedback explicit, uses sentence-case serif text, and replaces “belief” with the more accessible “estimates.” The conceptual distinction is carried by “Predict properties” versus “Reveal measurement.”

The drawing is 7 × 1.45 inches before tight cropping, compared with 7 × 2.1 inches for the current drawing. This is a nominal drawing-height comparison, not a measured manuscript pagination saving. The original font sizes and template layout should remain unchanged.

“Shortlist” is a reader-facing summary of the scored-candidate archive, not a proposal to change the environment's state or discard its audit history. “Estimates” refers to campaign predictions and uncertainty updated from paid outcomes.

Suggested caption:

> Two budgeted decision loops. Molecular design scores proposed molecules with predictive models; experimental selection purchases recorded measurements and updates its estimates. Each task uses its own feedback and resource budget to make the next decision.

If space remains tight after Related Work is drafted, remove the architecture figure entirely and replace its introduction cross-reference with this sentence:

> Molecular design evaluates proposed molecules using model predictions, whereas experimental selection purchases recorded measurements and updates campaign estimates; both operate under explicit budgets.

## Integration note for the main conversation

Review this alternative, then either export it to the manuscript's vector-PDF figure format or remove the existing architecture figure and its cross-reference. The editable drawing script is `draw_alternative.py`. Preserve the existing manuscript and figure generator until integration is chosen. This review does not request changes to empirical figures or scientific results.
