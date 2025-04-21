## AlmostSQL
You almost wrote that. We’ll take it from here. 
<p align="center">
  <img src="https://github.com/bhargaviHQ/almostsql/blob/main/assets/images/title.png" width="400" />
</p>


**AlmostSQL** is a multi-agent AI system that simplifies MySQL database interaction by enabling users to execute CRUD queries (Create, Read, Update, Delete), load data from CSV files, and revert queries using natural language or SQL inputs.  

Built using **LangChain**, **GROQ Cloud** (for accessing the `llama-3.3-70b-versatile` LLM), **Python**, and **Streamlit**, it automates query parsing, validation, execution, and rollbacks.

The application is targeted towards SQL learners, developers, educators, DB admins, and AI researchers, offering interactive learning, streamlined query execution, and safe experimentation, with use cases including SQL education and data prototyping.

### Key Functions

- Parses natural language queries into SQL using LLM.  
- Processes CSV uploads to create and populate tables.  
- Reverts queries (e.g., undo an `INSERT` with a corresponding `DELETE`).  
- Handles errors with clarification prompts and confirms risky queries before execution.

### Functional Modules
*Core components of AlmostSQL's perception, cognition, feedback, and memory.*
<p align="center">
  <img src="https://github.com/bhargaviHQ/almostsql/blob/main/assets/images/modules.jpg" width="500" />
</p>

### System Architecture
*High-level architecture of AlmostSQL’s multi-agent flow from natural language input to SQL execution and feedback.*
<p align="center">
  <img src="https://github.com/bhargaviHQ/almostsql/blob/main/assets/images/architecture.jpg" width="500" />
</p>
### Prerequisites
- **Python 3.8+** installed on system.
- A running **MySQL Server** with access credentials.
- **GROQ API Key** is required to access the language model for query parsing. Obtain one from [GROQ](https://groq.com). Other API keys may also be used.

### Setup & Usage

1. Clone the Repository


```bash
git clone https://github.com/bhargaviHQ/almostsql
cd almostsql
```
2.  Install dependencies

   ```bash
   pip install -r requirements.txt
   ```
3. Set up MySQL and ensure your MySQL server is running. Note the host, user, password, and database name for configuration.  
4. Start the Streamlit App:
```bash
streamlit run main.py
```
5. Access the UI by opening your browser and navigating to http://localhost:8501 (or the port shown in the terminal).

### Configure the Application
- GROQ API Key- GROQ API key used for query parsing
- Database Host- Typically localhost or MySQL server’s IP address (127.0.0.1)
- Database User
- Database Password
- Database Name- The schema name (e.g., mydb). 

Click Save and Proceed to connect. If successful, the main interface will load.

###  Features
- Choose or create a schema via the sidebar.
- Upload a CSV, specify the table name in the query or sidebar. Tables are created with VARCHAR(255) columns if needed.
- Destructive queries like DELETE, UPDATE, or ALTER queries require confirmation.
- View past queries and revert to a specific version or clear history.
