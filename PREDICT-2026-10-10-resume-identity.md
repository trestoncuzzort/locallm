# Factorial trainer resume identity

Registered before the changed-batch resume test. The trainer states that a resume
re-enters the same epoch at the same offset, but its comparison currently checks
arm, seed, dataset files, initial checkpoint and example order, omitting batch
size. Epoch and skip are then recalculated using the new command's batch size.

Prediction: a checkpoint resumed with another batch size is accepted even though
its next batch differs. Probe before repair. After repair, changed trajectory
settings must be rejected by name before loading mutable run state; an unchanged
resume must preserve exact checkpoint tensors and accounting. Identify required
settings from the actual training and encoding code, rather than blanket-locking
all command-line options. Logging/output and dry-run stopping controls may differ.

Prior work: this repository's test_train_factorial.py exact-resume check,
train_distributed.py identity validation, and the published PyTorch reproducibility
notes (https://pytorch.org/docs/stable/notes/randomness.html).

Results pending.

Before the data-byte probe: the current identity copies the dataset manifest but
does not hash the train.jsonl bytes it actually reads. Prediction: changed
completion text with unchanged task names and manifest is accepted on resume.
The byte read and its digest must come from the same read. Gradient clipping also
changes the trajectory but is absent from the saved identity; record it rather
than invent a value for an older checkpoint. Missing required identity fields
will require an explicit refusal, not an assumption about their old defaults.
