# Cyber Range As Scientific Instrument Notes

ACES experiment core should model the cyber range as a scientific instrument,
not merely as a deployment runtime. This means scenario descriptions, execution
apparatus, measurement channels, and result artifacts are part of experiment
validity.

## Cyber Range And Testbed Literature

Central sources:

- Yamin, Katt, and Gkioulos 2020, cyber ranges and security testbeds. DOI:
  10.1016/j.cose.2019.101636.
- Ukwandu et al. 2020, cyber-range and test-bed review. DOI:
  10.3390/s20247148.
- Yamin and Katt 2022, modeling and executing cybersecurity exercise scenarios.
  DOI: 10.1016/j.cose.2022.102635.
- Wen, Yamin, and Katt 2021, ontology-based scenario modeling. DOI:
  10.1109/EuroSPW54576.2021.00032.
- Yamin and Katt 2022, attack and defense agents in cyber ranges. DOI:
  10.1016/j.cose.2022.102892.

Implications:

- A scenario describes environment, roles, topology, objectives, and exercise
  conditions. It is reusable across many experiment tasks.
- A task binds a scenario to a research or evaluation protocol.
- Attack/defense agents and participant behavior need explicit roles and
  stochastic/parameter context when they affect results.
- Cyber-range ontology work supports controlled concepts for topology,
  scenario, event, actor, attack, defense, objective, and measurement.

## DETER And Security Experimentation

Central sources:

- Benzel et al. 2006, experience with DETER. DOI:
  10.1109/TRIDNT.2006.1649172.
- Benzel et al. 2009, current developments in DETER. DOI:
  10.1109/CATCH.2009.30.
- Mirkovic et al. 2010, DETER project and cyber-security experimentation. DOI:
  10.1109/THS.2010.5655108.
- Benzel 2011, science of cyber-security experimentation. DOI:
  10.1145/2076732.2076752.
- Peisert and Bishop 2007, computer security experiment design. DOI:
  10.1007/978-0-387-73269-5_19.
- Schwab and Kline 2019, program-scale cybersecurity experimentation. DOI:
  10.1109/EuroSPW.2019.00017.

Implications:

- Cyber-security experiments require clear hypotheses, controls, measurement
  plans, and reproducibility support.
- Testbeds are instruments whose configuration and limitations affect the
  evidence produced.
- Program-scale experimentation needs repeatable setup, comparable artifacts,
  and well-defined experiment packages.
- ACES must retain apparatus context separately from authored scenario meaning
  because the same scenario can produce different evidence on different
  backends, hosts, processors, or compatibility modes.

## Reproduction Across Emulation Testbeds

Central sources:

- Tarman et al. 2021, reproduced cyber experimentation across emulation
  testbeds. DOI: 10.1145/3474718.3474725.
- Thorpe et al. 2022, VM and host metrics for cyber emulation verification.
  DOI: 10.1145/3546096.3546115.
- Farhat et al. 2022, measuring and analyzing DoS flooding experiments. DOI:
  10.1145/3546096.3546105.
- Balto et al. 2023, hybrid IoT cyber range. DOI: 10.3390/s23063071.
- Faeroy, Yamin, Shukla, and Katt 2023, automatic verification/execution of
  cyber attacks on IoT devices. DOI: 10.3390/s23020733.

Implications:

- Apparatus identity is a scientific variable, not incidental infrastructure.
- Host and VM metrics can be needed to verify whether an emulated experiment was
  executed under valid conditions.
- Network load, timing, resource contention, and implementation details can
  alter results.
- Hybrid physical/virtual cyber ranges make apparatus boundaries even more
  important because physical devices, emulators, and virtual assets may coexist.

Design requirement:

- The run model must include planned apparatus declarations and observed
  apparatus evidence links. A mismatch between planned and observed setup should
  be representable.

## Simulation V&V And Instrument Validity

Central sources:

- Oberkampf and Trucano 2002. DOI: 10.1016/S0376-0421(02)00005-2.
- Oberkampf, Trucano, and Hirsch 2004. DOI: 10.1115/1.1767847.
- Roy and Oberkampf 2011. DOI: 10.1016/j.cma.2011.03.016.
- Oberkampf and Roy 2010. DOI: 10.1017/CBO9780511760396.
- Oberkampf and Smith 2017. DOI: 10.1115/1.4037887.
- Kennedy and O'Hagan 2001. DOI: 10.1111/1467-9868.00294.
- Santner, Williams, and Notz 2003. DOI: 10.1007/978-1-4757-3799-8.
- Sargent 2013. DOI: 10.1057/jos.2012.20.

Implications for ACES:

- Verification asks whether the apparatus and implementation execute as
  specified.
- Validation asks whether the apparatus and scenario adequately represent the
  real system or construct of interest.
- Uncertainty quantification requires records of controlled and uncontrolled
  factors.
- Calibration and validation data should be distinguishable from evaluation
  data.
- Computer experiment design supports repeated runs and structured variation of
  inputs; ACES studies should be able to describe such designs.

Design requirement:

- `apparatus_context` should record backend/processor identity, host and
  execution environment, compatibility declarations, manifest selections,
  configuration, parameters, stochastic controls, measurement channels, and
  known limitations.
- `study` should be able to declare apparatus variation as a planned factor,
  not only as an after-the-fact note.

## Empirical Software Engineering Criteria

Central sources:

- Wohlin et al. 2012, experimentation in software engineering. DOI:
  10.1007/978-3-642-29044-2.
- Kitchenham et al. 2002, empirical research guidelines. DOI:
  10.1109/TSE.2002.1027796.
- Shull et al. 2008, replications in empirical software engineering. DOI:
  10.1007/s10664-008-9060-1.
- Juristo and Vegas 2011, non-exact replications. DOI:
  10.1007/s10664-010-9141-9.

Implications:

- Studies need research questions, variables, hypotheses or claims, validity
  threats, experiment units, treatments, controls, assignment, and analysis
  design.
- Replications may be exact, close, or conceptual; apparatus/context changes
  must be explicit.
- Conclusion validity and external validity depend on sampling, randomization,
  blocking, and analysis details.

ACES translation:

- `study` is the right home for research questions, claims, sampling rationale,
  validity threats, comparison structure, and analysis plan.
- `task` is the right home for evaluation protocol and unit-of-analysis
  semantics.
- `run` is the right home for execution facts.
- `apparatus_context` is the right home for instrument setup and observed
  execution context.

## Minimum Instrument Criteria

The ACES design should preserve these distinctions:

- Authored scenario meaning: what environment and behavior are declared.
- Experiment task: what scientific/evaluation question is asked of that
  scenario.
- Execution apparatus: what processor/backend/configuration realizes the run.
- Live lifecycle state: what the control plane is currently doing.
- Archival run record: what execution happened and under what context.
- Result artifact: what was measured and how it links back to evidence.
- Study/collection: why multiple tasks/runs/results are grouped and compared.

The design should also support these evidence needs:

- repeatability within the same apparatus;
- reproduction on a different apparatus;
- comparison across processors, backends, configurations, or cyber-defense
  policies;
- validation against expected cyber-range behavior;
- audit of failed, partial, aborted, or invalidated runs;
- packaging of a complete experiment evidence bundle.
