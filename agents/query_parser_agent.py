from langchain.prompts import PromptTemplate
from config.config import Config
from database.db_connection import DBConnection
import streamlit as st

class QueryParserAgent:
    def parse_query(self, user_input, schema_name):
        db = DBConnection()
        try:
            # Gather context
            schemas = db.get_schemas()
            tables = db.get_tables(schema_name) if schema_name in schemas else []
            context = {
                "schemas": schemas,
                "current_schema": schema_name,
                "tables": tables,
                "columns": {table: db.get_columns(schema_name, table) for table in tables}
            }

            # Complete the prompt with column name correction
            completed_prompt = self._complete_prompt(user_input, context)
            prompt = PromptTemplate(
                input_variables=["query", "context"],
                template="""
                Given this user query: '{query}' and the database context: {context},
                generate a valid MySQL query.
                - Use lowercase for table and column names.
                - Include the schema name '{schema_name}' in the query where appropriate.
                - Support complex queries including JOINs, subqueries, GROUP BY, HAVING, and ORDER BY.
                - If the query implies a table creation and it doesn't exist, include a CREATE TABLE statement with inferred column types (INT for numbers, DATE for YYYY-MM-DD, VARCHAR(255) for text).
                - For INSERT/UPDATE, parse key-value pairs (e.g., 'id is 12', 'name to John') and conditions (e.g., 'where id = 12').
                - If column names don't exactly match but are similar (e.g., 'store id' vs 'store_id'), use the existing column name.
                - If multiple similar column names exist (e.g., 'productid' and 'product_id'), return 'CLARIFY: Multiple similar columns found: [list]. Which one did you mean?'.
                - For CSV data upload (e.g., 'upload csv into table_name'), parse the CSV content provided in the query and generate:
                  - A CREATE TABLE statement if the table doesn't exist, inferring column types from the CSV data.
                  - An INSERT INTO statement with the CSV data as VALUES, e.g., INSERT INTO table_name (col1, col2) VALUES (val1, val2), (val3, val4).
                  - Do NOT use COPY or LOAD DATA INFILE; use INSERT INTO for MySQL compatibility.
                - Return ONLY the plain SQL query string with no extra text, comments, or formatting like ```sql or backticks.
                """
            )

            formatted_prompt = prompt.format(query=completed_prompt, context=str(context), schema_name=schema_name)
            response = Config.groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": formatted_prompt}]
            )
            sql_query = response.choices[0].message.content.strip()
            
            # Clean up any unwanted formatting
            sql_query = sql_query.replace("```sql", "").replace("```", "").replace("\n", " ").strip()
            
            # Debug: Log the raw SQL query for inspection
            st.session_state.results.append({"status": "debug", "message": f"Raw SQL Query: {sql_query}"})
            
            return sql_query
        except Exception as e:
            return f"CLARIFY: Unable to parse query due to {str(e)}. Please provide more details."
        finally:
            db.close()

    def _complete_prompt(self, user_input, context):
        lower_input = user_input.lower()
        
        # Handle CSV upload
        if ("upload csv" in lower_input or "from csv" in lower_input or "load data" in lower_input) and "file_content" in st.session_state:
            return f"{user_input} with content: {st.session_state['file_content']}"
        elif "upload csv" in lower_input or "from csv" in lower_input or "load data" in lower_input:
            return "CLARIFY: Please upload a CSV file first."

        # Extract table name safely
        table_name = None
        for keyword in ["table", "into", "from", "update"]:
            if keyword in lower_input:
                parts = lower_input.split(keyword)
                if len(parts) > 1 and parts[-1].strip():
                    table_name = parts[-1].strip().split()[0]
                    break
        
        if not table_name:
            return user_input
        
        # Handle table creation
        if "create" in lower_input and table_name not in context["tables"]:
            return f"{user_input} with columns inferred from context if needed"

        # Column name correction and query completion
        if table_name in context["tables"]:
            columns = context["columns"][table_name]
            data_part = lower_input.split("where")[0] if "where" in lower_input else lower_input
            where_part = "where " + lower_input.split("where")[-1] if "where" in lower_input else ""
            corrected_data = []
            for part in data_part.split(","):
                part = part.strip()
                if not part:
                    continue
                if "is" in part or "=" in part or "to" in part:
                    split_char = "is" if "is" in part else "to" if "to" in part else "="
                    col_value_parts = part.split(split_char)
                    if len(col_value_parts) < 2:
                        continue
                    col_part = col_value_parts[0].strip()
                    value = col_value_parts[-1].strip()
                    col_name = col_part.replace(" ", "_").lower()
                    similar_cols = [c for c in columns if col_name in c or c in col_name]
                    if len(similar_cols) == 1:
                        corrected_data.append(f"{similar_cols[0]} {split_char} {value}")
                    elif len(similar_cols) > 1:
                        return f"CLARIFY: Multiple similar columns found in {table_name}: {similar_cols}. Which one did you mean for '{col_part}'?"
                    else:
                        corrected_data.append(part)
                else:
                    corrected_data.append(part)
            corrected_input = f"{lower_input.split(table_name)[0]}{table_name} {', '.join(corrected_data)} {where_part}".strip()
            return f"{corrected_input} in schema {context['current_schema']} table {table_name} with columns {columns}"
        
        return user_input