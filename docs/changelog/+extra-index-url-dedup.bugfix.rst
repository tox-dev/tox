Stop duplicating ``--extra-index-url`` entries when a requirements file adds a new extra index URL on a line that
also repeats an already-seen one: each new URL is now appended individually instead of re-adding the whole line.
