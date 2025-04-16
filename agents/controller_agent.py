from agents.query_parser_agent import QueryParserAgent
from agents.sql_executor_agent import SQLExecutorAgent
from agents.feedback_agent import FeedbackAgent
from database.history_manager import HistoryManager
from database.db_connection import DBConnection
import streamlit as st
from utils.logger import Logger
import re

class ControllerAgent:
    def __init__(self):
        self.parser = QueryParserAgent()
        self.executor = SQLExecutorAgent()
        self.feedback = FeedbackAgent()
        self.history = HistoryManager()
        self.logger = Logger()

    def process_query(self, user_input, schema_name):
        self.logger.debug(f"Starting process_query for input: {user_input}")
        
        sql_query = self.parser.parse_query(user_input, schema_name)
        self.logger.debug(f"Parsed SQL query: {sql_query}")
        
        if sql_query.startswith("CLARIFY:"):
            self.logger.debug("Query needs clarification")
            return {"status": "clarification_needed", "message": sql_query[8:]}
        
        if "delete" in sql_query.lower() or "update" in sql_query.lower() or "alter" in sql_query.lower():
            self.logger.debug("Query requires confirmation")
            st.session_state.confirm_needed = True
            st.session_state.pending_query = {"input": user_input, "sql": sql_query}
            return {"status": "confirmation_needed", "sql_query": sql_query}
        
        try:
            affected_rows = None
            table_name = None
            if sql_query.lower().startswith("update"):
                self.logger.debug("Capturing prior state for UPDATE query")
                match = re.match(r"update\s+(\w+\.\w+|\w+)\s+set\s+.*?\s*(where\s+.*)?$", sql_query.lower(), re.IGNORECASE)
                if match:
                    table_name = match.group(1)
                    where_clause = match.group(2) if match.group(2) else ""
                    
                    select_query = f"SELECT * FROM {table_name} {where_clause}"
                    db = DBConnection(**st.session_state.db_params)
                    try:
                        self.logger.debug(f"Executing SELECT for prior state: {select_query}")
                        result = db.execute_query(select_query)
                        affected_rows = result["rows"] if result else []
                        self.logger.debug(f"Retrieved {len(affected_rows)} rows for prior state")
                    finally:
                        db.close()

            self.logger.debug("Executing the main query")
            result = self.executor.execute(sql_query, schema_name)
            
            version_id = self.history.save_query(user_input, sql_query, schema_name, affected_rows, table_name)
            self.logger.debug(f"Saved query to history with version_id: {version_id}")
            
            self.logger.debug("Query processing completed successfully")
            return {
                "status": "success",
                "result": result,
                "sql_query": sql_query,
                "learning_output": f"For your request: '{user_input}'\nGenerated SQL: {sql_query}",
                "version_id": version_id
            }
        except Exception as e:
            self.logger.error(f"Error executing query: {str(e)}")
            return {"status": "error", "message": f"Error executing query: {str(e)}"}

    def revert_to_version(self, version_id):
        self.logger.debug(f"Starting revert_to_version for version_id: {version_id}")
        
        sql_query = self.history.get_query_by_version(version_id)
        if not sql_query:
            self.logger.error(f"Version {version_id} not found")
            return {"status": "error", "message": f"Version {version_id} not found"}
        
        history = self.history.get_history()
        schema_name = None
        for entry in history:
            if entry[0] == version_id:
                schema_name = entry[4]
                break
        
        if not schema_name:
            self.logger.error("Schema name not found for this version")
            return {"status": "error", "message": "Schema name not found for this version"}

        if sql_query.lower().startswith("update"):
            self.logger.debug("Reverting an UPDATE query")
            table_name, prior_state = self.history.get_prior_state(version_id)
            if not prior_state:
                self.logger.error("Cannot revert UPDATE: Prior state not available")
                return {"status": "error", "message": "Cannot revert UPDATE: Prior state not available"}

            inverse_queries = []
            db = DBConnection(**st.session_state.db_params)
            try:
                self.logger.debug("Fetching columns for table")
                columns = db.get_columns(schema_name, table_name.split(".")[-1])
                if len(columns) != len(prior_state[0]):
                    self.logger.error("Cannot revert UPDATE: Column count mismatch")
                    return {"status": "error", "message": "Cannot revert UPDATE: Column count mismatch"}
                
                self.logger.debug(f"Generating inverse queries for {len(prior_state)} rows")
                for row in prior_state:
                    set_clause = ", ".join([f"{col} = %s" for col in columns])
                    values = list(row)
                    where_clause = f"{columns[0]} = %s"
                    where_value = row[0]
                    
                    inverse_query = f"UPDATE {table_name} SET {set_clause} WHERE {where_clause}"
                    inverse_queries.append((inverse_query, values + [where_value]))
                    self.logger.debug(f"Generated inverse query: {inverse_query}")
                
                self.logger.debug("Executing inverse queries")
                for inverse_query, params in inverse_queries:
                    self.logger.debug(f"Executing: {inverse_query} with params {params}")
                    db.execute_query(inverse_query, params)
                
                self.logger.debug("Revert completed successfully")
                return {
                    "status": "success",
                    "message": f"Reverted version {version_id} by restoring prior state",
                    "sql_query": sql_query,
                    "inverse_query": "; ".join([q[0] for q in inverse_queries])
                }
            except Exception as e:
                self.logger.error(f"Error reverting version {version_id}: {str(e)}")
                return {"status": "error", "message": f"Error reverting version {version_id}: {str(e)}"}
            finally:
                db.close()

        self.logger.debug("Reverting a non-UPDATE query")
        inverse_query = self.parser.generate_inverse_query(sql_query, schema_name)
        if inverse_query.startswith("CLARIFY:"):
            self.logger.error(inverse_query[8:])
            return {"status": "error", "message": inverse_query[8:]}

        try:
            self.logger.debug(f"Executing inverse query: {inverse_query}")
            db = DBConnection(**st.session_state.db_params)
            db.execute_query(inverse_query)
            self.logger.debug("Inverse query executed successfully")
            return {
                "status": "success",
                "message": f"Reverted version {version_id} by executing inverse query: {inverse_query}",
                "sql_query": sql_query,
                "inverse_query": inverse_query
            }
        except Exception as e:
            self.logger.error(f"Error reverting version {version_id}: {str(e)}")
            return {"status": "error", "message": f"Error reverting version {version_id}: {str(e)}"}
        finally:
            db.close()