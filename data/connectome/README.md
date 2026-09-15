# Connectome runtime data

The files `winding_l1_connectome.npz`, `groups.json`, and `neurons.json` are generated locally by
`tools/prepare_connectome.py` from Supplementary Data S1 of Winding et al.
(Science, 2023; DOI: 10.1126/science.add9330).

They are intentionally ignored by Git because the republishing repository does
not declare an explicit data license. Download the supplementary archive from:

https://github.com/brain-networks/larval-drosophila-connectome

The simulator detects the generated pack automatically and otherwise starts
with a clearly labeled deterministic synthetic scaffold.
