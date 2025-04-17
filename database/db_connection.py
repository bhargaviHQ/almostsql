import mysql.connector
import streamlit as st

class DBConnection:
    def __init__(self, **db_params):
        self.connection = mysql.connector.connect(**db_params)
        self.connection.autocommit = True
        self.cursor = self.connection.cursor()

    def reset_cursor(self):
        """Reset cursor state by consuming unread results and creating a new cursor."""
        try:
            while self.cursor.nextset():  # Consume any remaining result sets
                pass
            self.cursor.close()
        except:
            pass
        self.cursor = self.connection.cursor()

    def execute_query(self, query, params=None):
        try:
            # Reset cursor to clear any unread results
            self.reset_cursor()
            
            if params:
                self.cursor.execute(query, params)
            else:
                self.cursor.execute(query)
            
            # Check if the query produced a result set
            if self.cursor.description:  # Query has results (e.g., SELECT)
                columns = [col[0] for col in self.cursor.description]
                rows = self.cursor.fetchall()
                # Ensure all results are consumed
                while self.cursor.nextset():
                    pass
                return {"columns": columns, "rows": rows}
            else:  # No result set (e.g., INSERT, UPDATE, DELETE)
                self.connection.commit()
                return {"columns": ["AffectedRows"], "rows": [[self.cursor.rowcount]]}
        except Exception as e:
            self.reset_cursor()  # Reset cursor on error to prevent lingering results
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

    def get_column_keys(self, schema_name, table_name):
        try:
            key_info = {}
            # Get primary keys
            self.cursor.execute(f"""
                SELECT COLUMN_NAME
                FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
                WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s AND CONSTRAINT_NAME = 'PRIMARY'
            """, (schema_name, table_name))
            pk_columns = [row[0] for row in self.cursor.fetchall()]
            
            # Get foreign keys
            self.cursor.execute(f"""
                SELECT COLUMN_NAME
                FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
                WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s AND REFERENCED_TABLE_NAME IS NOT NULL
            """, (schema_name, table_name))
            fk_columns = [row[0] for row in self.cursor.fetchall()]
            
            # Get indexes (non-unique and unique, excluding PK/FK)
            self.cursor.execute(f"""
                SELECT COLUMN_NAME
                FROM INFORMATION_SCHEMA.STATISTICS
                WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
                AND INDEX_NAME != 'PRIMARY'
            """, (schema_name, table_name))
            index_columns = [row[0] for row in self.cursor.fetchall()]
            
            # Combine key information
            for col in set(pk_columns + fk_columns + index_columns):
                key_info[col] = []
                if col in pk_columns:
                    key_info[col].append("PRIMARY KEY")
                if col in fk_columns:
                    key_info[col].append("FOREIGN KEY")
                if col in index_columns:
                    key_info[col].append("INDEX")
            
            return key_info
        except Exception as e:
            raise Exception(f"Error fetching column keys: {e}")

    def close(self):
        self.cursor.close()
        self.connection.close()