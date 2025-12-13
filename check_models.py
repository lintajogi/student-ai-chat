from groq import Groq 
import os 
client = Groq(api_key=os.getenv("GROQ_API_KEY")) 
print("AVAILABLE MODELS FOR YOUR SYSTEM:\n") 
for m in client.models.list().data: 
    print(m.id) 
