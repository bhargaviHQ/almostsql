class LearningAgent:
    # This agent can also be though of as a NarratorAgent
    # Purpose is to convey the learning output to the user
    def generate_learning_output(self, user_input, sql_query):
        return f"For your request: '{user_input}'\nGenerated SQL: {sql_query}"