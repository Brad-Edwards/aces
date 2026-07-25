# Initial Service State Precedent Review

Date: 2026-07-24

Purpose: test whether scenario data that represents prior company activity
should become a first-class historical ontology, and identify mature precedents
for initialization, runtime activity, time control, and backend realization.

## Sources Reviewed

- [FMI 3.0 initialization mode](https://fmi-standard.org/docs/3.0/#_state_initialization_mode)
- [ASAM OpenSCENARIO Init model](https://releases.asam.net/OpenSCENARIO/1.0.0/Model-Documentation/content/Init.html)
- [ASAM OpenSCENARIO actions and initialization](https://simulation.pages.asam.net/openscenario/openscenario-antora-gen/ASAM_OpenSCENARIO_XML/current_xml_v1.x/07_components_scenario/07_04_actions.html)
- [TENA architecture overview](https://www.tena-sda.org/tena-about.html)
- [ROS 2 clock and time design](https://design.ros2.org/articles/clock_and_time.html)
- CyRIS content operations and the existing ACES lineage record for
  `copy_content` and `emulate_traffic_capture`

## Findings

FMI gives initialization its own bounded lifecycle phase so a system reaches a
consistent initial condition before normal execution. It does not reclassify
each initial value by whether it narratively represents the past.

OpenSCENARIO likewise separates initialization actions from runtime stories and
maneuvers. Its model supports provider-specific user-defined actions at the
simulation boundary, which reinforces the separation between a portable
scenario requirement and the implementation that realizes it.

TENA uses shared object definitions to make independently implemented range
applications semantically interoperable. That supports a stable portable
contract plus backend-specific implementations; it does not support embedding
one scenario pack's product adapter or object inventory in the language.

ROS distinguishes system, steady, and simulated time and makes time-source
selection explicit. This is relevant to deterministic live activity and replay,
but not a reason to add clocks or time progression to static initial content.
Represented business timestamps inside data remain content. Runtime scheduling
needs a separate time-domain contract.

CyRIS is the closest cyber-range precedent for ordinary files and generated
past-looking data: these remain content-management concerns. ACES already
records this lineage for top-level `content`.

## Design Disposition

1. Reject a first-class historical-data ontology.
2. Keep top-level `content` as the sole authored initial-data authority.
3. Add only the demonstrated missing seam: exact materialization through a
   named service with tenant/reset ownership and participant-equivalent
   readback.
4. Keep the portable operation/control contract in ACES and product adapters in
   backends.
5. Assess delivery/golden equivalence by declared observable outcomes, not
   provider topology or implementation identity.
6. Treat deterministic live activity, replay, and controlled time progression
   separately because they simulate participants and evolve state after
   initialization.

The resulting ACES binding is ACES-native. The reviewed systems informed the
authority split and lifecycle discipline but do not define ACES syntax or
compatibility.
