from langchain.prompts import PromptTemplate
from config.config import Config
from database.db_connection import DBConnection
import streamlit as st
import time
from groq import GroqError
from utils.logger import Logger

class QueryParserAgent:
    def __init__(self):
        self.logger = Logger()

    def parse_query(self, user_input, schema_name):
        return self._generate_query(user_input, schema_name, invert=False)

    def generate_inverse_query(self, original_query, schema_name):
        return self._generate_query(original_query, schema_name, invert=True)

    def _generate_query(self, query_input, schema_name, invert=False):
        db = DBConnection(**st.session_state.db_params)
        try:
            schemas = db.get_schemas()
            tables = db.get_tables(schema_name) if schema_name in schemas else []
            context = {
                "schemas": schemas,
                "current_schema": schema_name,
                "tables": tables,
                "columns": {table: db.get_columns(schema_name, table) for table in tables}
            }

            completed_prompt = self._complete_prompt(query_input, context) if not invert else query_input
            prompt_template = """
            Given this {mode} query: '{query}' and the database context: {context},
            {task}.
            - Use lowercase for table and column names.
            - Include the schema name '{schema_name}' in the query where appropriate.
            - Support complex queries including JOINs, subqueries, GROUP BY, HAVING, and ORDER BY.
            - If the query implies a table creation and it doesn't exist (for normal mode), include a CREATE TABLE statement with inferred column types (INT for numbers, DATE for YYYY-MM-DD, VARCHAR(255) for text).
            - For INSERT/UPDATE, parse key-value pairs (e.g., 'id is 12', 'name to John') and conditions (e.g., 'where id = 12').
            - If column names don't exactly match but are similar (e.g., 'store id' vs 'store_id'), use the existing column name.
            - If multiple similar column names exist (e.g., 'productid' and 'product_id'), return 'CLARIFY: Multiple similar columns found: [list]. Which one did you mean?'.
            - For CSV data upload (e.g., 'upload csv into table_name'), parse the CSV content provided in the query and generate:
              - A CREATE TABLE statement if the table doesn't exist, inferring column types from the CSV data.
              - An INSERT INTO statement with the CSV data as VALUES, e.g., INSERT INTO table_name (col1, col2) VALUES (val1, val2), (val3, val4).
              - Do NOT use COPY or LOAD DATA INFILE; use INSERT INTO for MySQL compatibility.
            - Return ONLY the plain SQL query string with no extra text, comments, or formatting like ```sql or backticks.
            """
            
            if invert:
                mode = "original SQL"
                task = """
                generate the inverse MySQL query to undo the operation.
                - For CREATE TABLE, generate DROP TABLE.
                - For INSERT, generate DELETE with the same conditions.
                - For UPDATE, generate an UPDATE that reverses the SET clause (if possible).
                - For DROP TABLE, generate CREATE TABLE (if schema is known).
                - If the inverse operation is not feasible (e.g., due to missing prior state), return 'CLARIFY: Cannot generate inverse query due to missing state information.'
                """
            else:
                mode = "user"
                task = "generate a valid MySQL query"

            prompt = PromptTemplate(
                input_variables=["query", "context", "schema_name", "mode", "task"],
                template=prompt_template
            )

            formatted_prompt = prompt.format(
                query=completed_prompt,
                context=str(context),
                schema_name=schema_name,
                mode=mode,
                task=task
            )

            self.logger.debug("Sending request to GROQ API...")
            start_time = time.time()
            try:
                response = st.session_state.config.get_groq_client().chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": formatted_prompt}],
                    timeout=30
                )
                elapsed_time = time.time() - start_time
                self.logger.debug(f"GROQ API response received in {elapsed_time:.2f} seconds")
            except GroqError as e:
                self.logger.error(f"GROQ API error: {str(e)}")
                return f"CLARIFY: GROQ API error: {str(e)}"
            except Exception as e:
                self.logger.error(f"GROQ API timeout or error: {str(e)}")
                return f"CLARIFY: GROQ API timeout or error: {str(e)}"

            sql_query = response.choices[0].message.content.strip()
            
            sql_query = sql_query.replace("```sql", "").replace("```", "").replace("\n", " ").strip()
            
            if not invert:
                self.logger.debug(f"Raw SQL Query: {sql_query}")
            
            return sql_query
        except Exception as e:
            self.logger.error(f"Query parsing error: {str(e)}")
            return f"CLARIFY: Unable to parse query due to {str(e)}. Please provide more details."
        finally:
            db.close()

    def _complete_prompt(self, user_input, context):
        lower_input = user_input.lower()
        
        if ("upload csv" in lower_input or "from csv" in lower_input or "load data" in lower_input) and "file_content" in st.session_state:
            return f"{user_input} with content: {st.session_state['file_content']}"
        elif "upload csv" in lower_input or "from csv" in lower_input or "load data" in lower_input:
            return "CLARIFY: Please upload a CSV file first."

        table_name = None
        for keyword in ["table", "into", "from", "update"]:
            if keyword in lower_input:
                parts = lower_input.split(keyword)
                if len(parts) > 1 and parts[-1].strip():
                    table_name = parts[-1].strip().split()[0]
                    break
        
        if not table_name:
            return user_input
        
        if "create" in lower_input and table_name not in context["tables"]:
            return f"{user_input} with columns inferred from context if needed"

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