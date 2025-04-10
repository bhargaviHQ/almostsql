from agents.query_parser_agent import QueryParserAgent
from agents.sql_executor_agent import SQLExecutorAgent
from agents.feedback_agent import FeedbackAgent
from database.history_manager import HistoryManager
from database.db_connection import DBConnection
import streamlit as st

class ControllerAgent:
    def __init__(self):
        self.parser = QueryParserAgent()
        self.executor = SQLExecutorAgent()
        self.feedback = FeedbackAgent()
        self.history = HistoryManager()

    def process_query(self, user_input, schema_name):
        sql_query = self.parser.parse_query(user_input, schema_name)
        
        if sql_query.startswith("CLARIFY:"):
            return {"status": "clarification_needed", "message": sql_query[8:]}
        
        if "delete" in sql_query.lower() or "update" in sql_query.lower() or "alter" in sql_query.lower():
            st.session_state.confirm_needed = True
            st.session_state.pending_query = {"input": user_input, "sql": sql_query}
            return {"status": "confirmation_needed", "sql_query": sql_query}
        
        try:
            result = self.executor.execute(sql_query, schema_name)
            version_id = self.history.save_query(user_input, sql_query, schema_name)
            return {
                "status": "success",
                "result": result,
                "sql_query": sql_query,
                "learning_output": f"For your request: '{user_input}'\nGenerated SQL: {sql_query}",
                "version_id": version_id
            }
        except Exception as e:
            return {"status": "error", "message": f"Error executing query: {str(e)}"}

    def revert_to_version(self, version_id):
        sql_query = self.history.get_query_by_version(version_id)
        if not sql_query:
            return {"status": "error", "message": f"Version {version_id} not found"}
        
        # Get the schema name from history to pass to the parser
        history = self.history.get_history()
        schema_name = None
        for entry in history:
            if entry[0] == version_id:
                schema_name = entry[4]  # schema_name is the 5th element
                break
        
        if not schema_name:
            return {"status": "error", "message": "Schema name not found for this version"}

        # Use the LLM to generate the inverse query
        inverse_query = self.parser.generate_inverse_query(sql_query, schema_name)
        if inverse_query.startswith("CLARIFY:"):
            return {"status": "error", "message": inverse_query[8:]}

        try:
            db = DBConnection()
            db.execute_query(inverse_query)
            return {"status": "success", "message": f"Reverted version {version_id} by executing inverse query: {inverse_query}"}
        except Exception as e:
            return {"status": "error", "message": f"Error reverting version {version_id}: {str(e)}"}
        finally:
            db.close()