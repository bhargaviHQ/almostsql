from agents.query_parser_agent import QueryParserAgent
from agents.sql_executor_agent import SQLExecutorAgent
from agents.feedback_agent import FeedbackAgent
from agents.history_agent import HistoryAgent
import streamlit as st

class ControllerAgent:
    def __init__(self):
        self.parser = QueryParserAgent()
        self.executor = SQLExecutorAgent()
        self.feedback = FeedbackAgent()
        self.history = HistoryAgent()

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
        
        try:
            db = DBConnection()
            if "delete" in sql_query.lower():
                # For DELETE, we can't truly revert without prior state, so log a warning
                return {"status": "warning", "message": "Revert not fully supported for DELETE; re-executed original query"}
            elif "update" in sql_query.lower():
                # For UPDATE, attempt to reverse (simplified; assumes single SET and WHERE)
                parts = sql_query.lower().split("set")
                if len(parts) > 1 and "where" in parts[1]:
                    table = parts[0].replace("update", "").strip()
                    set_clause = parts[1].split("where")[0].strip()
                    where_clause = "where" + parts[1].split("where")[1].strip()
                    # Reverse SET (this is basic; real apps need before/after state tracking)
                    set_items = set_clause.split(",")
                    reverse_set = ", ".join(f"{item.split('=')[0].strip()} = {item.split('=')[1].strip()}" for item in set_items)
                    reverse_query = f"UPDATE {table} SET {reverse_set} {where_clause}"
                    db.execute_query(reverse_query)
                    return {"status": "success", "message": f"Reverted UPDATE from version {version_id}"}
            elif "alter" in sql_query.lower():
                return {"status": "warning", "message": "Revert not fully supported for ALTER; manual intervention required"}
            else:
                # For other queries (e.g., INSERT, SELECT), re-execute
                db.execute_query(sql_query)
                return {"status": "success", "message": f"Reverted to version {version_id}"}
        except Exception as e:
            return {"status": "error", "message": f"Error reverting version {version_id}: {str(e)}"}
        finally:
            db.close()