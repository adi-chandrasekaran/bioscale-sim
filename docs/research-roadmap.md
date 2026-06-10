# Research roadmap

## Paper 1: Mutation-to-protein layer

Question: Can mutation annotations be translated into interpretable protein-function parameters?

Build: Mutation engine + protein effect predictor.

Evaluation idea: Compare the direction of predicted effects against curated examples from known pathogenic variants.

## Paper 2: Protein-to-pathway propagation

Question: Can protein-level loss of function be propagated through a simplified pathway model to generate plausible pathway disruptions?

Build: Pathway graph simulator.

Evaluation idea: Use p53 pathway examples and check whether loss of p53 decreases apoptosis, cell-cycle arrest, and DNA repair in the model.

## Paper 3: Pathway-to-cell phenotype model

Question: Can pathway state changes be translated into cell-level behavior variables?

Build: Cell simulator.

Evaluation idea: Show that pathway disruption changes proliferation, death, stress, and genomic instability in expected directions.

## Paper 4: Cell-to-population dynamics

Question: Can a cell phenotype explain clonal expansion over time?

Build: Population simulator.

Evaluation idea: Compare low-risk and high-risk mutation scenarios and show different expansion trajectories.

## Paper 5: Integrated multi-scale framework

Question: Can a modular pipeline connect disease gene candidates to ecosystem-level disease behavior?

Build: Full linked pipeline.

Evaluation idea: Run a case study on TP53/p53 pathway and show interpretable outputs at every layer.
