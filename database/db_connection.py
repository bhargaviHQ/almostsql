import mysql.connector
from mysql.connector import errorcode
from config.config import Config

class DBConnection:
    def __init__(self):
        try:
            self.conn = mysql.connector.connect(
                host=Config.MYSQL_HOST,
                user=Config.MYSQL_USER,
                password=Config.MYSQL_PASSWORD
            )
            self.cursor = self.conn.cursor()  # Default cursor returns tuples
            self.cursor.execute(f"CREATE DATABASE IF NOT EXISTS {Config.MYSQL_DB}")
            self.cursor.execute(f"USE {Config.MYSQL_DB}")
            self.conn.database = Config.MYSQL_DB
        except mysql.connector.Error as err:
            print(f"Connection error: {err}")
            raise

    def execute_query(self, query, params=None):
        try:
            self.cursor.execute(query, params or ())
            if query.strip().upper().startswith('SELECT'):
                result = self.cursor.fetchall()
                columns = [desc[0] for desc in self.cursor.description]  # Get column names
                return {"rows": result, "columns": columns}  # Return dict with rows and columns
            self.conn.commit()
            return None
        except mysql.connector.Error as err:
            raise err

    def get_schemas(self):
        self.cursor.execute("SHOW SCHEMAS")
        return [row[0] for row in self.cursor.fetchall() if row[0] not in ['information_schema', 'mysql', 'performance_schema', 'sys', Config.MYSQL_DB]]

    def get_tables(self, schema):
        self.cursor.execute(f"SHOW TABLES FROM {schema}")
        return [row[0] for row in self.cursor.fetchall()]

    def get_columns(self, schema, table):
        self.cursor.execute(f"SHOW COLUMNS FROM {schema}.{table}")
        return [row[0] for row in self.cursor.fetchall()]

    def close(self):
        self.cursor.close()
        self.conn.close()