import os

# Ensure test suite runs with demo mode enabled and a predictable secret key
os.environ.setdefault("DEMO_MODE", "true")
os.environ.setdefault("SECRET_KEY", "pytest-test-secret-key-32chars-minimum-safe")
