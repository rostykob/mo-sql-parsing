# encoding: utf-8
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Contact: Kyle Lahnakoski (kyle@lahnakoski.com)
#


from threading import Lock
from typing import Mapping

from mo_dots import listwrap, Data, from_data

parse_locker = Lock()  # ENSURE ONLY ONE PARSING AT A TIME

sql_parser = _utils = ansi_string = scrub = None

lookup_parsers = {
    "common_parser": {"*": None, None: None},
    "mysql_parser": {"*": None, None: None},
    "sqlserver_parser": {"*": None, None: None},
    "bigquery_parser": {"*": None, None: None},
}

SQL_NULL: Mapping[str, Mapping] = {"null": {}}


def parse(sql, null=SQL_NULL, calls=None, all_columns=None):
    """
    GENERIC SQL PARSER. CHOSE ANOTHER IF YOU KNOW THE DIALECT
    :param sql: String of SQL
    :param null: What value to use as NULL (default is the null function `{"null":{}}`)
    :param calls: What to do with function calls (default is the simple_op function `{"op":{}}`)
    :param all_columns: use all_columns="*" for old behaviour (see version 10)
    :return: parse tree
    """
    with parse_locker:
        parser = _get_or_create_parser("common_parser", all_columns)
        return _parse(parser, sql, null, calls or simple_op)


def parse_mysql(sql, null=SQL_NULL, calls=None, all_columns=None):
    """
    PARSE MySQL ASSUME DOUBLE QUOTED STRINGS ARE LITERALS
    :param sql: String of SQL
    :param null: What value to use as NULL (default is the null function `{"null":{}}`)
    :param calls: What to do with function calls (default is the simple_op function `{"op":{}}`)
    :param all_columns: use all_columns="*" for old behaviour (see version 10)
    :return: parse tree
    """
    with parse_locker:
        parser = _get_or_create_parser("mysql_parser", all_columns)
        return _parse(parser, sql, null, calls or simple_op)


def parse_sqlserver(sql, null=SQL_NULL, calls=None, all_columns=None):
    """
    PARSE SqlServer ASSUME SQUARE BRACKETS ARE VARIABLE NAMES
    :param sql: String of SQL
    :param null: What value to use as NULL (default is the null function `{"null":{}}`)
    :param calls: What to do with function calls (default is the simple_op function `{"op":{}}`)
    :param all_columns: use all_columns="*" for old behaviour (see version 10)
    :return: parse tree
    """
    with parse_locker:
        parser = _get_or_create_parser("sqlserver_parser", all_columns)
        return _parse(parser, sql, null, calls or simple_op)


def parse_bigquery(sql, null=SQL_NULL, calls=None, all_columns=None):
    """
    PARSE BigQuery ASSUME DOUBLE QUOTED STRINGS ARE LITERALS, AND SQUARE BRACKETS ARE LISTS
    :param sql: String of SQL
    :param null: What value to use as NULL (default is the null function `{"null":{}}`)
    :param calls: What to do with function calls (default is the simple_op function `{"op":{}}`)
    :param all_columns: use all_columns="*" for old behaviour (see version 10)
    :return: parse tree
    """
    with parse_locker:
        parser = _get_or_create_parser("bigquery_parser", all_columns)
        return _parse(parser, sql, null, calls or simple_op)


def _get_or_create_parser(parser_name, all_columns=None):
    global sql_parser, _utils, ansi_string, scrub
    try:
        parser = lookup_parsers[parser_name][all_columns]
        if not parser:
            from mo_sql_parsing import sql_parser, utils as _utils
            from mo_sql_parsing.sql_parser import scrub
            from mo_sql_parsing.utils import ansi_string

            parser = lookup_parsers[parser_name][all_columns] = getattr(sql_parser, parser_name)(all_columns)
        return parser
    except Exception as cause:
        raise Exception("Expecting all_columns to be None or '*'") from cause


def _parse(parser, sql, null, calls):
    _utils.null_locations = []
    _utils.scrub_op = calls
    sql = sql.rstrip().rstrip(";")
    parse_result = parser.parse_string(sql, parse_all=True)
    output = scrub(parse_result)
    for o, n in _utils.null_locations:
        o[n] = null
    return output


def format(json, ansi_quotes=True, should_quote=None):
    """
    :param json:  Parsed SQL as json
    :param ansi_quotes: True if identifiers can be put in double quotes
    :param should_quote: Function that returns True if a string should be quoted (because contains spaces, etc)
    :return: SQL string
    """
    from mo_sql_parsing.formatting import Formatter

    return Formatter(ansi_quotes, should_quote).dispatch(json)


def simple_op(op, args, kwargs):
    if args is None:
        kwargs[op] = {}
    else:
        kwargs[op] = args
    return kwargs


def normal_op(op, args, kwargs):
    output = Data(op=op)
    args = listwrap(args)
    if args and (not isinstance(args[0], dict) or args[0]):
        output.args = args
    if kwargs:
        output.kwargs = kwargs
    return from_data(output)


__all__ = ["parse", "format", "parse_mysql", "parse_sqlserver", "parse_bigquery", "normal_op", "simple_op", "SQL_NULL"]
