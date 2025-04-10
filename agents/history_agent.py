from database.history_manager import HistoryManager
from database.db_connection import DBConnection

class HistoryAgent:
    def __init__(self):
        self.history_mgr = HistoryManager()

    def save_query(self, user_query, sql_query, schema_name):
        return self.history_mgr.save_query(user_query, sql_query, schema_name)

    def get_history(self):
        return self.history_mgr.get_history()

    def revert_to_version(self, version_id):
        sql_query = self.history_mgr.get_query_by_version(version_id)
        if sql_query:
            db = DBConnection()
            try:
                db.execute_query(sql_query)
                return f"Reverted to version {version_id}"
            except Exception as e:
                return f"Error reverting: {str(e)}"
            finally:
                db.close()
        return "Version not found"