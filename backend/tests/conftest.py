"""Points app.db at a throwaway temp file for the whole test session, set
before any test module (or app.main, which triggers a real DB connection
on startup) gets imported - so running the suite never touches or pollutes
the real dev database at backend/data/1822.db."""
import os
import tempfile

_tmp_dir = tempfile.mkdtemp(prefix="1822-test-db-")
os.environ["ONE822_DB_PATH"] = os.path.join(_tmp_dir, "test.db")
