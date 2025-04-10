class LearningAgent:
    def generate_learning_output(self, user_input, sql_query):
        return f"For your request: '{user_input}'\nGenerated SQL: {sql_query}"