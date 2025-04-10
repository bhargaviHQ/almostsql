import pandas as pd
from database.db_connection import DBConnection
import json

class CSVLoaderAgent:
    def load_csv(self, user_input, schema_name, st_session):
        file_path = user_input.split("csv ")[1].split(" into ")[0].strip()
        table_name = user_input.split("into ")[1].split()[1].lower() if "into" in user_input else None
        if not table_name:
            table_name = st_session.sidebar.text_input("Enter table name for CSV:", key=f"csv_{file_path}")
        
        if table_name and file_path:
            return self._load_csv_to_table(file_path, table_name, schema_name)
        return "Please specify table name in sidebar"

    def load_csv_from_json(self, json_str, schema_name, st_session):
        details = json.loads(json_str)
        file_path = details.get("file_path")
        table_name = details.get("table", "").lower()
        if file_path and table_name:
            return self._load_csv_to_table(file_path, table_name, schema_name)
        return "ERROR: Invalid CSV insert details"

    def _load_csv_to_table(self, file_path, table_name, schema_name):
        df = pd.read_csv(file_path)
        db = DBConnection()
        try:
            df.columns = [col.lower() for col in df.columns]
            table_name = table_name.lower()
            
            create_table_query = f"CREATE TABLE IF NOT EXISTS {schema_name}.{table_name} ({', '.join(f'{col} VARCHAR(255)' for col in df.columns)})"
            db.execute_query(create_table_query)
            
            for _, row in df.iterrows():
                insert_query = f"INSERT INTO {schema_name}.{table_name} VALUES ({','.join(['%s'] * len(row))})"
                db.execute_query(insert_query, tuple(row))
            
            return f"CSV loaded into {schema_name}.{table_name}"
        except Exception as e:
            return f"Error loading CSV: {str(e)}"
        finally:
            db.close()