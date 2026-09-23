You need to deliver a production training pipeline for a room-occupancy phase identification project. The team has already prepared the dev sequence index, holdout sequence index, phase label mapping, and the delivery contract, but there is not yet a stable, reusable production-grade entrypoint. The phase labels here describe the transition stage of a recent sensor trajectory segment, not a snapshot state at a single point in time. Your task is to generate a runnable, reproducible, and offline-replayable training workflow and produce the official deliverables, while preserving the existing data pipeline and delivery boundaries.

Input data is located at:
- `/root/environment/project/`: project scaffold, config placeholders, and run entrypoint directory
- `/root/environment/data/phase_sequences/`: the dev sequence index, holdout sequence index, per-sample sequence files, feature descriptions, phase label mapping, and provenance metadata
- `/root/environment/data/contracts/`: output contracts, split constraints for dev/validation/holdout, and model bundle manifest requirements

Business constraints:
- The final pipeline must perform training, validation, holdout evaluation, and model export from the provided sequence indices and per-sample sequence files; you must not change it into manual result curation or static answer assembly.
- The training and validation splits must be dynamically derived from the dev index according to the source-partition constraints defined in the contract. Holdout evaluation must use only the provided holdout index; you must not merge holdout back into the fitting stage, and you must not ignore the contract by using a hard-coded split.
- Each sequence sample includes an explicit `sequence_length`; formal training, evaluation, and exported inference must respect this effective-length boundary.
- Each `sequence_path` corresponds to an independent per-sample `.npy` file. The number of rows stored on disk is not guaranteed to be consistent across files; do not assume “the current file lengths happen to match” as a formal premise. `sequence_length` is the only authoritative boundary for the valid prefix.
- Do not first materialize an entire split into a single ndarray with a fixed time dimension and then assume all later sequences share that same time dimension; the formal pipeline must handle differences in on-disk row counts across per-sample files.
- Official deliverables must be reproducible. Do not write wall-clock time, temporary paths, random filenames, or other one-off fields into the final deliverables.
- The final pipeline must run stably in a CPU-only environment, and the exported offline replay results must be consistent with the formal evaluation definitions.
- The model bundle must retain the core weights, key metadata, and necessary configuration for formal inference and future continued training.
- Snapshots for restoring training state must include only the key state required for resuming; do not stuff extra array objects unrelated to continued training directly into the snapshot payload.

Your tasks

1. Under `/root/environment/project/`, generate the formal training and export pipeline so the following entrypoint can successfully produce the final deliverables:

```bash
python /root/environment/project/run_pipeline.py --output /root/answer
```

2. The generated pipeline must cover sequence loading, contract-driven dev split, training, validation, holdout evaluation, prediction export, and model bundle export, and must continue to use the existing directories in the repository as the only system-of-record sources.

3. The final results must include sample-level predictions, overall metrics, per-class performance, per-epoch training history, and a reproducible model bundle manifest.

Output formats:

- `/root/answer/holdout_predictions.csv`
  - Must cover all holdout sequence samples
  - Must include columns: `sequence_id`, `source_file`, `anchor_timestamp`, `sequence_length`, `phase_id`, `phase_label`, `predicted_phase_id`, `predicted_phase_label`, `confidence`

- `/root/answer/holdout_metrics.json`
  - Top-level must include keys: `dataset`, `split`, `training`, `holdout`, `per_class`, `notes`
  - `holdout` must include: `accuracy`, `macro_f1`, `weighted_f1`
  - `training` must explicitly provide `best_epoch` and `selected_val_macro_f1` corresponding to the exported artifact
  - `split` must explicitly describe the sample counts for train/validation/holdout, the source partitions, and the validation contract value used
  - `split` must explicitly include at least: `train_sequences`, `val_sequences`, `holdout_sequences`, `train_sources`, `val_sources`, `holdout_sources`, `validation_sources_from_contract`

- `/root/answer/confusion_matrix.csv`
  - Must output the confusion matrix using the standard phase labels
  - Must include an `actual_phase_label` column, and output prediction-label columns `pred_STEADY_EMPTY`, `pred_RAMPING_UP`, `pred_RAMPING_DOWN`, `pred_STEADY_OCCUPIED`
  - Row/column label semantics must be consistent with the classes used in `holdout_predictions.csv` and `holdout_metrics.json`

- `/root/answer/training_history.csv`
  - Must be per-epoch training history
  - Must cover at least 10 real training epochs
  - Must include at least columns: `epoch`, `train_loss`, `val_loss`, `val_macro_f1`, `selected_for_export`

- `/root/answer/model_bundle/manifest.json`
  - Must include path descriptions for each core file in the exported model bundle
  - Must cover the formal weights file, a snapshot that can restore training, the phase label mapping, preprocessing information, runtime configuration, split metadata, and the inference entrypoint
  - The manifest must be stable under identical inputs; do not write timestamps or one-off fields that change on each run
  - The model bundle must include a runnable `inference.py`, a formal weights file, and a snapshot that can restore training state, so the exported artifacts can replay predictions for the specified split without retraining
  - The inference weights file and the training-resume snapshot must both be portable and directly replayable in a CPU environment; the snapshot payload must include only the state truly needed to restore training
  - The top level of the training-resume snapshot must explicitly include at least: `epoch`, `model_state_dict`, `optimizer_state_dict`, `selected_val_macro_f1`

Notes:

- You may modify or add code, configuration, and helper scripts under `/root/environment/project/`, but do not modify any input data under `/root/environment/data/`.
- You may use locally installed dependencies in the environment, but do not introduce new services that require external accounts, cloud permissions, or interactive logins.
- Do not evade the task by hard-coding predictions, hard-coding metrics, deleting the training workflow, skipping real evaluation, faking the label mapping, only working for fixed samples, or using holdout data early for fitting.
- Do not evade the task by ignoring the contract and using a hard-coded validation partition, merging the entire dev set directly into fitting, or allowing the holdout set to participate in parameter updates.
- Do not modify hidden downstream services, test files, environment baselines, or dependency configuration.
- If you write temporary files, the official entrypoint must still write the correct deliverables into `/root/answer/`.
