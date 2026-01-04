# =====================================
# ISOLATED TEST RUNNER (NO DJANGO)
# =====================================
import unittest

loader = unittest.TestLoader()
suite = loader.discover("isolated_tests", pattern="test_myfita_isolated.py")

runner = unittest.TextTestRunner(verbosity=2)
runner.run(suite)
