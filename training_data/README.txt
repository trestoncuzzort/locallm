Drop your own text in this folder.

Any .txt, .md or .py file you put here (including in subfolders) becomes part of
the corpus your model learns from. More files, and more VARIED files, are worth
far more than more training steps: the model can only learn what is in here.

Then double-click the "Train My AI" shortcut on the Desktop. It rebuilds the
corpus from whatever is in this folder and opens the studio.

A few things worth knowing:
  - Many smaller documents beat one huge one. The validation split is taken by
    whole document, so a corpus of 3 files cannot be split sensibly.
  - Everything stays on this machine. Nothing is uploaded.
  - This README is skipped when building the corpus.
