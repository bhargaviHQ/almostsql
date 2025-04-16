from database.db_connection import DBConnection
import streamlit as st
import json

class HistoryManager:
    def __init__(self):
        self.db = DBConnection(**st.session_state.db_params)
        self.create_history_table()
        self.create_state_history_table()

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
            table_name VARCHAR(255),
            affected_rows JSON,
            PRIMARY KEY (version_id),
            FOREIGN KEY (version_id) REFERENCES query_history(version_id) ON DELETE CASCADE
        )
        """
        self.db.execute_query(query)

    def save_query(self, user_query, sql_query, schema_name, affected_rows=None, table_name=None):
        # Save the query to query_history
        query = "INSERT INTO query_history (user_query, sql_query, schema_name) VALUES (%s, %s, %s)"
        self.db.execute_query(query, (user_query, sql_query, schema_name))
        version_id = self.db.cursor.lastrowid

        # If affected_rows and table_name are provided (e.g., for UPDATE), save the prior state
        if affected_rows is not None and table_name:
            query = "INSERT INTO query_state_history (version_id, table_name, affected_rows) VALUES (%s, %s, %s)"
            self.db.execute_query(query, (version_id, table_name, json.dumps(affected_rows)))

        return version_id

    def get_history(self):
        query = "SELECT version_id, user_query, sql_query, timestamp, schema_name FROM query_history ORDER BY version_id DESC"
        result = self.db.execute_query(query)
        if result:
            return [row if len(row) == 5 else (row[0], row[1], row[2], row[3], None) for row in result["rows"]]
        return []

    def get_query_by_version(self, version_id):
        query = "SELECT sql_query FROM query_history WHERE version_id = %s"
        result = self.db.execute_query(query, (version_id,))
        return result["rows"][0][0] if result and result["rows"] else None

    def get_prior_state(self, version_id):
        query = "SELECT table_name, affected_rows FROM query_state_history WHERE version_id = %s"
        result = self.db.execute_query(query, (version_id,))
        if result and result["rows"]:
            table_name, affected_rows_json = result["rows"][0]
            return table_name, json.loads(affected_rows_json)
        return None, None

    def clear_history(self):
        query = "DELETE FROM query_history"  # This will cascade to query_state_history due to foreign key
        self.db.execute_query(query)
        self.db.execute_query("ALTER TABLE query_history AUTO_INCREMENT = 1")