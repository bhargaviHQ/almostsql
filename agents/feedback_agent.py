class FeedbackAgent:
    def request_clarification(self, user_input, schema_name, st_session, message="Please clarify your request:"):
        st_session.sidebar.write(f"Confused about: {user_input}")
        st_session.sidebar.write(message)
        clarification = st_session.sidebar.text_input("Please provide clarification:", key=f"clarify_{user_input}")
        if clarification:
            return f"Clarified request: {user_input} - {clarification}"
        return "Please provide clarification in the sidebar"