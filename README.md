# codika_dart_services

**codika_dart_services** is a thin wrapper around Codika's internal Dart analysis
services. It lets any project in this mono-repo import the services from a
stable, decoupled namespace.

## Installation

Install directly from the private GitHub repository that hosts this package:

```bash
pip install "codika_dart_services @ git+ssh://git@github.com/codika-io/codika_dart_services.git@v0.1.2"
```

Add the same line to your `pyproject.toml` (or `requirements.txt`) so CI and other developers get the library automatically:

```toml
codika_dart_services @ git+ssh://git@github.com/codika-io/codika_dart_services.git@v0.1.2
```

Notes:
1. Use the **SSH** URL (`git+ssh://git@github.com/...`) so that `pip` authenticates with the SSH key already configured on your machine/CI runner.  HTTPS URLs require a personal-access token.
2. Always pin to a tag (e.g. `@v0.1.2`) or commit hash for reproducible builds.
3. If you move the repository under a different organisation or rename it, update the URL accordingly.


## Usage

```python
from codika_dart_services import (
    DartWorkspaceService,
    DartCodeIntelligenceService,
    DartDiagnosticsService,
    DartLSPService,
)
```