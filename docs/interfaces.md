# Future boundary objects (specification only)

| Object | Required fields and ownership | Open decisions |
| --- | --- | --- |
| Sample identity | `data`: stable sample ID, source dataset and revision, HELM, chemistry, target identifier, original row provenance | Target and chemistry normalization |
| Endpoint observation | `data`: sample ID, endpoint ID, measured value, units, direction, assay provenance, missingness flag | Score scaling and cross-assay comparability |
| Split manifest | `evaluation`: sample ID, split name, partition, seed, upstream revision, construction parameters | Grouping and duplicate handling |
| Prediction | `models`: sample ID, endpoint ID, estimate, uncertainty value and explicit type, model revision | Calibration and units |
| Acquisition request/response | `acquisition`: eligible pool IDs, budget, seed, policy config; selected IDs and scores | Diversity and uncertainty combination |
| Experiment run | `evaluation`: data and split identity, label budget, acquired IDs, config, seeds, code/environment revisions | Band method and threshold tolerance |
| Candidate hypothesis | `design`: HELM, target, chemistry, predicted values, warnings, uncertainty, provenance, unvalidated status | Reward weights, signs, compatibility |

Missing endpoint labels must remain missing; predictions and hypotheses are never observations. No executable schema is provided yet.
