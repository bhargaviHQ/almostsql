import streamlit as st
from agents.controller_agent import ControllerAgent
from database.db_connection import DBConnection
from config.config import Config
import mysql.connector
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
        st.session_state.db_name = ""

    groq_api_key = st.text_input("GROQ API Key", value=st.session_state.groq_api_key, type="password")
    db_host = st.text_input("Database Host", value=st.session_state.db_host)
    db_user = st.text_input("Database User", value=st.session_state.db_user)
    db_password = st.text_input("Database Password", value=st.session_state.db_password, type="password")
    db_name = st.text_input("Database Name", value=st.session_state.db_name, placeholder="Enter your preferred schema name")

    if st.button("Save and Proceed"):
        if not db_name:
            st.error("Please enter a database name.")
            return
        # Validate schema name (basic check for SQL safety)
        if not re.match(r"^[a-zA-Z0-9_]+$", db_name):
            st.error("Database name must contain only letters, numbers, or underscores.")
            return

        st.session_state.groq_api_key = groq_api_key
        st.session_state.db_host = db_host
        st.session_state.db_user = db_user
        st.session_state.db_password = db_password
        st.session_state.db_name = db_name
        
        try:
            # Connect without database to check/create the schema
            temp_params = {
                "host": db_host,
                "user": db_user,
                "password": db_password
            }
            conn = mysql.connector.connect(**temp_params)
            cursor = conn.cursor()
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_name}")
            conn.commit()
            cursor.close()
            conn.close()

            # Connect with the specified schema
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
            st.success(f"Connection established and schema '{db_name}' created if it didn't exist!")
            st.rerun()
        except Exception as e:
            st.error(f"Failed to connect or create schema: {str(e)}")

def main():
    if not st.session_state.get("connection_setup", False):
        setup_connection_details()
        return

    db_params = st.session_state.db_params
    if "config" not in st.session_state:
        st.session_state.config = Config(st.session_state.groq_api_key)

    # Custom CSS for title and query output
    st.markdown("""
        <style>
        .almostsql-title {
            font-size: 28px !important;
            font-weight: bold;
            color: #2c3e50;
            margin-bottom: 20px;
        }
        .sql-query {
            background-color: #f8f9fa;
            color: #2c3e50;
            padding: 10px;
            border-radius: 5px;
            font-family: 'Courier New', Courier, monospace;
            font-size: 14px;
            border: 1px solid #ddd;
            margin-top: 10px;
        }
        .sql-query pre {
            margin: 0;
            color: inherit;
            background: transparent;
        }
        @media (prefers-color-scheme: dark) {
            .sql-query {
                color: inherit;
                background: transparent;
            }
        }
        </style>
    """, unsafe_allow_html=True)
    st.markdown('<div class="almostsql-title">AlmostSQL</div>', unsafe_allow_html=True)
    
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
    if 'new_schema_input' not in st.session_state:
        st.session_state.new_schema_input = ""
    
    # Sidebar controls
    available_schemas = get_available_schemas(db_params)
    schema_name = st.sidebar.selectbox("Select Schema", available_schemas, key="schema_select")
    
    new_schema = st.sidebar.text_input("Create new schema:", key="new_schema_input")
    if new_schema and st.sidebar.button("Create Schema"):
        if not re.match(r"^[a-zA-Z0-9_]+$", new_schema):
            st.sidebar.error("Schema name must contain only letters, numbers, or underscores.")
        else:
            try:
                create_schema(new_schema.lower(), db_params)
                # Clear only after rerun
                del st.session_state["new_schema_input"]  # Remove key safely
                st.rerun()
            except Exception as e:
                st.sidebar.error(f"Error creating schema: {str(e)}")

    
    csv_file = st.sidebar.file_uploader("Upload CSV", type=["csv"])
    if csv_file is not None:
        st.session_state.file_content = csv_file.read().decode("utf-8")
    
    # Display tables and columns in the sidebar
    st.sidebar.subheader(f"Tables in {schema_name}")
    db = DBConnection(**db_params)
    try:
        tables = sorted(db.get_tables(schema_name))  # Sort tables alphabetically
        if not tables:
            st.sidebar.write("No tables found in this schema.")
        else:
            html = """
            <style>
            .schema-table {
                font-family: 'Courier New', Courier, monospace;
                font-size: 14px;
                margin: 10px 0;
            }
            .schema-table ul {
                list-style-type: none;
                padding-left: 20px;
            }
            .schema-table li {
                margin: 5px 0;
            }
            .schema-table .table-name {
                font-weight: bold;
                color: #2c3e50;
            }
            .schema-table .key-indicator {
                color: #e74c3c;
                font-size: 12px;
                margin-left: 5px;
            }
            </style>
            <div class="schema-table">
            """
            for table in tables:
                html += f"<p><span class='table-name'>{table}</span></p><ul>"
                columns = db.get_columns(schema_name, table)
                key_info = db.get_column_keys(schema_name, table)
                for col in columns:
                    key_label = ""
                    if col in key_info:
                        key_types = key_info[col]
                        if "PRIMARY KEY" in key_types:
                            key_label += " (PK)"
                        if "FOREIGN KEY" in key_types:
                            key_label += " (FK)"
                        if "INDEX" in key_types and not ("PRIMARY KEY" in key_types or "FOREIGN KEY" in key_types):
                            key_label += " (INDEX)"
                    html += f"<li>{col}<span class='key-indicator'>{key_label}</span></li>"
                html += "</ul>"
            html += "</div>"
            st.sidebar.markdown(html, unsafe_allow_html=True)
    except Exception as e:
        st.sidebar.error(f"Error fetching schema metadata: {str(e)}")
    finally:
        db.close()
    
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
                #st.markdown(f'<div class="sql-query"><pre>SQL Query: {latest_result["sql_query"]}</pre></div>', unsafe_allow_html=True)
                # st.markdown("**SQL Query:**")
                # st.markdown(f"""```sql
                # {latest_result["sql_query"]}
                # """)
                learning_output = latest_result["learning_output"]

                with st.expander("Learning Output"):
                    if "Generated SQL:" in learning_output:
                        user_request, sql_part = learning_output.split("Generated SQL:", 1)
                        st.markdown(f"{user_request.strip()}")
                        st.markdown("**Generated SQL:**")
                        st.markdown(f"""```sql
                {sql_part.strip()}
                """)
                    else:
                        st.markdown(f"""```text
                {learning_output}
                ```""")

                #st.markdown(f'<div class="sql-query"><pre>Learning Output: {latest_result["learning_output"]}</pre></div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="sql-query"><pre>Original SQL Query: {latest_result["sql_query"]}</pre></div>', unsafe_allow_html=True)
                st.markdown(f'<div class="sql-query"><pre>Inverse Query Executed: {latest_result["inverse_query"]}</pre></div>', unsafe_allow_html=True)
        elif latest_result["status"] == "error":
            st.error(latest_result["message"])
        elif latest_result["status"] == "clarification_needed":
            st.warning(latest_result["message"])
        elif latest_result["status"] == "confirmation_needed":
            st.warning("Confirmation required")
            #st.markdown(f'<div class="sql-query"><pre>SQL Query: {latest_result["sql_query"]}</pre></div>', unsafe_allow_html=True)
            st.markdown("**SQL Query:**")
            st.markdown(f"""```sql
            {latest_result["sql_query"]}
                """)
            if st.button("Confirm Execution", key=f"confirm_{latest_result['sql_query']}"):
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
                    finally:
                        db.close()
                if st.session_state.results[-1]["status"] == "error":
                    st.rerun()
    
    with st.expander("Query History"):
        history = st.session_state.controller.history.get_history()
        if history:
            if st.button("Clear History"):
                with st.spinner("Clearing history..."):
                    st.session_state.controller.history.clear_history()
                    st.rerun()
            
            for index, (version_id, user_q, sql_q, timestamp, schema_name) in enumerate(history):
                st.write(f"Version {version_id} ({timestamp}): {user_q} (Schema: {schema_name or 'Unknown'})")
                if st.button(f"Revert to Version {version_id}", key=f"revert_{version_id}_{index}"):
                    with st.spinner("Reverting to version..."):
                        revert_result = st.session_state.controller.revert_to_version(version_id)
                        st.session_state.results = [revert_result]
                        if revert_result["status"] == "error":
                            st.rerun()

if __name__ == "__main__":
    main()