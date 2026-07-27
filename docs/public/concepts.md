# Understand the RAES model

Use these ideas to decide what a RAES result means.

## Authored scenario

A RAES SDL file records intent. It can name nodes, links, people, software,
goals, tasks, and evidence needs. The file is not a running environment.

## Realized environment

A processor and backend turn supported parts of the scenario into runtime
resources. Backend reports show what worked, what changed, and what was not
supported.

## Bounded reproduction

RAES can save inputs, choices, names, observations, and evidence for another
attempt. It does not promise equal outcomes, a fixed runtime, exact replay, or
scientific reproducibility.

## Conformance

Contracts and test fixtures check whether an implementation honors a stated
RAES boundary. Passing one profile does not mean that every SDL feature or
deployment target works.
