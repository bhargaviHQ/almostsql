# AlmostSQL User Guide

## Agents Overview
The agents in AlmostSQL work collaboratively to process user inputs and manage database operations.
- **ControllerAgent**
   - Acts as the central coordinator.
   - Receives user input, delegates tasks to other agents, and manages the overall workflow.
- **QueryParserAgent**
   - Uses a language model (via GROQ API) to parse user input into valid MySQL queries.
   - Handles natural language, SQL-like inputs, and CSV upload requests.
   - If clarification is needed, it returns a `CLARIFY` message.

- **SQLExecutorAgent**
   - Executes the parsed SQL query on the MySQL database.
   - Returns results or success messages.

-  **FeedbackAgent**
   - Requests clarification from the user if the query is ambiguous or incomplete.
   - Displays prompts in the sidebar.

-  **CSVLoaderAgent**
   - Processes CSV file uploads.
   - Creates tables if needed and inserts data into the database.

-  **HistoryAgent**
   - Stores query details (`user input`, `SQL query`, `schema`, and `state`) in a `query_history` table.
   - Captures pre-execution state in a `query_state_history` table for reversion.

-  **LearningAgent**
   - Generates user-friendly output showing the original request and the generated SQL query.

## Example Flow

When a user submits a query:
1. ControllerAgent receives the input and passes it to the QueryParserAgent.
2. QueryParserAgent generates a SQL query or requests clarification.
3. If clarification is needed, FeedbackAgent prompts the user via the sidebar.
4. If the query is valid but involves `DELETE`, `UPDATE`, or `ALTER`, ControllerAgent requests confirmation.
5. Upon confirmation, HistoryAgent captures the pre-execution state.
6. SQLExecutorAgent executes the query.
7. HistoryAgent saves the query and state to the database.
8. LearningAgent generates learning output for display.
9. Results are shown in the Streamlit UI as an HTML table.

## Using the Streamlit UI

### Main Panel:

- **Query Input Box**: Enter natural language queries (e.g., `“show all products”`) or SQL commands.
- **Submit Query Button**: Processes the query.
- **Results Display**: Shows query results as an HTML table or error/clarification messages. Displays up to 50 rows, configurable to show more as needed.
- **Learning Output Expander**: Displays the original request and generated SQL.
- **Query History Expander**: Lists past queries with options to revert to a specific version.

### Sidebar:

- **Schema Selection**: Choose an existing schema or create a new one.
- **CSV Upload**: Upload a CSV file to load into a table.
- **Table Metadata**: Displays tables and columns in the selected schema with indicators for PK, FK, and INDEX.
- **Clarification Input**: Appears if the system needs query clarification.

## Input Types and Examples

Users can provide various types of inputs in the query box. 

### Examples:

- **Natural Language**:  
  `"Show all products where price > 100"`
- **SQL-like**:  
  `"SELECT * FROM products WHERE price > 100"`
- **CSV Upload**:  
  `"Upload csv products.csv into products_table"`
- **Table Creation**:  
  `"Create table employees with columns id, name, salary"`
- **Data Modification**:  
  `"Update employees set salary to 50000 where id is 1"` 

---

## Configuration Options

- Schema Selection:
   - Choose the database schema to work with.
   - Create a new schema via the sidebar if needed.

-  CSV Upload:
   - Upload a CSV file.
   - Specify the target table name in the query or sidebar.
   - The system creates the table with `VARCHAR(255)` columns if it doesn’t exist.

- Confirmation for Destructive Queries:
   - Queries involving `DELETE`, `UPDATE`, or `ALTER` require user confirmation to prevent accidental changes.

- Query History and Reversion:
   - View past queries in the “Query History” expander.
   - Click **"Revert to Version X"** to undo a query.
   - Use **"Clear History"** to reset the history.
