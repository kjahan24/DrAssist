# Repository *interfaces* (ports) live here — abstract contracts the domain
# and application layers depend on. Concrete implementations (SQLAlchemy,
# Qdrant, etc.) live in app/infrastructure/repositories/ and must not be
# imported from here, preserving the dependency-inversion boundary.
