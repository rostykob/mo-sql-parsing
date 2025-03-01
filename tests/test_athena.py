# encoding: utf-8
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Author: Kyle Lahnakoski (kyle@lahnakoski.com)
#


from unittest import TestCase

from mo_sql_parsing import parse, normal_op


class TestAthena(TestCase):
    def test_issue_55_unnest(self):
        # UNNEST without AS is not understood.
        sql = """SELECT * FROM UNNEST(ARRAY[foo,bar]) table_name(column_name)"""
        result = parse(sql)
        expected = {
            "from": {"name": {"table_name": "column_name"}, "value": {"unnest": {"create_array": ["foo", "bar"]}}},
            "select": {"all_columns": {}},
        }
        self.assertEqual(result, expected)

    def test_issue_56_nulls_first(self):
        sql = """SELECT X() OVER (ORDER BY foo DESC NULLS FIRST)"""
        result = parse(sql)
        expected = {"select": {
            "over": {"orderby": {"nulls": "first", "sort": "desc", "value": "foo"}},
            "value": {"x": {}},
        }}
        self.assertEqual(result, expected)

    def test_issue_57_window_in_expression(self):
        sql = """SELECT X() OVER () = 1 AS is_true"""
        result = parse(sql)
        expected = {"select": {"name": "is_true", "value": {"eq": [{"over": {}, "value": {"x": {}}}, 1]}}}
        self.assertEqual(result, expected)

    def test_issue_58_filter_on_aggregate(self):
        sql = """SELECT MAX(1) FILTER (WHERE 1=1) AS foo"""
        result = parse(sql)
        expected = {"select": {"filter": {"eq": [1, 1]}, "name": "foo", "value": {"max": 1}}}
        self.assertEqual(result, expected)

    def test_issue_60_row_type(self):
        # eg CAST(ROW(1, 2.0) AS ROW(x BIGINT, y DOUBLE))
        sql = """SELECT CAST(x AS ROW(y VARCHAR))"""
        result = parse(sql)
        expected = {"select": {"value": {"cast": ["x", {"row": {"name": "y", "type": {"varchar": {}}}}]}}}
        self.assertEqual(result, expected)

    def test_issue_61_dot(self):
        sql = """SELECT b['c'].d"""
        result = parse(sql)
        expected = {"select": {"value": {"get": [{"get": ["b", {"literal": "c"}]}, {"literal": "d"}]}}}
        self.assertEqual(result, expected)

    def test_issue_59_is_distinct_from(self):
        # https://prestodb.io/docs/current/functions/comparison.html#is-distinct-from-and-is-not-distinct-from
        sql = """SELECT 1 IS DISTINCT FROM 2"""
        result = parse(sql)
        expected = {"select": {"value": {"eq!": [1, 2]}}}
        self.assertEqual(result, expected)

    def test_issue_59_is_not_distinct_from(self):
        sql = """SELECT 1 IS NOT DISTINCT FROM 2"""
        result = parse(sql)
        expected = {"select": {"value": {"ne!": [1, 2]}}}
        self.assertEqual(result, expected)

    def test_issue_62_structuralA(self):
        sql = """SELECT CAST(x AS ARRAY(ROW(y VARCHAR)))"""
        result = parse(sql)
        expected = {"select": {"value": {"cast": ["x", {"array": {"row": {"name": "y", "type": {"varchar": {}}}}}]}}}
        self.assertEqual(result, expected)

    def test_issue_62_structuralB(self):
        sql = """SELECT CAST(x AS ROW(y ARRAY(VARCHAR)))"""
        result = parse(sql)
        expected = {"select": {"value": {"cast": ["x", {"row": {"name": "y", "type": {"array": {"varchar": {}}}}}]}}}
        self.assertEqual(result, expected)

    def test_issue_62_structuralC(self):
        sql = """SELECT CAST(x AS ARRAY(ARRAY(VARCHAR)))"""
        result = parse(sql)
        expected = {"select": {"value": {"cast": ["x", {"array": {"array": {"varchar": {}}}}]}}}
        self.assertEqual(result, expected)

    def test_issue_85_json_type(self):
        sql = "SELECT CAST(x AS JSON)"
        result = parse(sql)
        expected = {"select": {"value": {"cast": ["x", {"json": {}}]}}}
        self.assertEqual(result, expected)

    def test_issue_92_empty_array(self):
        sql = "SELECT ARRAY[]"
        result = parse(sql)
        expected = {"select": {"value": {"create_array": {}}}}
        self.assertEqual(result, expected)

    def test_issue_93_order_by_parameter1(self):
        sql = "SELECT FOO(a ORDER BY b)"
        result = parse(sql)
        expected = {"select": {"value": {"foo": "a", "orderby": {"value": "b"}}}}
        self.assertEqual(result, expected)

    def test_issue_93_order_by_parameter2(self):
        sql = "SELECT FOO(a ORDER BY b)"
        result = parse(sql, calls=normal_op)  # normal_op FOR BETTER OUTPUT CLARITY
        expected = {"select": {"value": {"op": "foo", "args": ["a"], "kwargs": {"orderby": {"value": "b"}}}}}
        self.assertEqual(result, expected)

    def test_issue_125_pivot_identifier1(self):
        sql = """SELECT * FROM pivot;"""
        result = parse(sql)
        expected = {"from": "pivot", "select": {"all_columns": {}}}
        self.assertEqual(result, expected)

    def test_issue_125_pivot_identifier2(self):
        sql = """SELECT * FROM a AS pivot;"""
        result = parse(sql)
        expected = {"from": {"name": "pivot", "value": "a"}, "select": {"all_columns": {}}}
        self.assertEqual(result, expected)

    def test_issue_125_pivot_identifier3(self):
        sql = """SELECT * FROM UNNEST(ARRAY[1, 2, 3]) AS pivot(n);"""
        result = parse(sql)
        expected = {
            "from": {"name": {"pivot": "n"}, "value": {"unnest": {"create_array": [1, 2, 3]}}},
            "select": {"all_columns": {}},
        }
        self.assertEqual(result, expected)

    def test_issue_125_pivot_identifier4(self):
        sql = """SELECT * FROM UNNEST(ARRAY[1, 2, 3]) AS pivot(n)
        JOIN a ON a.id = pivot.n;"""
        result = parse(sql)
        expected = {
            "from": [
                {"name": {"pivot": "n"}, "value": {"unnest": {"create_array": [1, 2, 3]}}},
                {"join": "a", "on": {"eq": ["a.id", "pivot.n"]}},
            ],
            "select": {"all_columns": {}},
        }
        self.assertEqual(result, expected)

    def test_issue_125_unpivot_identifier1(self):
        sql = """SELECT * FROM unpivot;"""
        result = parse(sql)
        expected = {"from": "unpivot", "select": {"all_columns": {}}}
        self.assertEqual(result, expected)

    def test_issue_125_unpivot_identifier2(self):
        sql = """SELECT * FROM a AS unpivot;"""
        result = parse(sql)
        expected = {"from": {"name": "unpivot", "value": "a"}, "select": {"all_columns": {}}}
        self.assertEqual(result, expected)

    def test_issue_125_unpivot_identifier3(self):
        sql = """SELECT * FROM UNNEST(ARRAY[1, 2, 3]) AS unpivot(n);"""
        result = parse(sql)
        expected = {
            "from": {"name": {"unpivot": "n"}, "value": {"unnest": {"create_array": [1, 2, 3]}}},
            "select": {"all_columns": {}},
        }
        self.assertEqual(result, expected)

    def test_issue_125_unpivot_identifier4(self):
        sql = """SELECT * FROM UNNEST(ARRAY[1, 2, 3]) AS unpivot(n)
        JOIN a ON a.id = pivot.n;"""
        result = parse(sql)
        expected = {
            "from": [
                {"name": {"unpivot": "n"}, "value": {"unnest": {"create_array": [1, 2, 3]}}},
                {"join": "a", "on": {"eq": ["a.id", "pivot.n"]}},
            ],
            "select": {"all_columns": {}},
        }
        self.assertEqual(result, expected)
