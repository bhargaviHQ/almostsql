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
            # Capture state before execution
            operation_type, table_name, state_data, state_error = self.history.capture_state(sql_query, schema_name)
            if state_error:
                self.logger.error(state_error)
                return {"status": "error", "message": state_error}

            self.logger.debug("Executing the main query")
            result = self.executor.execute(sql_query, schema_name)
            
            version_id = self.history.save_query(user_input, sql_query, schema_name, operation_type, table_name, state_data)
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
        
        operation_type, table_name, state_data = self.history.get_state_data(version_id)
        schema_name = None
        history = self.history.get_history()
        for entry in history:
            if entry[0] == version_id:
                schema_name = entry[4]
                break
        
        if not schema_name:
            self.logger.error("Schema name not found for this version")
            return {"status": "error", "message": "Schema name not found for this version"}

        db = DBConnection(**st.session_state.db_params)
        try:
            if operation_type == "UPDATE" and state_data:
                self.logger.debug("Reverting an UPDATE query")
                columns = db.get_columns(schema_name, table_name.split(".")[-1])
                if len(columns) != len(state_data[0]):
                    self.logger.error("Cannot revert UPDATE: Column count mismatch")
                    return {"status": "error", "message": "Cannot revert UPDATE: Column count mismatch"}
                
                inverse_queries = []
                for row in state_data:
                    set_clause = ", ".join([f"{col} = %s" for col in columns])
                    values = list(row)
                    where_clause = f"{columns[0]} = %s"
                    where_value = row[0]
                    
                    inverse_query = f"UPDATE {table_name} SET {set_clause} WHERE {where_clause}"
                    inverse_queries.append((inverse_query, values + [where_value]))
                    self.logger.debug(f"Generated inverse query: {inverse_query}")
                
                for inverse_query, params in inverse_queries:
                    self.logger.debug(f"Executing: {inverse_query} with params {params}")
                    db.execute_query(inverse_query, params)
                
                return {
                    "status": "success",
                    "message": f"Reverted version {version_id} by restoring prior state",
                    "sql_query": sql_query,
                    "inverse_query": "; ".join([q[0] for q in inverse_queries])
                }
            
            elif operation_type == "INSERT" and state_data:
                self.logger.debug("Reverting an INSERT query")
                # Assume primary key is the first column
                columns = db.get_columns(schema_name, table_name.split(".")[-1])
                select_query = f"SELECT {columns[0]} FROM {table_name}"  # Fetch inserted IDs
                result = db.execute_query(select_query)
                inserted_ids = [row[0] for row in result["rows"]]
                
                inverse_query = f"DELETE FROM {table_name} WHERE {columns[0]} IN ({','.join(['%s'] * len(inserted_ids))})"
                db.execute_query(inverse_query, inserted_ids)
                
                return {
                    "status": "success",
                    "message": f"Reverted version {version_id} by deleting inserted rows",
                    "sql_query": sql_query,
                    "inverse_query": inverse_query
                }
            
            elif operation_type == "DELETE" and state_data:
                self.logger.debug("Reverting a DELETE query")
                columns = db.get_columns(schema_name, table_name.split(".")[-1])
                inverse_queries = []
                for row in state_data:
                    insert_query = f"INSERT INTO {table_name} ({','.join(columns)}) VALUES ({','.join(['%s'] * len(row))})"
                    inverse_queries.append((insert_query, row))
                    self.logger.debug(f"Generated inverse query: {insert_query}")
                
                for inverse_query, params in inverse_queries:
                    db.execute_query(inverse_query, params)
                
                return {
                    "status": "success",
                    "message": f"Reverted version {version_id} by re-inserting deleted rows",
                    "sql_query": sql_query,
                    "inverse_query": "; ".join([q[0] for q in inverse_queries])
                }
            
            elif operation_type == "DROP_TABLE" and state_data:
                self.logger.debug("Reverting a DROP TABLE query")
                columns = state_data["columns"]
                column_types = state_data["column_types"]
                create_query = f"CREATE TABLE {table_name} ({','.join([f'{col} {typ}' for col, typ in zip(columns, column_types)])})"
                db.execute_query(create_query)
                
                if state_data["data"]:
                    for row in state_data["data"]:
                        insert_query = f"INSERT INTO {table_name} ({','.join(columns)}) VALUES ({','.join(['%s'] * len(row))})"
                        db.execute_query(insert_query, row)
                
                return {
                    "status": "success",
                    "message": f"Reverted version {version_id} by recreating table",
                    "sql_query": sql_query,
                    "inverse_query": create_query
                }
            
            elif operation_type == "ALTER" and state_data:
                self.logger.debug("Reverting an ALTER query (column rename)")
                inverse_query = f"ALTER TABLE {table_name} RENAME COLUMN {state_data['new_column']} TO {state_data['old_column']}"
                db.execute_query(inverse_query)
                
                return {
                    "status": "success",
                    "message": f"Reverted version {version_id} by restoring column name",
                    "sql_query": sql_query,
                    "inverse_query": inverse_query
                }
            
            # Fallback to inverse query generation
            self.logger.debug("Falling back to inverse query generation")
            inverse_query = self.parser.generate_inverse_query(sql_query, schema_name)
            if inverse_query.startswith("CLARIFY:"):
                self.logger.error(inverse_query[8:])
                return {"status": "error", "message": inverse_query[8:]}
            
            db.execute_query(inverse_query)
            return {
                "status": "success",
                "message": f"Reverted version {version_id} by executing inverse query",
                "sql_query": sql_query,
                "inverse_query": inverse_query
            }
        except Exception as e:
            self.logger.error(f"Error reverting version {version_id}: {str(e)}")
            return {"status": "error", "message": f"Error reverting version {version_id}: {str(e)}"}
        finally:
            db.close()