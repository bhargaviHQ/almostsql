from database.db_connection import DBConnection

class HistoryManager:
    def __init__(self):
        self.db = DBConnection()
        self.create_history_table()

    def create_history_table(self):
        query = """
        CREATE TABLE IF NOT EXISTS query_history (
            version_id INT AUTO_INCREMENT PRIMARY KEY,
            user_query TEXT,
            sql_query TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            schema_name VARCHAR(255)
        )
        """
        self.db.execute_query(query)

    def save_query(self, user_query, sql_query, schema_name):
        query = "INSERT INTO query_history (user_query, sql_query, schema_name) VALUES (%s, %s, %s)"
        self.db.execute_query(query, (user_query, sql_query, schema_name))
        return self.db.cursor.lastrowid

    def get_history(self):
        query = "SELECT version_id, user_query, sql_query, timestamp, schema_name FROM query_history ORDER BY version_id"
        result = self.db.execute_query(query)
        if result:
            return [row if len(row) == 5 else (row[0], row[1], row[2], row[3], None) for row in result["rows"]]
        return []

    def get_query_by_version(self, version_id):
        query = "SELECT sql_query FROM query_history WHERE version_id = %s"
        result = self.db.execute_query(query, (version_id,))
        return result["rows"][0][0] if result and result["rows"] else None