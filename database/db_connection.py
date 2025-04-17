import mysql.connector
import streamlit as st

class DBConnection:
    def __init__(self, **db_params):
        self.connection = mysql.connector.connect(**db_params)
        self.connection.autocommit = True
        self.cursor = self.connection.cursor()

    def execute_query(self, query, params=None):
        try:
            if params:
                self.cursor.execute(query, params)
            else:
                self.cursor.execute(query)
            if query.strip().upper().startswith("SELECT"):
                columns = [col[0] for col in self.cursor.description]
                rows = self.cursor.fetchall()
                return {"columns": columns, "rows": rows}
            else:
                self.connection.commit()
                return {"columns": ["AffectedRows"], "rows": [[self.cursor.rowcount]]}
        except Exception as e:
            raise e

    def get_schemas(self):
        self.cursor.execute("SHOW DATABASES")
        return [row[0] for row in self.cursor.fetchall()]

    def get_tables(self, schema_name):
        self.cursor.execute(f"SHOW TABLES FROM {schema_name}")
        return [row[0] for row in self.cursor.fetchall()]

    def get_columns(self, schema_name, table_name):
        self.cursor.execute(f"SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s", (schema_name, table_name))
        return [row[0] for row in self.cursor.fetchall()]

    def close(self):
        self.cursor.close()
        self.connection.close()