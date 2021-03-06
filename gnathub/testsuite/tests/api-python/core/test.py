"""Check that all files have been created."""

from unittest import TestCase
from support.mock import GNAThub, Project


class TestSimpleExample(TestCase):
    def setUp(self):
        self.longMessage = True

        # Run GNAThub with only the sonar-config plugin
        self.gnathub = GNAThub(Project.simple(), plugins=['sonar-config'])

    def testPythonAPIDefined(self):
        # Test the core Python API
        self.gnathub.run(script='check-api.py', tool_args={
            'codepeer': ['-msg-output-only', '-j0', 'positional-arg'],
            'codepeer_msg_reader': ['-msg-output-only']
        }, runners_only=True)
