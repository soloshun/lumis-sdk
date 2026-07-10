# Feature drift investigation

1. Confirm the metric, reference window, threshold, and affected feature.
2. Segment the new population by source, geography, customer cohort, or ingestion version before calling it model drift.
3. Compare feature-generation code and upstream source contracts with the last accepted run.
4. Evaluate the deployed model on a labeled holdout if labels are available.
5. Do not retrain, promote, or alter thresholds until a human reviews the evidence.
