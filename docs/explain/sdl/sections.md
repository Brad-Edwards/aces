# SDL Sections Reference

A scenario is a YAML document with a required top-level `name`, optional
top-level composition fields (`version`, `module`, `imports`), and up to 21 named SDL
sections. Aside from `name`, all sections are optional.

Top-level composition fields are:

- `version` — scenario or module version
- `module` — optional publishable module descriptor (`id`, `version`, `parameters`, `exports`, `description`)
- `imports` — optional module imports using backward-compatible `path:` or canonical `source:`

Canonical `imports.source` classes are:

- `local:...` for repo-local files
- `oci:...` for remote OCI-packaged modules
- `locked:...` for lockfile-resolved concrete imports

## Section Overview

### From Open Cyber Range SDL (14 sections)

| Section | Type | Purpose |
|---------|------|---------|
| `nodes` | `dict[str, Node]` | VMs and network switches — the compute/network topology |
| `infrastructure` | `dict[str, InfraNode]` | Deployment topology: counts, links, dependencies, IP/CIDR, ACLs |
| `features` | `dict[str, Feature]` | Software (Service/Configuration/Artifact) deployed to VMs |
| `conditions` | `dict[str, Condition]` | Health checks (command+interval or library source) |
| `vulnerabilities` | `dict[str, Vulnerability]` | CWE-classified vulnerabilities assigned to nodes/features |
| `metrics` | `dict[str, Metric]` | Scoring: Manual (human-graded) or Conditional (automated) |
| `evaluations` | `dict[str, Evaluation]` | Metric groups with pass/fail thresholds |
| `tlos` | `dict[str, TLO]` | Training Learning Objectives linked to evaluations |
| `goals` | `dict[str, Goal]` | High-level goals composed of TLOs |
| `entities` | `dict[str, Entity]` | Teams, organizations, people (recursive, with exercise roles) |
| `injects` | `dict[str, Inject]` | Actions between entities during exercises |
| `events` | `dict[str, Event]` | Triggered actions combining conditions + injects |
| `scripts` | `dict[str, Script]` | Timed event sequences with human-readable durations |
| `stories` | `dict[str, Story]` | Top-level exercise orchestration grouping scripts |

### Extended Sections (7 sections)

| Section | Type | Purpose | Adapted From |
|---------|------|---------|--------------|
| `content` | `dict[str, Content]` | Data placed into systems (files, datasets, emails) | CyRIS `copy_content` |
| `accounts` | `dict[str, Account]` | Curated scenario/provisioning accounts on nodes, not full runtime identity inventory | CyRIS `add_account` |
| `relationships` | `dict[str, Relationship]` | Typed edges between elements (auth, trust, federation) | STIX Relationship SRO |
| `agents` | `dict[str, Agent]` | Autonomous participants (actions, knowledge, scope) | CybORG Agents |
| `objectives` | `dict[str, Objective]` | Declarative experiment tasks binding actors, targets, windows, and success | OCR scoring + CACAO action/target/agent |
| `workflows` | `dict[str, Workflow]` | Branching and parallel control graphs over declared objectives | CACAO workflow graph patterns; semantics tightened using Step Functions / Argo / SCXML style control-flow rules |
| `variables` | `dict[str, Variable]` | Parameterization (types, defaults, substitution) | CACAO playbook_variables |

---

## Nodes

Nodes are the compute and network elements of the scenario.

```yaml
nodes:
  corp-switch:
    type: Switch
    description: Corporate LAN

  web-server:
    type: VM
    os: linux                           # windows, linux, macos, freebsd, other
    os_version: "Ubuntu 22.04"
    source: ubuntu-22.04                # provider-neutral image reference
    resources:
      ram: 4 GiB                        # human-readable: GiB, MiB, GB, MB
      cpu: 2
    features:                           # dict form: {feature: role} or list form: [feature]
      nginx: web-admin
    conditions:
      web-health: web-admin
    vulnerabilities: [sqli, xss]
    roles:
      web-admin: www-data               # shorthand: role: username
      operator:                         # longhand
        username: ops
        entities: [blue-team.alice]     # binds to entity
    services:                           # exposed network services
      - port: 80
        protocol: tcp
        name: http
      - port: 443
        name: https
      - port: 389
        name: ldap
    runtime:                            # observed runtime configuration facts
      mounts:
        - target: /shuffle-database
          source: aptl_shuffle_data
          source_sensitivity: plain
          source_kind: volume
          filesystem_type: ext4
          read_only: false
          options: [rw, nosuid]
          options_sensitivity: plain
          propagation: rprivate
          stability: volume_backed
          backend_generated: true
      filesystem_inventory:
        - path: /app/app.py
          entry_type: file
          owner_user: root
          owner_group: root
          uid: 0
          gid: 0
          mode: "0644"                 # quote to preserve leading zeroes
          size: 4096
          content_digest: 4f8c2d
          digest_algorithm: sha256
          source_path: src/webapp/app.py
          provenance: python-package
          stability: stable
          sensitivity: plain
        - path: /var/log/gunicorn/access.log
          entry_type: file
          mode: "0600"
          stability: log
          sensitivity: operator_secret
      local_control_interfaces:
        - path: /run/docker.sock
          kind: unix_socket
          protocol: docker
          bind_source_sensitivity: operator_secret
          access: read_write
      process:
        pid: 1
        command: ./shufflebackend
        user: root
        working_directory: /app
      processes:
        - name: supervisord
          pid: 1
          command: supervisord -n
          role: supervisor
        - name: gunicorn
          parent_pid: 1
          command: [gunicorn, app:app]
          role: worker
      environment:
        - name: TECHVAULT_ADMIN_PASSWORD
          value_classification: redacted
          provenance: operator
        - name: SCENARIO_FIXTURE_TOKEN
          value: fixture-token
          value_classification: secret_fixture
          provenance: compose
      linux_capabilities:
        required: [CAP_NET_ADMIN]
        effective: CAP_NET_ADMIN
      operational_policy:
        restart: unless_stopped
        resource_limits:
          memory: 512 MiB
          cpu: 0.5
          pids: 128
      container:
        entrypoint: [/entrypoint.sh]
        command: [gunicorn, app:app]
        log_driver: json-file
        log_options:
          max-size: 10m
          max-file: "3"
        namespaces:
          cgroup: private
          ipc: private
          pid: private
          userns: host
          uts: private
        privileged: false
        read_only_rootfs: false
        publish_all_ports: false
        autoremove: false
        shm_size: 64 MiB
        masked_paths: [/proc/acpi, /proc/kcore]
        read_only_paths: [/proc/sys]
        cgroup_parent: /docker
        runtime_name: runc
        devices:
          - host_path: /dev/null
            container_path: /dev/null
            permissions: rwm
        device_cgroup_rules: [c 1:3 rwm]
        seccomp_profile: unconfined
        security_opt: [seccomp:unconfined, no-new-privileges]
        extra_hosts:
          - hostname: wazuh-manager
            address: 172.20.0.10
        dns: [8.8.8.8]
        dns_options: [ndots:0]
        dns_search: [techvault.local]
        group_add: [adm, "101"]
      health:
        status: healthy
        failing_streak: 0
        log:
          - start: "2026-05-20T12:00:00Z"
            end: "2026-05-20T12:00:01Z"
            exit_code: 0
            output: ok
      packages:
        - manager: apk
          name: musl
          version: 1.2.4-r2
      software_components:
        - component_id: shuffle-backend-app
          name: shuffle-backend
          version: 1.2.3
          component_type: application
          provenance: scanner
          ecosystem: go
          purl: "pkg:golang/github.com/frikky/shuffle@1.2.3"
          cpe: "cpe:2.3:a:shuffle:shuffle:1.2.3:*:*:*:*:*:*:*"
          package_manager: apk
          package_name: shuffle-backend
          package_version: 1.2.3-r0
          manifest_path: /app/go.mod
          installed_paths: [/app/shufflebackend, /app/go.mod]
          hashes:
            - algorithm: sha256
              value: abc123
      dependency_manifests:
        - ecosystem: go
          path: /app/go.mod
          format: go-module
      package_vulnerabilities:
        - id: CVE-2026-12345
          package_name: musl
          installed_version: 1.2.4-r2
          fixed_version: 1.2.5-r0
          severity: high
          scanner: trivy
          image_digest: sha256:abc123
          scan_time: "2026-05-20T12:00:00Z"
      local_identity:                   # observed /etc/passwd, /etc/group, sudo facts
        users:
          - username: www-data
            uid: 33
            primary_gid: 33
            primary_group: www-data
            home: /var/www
            shell: /usr/sbin/nologin
            no_login: true
            provenance: image
            stability: stable
        groups:
          - name: www-data
            gid: 33
            members: [www-data]
            provenance: image
        sudo_rules:
          - principal: wazuh
            principal_kind: user
            run_as_users: [root]
            commands: ["/usr/bin/systemctl restart wazuh-agent"]
            nopasswd: true
      network:                          # observed container network realization
        hostname: techvault-webapp
        domainname: techvault.local
        endpoints:
          - network: aptl-dmz           # references a switch-backed infrastructure entry
            network_id: 7f2c1ad4e9b3...
            network_id_stability: stable
            endpoint_id: 3a9c7e0d3f5b...
            endpoint_id_stability: ephemeral
            backend_generated: true
            ip_address: 172.20.0.20
            ip_prefix_length: 24
            gateway: 172.20.0.1
            mac_address: 02:42:ac:14:00:14
            aliases: [aptl-webapp, webapp]
            dns_names: [aptl-webapp, webapp]
            generated_dns_names: [3a9c7e0d3f5b]
            backend:
              driver: bridge
              ipam_driver: default
              driver_options: {com.docker.network.bridge.name: br-aptl-dmz}
        published_ports:
          - container_port: 8080
            protocol: tcp
            host_ip: 0.0.0.0
            host_port: 8080
      applications:                     # observed HTTP route/API/UI surface
        - application_id: techvault-webapp
          service: techvault-http       # owning same-node Node.services[].name
          protocol: http
          framework: flask
          base_path: /
          routes:
            - route_id: login
              path: /login
              methods: [GET, POST]
              auth_required: false
              session_required: false
              auth_scheme: form_login
              parameters:
                - name: username
                  location: form
                  required: true
                - name: password
                  location: form
                  required: true
              responses:
                - status_code: 200
                  content_type: text/html
              templates: [/app/templates/login.html]
              static_assets: [/app/static/style.css]
              redirects:
                - target: /dashboard
                  status_code: 302
                  condition: valid credentials
            - route_id: upload
              path: /files/upload
              methods: [POST]
              auth_required: true
              session_required: true
              parameters:
                - name: document
                  location: uploaded_file
                  required: true
              vulnerability_refs: [unrestricted-upload]   # → top-level vulnerabilities
            - route_id: diagnostics
              path: /debug/info
              methods: [GET]
              exposed_fields:
                - name: build_token
                  sensitivity: secret_fixture
                  value: fixture-token-1234
              disclosures:
                - trigger: any request
                  status_code: 200
                  disclosure: internal package versions and host paths
                  sensitivity: plain
      database_services:                # observed database logical state
        - database_service_id: techvault-postgres
          service: techvault-pg         # owning same-node Node.services[].name
          engine: postgresql
          protocol: postgresql
          version: "16.13"
          listeners:
            - address: "*"
              port: 5432
          databases:
            - database_id: techvault-db
              name: techvault
              origin: scenario
              schemas:
                - schema_id: public-schema
                  name: public
                  tables:
                    - {table_id: users-tbl, name: users}
                    - {table_id: audit-tbl, name: audit_log}
            - database_id: template0-db
              name: template0
              origin: built_in           # engine built-in, not scenario-authored
          roles:
            - {role_id: app-role, name: techvault, role_type: application, can_login: true}
          grants:
            - grantee_role_ref: app-role
              object_type: table
              object_ref: users-tbl
              privileges: [SELECT, INSERT, UPDATE]
          settings:
            - {name: listen_addresses, value: "*", provenance: configuration_file}
            - name: password_encryption     # secret-bearing settings omit value
              value_classification: redacted
              provenance: operator_override
      dns_services:                     # observed DNS authoritative/resolver state
        - dns_service_id: techvault-bind
          service: dns                  # owning same-node Node.services[].name
          implementation: bind
          roles: [authoritative, recursive_resolver]
          configuration_file_refs: [/etc/bind/named.conf]
          resolver_policy:
            recursion_enabled: true
            allow_recursion: [10.0.0.0/24]
            dnssec_validation: auto
            forwarders:
              - {address: 8.8.8.8, port: 53, transport: udp}
          zones:
            - zone_id: techvault-local
              name: techvault.local.
              purpose: forward
              zone_file_refs: [/etc/bind/db.techvault.local]
              rrsets:
                - rrset_id: root-soa
                  owner: techvault.local.
                  record_type: soa
                  ttl: 3600
                  records:
                    - soa:
                        mname: ns1.techvault.local.
                        rname: hostmaster.techvault.local.
                        serial: 2026052801
                        refresh: 3600
                        retry: 600
                        expire: 604800
                        minimum: 300
                - rrset_id: web-a
                  owner: web.techvault.local.
                  record_type: a
                  ttl: 300
                  records:
                    - {address: 10.0.0.20}
          settings:
            - name: tsig_secret          # secret-bearing settings omit value
              value_classification: redacted
              provenance: operator_override
      identity_authorities:             # observed directory/domain/IdP/IAM state
        - authority_id: techvault-domain
          kind: domain
          namespace: techvault.local
          domain_name: TECHVAULT
          realm: TECHVAULT.LOCAL
          base_dn: DC=techvault,DC=local
          services:
            - service_id: ldap-endpoint
              service: ldap             # owning same-node Node.services[].name
              protocol: ldap
              address: dc.techvault.local
              port: 389
          subjects:
            - subject_id: alice
              kind: user
              name: alice
              principal_name: alice@TECHVAULT.LOCAL
              distinguished_name: CN=Alice,CN=Users,DC=techvault,DC=local
              enabled: true
            - subject_id: domain-admins
              kind: group
              name: Domain Admins
            - subject_id: app-svc
              kind: service_principal
              name: webapp
              service_principal_names: [HTTP/web.techvault.local]
          relationships:
            - relationship_id: alice-admin
              relationship_type: member_of
              source_ref: alice
              target_ref: domain-admins
          policies:
            - policy_id: default-domain-policy
              policy_kind: password
              applies_to_refs: [techvault-domain, ldap-endpoint, alice-admin]
              settings:
                - name: min_length
                  values: "14"
    asset_value:                        # CIA triad (from CybORG)
      confidentiality: high
      integrity: medium
      availability: critical
```

**Switch** nodes are pure connectivity objects. They may define `type` and an optional `description`, but `source`, `resources`, `os`, `os_version`, `features`, `conditions`, `injects`, `vulnerabilities`, `roles`, `services`, `asset_value`, and `runtime` are rejected.

For **VM** nodes, `resources` remain optional at the SDL layer to preserve abstract specifications, but a VM without `resources` emits a non-fatal advisory because many deployment backends will need explicit sizing or well-defined defaults.

**Feature list shorthand:** `features: [nginx, php]` expands to `{nginx: "", php: ""}` (no role binding required).

When `features`, `conditions`, or `injects` use the `{name: role}` form, the role must be declared in the node's `roles` map.

Concrete service bindings on a VM must be unique by `protocol` + `port`. Reusing `53/tcp` and `53/udp` is valid; declaring `443/tcp` twice on the same node is rejected. If a service binding also has a `name`, that `name` must be unique within the node and can be targeted directly as `nodes.<node>.services.<service_name>`.

`runtime` captures observed facts about realized VM/container nodes. It covers
participant-observable and analysis-relevant runtime state that is distinct
from authored deployment intent and top-level authored declarations such as
feature placement or service bindings; it does not exclude host-published
bindings, application routes, daemon policy, databases, identity authorities,
DNS service logical state, or other participant-interactable state merely because the evidence came from
Docker, Compose, a scanner, or a backend inspector. Mounts describe realized
filesystem attachments, including filesystem type, propagation, stability,
whether a backend generated the source, and sensitivity classifications for
the source and option strings. Mount sources or options classified as
`redacted` or `operator_secret` must omit the raw value. This sensitivity
vocabulary is an ACES runtime contract, not an adopted taxonomy from Docker,
Compose, or the cited scenario-language precedents. `filesystem_inventory` records
runtime-observed filesystem entries with absolute path, entry type, ownership,
UID/GID, mode, size, digest algorithm/value pairs, source-package path,
provenance, stability, and sensitivity classification.
`local_control_interfaces` describe path-local control APIs such as Unix
sockets; host-side bind sources use `bind_source_sensitivity` and must omit
`bind_source` when classified as `redacted` or `operator_secret`; `process`
records primary execution identity; `processes` records a supervised or
load-bearing process set; `environment` records observed runtime environment
variables with provenance and redaction classification; `linux_capabilities`
records container/Linux
capability policy; `operational_policy` records restart policy and observed
resource limits; `container` records observed host/container configuration and
namespace/security facts, including `seccomp_profile` (the portable seccomp
posture — `default`, `unconfined`, a named profile, or a profile path) and
`security_opt` (the bounded list of backend-native engine security options
such as `seccomp:unconfined` or `no-new-privileges`); a seccomp posture is a
distinct security control from `privileged`, so it is recorded separately (see
[ADR-028](../../decisions/adrs/adr-028-container-seccomp-security-options-surface.md));
`health` records observed health status and bounded healthcheck log facts;
`packages` records package-manager rows; `software_components` records
node-local software identity at component granularity with stable ACES ids,
component type, version, purl/CPE/hash identifiers, package or manifest
lineage, and runtime paths when known; `dependency_manifests` records observed
manifest files; and `package_vulnerabilities` records scanner-derived
CVE/advisory findings tied to an image digest and scan time. Software
components are WHAT-IS state, not invocation surfaces, process snapshots, HTTP
route inventory, build provenance, or authored deployment intent (see
[ADR-034](../../decisions/adrs/adr-034-runtime-software-component-inventory.md)).
Package findings are separate from the top-level `vulnerabilities` section,
which remains the CWE-classified scenario vulnerability surface.

`runtime.service_manager_units` records observed service-manager unit
lifecycle state — what `systemctl` exposes from inside a realized range node.
Each entry carries a stable ACES `unit_id`, a `manager_kind` (initially
`systemd`, with `other` reserved), the native `unit_name` such as
`sshd.service`, a `unit_type` (`service`/`socket`/`target`/`timer`/`path`/
`mount`/`automount`/`swap`/`device`/`slice`/`scope`/`other`), and the
participant-observable state quadruple `load_state` (loaded/not_found/masked/
error/merged/stub/bad_setting/unknown), `active_state` (active/reloading/
inactive/failed/activating/deactivating/unknown), bounded free-form `sub_state`
(e.g. `running`/`exited`/`dead`), and `enabled_state` (enabled/enabled_runtime/
disabled/static/alias/masked/generated/indirect/transient/unknown). The last
run is classified via `result` (success/exit_code/signal/timeout/watchdog/
oom_kill/core_dump/start_limit_hit/resources/protocol/other/unknown) with
optional `exit_code` (only valid when `result` is `exit_code`) and a short
`status_text` for evidence like `226/NAMESPACE`. Optional fields capture the
`main_pid` when a live process exists, the `unit_file_path` (cross-checked
against `runtime.filesystem_inventory` when that inventory is non-empty), and
a redactable `exec_start` (`command_kind` `absolute_path` / `redacted`, with
`command_redacted` forcing an empty `command`). An optional `service` ref
pointing at the same-node `Node.services[].name` (bare or
`nodes.<node>.services.<name>`) ties a unit to the transport service it
launches. This surface is observed WHAT-IS lifecycle state: it is not
`Node.services` (transport bindings), not `conditions` (authored
monitoring/readiness intent), not `runtime.processes` (live processes — a
failed, disabled, static, or active/exited unit may have no live process),
not `runtime.container.init_process` (container PID-1/init configuration),
not `runtime.operational_policy.restart` (orchestrator restart policy), not
`runtime.ssh_servers` (sshd policy — `sshd.service` lifecycle is the unit,
sshd directives are the SSH surface), and not package/software/filesystem
inventory. Raw `systemctl`, `journalctl`, unit-file text, and backend
inspector payloads are not portable schema; secret-bearing `ExecStart` values
must be classified `redacted` and omit the raw command (see
[ADR-035](../../decisions/adrs/adr-035-service-manager-unit-state-runtime-surface.md)).

`runtime.local_identity` records the observed local identity database — the
node-scoped `/etc/passwd`, `/etc/group`, and sudo/sudoers facts. `users` carry
`username`, `uid`, `primary_gid`, `primary_group`, `gecos`, `home`, `shell`,
`supplemental_groups`, and the three distinct status facts `disabled`,
`locked`, and `no_login` (a no-login shell is not the same fact as a locked
password or a disabled account), plus `provenance` and `stability`. `groups`
carry `name`, `gid`, and `members`. `sudo_rules` model privilege grants as
structured `principal`/`principal_kind`, `run_as_users`/`run_as_groups`,
`host_scope`, and a portable `commands` scope, with `nopasswd` and a
`command_redacted` flag; an optional `raw_entry` may carry the original
sudoers line as descriptive evidence only. This is observed inventory: it is
distinct from the top-level `accounts` provisioning surface, and service
accounts recorded here are not implicitly compiled into account placements
(see [ADR-024](../../decisions/adrs/adr-024-local-identity-inventory-surface.md)).

`runtime.network` records the observed container network realization — the
facts visible from inside the realized range or by a harness, distinct from the
`infrastructure` topology declaration. `hostname` and `domainname` are the
container's network identity. Each `endpoints` entry is a per-network
attachment: `network` references a declared switch-backed infrastructure entry,
and the entry carries the realized `ip_address`, `ip_prefix_length`, `gateway`,
and `mac_address`; backend `network_id`/`endpoint_id` each with an explicit
`stable`/`ephemeral` stability classification; a `backend_generated` flag; and
three distinct name lists — stable per-network `aliases`, observed `dns_names`,
and backend-`generated_dns_names` (such as a container-ID-prefixed DNS name,
which is not stable scenario identity). The optional `backend` block records
observable network `driver` and `ipam_driver` plus bounded backend-native
`driver_options`/`ipam_options` maps — not raw engine inspect payloads.
`published_ports` records host-published bindings, keeping container port, host
IP, host port, and protocol distinct; this is host exposure observed at
runtime, separate from the authored `services` declaration and image-default
`source.build.config.exposed_ports`
(see [ADR-025](../../decisions/adrs/adr-025-container-network-realization-surface.md)).

`runtime.applications` records the participant-observable HTTP application
route/API/UI surface — what an adversary, defender, agent, scanner, or evaluator
can observe of the web application itself, distinct from the transport-level
`services` binding and from the host exposure in `runtime.network`. Each entry
is a `RuntimeApplicationSurface` with a stable `application_id`, an optional
`service` referencing the owning same-node `Node.services[].name` (bare name or
the qualified `nodes.<node>.services.<name>` form), a `protocol`/`framework`
classification, and an optional `base_path`. Each `routes` entry carries a
stable `route_id` (the route `path` is data, never a mapping key, and may carry
path variables and be shared across methods), normalized HTTP `methods`,
observable `auth_required`/`session_required`/`auth_scheme`, typed `parameters`
located by `path`/`query`/`header`/`cookie`/`form`/`json_body`/`uploaded_file`,
`responses` with status code and content type, `templates`/`static_assets`
associations resolving to the node's observed file inventory,
`vulnerability_refs` pointing at top-level `vulnerabilities` for route-specific
weakness placement, `redirects`, observable error/disclosure behavior in
`disclosures`, and `exposed_fields` for route-visible fixture secrets or
intentionally exposed diagnostic fields classified with the shared runtime
sensitivity vocabulary — `redacted` and `operator_secret` fields omit their raw
value (see
[ADR-026](../../decisions/adrs/adr-026-application-http-surface-inventory.md)).

`runtime.database_services` records the participant-observable database
logical state — what an adversary, defender, agent, scanner, or evaluator can
observe of a database itself, distinct from the transport-level `services`
binding, the host exposure in `runtime.network`, and the HTTP surface in
`runtime.applications`. Each entry is a `DatabaseService` with a stable
`database_service_id`, an optional `service` referencing the owning same-node
`Node.services[].name`, and distinct `engine`/`protocol`/`version` facts — a
PostgreSQL service is never modelled as `protocol: other`. `listeners` record
what the database process listens on (the wildcard `*`, an IP, a hostname, or a
Unix socket path) and are not host publication, which remains
`runtime.network.published_ports`. `databases` carry typed `schemas` and
`tables`; `roles` are database-local authorization principals, not OS accounts
or top-level `accounts`; and every database, schema, table, and role has a
stable `*_id` symbol kept separate from its observed `name`, plus an `origin`
classification so engine built-ins (`template0`, `postgres`) are not mistaken
for scenario-authored objects. `grants` are typed privilege facts structured by
grantee role, target object, and privileges. `settings` carry a `provenance`
(introspection, configuration file, image default, operator override, runtime
default) and a value classification reusing the shared runtime sensitivity
vocabulary — `redacted`/`operator_secret` settings omit their raw value, so
PostgreSQL secret areas such as `primary_conninfo`, password attributes, and
TLS key material never enter the model. An application-to-database access edge
reuses the top-level `relationships` graph: the relationship endpoints resolve
to the runtime application and the database service or logical database, and a
typed `database_access` block keeps the access `role_ref` and `auth_method`
structurally validated (see
[ADR-029](../../decisions/adrs/adr-029-database-logical-state-runtime-surface.md)).

`runtime.dns_services` records observed DNS logical and protocol state hosted
by the node: authoritative zones, RRsets, typed common RDATA, resolver policy,
forwarders, DNSSEC validation posture, dynamic-update posture, logging posture,
bounded settings, and evidence refs. It is distinct from `Node.services`
(transport listeners such as UDP/TCP 53), `runtime.container` resolver client
options, `runtime.network` endpoint aliases/generated DNS names, HTTP
applications, filesystem evidence, and generic relationships. Each service has
a stable `dns_service_id` and optional same-node `service` ref. Zones use
stable `zone_id` values and observed DNS names. `rrsets` group records by
owner, class, type, and TTL; typed payloads exist for SOA, MX, SRV, TXT, A,
and AAAA, with target/rdata fields and an `other` + `type_code` path for
additional IANA RR types. `configuration_file_refs`, `log_file_refs`, and
`zone_file_refs` are checked against `runtime.filesystem_inventory` when that
inventory is non-empty. Fully qualified refs such as
`nodes.dns.runtime.dns_services.bind.zones.corp.rrsets.web-a` participate in
relationships, generic reference validation, and module import rewriting (see
[ADR-039](../../decisions/adrs/adr-039-dns-service-runtime-inventory.md)).

`runtime.mail_services` records the participant-observable mail-server logical
state, distinct from transport-level `services`, host publication in
`runtime.network`, HTTP application routes, filesystem evidence, and top-level
scenario accounts. Each entry is a `RuntimeMailService` with a stable
`service_id`, optional same-node `Node.services[].name` reference,
engine/version/name data, and typed child records for components, listeners,
domains, mailbox stores, mailboxes, aliases, routing rules, queues, and
settings. `listeners` bind SMTP/ESMTP, submission, IMAP/IMAPS, POP3, LMTP,
Sieve, or other mail protocols to same-node transport services and carry
advertised capabilities, banners, AUTH mechanisms, and TLS/STARTTLS posture.
`mailboxes` are service-local runtime records with address, domain/store refs,
role/status, authentication mechanisms, and credential-strength classification;
raw passwords and hashes are not representable. `settings` carry provenance and
source paths, and secret-bearing setting names must omit raw values. Mail
client, DNS, logging/SIEM, relay, and similar edges stay in top-level
`relationships`; a typed `mail_access` block records mail protocol/auth/TLS and
mailbox/domain/listener refs when an edge needs mail-specific semantics (see
[ADR-038](../../decisions/adrs/adr-038-runtime-mail-service-logical-state.md)).

`runtime.identity_authorities` records observed directory, domain, realm,
identity-provider, cloud-IAM, authorization-system, and federation state. It is
not a provisioning command surface and it is not an Active Directory, LDAP,
SCIM, SAML, OIDC, or IAM schema clone. Each authority has a stable
`authority_id`; optional namespace facts such as `domain_name`, `realm`,
`issuer`, `tenant_id`, and `base_dn`; protocol/API services that may reference
same-node `Node.services[].name` transport bindings; identity-bearing
subjects; policies; and typed relationships for membership, trust,
federation, delegation, ownership, synchronization, and association. Stable
ACES ids (`authority_id`, `service_id`, `subject_id`, `policy_id`, and
`relationship_id`) are the portable reference surface and must be unique across
the owning authority's local namespace. Provider-stable object identifiers
remain observed data: use the specific field when one exists
(`distinguished_name`, `principal_name`, `service_principal_names`,
`issuer`, `tenant_id`, `base_dn`) or a bounded `attributes` entry for values
such as AD `objectGUID`/SID, LDAP `entryUUID`, SCIM `id`/`externalId`, SAML
NameID, or the OIDC `iss` + `sub` pair. Secret-bearing attribute or policy
setting names must omit raw values and use the runtime sensitivity vocabulary.
Local authority references resolve against all stable ids in the owning
authority; fully qualified references such as
`nodes.ad.runtime.identity_authorities.corp-domain.subjects.alice` participate
in top-level relationships, objectives, module import rewriting, and generic
reference validation (see
[ADR-032](../../decisions/adrs/adr-032-directory-domain-identity-runtime-surface.md)).

`source` identifies the node's artifact by provider-neutral `name` and
`version`. When that artifact is a custom-built container image, the optional
`source.build` block records its observable build/provenance facts without
making any container engine the normative deployment model. `build` captures
the `base_image` and `base_image_digest`; the `dockerfile_path` and structured
`instructions` (typed `instruction` kind plus tokenized `arguments` — raw
recipe text is intentionally not stored, since `${...}` in shell/Dockerfile
syntax would collide with SDL variable substitution); the `layers` chain with
per-layer `digest`, `created_by`, `size`, and `empty` flag; `build_args` with a
`value_classification` so secret build arguments are redacted rather than
recorded; `copied_sources` mapping build-context `source_path` to in-image
`destination_path`; `config` recording image *defaults* (entrypoint, command,
working directory, exposed ports, native-keyed `labels`, and
`default_environment`); `source_inputs` mapping source-package inputs to
runtime destinations with optional checksums; and `attestation`, which records
attestation `status` (availability) separately from `verification` (result) so
that "no registry-visible attestation" is a distinct, falsifiable fact rather
than an inferred verification failure. Image-default `config` facts are kept
separate from runtime-effective facts under `runtime.container`; the same value
may appear in both with different meanings. See
[ADR-023](../../decisions/adrs/adr-023-container-image-build-provenance-surface.md).

---

## Infrastructure

Maps node names to deployment parameters.

```yaml
infrastructure:
  corp-switch:
    count: 1
    properties:
      cidr: 10.0.0.0/24
      gateway: 10.0.0.1
      internal: true                    # blocks internet egress
    acls:                               # network access controls (from CybORG NACLs)
      - name: allow-dmz-https
        direction: in
        from_net: dmz-switch
        protocol: tcp
        ports: [443]
        action: allow
      - name: deny-dmz-default
        direction: in
        from_net: dmz-switch
        action: deny

  web-server:
    count: 1                            # shorthand: web-server: 1
    links: [corp-switch]
    dependencies: [db-server]
    properties:                         # per-link IP assignments
      - corp-switch: 10.0.0.10
```

**Shorthand:** `web-server: 3` expands to `{count: 3}`.

`links` are switch/network connectivity references, not arbitrary infrastructure edges. If a node has attached `conditions`, its `count` must stay at `1` so the condition-to-node binding remains unambiguous. Per-link IP assignments must be valid IP addresses within the linked switch's CIDR.

ACL rule `name` is optional, but when present it must be unique within that infrastructure entry and can be targeted directly as `infrastructure.<infra>.acls.<acl_name>`.

---

## Features

Software deployed onto VMs. Three types: Service, Configuration, Artifact.

```yaml
features:
  nginx:
    type: Service
    source: nginx-1.24
  php-config:
    type: Configuration
    source: php-8.2-config
    dependencies: [nginx]               # deployed after nginx; cycles rejected
  log-agent:
    type: Artifact
    source: filebeat-8
    destination: /opt/filebeat
    environment: ["ELASTICSEARCH_HOST=10.0.0.5"]
```

Feature dependencies are hard same-node prerequisites at runtime. If a node
binds a feature whose declared dependency is not also bound on that same node,
runtime compilation emits a diagnostic and the plan is invalid rather than
silently ignoring the missing prerequisite.

---

## Conditions

Health checks with optional timeout/retries/start_period.

```yaml
conditions:
  web-alive:
    command: "curl -sf http://localhost/ || exit 1"
    interval: 15
    timeout: 5
    retries: 3
    start_period: 30
  scanner:
    source: vuln-scanner-pkg            # alternative: library-based check
```

Must have either `command` + `interval` or `source`, not both.

---

## Vulnerabilities

CWE-classified weaknesses. The `class` field is validated against `CWE-\d+`.

```yaml
vulnerabilities:
  sqli:
    name: SQL Injection
    description: SQLi in login form allows auth bypass
    technical: true
    class: CWE-89
```

---

## Scoring Pipeline: Metrics, Evaluations, TLOs, Goals

```
Conditions → Metrics → Evaluations → TLOs → Goals
```

```yaml
metrics:
  service-uptime:
    type: CONDITIONAL
    max-score: 100
    condition: web-alive
  report-quality:
    type: MANUAL
    max-score: 50
    artifact: true

evaluations:
  overall:
    metrics: [service-uptime, report-quality]
    min-score: 75                       # shorthand = percentage
    # or: min-score: {absolute: 100}

tlos:
  web-defense:
    name: Web Application Defense
    evaluation: overall

goals:
  pass-exercise:
    tlos: [web-defense]
```

---

## Entities

Recursive team/organization hierarchy with exercise roles and OCR-style
fact maps.

```yaml
entities:
  blue-team:
    name: Blue Team
    role: Blue
    mission: Defend infrastructure
    tlos: [web-defense]
    facts:
      department: SOC
      primary-shift: nights
    entities:
      alice: {name: Alice}
      bob: {name: Bob}
  red-team:
    name: Red Team
    role: Red                           # White, Green, Red, Blue
```

Nested entities are referenced via dot-notation: `blue-team.alice`.

---

## Orchestration: Injects, Events, Scripts, Stories

```yaml
injects:
  phishing-email:
    source: phishing-pkg
    from-entity: red-team
    to-entities: [blue-team]

events:
  attack-wave:
    conditions: [scanner]
    injects: [phishing-email]

scripts:
  main-timeline:
    start-time: 5 min                  # OCR units: y, mon, w, d, h, m/min, s/sec, ms, us, ns
    end-time: 2 hour
    speed: 1.0
    events:
      attack-wave: 30 min

stories:
  exercise:
    speed: 1
    scripts: [main-timeline]
```

Sub-second durations are rounded up to the nearest second, so `1 ms`,
`1 us`, and `1 ns` all parse as `1`.

---

## Content

Data placed into scenario systems. Adapted from CyRIS `copy_content`.

```yaml
content:
  phishing-emails:
    type: dataset
    target: exchange-server
    destination: /var/mail/
    format: eml
    sensitive: true
    items:
      - name: "Q3 Budget.eml"
        tags: [phishing, macro]
  flag-file:
    type: file
    target: victim
    path: /var/www/html/flag.txt
    text: "FLAG{found_it}"
  seed-data:
    type: dataset
    target: database
    source: customer-pii-seed          # large dataset via package reference
    format: sql
```

`target` is required for every content entry and must reference a VM node, not a switch/network node. `file` content requires `path`; `dataset` content requires either `source` or non-empty `items`; `directory` content requires `destination`.

---

## Accounts

Curated scenario/provisioning account resources within scenario nodes. Adapted
from CyRIS `add_account`.

```yaml
accounts:
  phished-user:
    username: jane
    node: workstation-01
    groups: [Users]
    password_strength: medium           # weak, medium, strong, none
    mail: jane@example.test
  app-service:
    username: appsvc
    node: web-server
    password_strength: weak
    auth_method: password               # password, key, certificate
```

`username` and `node` are required. `node` must reference a VM node, not a switch/network node.
Directory users, groups, service principals, devices, IAM roles, IdP
applications, and federation subjects belong in
`nodes.<node>.runtime.identity_authorities` when they are observed
identity-authority inventory. A top-level account may intentionally mirror one
of those subjects when the scenario needs a provisioned or participant starting
credential, but that is a second authored resource rather than the directory
model itself.

---

## Relationships

Typed directed edges between any named scenario elements. Adapted from STIX Relationship SROs.

```yaml
relationships:
  exchange-auth:
    type: authenticates_with
    source: exchange-service
    target: ad-ds
  domain-trust:
    type: trusts
    source: child-domain
    target: parent-domain
    properties:
      trust_type: parent-child
      trust_direction: bidirectional
  sso:
    type: federates_with
    source: adfs
    target: azure-ad
    properties: {protocol: SAML}
  app-to-db:
    type: connects_to
    source: webapp
    target: postgres
    properties: {protocol: tcp, port: "5432"}
```

Types: `authenticates_with`, `trusts`, `federates_with`, `connects_to`, `depends_on`, `manages`, `replicates_to`.

Relationship endpoints resolve against the scenario's named elements,
including top-level section keys, nested entity dot-paths, variables, other
relationships, content item `name` values, named service bindings
(`nodes.<node>.services.<service_name>`), runtime identity-authority refs
(`nodes.<node>.runtime.identity_authorities.<authority_id>` and nested
`.services.<service_id>`, `.subjects.<subject_id>`, `.policies.<policy_id>`,
or `.relationships.<relationship_id>` refs), runtime DNS refs
(`nodes.<node>.runtime.dns_services.<dns_service_id>` and nested
`.zones.<zone_id>` or `.zones.<zone_id>.rrsets.<rrset_id>` refs), and named
ACL rules (`infrastructure.<infra>.acls.<acl_name>`).

Bare refs like `webapp` are valid when they are unambiguous. Any top-level section key may also be referenced explicitly as `<section>.<name>`, for example `nodes.webapp`, `features.postgres`, `accounts.db-admin`, or `infrastructure.dmz-net`. Content items may be referenced as `content.<content_name>.items.<item_name>` when a bare item `name` would collide with some other named element.

---

## Agents

Autonomous scenario participants. Adapted from CybORG CAGE Challenge. This
section is also the SDL-authoring surface for declarative participant framing
(ACT-601, ADR-020) — it covers all five framing facets the language
guarantees: identity, role, starting conditions, authority anchors, and
operating scope.

```yaml
agents:
  red-agent:
    entity: red-team                    # identity + role (via entities.role)
    actions: [Scan, Exploit, Escalate]
    starting_accounts: [phished-user]   # references accounts section
    starting_conditions: [beacon-online]  # references conditions section
    initial_knowledge:
      hosts: [user0]                    # known at scenario start
      subnets: [user-net]
      services: [ssh]                   # references nodes.*.services[].name
      accounts: [helpdesk-user]         # references accounts section
    authority_anchors:                  # declared bases for what the participant
      - red-team                        # may or is expected to do in scenario
      - red-controls-vm                 # meaning (entities, relationships, ...)
    allowed_subnets: [user-net, corp-net]
    operating_scope:                    # broader targetable scope beyond subnets
      - corp-net
      - user-net
    reward_calculator: HybridImpactPwn
```

`entity` is required and must resolve to the `entities` section; the
participant's authored identity and role both come from this binding (per
ADR-020). `initial_knowledge.hosts` references VM node names, `subnets`
references switch-backed infrastructure names, `services` references service
names declared in `nodes.*.services`, and `accounts` references entries in the
`accounts` section. `allowed_subnets` follows the same switch-backed
infrastructure rule.

`starting_conditions` lists names from the `conditions` section, giving the
authoring surface a declarative hook for participant-relevant precondition
checks without embedding executable setup commands. `authority_anchors`
references any declared scenario element (entities, relationships, content,
nodes, …) that anchors what the participant is allowed or expected to do in
scenario meaning — these are SDL-level anchors, not control-plane
authentication or bearer-token identity. `operating_scope` references
targetable named scenario elements (subnets, hosts, services, content) that
define the boundary of where the participant may act or observe; it
generalises `allowed_subnets`, which remains restricted to switch-backed
infrastructure.

Each of `starting_conditions`, `authority_anchors`, and `operating_scope`
accepts `${var}` placeholders that resolve through the declared `variables`
section. Symbol-defining keys (agent names) remain stable identifiers and
must not be variables.

This section captures the authoring-layer guarantees of ACT-601. Broader
participant concerns — behavior semantics, visibility, trajectories,
budgets, verifier/reward — remain owned by separate ecosystem requirements
(ACT-602, SEM-208, ...) and are not fully represented by the `agents` section.

Broader participant concerns are treated as first-class ecosystem surfaces,
even where the current SDL syntax does not expose their full shape. Those
concerns include:

- participant-visible tool and affordance surfaces
- participant control-context artifacts such as directives and policies
- decision-surface exposure policies describing what is visible or hidden to a
  participant
- trajectory, episode, benchmark, verifier, and reward assets
- concrete participant implementations, which remain distinct from authored
  participant intent and from backend realization

That distinction is important: the SDL describes participant intent and
scenario meaning, while processors, backends, and participant implementations
remain separate apparatus surfaces.

---

## Objectives

Declarative experiment semantics that bind actors, targets, timing, and success criteria in the same SDL. Inspired by OCR's in-spec assessment model and CACAO's separation of agent, target, and workflow context.

```yaml
objectives:
  red-initial-access:
    agent: red-agent                   # or: entity: red-team
    actions: [Scan, Exploit]           # should be declared on the agent
    targets:                           # any named scenario elements except variables/objectives/workflows
      - web-server
      - app-to-db
      - nodes.web-server.services.https
      - infrastructure.dmz-switch.acls.allow-dmz-https
    success:
      mode: all_of                     # all_of, any_of
      goals: [pass-exercise]
      metrics: [service-uptime]
    window:
      stories: [exercise]
      scripts: [main-timeline]
      events: [attack-wave]
      workflows: [release-response]
      steps: [release-response.validate-release]

  blue-reporting:
    entity: blue-team
    success:
      metrics: [report-quality]
    depends_on: [red-initial-access]
```

Every objective must declare exactly one actor: either `agent` or `entity`. `success` is required and must reference at least one declared `condition`, `metric`, `evaluation`, `tlo`, or `goal`. `targets` are optional, but when present they must resolve to named scenario elements. Bare target refs work when unambiguous; otherwise use a qualified ref such as `nodes.web-server`, `features.app-to-db`, or `content.mailbox.items.invoice.eml`. `window` is optional; when supplied, referenced stories/scripts/events/workflows must exist and remain internally consistent. Workflow steps use qualified refs of the form `<workflow>.<step>`.

`depends_on` is an ordering relation, not just commentary. It defines a partial order over objectives: downstream objectives are not considered ready until their predecessors have been satisfied. Objective dependency cycles are rejected.

This section is intentionally declarative. It says who is trying to do what, against what, during which window, and how success is interpreted. It does **not** embed backend-specific probes such as Wazuh queries or command-output checks.

---

## Workflows

Declarative control programs over SDL-defined objectives and portable workflow state. Workflows remain backend-agnostic: they express experiment control intent, retries, failure handling, and concurrency without embedding backend-native commands.

```yaml
workflows:
  release-response:
    start: validate-release
    steps:
      validate-release:
        type: objective
        objective: blue-validate-release
        on-success: branch-on-promotion
      branch-on-promotion:
        type: decision
        when:
          conditions: [rogue-release-promoted]
        then: rollback-fanout
        else: finish
      rollback-fanout:
        type: parallel
        branches: [revoke-artifact, rollback-edge]
        join: rollback-joined
      revoke-artifact:
        type: objective
        objective: blue-revoke-artifact
        on-success: rollback-joined
      rollback-edge:
        type: objective
        objective: blue-preserve-service
        on-success: rollback-joined
      rollback-joined:
        type: join
        next: verify-rollback
      verify-rollback:
        type: decision
        when:
          steps:
            - step: revoke-artifact
              outcomes: [succeeded]
        then: finish
        else: revalidate-release
      revalidate-release:
        type: objective
        objective: blue-validate-release
        on-success: finish
      finish:
        type: end
```

Workflow step types are:

- `objective` — execute a declared objective; `on-success` is required and `on-failure` is optional. If `on-failure` is omitted, workflow execution fails terminally on objective failure.
- `decision` — branch on a declarative predicate using `then` / `else`
- `switch` — evaluate ordered `cases`, take the first matching case target, and fall back to `default` when no case predicate matches
- `retry` — re-run a declared objective until it succeeds or `max-attempts` is exhausted; `on-success` is required and `on-exhausted` is optional
- `call` — invoke another declared workflow as a reusable subflow; `workflow` and `on-success` are required, and `on-failure` is optional
- `parallel` — launch two or more branch entry steps concurrently and require all explicit branch paths to converge on a named `join` step; `on-failure` is optional
- `join` — an explicit barrier step, not a normal direct successor edge, that resumes linear control via `next` only after the owning `parallel` step has observed all branches converge
- `end` — terminal node

Compensation is step-attached and workflow-governed:

- compensable steps are `objective` and `call`
- those step kinds may declare `compensate-with: <workflow>`
- workflows may declare a `compensation:` policy with:
  - `mode: automatic | disabled`
  - `on: [failed, cancelled, timed_out]`
  - `failure_policy: fail_workflow | record_and_continue`
  - `order: reverse_completion` (the only supported ordering in v1)

Compensation targets are always declared workflows, never inline rollback step
graphs. Successful compensable steps register rollback intent, and automatic
compensation executes in reverse completion order when the primary workflow
terminates with a configured trigger.

Workflow predicates may observe:

- scoring/evaluation data via `conditions`, `metrics`, `evaluations`, `tlos`, `goals`, and `objectives`
- prior step state via `steps`, where each entry names a prior executable step plus one or more expected outcomes (`succeeded`, `failed`, `exhausted`) and an optional `min-attempts`

Example predicate over prior step state:

```yaml
when:
  steps:
    - step: validate-release
      outcomes: [failed]
      min-attempts: 2
```

Workflow-visible step state is an immutable execution history. In v1, predicates may only inspect step outcomes and attempt counts; they may not inspect backend-specific failure classes. Step-state predicates must reference steps whose state is guaranteed to be known before the predicate executes.

After a `join`, downstream predicates may inspect executable branch steps from that fanout, but only when those steps are guaranteed on every path within their own branch before the join. Branch-local step state does not leak across sibling branches before the join, and a `parallel.on-failure` bypass does not expose abandoned branch state.

Workflow graphs remain acyclic. Every referenced step must exist, every step
must be reachable from `start`, joins must be referenced by exactly one
`parallel` step, every explicit branch path from a `parallel` step must
converge on its declared join, and workflow call graphs must also remain
acyclic. Workflow names may use canonical namespace-style dots, but workflow
step names may not because objective window refs use `<workflow>.<step>`
syntax and split on the final `.`.

Migration from the exploratory workflow syntax:

- replace `if` with `decision`
- replace `while` with `retry` when the repeated work is a single objective
- replace `next` on objective steps with required `on-success`
- replace `on-error` with `on-failure` (for `objective` / `parallel`) or `on-exhausted` (for `retry`)
- replace `parallel.next` with an explicit `join` step
- replace `step-outcomes: [step-name]` with `steps: [{step: step-name, outcomes: [...]}]`

---

## Variables

Scenario parameterization. Adapted from CACAO playbook_variables.

```yaml
variables:
  domain_name:
    type: string
    default: "corp.local"
    description: Active Directory domain name
  num_workstations:
    type: integer
    default: 5
  admin_strength:
    type: string
    default: weak
    allowed_values: [weak, medium, strong]
    required: false
```

Variables are referenced as `${var_name}` in other sections. They are **not resolved at parse time** — resolution happens at instantiation.

Full-value placeholders are currently supported in ordinary string fields, common scalar fields (counts, booleans, scores, timings, RAM/CPU, ports), many reference values, and selected leaf enum-backed property fields such as `accounts.*.password_strength`, `entities.*.role`, `nodes.*.os`, `nodes.*.asset_value.*`, `nodes.*.runtime.identity_authorities.*.kind`, identity-authority subject/policy/relationship kinds, identity-authority ports and enabled flags, `nodes.*.runtime.dns_services.*.implementation`, DNS service roles, DNS zone kinds/purposes/classes, DNS record classes/types/provenance, DNS resolver booleans and DNSSEC validation modes, `infrastructure.*.acls[*].action`, and `objectives.*.success.mode`. The semantic validator checks that `${var_name}` refers to a declared variable, and the repo-owned instantiation phase substitutes concrete values before compilation/runtime planning. User-defined mapping keys and discriminant/schema-shaping enum fields such as section `type` tags still need concrete values, and placeholder keys are rejected at parse time.

Think of variables as parameterizing **properties of declared objects**, not the object graph itself. For example, a node's hostname, a content file's text, or a subnet CIDR may be variable-backed, while top-level identifiers like `nodes.web`, `features.nginx`, or `accounts.domain-admin` must remain literal.

`default` and every entry in `allowed_values` must match the declared `type`. If `allowed_values` is provided, `default` must be one of those values.

---

## Scoring, Objectives, and Runtime Checks

The SDL carries both:

- the OCR-style scoring pipeline (`conditions → metrics → evaluations → TLOs → goals`)
- declarative objectives that bind actors, targets, windows, and success criteria
- workflow graphs that branch or parallelize declared objectives without embedding runtime probe logic

Backend-specific auto-validation mechanics still live outside the SDL. The runtime may use Wazuh queries, command probes, file checks, or other adapters to determine whether an SDL-declared objective or scoring condition has been satisfied, but those probe details are not the language itself.
