# GNAThub (GNATdashboard)
# Copyright (C) 2016-2017, AdaCore
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

"""GNAThub reporters.

It massages the collected results of the various input tools in a common format
prior to export.
"""

import GNAThub

import collections
import json
import logging
import os
import time

from enum import Enum
from itertools import chain

import pygments.lexers
import pygments.util

from pygments import highlight
from pygments.formatters import HtmlFormatter


def _write_json(output, obj, **kwargs):
    """Dump a JSON-encoded representation of `obj` into `output`.

    :param str output: path to the output file
    :param obj: object to serialize and save into `output`
    :type obj: dict or list or str or int
    :param dict kwargs: the parameters to pass to the underlying
        :func:`json.dumps` function; see :func:`json.dumps` documentation
        for more information
    :raises: IOError
    :see: :func:`json.dumps`
    """

    with open(output, 'w') as outfile:
        outfile.write(json.dumps(obj, **kwargs))


def _count_extra_newlines(lines):
    """Count the number of leading and trailing newlines.

    :rtype: int, int
    """
    leading_newline_count, trailing_newline_count = 0, 0
    for line in lines:
        if not line:
            leading_newline_count += 1
        else:
            break
    for line in reversed(lines):
        if not line:
            trailing_newline_count += 1
        else:
            break
    return leading_newline_count, trailing_newline_count


class CoverageStatus(Enum):
    """Coverage status enumeration."""

    NO_CODE, COVERED, NOT_COVERED, PARTIALLY_COVERED = range(4)


class MessageRanking(Enum):
    """Ranking values for messages collected and reported by GNAThub."""

    INFO, MINOR, MAJOR, CRITICAL, BLOCKER = range(5)


class _HtmlFormatter(HtmlFormatter):
    """Custom implementation of the Pygments' HTML formatter."""

    def wrap(self, source, _):
        # The default wrap() implementation adds a <div> and a <pre> tag.
        return source


def _decorate_dict(obj, extra=None):
    """Decorate a Python dictionary with additional properties.

    :param dict[str, *] obj: the Python dictionary to decorate
    :param extra: extra fields to decorate the encoded object with
    :type extra: dict or None
    :rtype: dict[str, *]
    """
    if extra:
        obj.update(extra)
    return obj


def _encode_tool(tool, extra=None):
    """JSON-encode a tool.

    :param GNAThub.Tool tool: the tool to encode
    :param extra: extra fields to decorate the encoded object with
    :type extra: dict or None
    :rtype: dict[str, *]
    """
    return _decorate_dict({
        'id': tool.id,
        'name': tool.name
    }, extra)


def _encode_rule(rule, tool, extra=None):
    """JSON-encode a rule.

    :param GNAThub.Rule rule: the rule to encode
    :param GNAThub.Tool tool: the tool associated with the rule
    :param extra: extra fields to decorate the encoded object with
    :type extra: dict or None
    :rtype: dict[str, *]
    """
    return _decorate_dict({
        'id': rule.id,
        'identifier': rule.identifier,
        'name': rule.name,
        'kind': rule.kind,
        'tool': _encode_tool(tool)
    }, extra)


def _encode_property(prop, extra=None):
    """JSON-encode a message property.

    :param GNAThub.Property prop: the property associated with the message
    :param extra: extra fields to decorate the encoded object with
    :type extra: dict or None
    :rtype: dict[str,*]
    """
    return _decorate_dict({
        'id': prop.id,
        'identifier': prop.identifier,
        'name': prop.name
    }, extra)


def _encode_message(message, rule, tool, extra=None):
    """JSON-encode a message.

    :param GNAThub.Message message: the message to encode
    :param GNAThub.Rule rule: the rule associated with the message
    :param GNAThub.Tool tool: the tool associated with the rule
    :param extra: extra fields to decorate the encoded object with
    :type extra: dict or None
    :rtype: dict[str, *]
    """
    return _decorate_dict({
        'begin': message.col_begin,
        'end': message.col_end,
        'rule': _encode_rule(rule, tool),
        'properties': [
            _encode_property(prop) for prop in message.get_properties()],
        'message': message.data
    }, extra)


def _encode_metric(message, rule, tool, extra=None):
    """JSON-encode a metric.

    :param GNAThub.Message message: the message to encode
    :param GNAThub.Rule rule: the rule associated with the message
    :param GNAThub.Tool tool: the tool associated with the rule
    :param extra: extra fields to decorate the encoded object with
    :type extra: dict or None
    :rtype: dict[str, *]
    """
    return _decorate_dict({
        'rule': _encode_rule(rule, tool),
        'value': message.data
    }, extra)


def _get_coverage(message, tool):
    """Compute coverage results.

    :param GNAThub.Message message: the message to encode
    :param GNAThub.Tool tool: the coverage tool that generated this message
    :return: the number of hits for that line and the coverage status
    :rtype: int, CoverageStatus
    """
    hits, status = -1, CoverageStatus.NO_CODE
    if tool.name == 'gcov':
        hits = int(message.data)
        status = (
            CoverageStatus.COVERED if hits else CoverageStatus.NOT_COVERED)
    # TODO: augment with support for GNATcoverage
    return hits, status


def _encode_coverage(hits, status, extra=None):
    """JSON-encode coverage information.

    :param int hits: ???
    :param CoverageStatus status: ???
    :param extra: extra fields to decorate the encoded object with
    :type extra: dict or None
    :rtype: dict[str, *]
    """
    return _decorate_dict({
        'status': status.name,
        'hits': hits
    }, extra)


def with_static(**kwargs):
    """Declare static variables for functions with annotation."""

    def decorate(func):
        for k in kwargs:
            setattr(func, k, kwargs[k])
        return func
    return decorate


@with_static(rules=None)
def _rule_by_id(rule_id):
    """Return the :class:`GNAThub.Rule` with ``rule_id``.

    :param int rule_id: the unique ID of the rule
    :rtype: GNAThub.Rule
    """
    if _rule_by_id.rules is None:
        _rule_by_id.rules = {rule.id: rule for rule in GNAThub.Rule.list()}
    return _rule_by_id.rules[rule_id]


@with_static(tools=None)
def _tool_by_id(tool_id):
    """Return the :class:`GNAThub.Tool` with ``tool_id``.

    :param int tool_id: the unique ID of the tool
    :rtype: GNAThub.Tool
    """
    if _tool_by_id.tools is None:
        _tool_by_id.tools = {tool.id: tool for tool in GNAThub.Tool.list()}
    return _tool_by_id.tools[tool_id]


def _inc_msg_count(store, key, gen_value, *args):
    """Increment the "message_count" property of a dictionary.

    Create the dictionary and the "message_count" property if needed.

    :param dict store: the dictionary to update
    :param str key: the key to create/update
    :param Function gen_value: the function to call to create the value
        if missing from the dictionary (takes one positional `extra`
        argument that is a dictionary, ie. see `_encode_*` functions)
    :param list *args: arguments of the `gen_value` function
    """
    if key not in store:
        store[key] = gen_value(*args, extra={'message_count': 0})
    store[key]['message_count'] += 1


class Average(object):
    """Accumulator to compute an average."""

    def __init__(self):
        self._acc = None
        self._count = 0

    def add(self, value):
        """Add a new sample value.

        :param value:
        :type value: int or None
        """
        self._count += 1
        if value is None:
            return
        self._acc = (self._acc or 0) + value

    def compute(self):
        """Compute the average of the sample values added so far.

        :return: the average, or ``None`` if no sample was recorded
        :rtype: int or None
        """
        if self._acc is None or not self._count:
            return None
        return self._acc / self._count


class SourceBuilder(object):
    """Representation of a source file."""

    def __init__(self, project, path):
        """
        :param str project: the name of the project
        :param str path: the path to the source
        """
        self.project = project
        self.path = path
        self.source_dir, self.filename = os.path.split(self.path)
        self.log = logging.getLogger(
            '{}({})'.format(self.__class__.__name__, self.filename))

        self.tools, self.rules, self.props = {}, {}, {}
        self.metrics, self.coverage = [], {}
        self.messages = collections.defaultdict(list)
        self.message_count = collections.defaultdict(int)

        self._process_messages()

    @property
    def file_coverage(self):
        """
        :return: the average coverage of the file
        :rtype: int or None
        """
        if not self.coverage:
            return None
        # TODO: double-check formula when adding support for GNATcoverage.
        return sum(
            1 if status == CoverageStatus.COVERED else 0
            for _, status in self.coverage.itervalues()
        ) * 100 / len(self.coverage)

    def _process_messages(self):
        """Process all messages attached to this source file."""
        for message in GNAThub.Resource.get(self.path).list_messages():
            rule = _rule_by_id(message.rule_id)
            tool = _tool_by_id(rule.tool_id)

            if rule.identifier == 'coverage':
                # Only one coverage tool shall be used. The last entry
                # overwrites previous ones.
                self.coverage[message.line] = _get_coverage(message, tool)
                # Do not register message, rule or property for coverage.
                continue

            if message.line == 0:
                # Messages stored with line = 0 are metrics from GNATmetric.
                self.metrics.append((message, rule, tool))
                continue

            _inc_msg_count(self.tools, tool.id, _encode_tool, tool)
            _inc_msg_count(self.rules, rule.id, _encode_rule, rule, tool)
            for prop in message.get_properties():
                _inc_msg_count(self.props, prop.id, _encode_property, prop)
            self.messages[message.line].append((message, rule, tool))
            self.message_count[tool.id] += 1

    def to_json(self):
        """Generate the JSON-encoded representation of a source file.

        :rtype: dict[str, *]
        """
        if not os.path.isfile(self.path):
            self.log.error('%s: not such file (%s)', self.filename, self.path)
            return

        this = {
            'project': self.project,
            'filename': self.filename,
            'source_dir': self.source_dir,
            'has_messages': not not self.messages,
            'has_coverage': not not self.coverage,
            'full_path': self.path,
            'metrics': [_encode_metric(*metric) for metric in self.metrics],
            'properties': self.props,
            'tools': self.tools,
            'rules': self.rules,
            'lines': None
        }

        try:
            with open(self.path, 'r') as infile:
                content = infile.read()
        except IOError:
            self.log.exception('failed to read source file: %s', self.path)
            self.log.warn('report will be incomplete')
            return this

        # NOTE: Pygments lexer seems to drop those leading and trailing new
        # lines in its output. Add them back after HTMLization to avoid line
        # desynchronization with the original files.
        raw_lines = content.splitlines()
        lead_nl_count, trail_nl_count = _count_extra_newlines(raw_lines)

        # Select the appropriate lexer; fall back on "Null" lexer if no match.
        try:
            lex = pygments.lexers.guess_lexer_for_filename(self.path, content)
        except pygments.util.ClassNotFound:
            self.log.warn('could not guess lexer from file: %s', self.path)
            self.log.warn('fall back to using TextLexer (ie. no highlighting)')
            lex = pygments.lexers.special.TextLexer()

        # Attempt to decode the source file from UTF-8.
        try:
            decoded = [line.decode('utf-8') for line in raw_lines]
            if len(raw_lines) != len(decoded):
                raise IndexError(' '.join([
                    'mismatching number of source line in the decoded output;',
                    'expected {}, got {}'
                ]).format(len(raw_lines), len(decoded)))
        except UnicodeDecodeError:
            self.log.exception('failed to decode UTF-8: %s', self.path)
            self.log.warn('source file content may not be available')
            decoded = None

        # Attempt to highligth the source file; fall back to raw on failure.
        try:
            # HTML formatter outputting the decorated source code as a DOM.
            highlighted = (
                [''] * lead_nl_count +
                highlight(content, lex, _HtmlFormatter()).splitlines() +
                [''] * trail_nl_count)
            if len(raw_lines) != len(highlighted):
                raise IndexError(' '.join([
                    'mismatching number of source line in the HTML output;',
                    'expected {}, got {}'
                ]).format(len(raw_lines), len(highlighted)))
        except Exception:
            self.log.exception('failed to generate HTML: %s', self.path)
            self.log.warn('source file content may not be available')
            highlighted = None

        this['lines'] = [{
            'number': no,
            'content': decoded[no - 1] if decoded else None,
            'html_content': highlighted[no - 1] if highlighted else None,
            'coverage': (
                _encode_coverage(*self.coverage[no])
                if no in self.coverage else None),
            'messages': [
                _encode_message(*message) for message in self.messages[no]
            ] if no in self.messages else None,
        } for no in range(1, len(raw_lines) + 1)]

        # Return the best-effort representation of the source file.
        return this

    def save_as(self, path):
        """Save the JSON-encoded representation of the source file to disk.

        :param str path: the path to the output file
        """
        self.log.info('writing source %s', self.filename)
        _write_json(path, self.to_json(), indent=2)


class SourceDirBuilder(object):
    """Representation of a source directory."""

    def __init__(self, path):
        """
        :param str path: the path to the source directory
        """
        self.path = path
        self.source_files = []
        self.coverage = None

        self._coverage_avg = Average()
        self.message_count = collections.defaultdict(int)

    def add_source(self, source):
        """Record a new source file of the directory.

        :param SourceBuilder source: the source to add to this directory
        """
        file_coverage = source.file_coverage
        self.source_files.append({
            'filename': source.filename,
            'metrics': [_encode_metric(*metric) for metric in source.metrics],
            'message_count': source.message_count,
            'coverage': file_coverage
        })
        for _, _, tool in chain.from_iterable(source.messages.itervalues()):
            self.message_count[tool.id] += 1
        self._coverage_avg.add(file_coverage)

    def to_json(self):
        """Generate the JSON-encoded representation of a source directory.

        :rtype: dict[str, *]
        """
        return {
            'path': self.path,
            'sources': self.source_files,
            'message_count': self.message_count or None,
            'coverage': self._coverage_avg.compute()
        }


class ModuleBuilder(object):
    """Representation of a module (ie. a project)."""

    def __init__(self, name):
        """
        :param str name: the name of the project or subproject
        """
        self.name = name
        self.source_dirs = {}
        self.coverage = None
        self.log = logging.getLogger(
            '{}({})'.format(self.__class__.__name__, self.name))

        self._coverage_avg = Average()
        self.message_count = collections.defaultdict(int)

    def add_source(self, source):
        """Record a new source file of the module.

        :param SourceBuilder source: the source to add to this module
        """
        if source.source_dir not in self.source_dirs:
            source_dir = SourceDirBuilder(source.source_dir)
            self.source_dirs[source.source_dir] = source_dir
        self.source_dirs[source.source_dir].add_source(source)

        for tool_id, count in source.message_count.iteritems():
            self.message_count[tool_id] += count
        self._coverage_avg.add(source.file_coverage)

    def to_json(self):
        """Generate the JSON-encoded representation of a module.

        :rtype: dict[str, *]
        """
        paths = self.source_dirs.keys()
        return {
            'name': self.name,
            'source_dirs': {
                path: source_dir.to_json()
                for path, source_dir in self.source_dirs.iteritems()
            },
            'message_count': self.message_count or None,
            'coverage': self._coverage_avg.compute(),
            '_source_dirs_common_prefix': (
                os.path.commonprefix(paths)
                if len(paths) > 1 else os.path.dirname(paths[0]))
        }


class IndexBuilder(object):
    """Representation of the HTML report index."""

    def __init__(self):
        self.source_files = GNAThub.Project.source_files()
        self.source_file_count = sum(
            len(sources)
            for sources in self.source_files.itervalues())
        self.log = logging.getLogger(__name__)

        self.rules, self.tools = set(), set()
        self.modules = {}
        self.message_count = collections.defaultdict(int)

    def save_source(self, source):
        """Record a new source file of the root project.

        :param SourceBuilder source: a project source
        :return: the input source for conveniency
        :rtype: SourceBuilder
        """
        if source.project not in self.modules:
            self.modules[source.project] = ModuleBuilder(source.project)
        self.modules[source.project].add_source(source)

        for _, rule, tool in chain.from_iterable(source.messages.itervalues()):
            self.tools.add(tool)
            self.rules.add((rule, tool))
        for tool_id, count in source.message_count.iteritems():
            self.message_count[tool_id] += count

        return source

    def to_json(self):
        return {
            'modules': {
                name: module.to_json()
                for name, module in self.modules.iteritems()
            },
            'project': GNAThub.Project.name(),
            'creation_time': int(time.time()),
            'tools': {tool.id: _encode_tool(tool) for tool in self.tools},
            'rules': {
                rule.id: _encode_rule(rule, tool) for rule, tool in self.rules
            },
            'properties': [
                _encode_property(prop) for prop in GNAThub.Property.list()
            ],
            'message_count': self.message_count,
            '_database': GNAThub.database()
        }

    def save_as(self, path):
        """Save the JSON-encoded representation of the report index to disk.

        :param str path: the path to the output file
        """
        self.log.info('writing index')
        _write_json(path, self.to_json(), indent=2)


class ReportBuilder(object):
    """Report builder."""

    def __init__(self):
        self.log = logging.getLogger(self.__class__.__name__)
        self.index = IndexBuilder()

    def iter_sources(self):
        """Iterate over sources and yield JSON-encoded, augmenting the index.

        :yield: SourceBuilder
        """
        for project, sources in self.index.source_files.iteritems():
            for path in sources:
                self.log.info('processing %s', path)
                yield self.index.save_source(SourceBuilder(project, path))
