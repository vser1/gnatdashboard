##############################################################################
##                                                                          ##
##                               G N A T h u b                              ##
##                                                                          ##
##                     Copyright (C) 2013-2014, AdaCore                     ##
##                                                                          ##
## The QM is free software; you can redistribute it  and/or modify it       ##
## under terms of the GNU General Public License as published by the Free   ##
## Software Foundation; either version 3, or (at your option) any later     ##
## version.  The QM is distributed in the hope that it will be useful,      ##
## but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHAN-  ##
## TABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public ##
## License  for more details. You  should  have  received a copy of the GNU ##
## General Public License  distributed with the QM; see file COPYING3. If   ##
## not, write  to  the Free  Software  Foundation,  59 Temple Place - Suite ##
## 330, Boston, MA 02111-1307, USA.                                         ##
##                                                                          ##
##############################################################################

"""GNAThub plug-in for the CodePeer command-line tool.

It exports the CodePeer Python class which implements the GNAThub.Plugin
interface. This allows GNAThub's plug-in scanner to automatically find this
module and load it as part of the GNAThub default execution.
"""

import csv
import os

import GNAThub
from GNAThub import System


class CodePeer(GNAThub.Plugin):
    """CodePeer plugin for GNAThub

    Configures and executes CodePeer, then analyzes the output.
    """

    name = 'codepeer'

    def __init__(self):
        super(CodePeer, self).__init__()

        self.tool = None

        output = '%s.csv' % GNAThub.Project.name().lower()
        self.csv_report = os.path.join(GNAThub.Project.object_dir(),
                                       'codepeer', output)

        self.report = os.path.join(GNAThub.Project.object_dir(),
                                   '%s.out' % self.name)

    def __cmd_line(self):
        """Creates CodePeer command line arguments list.

        RETURNS
            :rtype: a list of string
        """

        return ['codepeer', '-update-scil', '-level', '1',
                '-P', GNAThub.Project.path(), '-jobs', str(GNAThub.jobs())]

    def __msg_reader_cmd_line(self):
        """Creates CodePeer Message Reader command line arguments list.

        RETURNS
            :rtype: a list of string
        """

        msg_dir = os.path.join(GNAThub.Project.object_dir(), 'codepeer',
                               '%s.output' % GNAThub.Project.name().lower())

        return ['codepeer_msg_reader', '-csv', msg_dir]

    def execute(self):
        """Executes the CodePeer.

        CodePeer.execute_msg_reader() will be called upon process completion.
        """

        proc = GNAThub.Run(self.name, self.__cmd_line())

        if proc.status:
            return

        self.execute_msg_reader()

    def execute_msg_reader(self):
        """Executes the CodePeer Message Reader.

        CodePeer.postprocess() will be called upon process completion.
        """

        System.info('%s: execute msg_reader to collect results' % self.name)
        proc = GNAThub.Run('msg_reader', self.__msg_reader_cmd_line(),
                           out=self.csv_report)

        self.postprocess(proc.status)

    def postprocess(self, exit_code):
        """Postprocesses the tool execution: parse the output report on
        success.

        Sets the exec_status property according to the success of the
        analysis:

            GNAThub.EXEC_SUCCESS: on successful execution and analysis
            GNAThub.EXEC_FAILURE: on any error
        """

        if exit_code != 0:
            self.exec_status = GNAThub.EXEC_FAILURE
            return

        self.__parse_csv_report()

    def __parse_csv_report(self):
        """Parses CodePeer output CSV report.

        Sets the exec_status property according to the success of the
        analysis:

            GNAThub.EXEC_SUCCESS: on successful execution and analysis
            GNAThub.EXEC_FAILURE: on any error
        """

        System.info('%s: analysing CSV report', self.name)
        self.tool = GNAThub.Tool(self.name)

        self.log.debug('Parse report: %s' % self.csv_report)

        if not os.path.exists(self.csv_report):
            self.exec_status = GNAThub.EXEC_FAILURE
            System.error('%s: no report found' % self.name)
            return

        with open(self.csv_report, 'rb') as report:
            # Compute the total number of lines for progress report (-1 because
            # the first line in irrelevant to the analysis).
            total = len(report.readlines()) - 1

            # Reset the read cursor to the first byte
            report.seek(0)

            try:
                # Parse the file and drop the first line (containing the
                # columns name).
                reader = csv.reader(report, quotechar='\"')

                # Drop the first line (containing the columns name)
                header = reader.next()
                self.log.debug('Drop header line: %s' % header)

                # Iterate over each relevant record
                for index, record in enumerate(reader, start=1):
                    self.log.debug('Parse record: %r' % record)

                    # Each row is a list of strings:
                    # [File, Line, Column, Category, New?, Review?, Ranking,
                    #  Kind, Message, Classification, CWE]

                    source = record[0]
                    line = record[1]
                    column = record[2]
                    rule = record[3]
                    severity = record[6]
                    category = record[7]
                    message = record[8]

                    # See L919-022: duplicated rules for priorities and
                    # categories in SonarQube Rule Repository.
                    # ???: Remove this work-around once fixed in SonarQube.
                    category = '%s__%s' % (severity.upper(), category.upper())

                    self.__add_message(source, line, column, rule, message,
                                       category)

                    System.progress(index, total, new_line=(index == total))

            except csv.Error as ex:
                self.exec_status = GNAThub.EXEC_FAILURE
                System.error('%s: error: %s (%s:%d)' %
                             (self.name, ex, os.path.basename(report), total))
                return

            self.exec_status = GNAThub.EXEC_SUCCESS

    def __add_message(self, src, line, column, rule_id, msg, category):
        """Adds CodePeer message to current session database.

        Parameters:
            :param src: message source file
            :type src: a string
            :param line: message line number
            :type line: a string
            :param column: message column number
            :type column: a string
            :param rule_id: message's rule identifier
            :type rule_id: a string
            :param msg: description of the message
            :type msg: a string
            :param category: the category of the message
            :type category: a string
        """

        rule = GNAThub.Rule(rule_id, rule_id, GNAThub.RULE_KIND, self.tool)
        cat = GNAThub.Category(category)
        message = GNAThub.Message(rule, msg, cat)
        resource = GNAThub.Resource.get(src)

        if resource:
            resource.add_message(message, int(line), int(column))
