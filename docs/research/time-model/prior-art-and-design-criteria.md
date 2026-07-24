# Shared Time Model Prior Art And Design Criteria

This note supports issue #117 and ADR-090. It is research and design evidence,
not contract authority.

## Question

What is the smallest backend-neutral time model that lets ACES author, compile,
control, observe, reset, replay, and compare temporal behavior across emulated,
simulated, hybrid, and externally paced realizations?

## Existing ACES Authorities

ACES already distinguishes participant action schedules, cadence, deadlines,
dwell, latency, and windows. Participant runtime records also distinguish event
order, logical order, predecessor relationships, and clock disclosures. These
are valid local semantics, but their time-domain and clock-authority fields are
unresolved strings. Runtime `time_management_contexts` are evidence carriers,
not an authored shared authority. Host UTC timestamps and control-plane
timeouts are operational apparatus and cannot silently define scenario time.

The new model therefore normalizes authority; it does not replace participant
temporal contracts, attribution, workflow lifecycle, experiment apparatus, or
backend scheduling.

## External Precedents

### ROS 2 Clock And Time

The [ROS 2 Clock and Time design](https://design.ros2.org/articles/clock_and_time.html)
separates system, steady, and externally controlled ROS time. It makes source
activation explicit and treats pause and backward jumps as events clients must
handle. The transferable criteria are:

- time values from distinct domains are not interchangeable by type accident;
- an externally controlled semantic clock has one explicit authority;
- pausing and jumping are lifecycle transitions, not ordinary elapsed time;
- extrapolation from wall time is invalid without an admitted pacing
  guarantee.

ACES adopts those criteria without adopting ROS topics, nodes, or `/clock`.

### FMI 3.0

The [FMI 3.0.2 specification](https://fmi-standard.org/docs/3.0.2/) separates
model-unit capability from importer-controlled time advancement. Scheduled
execution activates model partitions on clocks; co-simulation negotiates steps,
early return, and events. FMI also uses superdense time to distinguish multiple
events at one real-valued time.

ACES therefore separates capability from control, uses exact ticks plus a
microstep, and requires advance/readback records. Claiming FMI compatibility
still requires an FMI-specific conformance profile; generic ACES support does
not imply it.

### HLA And TENA

The [IEEE 1516 HLA family](https://standards.ieee.org/ieee/1516/3744/) treats
time regulation, constrained advancement, and ordered delivery as federation
services rather than properties inferred from timestamps.

[TENA](https://www.tena-sda.org/tena-about.html) separates execution middleware
and real-time object exchange from the Logical Range Data Archive. That
separation reinforces three ACES planes:

1. authored temporal meaning;
2. runtime/backend coordination and readback;
3. archival evidence and run provenance.

ACES does not adopt an HLA federation or TENA middleware/object model.

### ASAM OpenSCENARIO

[OpenSCENARIO storyboard semantics](https://publications.pages.asam.net/standards/ASAM_OpenSCENARIO/ASAM_OpenSCENARIO_XML/v1.3.0/07_components_scenario/07_02_storyboard_entities.html)
separate lifecycle, triggers, actions, and simulation-time conditions. ACES
retains that separation while using ordinary ACES subjects rather than
automotive entities, maneuvers, or storyboard hierarchy.

## Design Criteria

The shared model must:

1. define exact domain resolution and epoch meaning;
2. bind each semantic clock to one declared authority;
3. make mappings explicit and exact, initially identity or affine rational;
4. separate advancement, pacing, synchronization, and drift;
5. represent simultaneity with superdense coordinates rather than equal
   timestamps alone;
6. preserve partial ordering and keep causality in attribution semantics;
7. treat pause, jump, reset, and replay as recorded lifecycle transitions;
8. start a new segment after discontinuity instead of rewriting history;
9. keep host watchdog time separate from scenario deadlines;
10. let backends admit, weaken, or reject requirements before execution and
    prove realized behavior through readback.

## Rejected Alternatives

- **One universal timestamp:** loses domain, authority, pacing, and reset
  meaning.
- **Floating-point seconds:** introduces avoidable comparison and replay drift.
- **Backend-local scheduler semantics:** cannot be validated across backends.
- **A live-activity-specific clock:** creates a private time ontology and makes
  benign participants non-portable.
- **Causality from timestamp order:** contradicts existing ACES attribution
  semantics and distributed-systems precedent.
- **Historical data as a time-model class:** initial files and records remain
  ordinary authored service state; their narrative age is not clock authority.
