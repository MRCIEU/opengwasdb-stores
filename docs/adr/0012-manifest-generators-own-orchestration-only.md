# Manifest generators own orchestration only

Manifest Generators may live in this repository when they perform Store Family-specific discovery, selection, prioritisation, and manifest emission. Reusable source readers, normalisation logic, and store build engines belong in OpenGWASDB or another shared package rather than being reimplemented inside the registry.
