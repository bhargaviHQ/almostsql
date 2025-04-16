from database.db_connection import DBConnection
import streamlit as st

class SQLExecutorAgent:
    def execute(self, sql_query, schema_name):
        db = DBConnection(**st.session_state.db_params)
        try:
            result = db.execute_query(sql_query)
            if result is not None:
                return result
            return "Query executed successfully"
        finally:
            db.close()