"""Run the tests from the project root so that the CSV files are found."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

os.chdir(ROOT)
sys.path.insert(0, ROOT)
