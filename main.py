import streamlit as st
from agents.controller_agent import ControllerAgent
from database.db_connection import DBConnection

def get_available_schemas():
    db = DBConnection()
    try:
        return db.get_schemas()
    finally:
        db.close()

def create_schema(schema_name):
    db = DBConnection()
    try:
        db.execute_query(f"CREATE SCHEMA IF NOT EXISTS {schema_name}")
    finally:
        db.close()

def format_html_table(table_data):
    if isinstance(table_data, str) or not table_data:
        return f"<p>{table_data or 'No results found'}</p>"
    
    rows = table_data["rows"]
    columns = table_data["columns"]
    
    # Limit to top 50 rows
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
    for row in display_rows:
        html += "<tr>" + "".join(f"<td>{str(val)}</td>" for val in row) + "</tr>"
    html += "</tbody></table></div>"
    html += row_limit_message
    return html

def main():
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
    
    # Schema selection and creation
    available_schemas = get_available_schemas()
    schema_name = st.sidebar.selectbox("Select Schema", available_schemas, key="schema_select")
    
    new_schema = st.sidebar.text_input("Create new schema:")
    if new_schema and st.sidebar.button("Create Schema"):
        create_schema(new_schema.lower())
        st.rerun()
    
    # CSV Upload
    csv_file = st.sidebar.file_uploader("Upload CSV", type=["csv"])
    if csv_file is not None:
        st.session_state.file_content = csv_file.read().decode("utf-8")
    
    # Chat interface with submit button
    user_input = st.text_area("Enter your query:", 
                            value=st.session_state.input_value,
                            height=150,
                            key="query_input_box")
    
    if st.button("Submit Query") and user_input and schema_name:
        st.session_state.results = []  # Clear previous results
        result = st.session_state.controller.process_query(user_input, schema_name)
        st.session_state.results.append(result)
        if result["status"] != "confirmation_needed":
            st.session_state.input_value = ""
    
    # Display results (only latest)
    for result in st.session_state.results:
        if result["status"] == "success":
            st.success("Query executed successfully")
            st.markdown(format_html_table(result.get("result", "No output")), unsafe_allow_html=True)
            st.write("SQL Query:", result["sql_query"])
            st.write("Learning Output:", result["learning_output"])
        elif result["status"] == "error":
            st.error(result["message"])
        elif result["status"] == "clarification_needed":
            st.warning(result["message"])
        elif result["status"] == "debug":
            st.info(result["message"])
        elif result["status"] == "confirmation_needed":
            st.warning("Confirmation required")
            st.write("SQL Query:", result["sql_query"])
            if st.sidebar.button("Confirm Execution", key=f"confirm_{result['sql_query']}"):
                try:
                    db = DBConnection()
                    result_exec = db.execute_query(result["sql_query"])
                    version_id = st.session_state.controller.history.save_query(
                        st.session_state.pending_query["input"], 
                        result["sql_query"], 
                        schema_name
                    )
                    st.session_state.results = [{
                        "status": "success",
                        "result": result_exec,
                        "sql_query": result["sql_query"],
                        "learning_output": f"For your request: '{st.session_state.pending_query['input']}'\nGenerated SQL: {result['sql_query']}",
                        "version_id": version_id
                    }]
                    st.session_state.confirm_needed = False
                    st.session_state.pending_query = None
                    st.session_state.input_value = ""
                except Exception as e:
                    st.session_state.results = [{"status": "error", "message": f"Error executing confirmed query: {str(e)}"}]
                st.rerun()
    
    # History section with revert in collapsible panel
    with st.expander("Query History"):
        history = st.session_state.controller.history.get_history()
        if history:
            for version_id, user_q, sql_q, timestamp, schema_name in history:
                st.write(f"Version {version_id} ({timestamp}): {user_q} (Schema: {schema_name or 'Unknown'})")
                if st.button(f"Revert to Version {version_id}", key=f"revert_{version_id}"):
                    revert_result = st.session_state.controller.revert_to_version(version_id)
                    st.session_state.results = [revert_result]
                    st.rerun()

if __name__ == "__main__":
    main()