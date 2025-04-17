class Config:
    def __init__(self, groq_api_key):
        self.groq_api_key = groq_api_key

    def get_groq_api_key(self):
        return self.groq_api_key

    def get_groq_client(self):
        from groq import Groq
        return Groq(api_key=self.groq_api_key)