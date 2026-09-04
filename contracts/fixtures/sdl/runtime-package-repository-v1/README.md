# Runtime package repository profile fixtures

These fixtures exercise the portable APT repository profile introduced for
issue #847. The valid case pins the exact public signing-key bytes; the invalid
case demonstrates that an HTTPS key locator without its mandatory SHA-256
digest is not an exact trust binding.
