import streamlit as st
from agents.controller_agent import ControllerAgent
from database.db_connection import DBConnection
from config.config import Config
from utils.logger import Logger
import re

def get_available_schemas(db_params):
    db = DBConnection(**db_params)
    try:
        return db.get_schemas()
    finally:
        db.close()

def create_schema(schema_name, db_params):
    db = DBConnection(**db_params)
    try:
        db.execute_query(f"CREATE SCHEMA IF NOT EXISTS {schema_name}")
    finally:
        db.close()

def format_html_table(table_data):
    if isinstance(table_data, str):
        return f"<p>{table_data or 'No results found'}</p>"
    
    # Ensure table_data is a dict with columns and rows
    if not isinstance(table_data, dict) or "columns" not in table_data or "rows" not in table_data:
        return "<p>Invalid result format</p>"
    
    columns = table_data["columns"]
    rows = table_data["rows"]
    
    total_rows = len(rows)
    display_rows = rows[:50] if total_rows > 50 else rows
    row_limit_message = f"<p>Showing top 50 of {total_rows} rows</p>" if total_rows > 50 else ""
    
    html = """
    <style>
    .sql-table-container {
        max-height: 400px;
        overflow-y: auto;
        margin: 20px 0;
        border: 1px solid #ddd;
        border-radius: 5px;
    }
    table {
        width: 100%;
        border-collapse: collapse;
        font-family: 'Courier New', Courier, monospace;
        font-size: 14px;
        text-align: left;
    }
    th, td {
        padding: 10px 15px;
        border: 1px solid #ddd;
    }
    th {
        background-color: #2c3e50;
        color: white;
        position: sticky;
        top: 0;
        z-index: 1;
    }
    td {
        background-color: #fff;
        color: #333;
    }
    tr:nth-child(even) td {
        background-color: #f8f9fa;
    }
    tr:hover td {
        background-color: #e9ecef;
    }
    </style>
    <div class="sql-table-container">
    <table>
    <thead>
    <tr>"""
    html += "".join(f"<th>{col}</th>" for col in columns)
    html += "</tr></thead><tbody>"
    if not display_rows:
        html += "<tr><td colspan='{}' style='text-align: center;'>No data returned</td></tr>".format(len(columns))
    else:
        for row in display_rows:
            html += "<tr>" + "".join(f"<td>{str(val)}</td>" for val in row) + "</tr>"
    html += "</tbody></table></div>"
    html += row_limit_message
    return html

def setup_connection_details():
    st.title("Setup Connection Details")
    st.write("Please provide the following details to connect to the database and LLM service.")

    if "groq_api_key" not in st.session_state:
        st.session_state.groq_api_key = ""
    if "db_host" not in st.session_state:
        st.session_state.db_host = "localhost"
    if "db_user" not in st.session_state:
        st.session_state.db_user = "root"
    if "db_password" not in st.session_state:
        st.session_state.db_password = ""
    if "db_name" not in st.session_state:
        st.session_state.db_name = "sql_chat_db"
    if "connection_setup" not in st.session_state:
        st.session_state.connection_setup = False

    groq_api_key = st.text_input("GROQ API Key", value=st.session_state.groq_api_key, type="password")
    db_host = st.text_input("Database Host", value=st.session_state.db_host)
    db_user = st.text_input("Database User", value=st.session_state.db_user)
    db_password = st.text_input("Database Password", value=st.session_state.db_password, type="password")
    db_name = st.text_input("Database Name", value=st.session_state.db_name)

    if st.button("Save and Proceed"):
        st.session_state.groq_api_key = groq_api_key
        st.session_state.db_host = db_host
        st.session_state.db_user = db_user
        st.session_state.db_password = db_password
        st.session_state.db_name = db_name
        
        try:
            db_params = {
                "host": db_host,
                "user": db_user,
                "password": db_password,
                "database": db_name
            }
            db = DBConnection(**db_params)
            db.close()
            st.session_state.connection_setup = True
            st.session_state.db_params = db_params
            st.session_state.config = Config(groq_api_key)
            st.success("Connection details saved successfully!")
            st.rerun()
        except Exception as e:
            st.error(f"Failed to connect to the database: {str(e)}")

def main():
    if not st.session_state.get("connection_setup", False):
        setup_connection_details()
        return

    db_params = st.session_state.db_params
    if "config" not in st.session_state:
        st.session_state.config = Config(st.session_state.groq_api_key)

    st.title("SQL Chat Application")
    
    if 'controller' not in st.session_state:
        st.session_state.controller = ControllerAgent()
    if 'results' not in st.session_state:
        st.session_state.results = []
    if 'confirm_needed' not in st.session_state:
        st.session_state.confirm_needed = False
    if 'pending_query' not in st.session_state:
        st.session_state.pending_query = None
    if 'input_value' not in st.session_state:
        st.session_state.input_value = ""
    
    available_schemas = get_available_schemas(db_params)
    schema_name = st.sidebar.selectbox("Select Schema", available_schemas, key="schema_select")
    
    new_schema = st.sidebar.text_input("Create new schema:")
    if new_schema and st.sidebar.button("Create Schema"):
        create_schema(new_schema.lower(), db_params)
        st.rerun()
    
    csv_file = st.sidebar.file_uploader("Upload CSV", type=["csv"])
    if csv_file is not None:
        st.session_state.file_content = csv_file.read().decode("utf-8")
    
    user_input = st.text_area("Enter your query:", 
                            value=st.session_state.input_value,
                            height=150,
                            key="query_input_box")
    
    if st.button("Submit Query") and user_input and schema_name:
        with st.spinner("Processing your query..."):
            new_result = st.session_state.controller.process_query(user_input, schema_name)
            st.session_state.results = [new_result]
            if new_result["status"] != "confirmation_needed":
                st.session_state.input_value = ""

    if st.session_state.results:
        latest_result = st.session_state.results[-1]
        if latest_result["status"] == "success":
            st.success("Query executed successfully")
            if "result" in latest_result:
                st.markdown(format_html_table(latest_result.get("result", "No output")), unsafe_allow_html=True)
                st.write("SQL Query:", latest_result["sql_query"])
                st.write("Learning Output:", latest_result["learning_output"])
            else:
                st.write("Original SQL Query:", latest_result["sql_query"])
                st.write("Inverse Query Executed:", latest_result["inverse_query"])
        elif latest_result["status"] == "error":
            st.error(latest_result["message"])
        elif latest_result["status"] == "clarification_needed":
            st.warning(latest_result["message"])
        elif latest_result["status"] == "confirmation_needed":
            st.warning("Confirmation required")
            st.write("SQL Query:", latest_result["sql_query"])
            if st.sidebar.button("Confirm Execution", key=f"confirm_{latest_result['sql_query']}"):
                with st.spinner("Executing confirmed query..."):
                    try:
                        db = DBConnection(**db_params)
                        operation_type, table_name, state_data, state_error = st.session_state.controller.history.capture_state(latest_result["sql_query"], schema_name)
                        if state_error:
                            st.session_state.results = [{"status": "error", "message": state_error}]
                            st.error(state_error)
                        else:
                            result_exec = db.execute_query(latest_result["sql_query"])
                            st.success("Query executed successfully")
                            version_id = st.session_state.controller.history.save_query(
                                st.session_state.pending_query["input"], 
                                latest_result["sql_query"], 
                                schema_name,
                                operation_type,
                                table_name,
                                state_data
                            )
                            st.session_state.results = [{
                                "status": "success",
                                "result": result_exec,
                                "sql_query": latest_result["sql_query"],
                                "learning_output": f"For your request: '{st.session_state.pending_query['input']}'\nGenerated SQL: {latest_result['sql_query']}",
                                "version_id": version_id
                            }]
                            st.session_state.confirm_needed = False
                            st.session_state.pending_query = None
                            st.session_state.input_value = ""
                    except Exception as e:
                        st.session_state.results = [{"status": "error", "message": f"Error executing confirmed query: {str(e)}"}]
                        st.error(f"Error: {str(e)}")
                if st.session_state.results[-1]["status"] == "error":
                    st.rerun()
    
    with st.expander("Query History"):
        history = st.session_state.controller.history.get_history()
        if history:
            if st.button("Clear History"):
                with st.spinner("Clearing history..."):
                    st.session_state.controller.history.clear_history()
                    st.rerun()
            
            for version_id, user_q, sql_q, timestamp, schema_name in history:
                st.write(f"Version {version_id} ({timestamp}): {user_q} (Schema: {schema_name or 'Unknown'})")
                if st.button(f"Revert to Version {version_id}", key=f"revert_{version_id}"):
                    with st.spinner("Reverting to version..."):
                        revert_result = st.session_state.controller.revert_to_version(version_id)
                        st.session_state.results = [revert_result]
                        if revert_result["status"] == "error":
                            st.rerun()

if __name__ == "__main__":
    main()