from database.db_connection import DBConnection
import streamlit as st
import json
import re
from datetime import date, datetime

class HistoryManager:
    def __init__(self):
        self.db = DBConnection(**st.session_state.db_params)
        self.schema_updated = False
        self.create_history_table()
        self.create_state_history_table()
        self.update_state_history_schema()

    def _serialize_state_data(self, data):
        """Recursively convert non-JSON-serializable objects to strings."""
        if isinstance(data, (date, datetime)):
            return data.isoformat()
        elif isinstance(data, list):
            return [self._serialize_state_data(item) for item in data]
        elif isinstance(data, dict):
            return {key: self._serialize_state_data(value) for key, value in data.items()}
        return data

    def create_history_table(self):
        query = """
        CREATE TABLE IF NOT EXISTS query_history (
            version_id INT AUTO_INCREMENT PRIMARY KEY,
            user_query TEXT,
            sql_query TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            schema_name VARCHAR(255)
        )
        """
        self.db.execute_query(query)

    def create_state_history_table(self):
        query = """
        CREATE TABLE IF NOT EXISTS query_state_history (
            version_id INT,
            operation_type VARCHAR(50),
            table_name VARCHAR(255),
            state_data JSON,
            PRIMARY KEY (version_id),
            FOREIGN KEY (version_id) REFERENCES query_history(version_id) ON DELETE CASCADE
        )
        """
        self.db.execute_query(query)

    def update_state_history_schema(self):
        if self.schema_updated:
            return
        query = """
        SELECT COLUMN_NAME 
        FROM INFORMATION_SCHEMA.COLUMNS 
        WHERE TABLE_NAME = 'query_state_history' 
        AND COLUMN_NAME = 'operation_type'
        """
        result = self.db.execute_query(query)
        if not result or not result["rows"]:
            alter_query = """
            ALTER TABLE query_state_history 
            ADD COLUMN operation_type VARCHAR(50) AFTER version_id,
            ADD COLUMN state_data JSON AFTER table_name
            """
            self.db.execute_query(alter_query)
        self.schema_updated = True

    def save_query(self, user_query, sql_query, schema_name, operation_type=None, table_name=None, state_data=None):
        query = "INSERT INTO query_history (user_query, sql_query, schema_name) VALUES (%s, %s, %s)"
        self.db.execute_query(query, (user_query, sql_query, schema_name))
        version_id = self.db.cursor.lastrowid

        if operation_type and table_name and state_data is not None:
            query = "INSERT INTO query_state_history (version_id, operation_type, table_name, state_data) VALUES (%s, %s, %s, %s)"
            serialized_data = self._serialize_state_data(state_data)
            self.db.execute_query(query, (version_id, operation_type, table_name, json.dumps(serialized_data)))

        return version_id
    
    def get_history(self):
        query = "SELECT version_id, user_query, sql_query, timestamp, schema_name FROM query_history ORDER BY version_id DESC"
        result = self.db.execute_query(query)
        if result and result.get("rows"):
            history = []
            for row in result["rows"]:
                # Ensure row has at least 5 elements; pad with None if necessary
                row = list(row) + [None] * (5 - len(row))
                # Serialize timestamp (row[3])
                timestamp = row[3]
                if isinstance(timestamp, (date, datetime)):  # Fixed: Use date and datetime directly
                    timestamp = timestamp.isoformat()
                elif timestamp is None:
                    timestamp = None
                # Else, keep as is (e.g., if already a string)
                history.append((row[0], row[1], row[2], timestamp, row[4]))
            return history
        return []
    def get_query_by_version(self, version_id):
        query = "SELECT sql_query FROM query_history WHERE version_id = %s"
        result = self.db.execute_query(query, (version_id,))
        return result["rows"][0][0] if result and result["rows"] else None

    def get_state_data(self, version_id):
        query = "SELECT operation_type, table_name, state_data FROM query_state_history WHERE version_id = %s"
        result = self.db.execute_query(query, (version_id,))
        if result and result["rows"]:
            operation_type, table_name, state_data_json = result["rows"][0]
            state_data = json.loads(state_data_json)
            return operation_type, table_name, self._serialize_state_data(state_data)  # Serialize again
        return None, None, None

    def clear_history(self):
        query = "DELETE FROM query_history"
        self.db.execute_query(query)
        self.db.execute_query("ALTER TABLE query_history AUTO_INCREMENT = 1")

    def capture_state(self, sql_query, schema_name):
        sql_query_lower = sql_query.lower().strip()
        db = self.db
        operation_type = None
        table_name = None
        state_data = None

        if sql_query_lower.startswith("update"):
            operation_type = "UPDATE"
            match = re.match(r"update\s+(\w+\.\w+|\w+)\s+set\s+.*?\s*(where\s+.*)?$", sql_query_lower, re.IGNORECASE)
            if match:
                table_name = match.group(1)
                where_clause = match.group(2) if match.group(2) else ""
                select_query = f"SELECT * FROM {table_name} {where_clause} LIMIT 100"
                try:
                    result = db.execute_query(select_query)
                    state_data = result["rows"] if result else []
                    state_data = self._serialize_state_data(state_data)  # Serialize state_data
                except Exception as e:
                    db.reset_cursor()  # Reset cursor on error
                    return None, None, None, f"Failed to capture state for UPDATE: {str(e)}"
                finally:
                    db.reset_cursor()  # Ensure cursor is clean
                    
        elif sql_query_lower.startswith("insert"):
            operation_type = "INSERT"
            match = re.match(r"insert\s+into\s+(\w+\.\w+|\w+)\s+", sql_query_lower, re.IGNORECASE)
            if match:
                table_name = match.group(1)
                state_data = {"inserted": True}
                state_data = self._serialize_state_data(state_data)  # Serialize state_data
            
        elif sql_query_lower.startswith("delete"):
            operation_type = "DELETE"
            match = re.match(r"delete\s+from\s+(\w+\.\w+|\w+)\s*(where\s+.*)?$", sql_query_lower, re.IGNORECASE)
            if match:
                table_name = match.group(1)
                where_clause = match.group(2) if match.group(2) else ""
                select_query = f"SELECT * FROM {table_name} {where_clause} LIMIT 100"
                try:
                    result = db.execute_query(select_query)
                    state_data = result["rows"] if result else []
                    state_data = self._serialize_state_data(state_data)  # Serialize state_data
                except Exception as e:
                    db.reset_cursor()  # Reset cursor on error
                    return None, None, None, f"Failed to capture state for DELETE: {str(e)}"
                finally:
                    db.reset_cursor()  # Ensure cursor is clean
            
        elif sql_query_lower.startswith("drop table"):
            operation_type = "DROP_TABLE"
            match = re.match(r"drop\s+table\s+(\w+\.\w+|\w+)", sql_query_lower, re.IGNORECASE)
            if match:
                table_name = match.group(1)
                try:
                    columns = db.get_columns(schema_name, table_name.split(".")[-1])
                    select_query = f"SELECT * FROM {table_name}"
                    result = db.execute_query(select_query)
                    # Fetch column types using execute_query
                    col_query = f"SHOW COLUMNS FROM {table_name}"
                    col_result = db.execute_query(col_query)
                    column_types = [row[1] for row in col_result["rows"]]
                    state_data = {
                        "columns": columns,
                        "data": result["rows"] if result else [],
                        "column_types": column_types
                    }
                    state_data = self._serialize_state_data(state_data)  # Serialize state_data
                except Exception as e:
                    db.reset_cursor()  # Reset cursor on error
                    return None, None, None, f"Failed to capture state for DROP TABLE: {str(e)}"
                finally:
                    db.reset_cursor()  # Ensure cursor is clean
            
        elif sql_query_lower.startswith("alter table"):
            operation_type = "ALTER"
            match = re.match(r"alter\s+table\s+(\w+\.\w+|\w+)\s+rename\s+column\s+(\w+)\s+to\s+(\w+)", sql_query_lower, re.IGNORECASE)
            if match:
                table_name = match.group(1)
                old_col = match.group(2)
                new_col = match.group(3)
                try:
                    columns = db.get_columns(schema_name, table_name.split(".")[-1])
                    if not columns:
                        return None, None, None, f"Failed to capture state for ALTER: No columns found in {table_name}"
                    state_data = {"old_column": old_col, "new_column": new_col, "columns": columns}
                    state_data = self._serialize_state_data(state_data)  # Serialize state_data
                except Exception as e:
                    db.reset_cursor()  # Reset cursor on error
                    return None, None, None, f"Failed to capture state for ALTER: {str(e)}"
                finally:
                    db.reset_cursor()  # Ensure cursor is clean
            else:
                return operation_type, None, None, None  # Allow ALTER to proceed

        return operation_type, table_name, state_data, None