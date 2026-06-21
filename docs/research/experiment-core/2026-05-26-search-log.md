# Experiment Core Research Log

Date: 2026-05-26

Issue: #87, covering EXP-701 through EXP-705.

Purpose: gather published academic evidence before designing the ACES experiment
core model. The design target is cyber range as a scientific instrument: tasks,
runs, apparatus context, studies, and result groupings must support experiments
whose data can survive scrutiny under machine learning, cyber-security
experimentation, empirical software engineering, provenance, and simulation
validation criteria.

## Source Rule

Only published academic sources are used as evidence. Preprints, vendor pages,
project manuals, and standards documents may explain terminology but are not used
as primary research evidence in these notes.

One candidate was explicitly excluded:

- A TechRxiv preprint on cyber range scenario generation was found in Zotero but
  excluded because it is a preprint.

## Tooling Used

- Zotero search through the local citation tooling for known source names and
  cyber range terms.
- Crossref/OpenAlex search through the local citation tooling for literature
  discovery and DOI resolution.
- Forward and backward citation checks for OpenML, experiment databases,
  cyber-range experimentation, PROV, RO-Crate, and ML reproducibility sources.

The notes below retain enough detail to audit why the final design criteria
appear in the design notes and ADR.

## Search Families

### ML Rigor And Reproducibility

Queries used:

- `machine learning reproducibility checklist`
- `REFORMS machine learning science reproducibility`
- `machine learning leakage reproducibility crisis`
- `DOME recommendations supervised machine learning reproducibility`
- `statistical comparisons classifiers multiple data sets`
- `cross-validation survey model selection assessment`
- `deep reinforcement learning that matters reproducibility`
- `model cards data sheets data statements`

Included published sources:

- Kapoor et al., "REFORMS: Reporting standards for machine learning based
  science", Science Advances, 2024. DOI: 10.1126/sciadv.adk3452.
- Kapoor and Narayanan, "Leakage and the reproducibility crisis in
  machine-learning-based science", Patterns, 2023. DOI:
  10.1016/j.patter.2023.100804.
- Walsh et al., "DOME: recommendations for supervised machine learning
  validation in biology", Nature Methods, 2021. DOI:
  10.1038/s41592-021-01205-4.
- Haibe-Kains et al., "Transparency and reproducibility in artificial
  intelligence", Nature, 2020. DOI: 10.1038/s41586-020-2766-y.
- Gundersen and Kjensmo, "State of the Art: Reproducibility in Artificial
  Intelligence", AAAI, 2018. DOI: 10.1609/aaai.v32i1.11503.
- Pineau et al., "Improving reproducibility in machine learning research: a
  report from the NeurIPS 2019 reproducibility program", JMLR, 2021/2022.
- Lones, "Avoiding common machine learning pitfalls", Patterns, 2024. DOI:
  10.1016/j.patter.2024.101046.
- Mitchell et al., "Model Cards for Model Reporting", FAT*, 2019. DOI:
  10.1145/3287560.3287596.
- Gebru et al., "Datasheets for Datasets", Communications of the ACM, 2021.
  DOI: 10.1145/3458723.
- Bender and Friedman, "Data Statements for Natural Language Processing",
  Transactions of the ACL, 2018. DOI: 10.1162/tacl_a_00041.
- Dietterich, "Approximate Statistical Tests for Comparing Supervised
  Classification Learning Algorithms", Neural Computation, 1998. DOI:
  10.1162/089976698300017197.
- Demsar, "Statistical Comparisons of Classifiers over Multiple Data Sets",
  JMLR, 2006.
- Nadeau and Bengio, "Inference for the Generalization Error", Machine
  Learning, 2003. DOI: 10.1023/a:1024068626366.
- Arlot and Celisse, "A survey of cross-validation procedures for model
  selection", Statistics Surveys, 2010. DOI: 10.1214/09-SS054.

Design implications retained:

- Tasks need explicit evaluation protocols, not just scenarios.
- Splits, leakage controls, metrics, statistical analysis, and intended
  population must be task/study concepts.
- Runs must retain stochastic controls, repeated-run identity, environment
  state, and execution context.
- Studies must support comparison over many tasks, repeated runs, multiple
  metrics, and uncertainty/statistical analysis plans.

### Experiment Databases And ML Metadata

Queries used:

- `OpenML networked science machine learning`
- `experiment databases machine learning experiments`
- `MEX vocabulary machine learning experiment`
- `Ontology of core data mining entities`
- `ontology of scientific experiments Soldatova King`
- `MLflow provenance ML lifecycle`

Included published sources:

- Vanschoren et al., "OpenML: networked science in machine learning", SIGKDD,
  2014. DOI: 10.1145/2641190.2641198.
- Vanschoren et al., "Experiment databases: A new way to share, organize and
  learn from experiments", Machine Learning, 2012. DOI:
  10.1007/s10994-011-5277-0.
- Esteves et al., "MEX Vocabulary: a lightweight interchange format for machine
  learning experiments", SEMANTICS, 2015. DOI: 10.1145/2814864.2814883.
- Panov et al., "Ontology of core data mining entities", Data Mining and
  Knowledge Discovery, 2014. DOI: 10.1007/s10618-014-0363-0.
- Soldatova and King, "An ontology of scientific experiments", Journal of the
  Royal Society Interface, 2006. DOI: 10.1098/rsif.2006.0134.
- Zaharia et al., "Developments in MLflow", DEEM, 2020. DOI:
  10.1145/3399579.3399867.
- Souza et al., "Machine Learning Provenance Data in the Lifecycle of
  Scientific Machine Learning", WORKS, 2019. DOI:
  10.1109/WORKS49585.2019.00006.

Design implications retained:

- ACES should separate scenario/data objects, task definitions, executable
  flows/processors, run records, and evaluations.
- Evaluation outputs need stable links back to task, run, processor, scenario,
  and data snapshot identifiers.
- Metadata should be structured enough for indexing and later meta-analysis.
- The design should support a future semantic export path instead of baking
  one-off JSON fields that cannot be mapped to known experiment vocabularies.

### Provenance, FAIRness, And Research Object Packaging

Queries used:

- `Open Provenance Model`
- `PROV rationale provenance`
- `RO-Crate research artefacts`
- `FAIR Guiding Principles`
- `CWLProv workflow provenance`
- `Sumatra automated provenance computational experiments`
- `ReproZip reproducible computational experiments`
- `noWorkflow provenance scripts`

Included published sources:

- Moreau et al., "The Open Provenance Model core specification", Future
  Generation Computer Systems, 2011. DOI: 10.1016/j.future.2010.07.005.
- Moreau et al., "The rationale of PROV", Web Semantics, 2015. DOI:
  10.1016/j.websem.2015.04.001.
- Soiland-Reyes et al., "Packaging research artefacts with RO-Crate", Data
  Science, 2022. DOI: 10.3233/DS-210053.
- Wilkinson et al., "The FAIR Guiding Principles for scientific data management
  and stewardship", Scientific Data, 2016. DOI: 10.1038/sdata.2016.18.
- Khan et al., "Sharing interoperable workflow provenance: A review of best
  practices and their practical application in CWLProv", GigaScience, 2019.
  DOI: 10.1093/gigascience/giz095.
- Davison, "Automated Capture of Experiment Context for Easier Reproducibility
  in Computational Research", Computing in Science and Engineering, 2012. DOI:
  10.1109/MCSE.2012.41.
- Chirigati et al., "ReproZip: Computational Reproducibility With Ease",
  SIGMOD, 2016. DOI: 10.1145/2882903.2899401.
- Murta et al., "noWorkflow: Capturing and Analyzing Provenance of Scripts",
  IPAW, 2014. DOI: 10.1007/978-3-319-16462-5_6.
- Jimenez et al., "The Popper convention: making reproducible systems
  evaluation practical", IPDPSW, 2017. DOI: 10.1109/IPDPSW.2017.157.

Design implications retained:

- Runs must be provenance nodes, not mutable status summaries.
- ACES needs enough identifiers, version references, derivation links, and
  artifact roles to map to PROV-like entity/activity/agent structures.
- Packaging should be feasible through an RO-Crate-like export: task, run,
  apparatus, manifests, observations, metrics, and analysis artifacts need
  explicit roles and stable identifiers.
- Capture automation is useful, but design authority should remain separate
  from backend-native logs and raw payloads.

### Cyber Range, Security Experimentation, And Testbeds

Queries used:

- `cyber ranges security testbeds scenarios functions tools architecture`
- `modeling executing cyber security exercise scenarios cyber ranges`
- `ontology based scenario modeling cyber security exercise`
- `DETER science of cyber security experimentation`
- `computer security experiments design`
- `cybersecurity experimentation at program scale`
- `FAIR cybersecurity artifacts`
- `reproduced cyber experimentation studies emulation testbeds`
- `verification cyber emulation experiments host metrics`

Included published sources:

- Yamin, Katt, and Gkioulos, "Cyber ranges and security testbeds: Scenarios,
  functions, tools and architecture", Computers and Security, 2020. DOI:
  10.1016/j.cose.2019.101636.
- Yamin and Katt, "Modeling and executing cyber security exercise scenarios in
  cyber ranges", Computers and Security, 2022. DOI: 10.1016/j.cose.2022.102635.
- Wen, Yamin, and Katt, "Ontology-Based Scenario Modeling for Cyber Security
  Exercise", EuroS&P Workshops, 2021. DOI:
  10.1109/EuroSPW54576.2021.00032.
- Yamin and Katt, "Use of cyber attack and defense agents in cyber ranges",
  Computers and Security, 2022. DOI: 10.1016/j.cose.2022.102892.
- Ukwandu et al., "A Review of Cyber-Ranges and Test-Beds: Current and Future
  Trends", Sensors, 2020. DOI: 10.3390/s20247148.
- Benzel, Braden, et al., "Experience with DETER", TridentCom, 2006. DOI:
  10.1109/TRIDNT.2006.1649172.
- Benzel et al., "Current Developments in DETER Cybersecurity Testbed
  Technology", CATCH, 2009. DOI: 10.1109/CATCH.2009.30.
- Mirkovic et al., "The DETER project: Advancing the science of cyber security
  experimentation and test", HST, 2010. DOI: 10.1109/THS.2010.5655108.
- Benzel, "The science of cyber security experimentation: the DETER project",
  ACSAC, 2011. DOI: 10.1145/2076732.2076752.
- Peisert and Bishop, "How to Design Computer Security Experiments", 2007. DOI:
  10.1007/978-0-387-73269-5_19.
- Sommestad and Hallberg, "Cyber Security Exercises and Competitions as a
  Platform for Cyber Security Experiments", 2012. DOI:
  10.1007/978-3-642-34210-3_4.
- Schwab and Kline, "Cybersecurity Experimentation at Program Scale", EuroS&P
  Workshops, 2019. DOI: 10.1109/EuroSPW.2019.00017.
- Balenson et al., "Toward FAIR Cybersecurity Artifacts", Cybersecurity
  Experimentation and Test, 2022. DOI: 10.1145/3546096.3546104.
- Le Pochat and Joosen, "Analyzing Cyber Security Research Practices through a
  Meta-Research Framework", CSET, 2023. DOI: 10.1145/3607505.3607523.
- Tarman et al., "Comparing reproduced cyber experimentation studies across
  different emulation testbeds", CSET, 2021. DOI:
  10.1145/3474718.3474725.
- Thorpe et al., "Verification of Cyber Emulation Experiments Through VM and
  Host Metrics", CSET, 2022. DOI: 10.1145/3546096.3546115.
- Farhat et al., "Measuring and Analyzing DoS Flooding Experiments", CSET,
  2022. DOI: 10.1145/3546096.3546105.

Design implications retained:

- A cyber range scenario is not identical to an experiment task. It is an
  environment/exercise artifact that can be reused under multiple protocols.
- Apparatus must record emulation/testbed/backend identity, host and VM
  context, topology/manifests, compatibility declarations, and measurement
  affordances.
- Security experiments need explicit hypotheses or claims, variables,
  experimental units, controls, instrumentation, and repeatability conditions.
- Cross-testbed reproduction and instrument drift are core risks; ACES run
  records need enough apparatus context to diagnose them.

### Simulation V&V And Empirical Experiment Design

Queries used:

- `verification validation scientific computing experiments`
- `validation experiments criteria Oberkampf Smith`
- `predictive capability computational model validation uncertainty`
- `design analysis computer experiments`
- `experimentation in software engineering controlled experiments`
- `empirical software engineering guidelines experiments`
- `replication empirical software engineering`

Included published sources:

- Oberkampf and Trucano, "Verification and validation in computational fluid
  dynamics", Progress in Aerospace Sciences, 2002. DOI:
  10.1016/S0376-0421(02)00005-2.
- Oberkampf, Trucano, and Hirsch, "Verification, validation, and predictive
  capability in computational engineering and physics", Applied Mechanics
  Reviews, 2004. DOI: 10.1115/1.1767847.
- Roy and Oberkampf, "A comprehensive framework for verification, validation,
  and uncertainty quantification in scientific computing", Computer Methods in
  Applied Mechanics and Engineering, 2011. DOI:
  10.1016/j.cma.2011.03.016.
- Oberkampf and Roy, "Verification and Validation in Scientific Computing",
  Cambridge University Press, 2010. DOI: 10.1017/CBO9780511760396.
- Oberkampf and Smith, "Assessment Criteria for Computational Fluid Dynamics
  Model Validation Experiments", Journal of Verification, Validation and
  Uncertainty Quantification, 2017. DOI: 10.1115/1.4037887.
- Kennedy and O'Hagan, "Bayesian calibration of computer models", JRSS B,
  2001. DOI: 10.1111/1467-9868.00294.
- Santner, Williams, and Notz, "The Design and Analysis of Computer
  Experiments", Springer, 2003. DOI: 10.1007/978-1-4757-3799-8.
- Sargent, "Verification and validation of simulation models", Journal of
  Simulation, 2013. DOI: 10.1057/jos.2012.20.
- Wohlin et al., "Experimentation in Software Engineering", Springer, 2012.
  DOI: 10.1007/978-3-642-29044-2.
- Kitchenham et al., "Preliminary guidelines for empirical research in software
  engineering", IEEE TSE, 2002. DOI: 10.1109/TSE.2002.1027796.
- Shull et al., "The role of replications in Empirical Software Engineering",
  Empirical Software Engineering, 2008. DOI: 10.1007/s10664-008-9060-1.
- Juristo and Vegas, "The role of non-exact replications in software
  engineering experiments", Empirical Software Engineering, 2011. DOI:
  10.1007/s10664-010-9141-9.

Design implications retained:

- ACES should treat apparatus as part of instrument validity, not incidental
  runtime metadata.
- Formal distinctions are needed between authored scenario meaning, apparatus
  realization, live lifecycle state, and archival result records.
- Studies need validity framing: construct, internal, external, conclusion, and
  statistical validity threats.
- Reproduction and replication require records for exact replay attempts,
  conceptual replications, apparatus variations, and analysis comparability.

## Evidence Quality Notes

- The included corpus spans ML method reporting, empirical experiment design,
  provenance standards, research-object packaging, cyber-range/testbed research,
  and simulation V&V. This mix is deliberate because ACES is not just a cyber
  range runtime; it is intended to be an experiment instrument.
- Where standards are named, the evidence source is a peer-reviewed paper about
  that standard or format family, not the standard text itself.
- This log does not claim every source is equally central. The central sources
  for the ADR should be OpenML/experiment databases, REFORMS/leakage/DOME,
  PROV/RO-Crate/FAIR, cyber-range/testbed papers, and V&V/empirical experiment
  design sources.
