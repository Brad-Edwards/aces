# Check a backend boundary

Use backend manifests and conformance fixtures to state what an implementation
accepts and what it can realize.

RAES separates three questions:

1. Is the SDL document valid?
2. Can a processor compile the requested meaning?
3. Can a selected backend realize the compiled request?

A valid scenario can still exceed a backend's declared capabilities. Read the
backend report and keep unsupported or degraded results with the run evidence.

The repository includes contracts, stubs, a reference emulation backend, and
conformance tests. It does not ship a production deployment backend or managed
environment service.

Start with the [backend schemas](https://github.com/OpenRAE/rae/tree/main/contracts/schemas/backend-manifest)
and the [conformance API](api/contracts.rst).
