# Ports the application layer depends on for external capabilities (AI
# providers, object storage, vector search, task dispatch). Concrete
# adapters live in app/infrastructure/ and are bound at the composition
# root (app/main.py / DI container), never imported here directly.
