# Sonar Ada Plugin (GNATdashboard)
# Copyright (C) 2015-2017, AdaCore
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

"""Provide encoding functions for SonarQube integration."""


def encode_codepeer_key(message):
    """Create a rule key for CodePeer rule.

    :param str message: the rule message
    :rtype: str
    """

    return message.lower().partition(';')[0].replace(' ', '_')
