from groq import Groq

# Test Groq connection
# Replace with your actual Groq API key
GROQ_API_KEY='GROQ_API_KEY'
# Initialize the client
groq_client = Groq(api_key=GROQ_API_KEY)

# Get user input
user_input = input("Enter your prompt: ")

# Make the chat completion request
response = groq_client.chat.completions.create(
    model="llama-3.3-70b-versatile", 
    messages=[
        {"role": "user", "content": user_input}
    ]
)

# Print the model's response
print("\nResponse from Groq model:\n")
print(response.choices[0].message.content)