
# tests/conftest.py
# Shared pytest configuration for FairHire test suite.
# Add any project-wide fixtures or plugins here.
 
import os
import sys
 
# Ensure project root is on the path so both test files can import
# audit_engine and api without installing the package.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
 