# coding: utf-8
from oar.modules.sarko import Sarko
from oar.lib import config

import pytest

def test_finaud_void():
    sarko = Sarko()
    sarko.run()
    print(sarko.guilty_found)
    assert sarko.guilty_found == 0
