import mysql.connector
from mysql.connector import errorcode

class DBConnection:
    def __init__(self, host, user, password, database):
        try:
            self.conn = mysql.connector.connect(
                host=host,
                user=user,
                password=password,
                connection_timeout=30  # 30-second timeout for connection
            )
            self.cursor = self.conn.cursor()
            self.cursor.execute(f"CREATE DATABASE IF NOT EXISTS {database}")
            self.cursor.execute(f"USE {database}")
            self.conn.database = database
        except mysql.connector.Error as err:
            raise Exception(f"Connection error: {err}")

    def execute_query(self, query, params=None):
        try:
            # Set a query timeout (MySQL-specific)
            self.cursor.execute("SET SESSION max_execution_time = 30000")  # 30 seconds in milliseconds
            self.cursor.execute(query, params or ())
            if query.strip().upper().startswith('SELECT'):
                result = self.cursor.fetchall()
                columns = [desc[0] for desc in self.cursor.description]
                return {"rows": result, "columns": columns}
            self.conn.commit()
            return None
        except mysql.connector.Error as err:
            raise err

    def get_schemas(self):
        self.cursor.execute("SHOW SCHEMAS")
        return [row[0] for row in self.cursor.fetchall() if row[0] not in ['information_schema', 'mysql', 'performance_schema', 'sys', self.conn.database]]

    def get_tables(self, schema):
        self.cursor.execute(f"SHOW TABLES FROM {schema}")
        return [row[0] for row in self.cursor.fetchall()]

    def get_columns(self, schema, table):
        self.cursor.execute(f"SHOW COLUMNS FROM {schema}.{table}")
        return [row[0] for row in self.cursor.fetchall()]

    def close(self):
        self.cursor.close()
        self.conn.close()