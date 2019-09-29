import unittest
import logging
import sys
sys.path.append('../')
from backend.actions import Actions
from raspiot.utils import InvalidParameter, MissingParameter, CommandError, Unauthorized
from raspiot.libs.tests import session
import os
import time
from mock import Mock

class TestActions(unittest.TestCase):

    def setUp(self):
        self.session = session.Session(logging.CRITICAL)
        _action = Actions
        self.module = self.session.setup(_actions)

    def tearDown(self):
        self.session.clean()

if __name__ == "__main__":
    unittest.main()
    
