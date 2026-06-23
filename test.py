from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate

# 1. Initialize Qwen with reasoning enabled
llm = ChatOllama(
    model='qwen3.5:9b',
    temperature=0.3,
    reasoning=True # Captures internal thought blocks separately
)

# 2. Define your news template
prompt = ChatPromptTemplate.from_messages([
    ("system", "You are an expert editor. First think about the bias/validity of the headline, then write a 2-sentence breakdown."),
    ("human", "Process this news payload: {news_input}")
])

# 3. Create the Chain (Notice: NO StrOutputParser at the end!)
# This ensures the chain yields raw 'AIMessageChunk' objects containing all data metadata.
news_chain = prompt | llm

# --- RUNNING & STREAMING THE CHAIN ---

payload = "Tech Corp announces new chip that runs 500% faster but uses double the electricity."
print("--- STARTING CHAIN STREAM ---\n")

has_started_answer = False

# Invoke the stream method on your chain directly!
for chunk in news_chain.stream({"news_input": payload}):
    
    # Extract the thinking tokens from the message chunk
    thinking_text = chunk.additional_kwargs.get("reasoning_content", "")
    if thinking_text:
        # Print thinking in dim/grey text style
        print(f"\033[2m{thinking_text}\033[0m", end="", flush=True)
        
    # Extract the actual finalized response text
    elif chunk.content:
        if not has_started_answer:
            print("\n\n=== FINAL EDITORIAL RESUMÉ ===")
            has_started_answer = True
            
        print(chunk.content, end="", flush=True)

print("\n\n--- STREAM COMPLETE ---")