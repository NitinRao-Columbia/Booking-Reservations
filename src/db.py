from typing import Any, Dict, List, Tuple, Union

import pymysql

# Type definitions
# Key-value pairs
KV = Dict[str, Any]
# A Query consists of a string (possibly with placeholders) and a list of values to be put in the placeholders
Query = Tuple[str, List]

class DB:
    def __init__(self, host: str, port: int, user: str, password: str, database: str):
        conn = pymysql.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database,
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=True,
        )
        self.conn = conn

    def get_cursor(self):
        return self.conn.cursor()

    def execute_query(self, query: str, args: List, ret_result: bool) -> Union[List[KV], int]:
        """Executes a query.

        :param query: A query string, possibly containing %s placeholders
        :param args: A list containing the values for the %s placeholders
        :param ret_result: If True, execute_query returns a list of dicts, each representing a returned
                          row from the table. If False, the number of rows affected is returned. Note
                          that the length of the list of dicts is not necessarily equal to the number
                          of rows affected.
        :returns: a list of dicts or a number, depending on ret_result
        """
        cur = self.get_cursor()
        count = cur.execute(query, args=args)
        if ret_result:
            return cur.fetchall()
        else:
            return count

    # TODO: all methods below

    @staticmethod
    def build_select_query(table: str, rows: List[str], filters: KV, limit: int = None, offset: int = None) -> Tuple[str, List[Any]]:
        """
        Builds a query that selects rows with optional limit and offset.

        :param table: The table to be selected from
        :param rows: The attributes to select. If empty, then selects all rows.
        :param filters: Key-value pairs that the rows from table must satisfy
        :param limit: The maximum number of rows to return
        :param offset: The number of rows to skip before starting to return rows
        :returns: A query string and any placeholder arguments
        """
        # Select specific columns or all columns if rows is empty
        columns = ', '.join(rows) if rows else '*'

        # Build WHERE clause and values list
        where_clauses = [f"{key} = %s" for key in filters]
        values = list(filters.values())
        where_statement = ' AND '.join(where_clauses)

        # Construct the basic query
        query = f"SELECT {columns} FROM {table}"
        if where_clauses:
            query += f" WHERE {where_statement}"

        # Add LIMIT and OFFSET if they are specified
        if limit is not None:
            query += f" LIMIT %s"
            values.append(limit)
        if offset is not None:
            query += f" OFFSET %s"
            values.append(offset)

        return query, values

    def select(self, table: str, rows: List[str], filters: KV, limit: int = None, offset: int = None) -> List[KV]:
        """
        Runs a select statement with optional limit and offset.

        :param table: The table to be selected from
        :param rows: The attributes to select. If empty, then selects all rows.
        :param filters: Key-value pairs that the rows to be selected must satisfy
        :param limit: The maximum number of rows to return
        :param offset: The number of rows to skip before starting to return rows
        :returns: The selected rows
        """
        # Build the query with the new limit and offset arguments
        query, args = self.build_select_query(table, rows, filters, limit, offset)
        # Execute the query
        return self.execute_query(query, args, True)

    @staticmethod
    def build_insert_query(table: str, values: KV) -> Query:
        """Builds a query that inserts a row. See db_test for examples.

        :param table: The table to be inserted into
        :param values: Key-value pairs that represent the values to be inserted
        :returns: A query string and any placeholder arguments
        """
        query_base = "INSERT INTO {table} ".format(table=table)

        columns = []
        vals = []
        value_str = "("
        for key, value in values.items():
            columns.append(key)
            vals.append(value)
            value_str += "%s, "

        value_str = value_str[:-2] + ")"

        query_base += "(" + ", ".join(columns) + ") VALUES " + value_str

        return query_base, vals

    def insert(self, table: str, values: KV) -> int:
        """Runs an insert statement. You should use build_insert_query and execute_query.

        :param table: The table to be inserted into
        :param values: Key-value pairs that represent the values to be inserted
        :returns: The number of rows affected
        """
        query, args = self.build_insert_query(table, values)

        return self.execute_query(query, args, False)

    @staticmethod
    def build_update_query(table: str, values: KV, filters: KV) -> Query:
        """Builds a query that updates rows. See db_test for examples.

        :param table: The table to be updated
        :param values: Key-value pairs that represent the new values
        :param filters: Key-value pairs that the rows from table must satisfy
        :returns: A query string and any placeholder arguments
        """
        query_base = "UPDATE {table} SET ".format(table=table)

        clauses = []
        vals = []
        for key, value in values.items():
            clauses.append(f"{key} = %s")
            vals.append(value)

        query_base += ", ".join(clauses)

        if filters:
            query_base += " WHERE "
            where_clauses = []
            for key, value in filters.items():
                where_clauses.append(f"{key} = %s")
                vals.append(value)

            query_base += " AND ".join(where_clauses)

        return query_base, vals

    def update(self, table: str, values: KV, filters: KV) -> int:
        """Runs an update statement. You should use build_update_query and execute_query.

        :param table: The table to be updated
        :param values: Key-value pairs that represent the new values
        :param filters: Key-value pairs that the rows to be updated must satisfy
        :returns: The number of rows affected
        """
        query, args = self.build_update_query(table, values, filters)

        return self.execute_query(query, args, False)

    @staticmethod
    def build_delete_query(table: str, filters: KV) -> Query:
        """Builds a query that deletes rows. See db_test for examples.

        :param table: The table to be deleted from
        :param filters: Key-value pairs that the rows to be deleted must satisfy
        :returns: A query string and any placeholder arguments
        """
        query_base = "DELETE FROM {}".format(table)
        where_clauses = []
        values = []
        if filters:
            query_base += " WHERE "

        for key, value in filters.items():
            where_clauses.append(f"{key} = %s")
            values.append(value)

        wheres = " AND ".join(where_clauses)

        query_base += wheres

        return query_base, values

    def delete(self, table: str, filters: KV) -> int:
        """Runs a delete statement. You should use build_delete_query and execute_query.

        :param table: The table to be deleted from
        :param filters: Key-value pairs that the rows to be deleted must satisfy
        :returns: The number of rows affected
        """
        query, args = self.build_delete_query(table, filters)

        return self.execute_query(query, args, False)
