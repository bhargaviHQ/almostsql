from database.db_connection import DBConnection

class SQLExecutorAgent:
    def execute(self, sql_query, schema_name):
        db = DBConnection()
        try:
            result = db.execute_query(sql_query)
            if result is not None:  # SELECT query
                return result  # Return raw result (dict with rows and columns)
            return "Query executed successfully"
        finally:
            db.close()