# GNAThub (GNATdashboard)
# Copyright (C) 2013-2015, AdaCore
#
# This is free software;  you can redistribute it  and/or modify it  under
# terms of the  GNU General Public License as published  by the Free Soft-
# ware  Foundation;  either version 3,  or (at your option) any later ver-
# sion.  This software is distributed in the hope  that it will be useful,
# but WITHOUT ANY WARRANTY;  without even the implied warranty of MERCHAN-
# TABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public
# License for  more details.  You should have  received  a copy of the GNU
# General  Public  License  distributed  with  this  software;   see  file
# COPYING3.  If not, go to http://www.gnu.org/licenses for a complete copy
# of the license.

"""GNAThub plug-in for the SonarQube Runner command-line tool

It exports the SonarRunner class which implements the :class:`GNAThub.Plugin`
interface. This allows GNAThub's plug-in scanner to automatically find this
module and load it as part of the GNAThub default execution.
"""

import platform

import GNAThub

from _sonarqube import SonarQube


class SonarRunner(GNAThub.Plugin):
    """GNATmetric plugin for GNAThub"""

    def __init__(self):
        super(SonarRunner, self).__init__()

    @property
    def name(self):
        return 'sonar-runner'

    def setup(self):
        # Do not call the super method: we do not need a database session to be
        # opened.

        SonarQube.make_workdir()

    @staticmethod
    def __cmd_line():
        """Returns command line for sonar runner execution

        :return: the SonarRunner command line
        :rtype: list[str]
        """

        # Enable verbose and debugging output with -e and -X. This is handy for
        # debugging in case of issue in the SonarRunner step.

        if platform.system() == 'Windows':
            return ['cmd', '/c',
                    'sonar-runner -Dproject.settings=%s -e -X'
                    % SonarQube.configuration()]
        else:
            return ['sonar-runner',
                    '-Dproject.settings=%s' % SonarQube.configuration(),
                    '-e', '-X']

    def execute(self):
        """Executes the Sonar Runner

        :meth:`postprocess()` is called upon process completion.
        """

        proc = GNAThub.Run(self.name, SonarRunner.__cmd_line())
        self.postprocess(proc.status)

    def postprocess(self, exit_code):
        """Postprocesses the tool execution

        Sets the exec_status property according to the successful of the
        analysis:

            * ``GNAThub.EXEC_SUCCESS``: on successful execution and analysis
            * ``GNAThub.EXEC_FAILURE``: on any error
        """

        if exit_code != 0:
            self.exec_status = GNAThub.EXEC_FAILURE
        else:
            self.exec_status = GNAThub.EXEC_SUCCESS
