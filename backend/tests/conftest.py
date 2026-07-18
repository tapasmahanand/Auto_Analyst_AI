import os
import tempfile

# Must run before any `app` import: point storage at a throwaway directory and
# make sure no real API key leaks into tests.
os.environ["STORAGE_DIR"] = tempfile.mkdtemp(prefix="autoanalyst_test_")
os.environ["OPENAI_API_KEY"] = "test-key-never-called"
os.environ["EXEC_TIMEOUT_SECONDS"] = "30"
