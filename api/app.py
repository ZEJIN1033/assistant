import os
import json
from time import sleep
from packaging import version
from flask import Flask, request, jsonify
import openai
from openai import OpenAI
# import functions
# ------------------------------------------------------------------------------
def create_assistant(client):
  assistant_file_path = 'assistant.json'

  if os.path.exists(assistant_file_path):
    with open(assistant_file_path, 'r') as file:
      assistant_data = json.load(file)
      assistant_id = assistant_data['assistant_id']
      print("Loaded existing assistant ID.")
  else:
    file = client.files.create(file=open("knowledge.pdf", "rb"),
                               purpose='assistants')

    assistant = client.beta.assistants.create(instructions="""
          Ella is a specialized tutor for the A-level biology, 'Clocks, Sleep and Biological Time', aimed at helping students achieve in-depth understanding and excel in the final exam. She has comprehensive knowledge of the Cell structure, Biological molecules, Enzymes, Cell membranes and transport, The mitotic cell cycle, Nucleic acids and protein synthesis, Transport in plants, Transport in mammals, Gas exchange and smoking, Infectious diseases, Immunity, Energy and respiration, Photosynthesis, Homeostasis, Coordination, Inherited change, Selection and evolution, biodiversity, classification and conservation and Genetic technology
Ella employs a highly interactive and adaptable tutoring approach, fostering critical thinking and problem-solving skills. She provides tailored key concepts, practice questions, and problem-solving strategies, suited to the final exam's format. This exam involves integrating knowledge from multiple topics.
Ella integrates technology in her tutoring, recommending useful apps and tools, while focusing primarily on the Book "Cambridge International AS and A level Biology courseboook". She personalizes her strategy based on student feedback and progression, adjusting her methods to fit individual learning needs. Ella uses a combination of quizzes, reflective questions, and discussions of key concepts to assess students' understanding of the material, ensuring a comprehensive and effective learning experience.
When users ask you questions, always try to use your knowledge base first, if you do not find an answer, search the internet.
          """,
                                              model="gpt-3.5-turbo-1106",
                                              tools=[{
                                                  "type": "retrieval"
                                              }],
                                              file_ids=[file.id])

    with open(assistant_file_path, 'w') as file:
      json.dump({'assistant_id': assistant.id}, file)
      print("Created a new assistant and saved the ID.")

    assistant_id = assistant.id

  return assistant_id

# ------------------------------------------------------------------------------

# Check OpenAI version is correct
required_version = version.parse("1.1.1")
current_version = version.parse(openai.__version__)
# OPENAI_API_KEY = os.getenv['OPENAI_API_KEY']
OPENAI_API_KEY = "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"

if current_version < required_version:
  raise ValueError(f"Error: OpenAI version {openai.__version__}"
                   " is less than the required version 1.1.1")
else:
  print("OpenAI version is compatible.")

# Start Flask app
app = Flask(__name__)

# Init client
client = OpenAI(
    api_key=OPENAI_API_KEY)  # should use env variable OPENAI_API_KEY in secrets (bottom left corner)

# Create new assistant or load existing
assistant_id = create_assistant(client)

# Start conversation thread
@app.route('/start', methods=['GET'])
def start_conversation():
  print("Starting a new conversation...")  # Debugging line
  thread = client.beta.threads.create()
  print(f"New thread created with ID: {thread.id}")  # Debugging line
  return jsonify({"thread_id": thread.id})

# Generate response
@app.route('/chat', methods=['POST'])
def chat():
  data = request.json
  thread_id = data.get('thread_id')
  user_input = data.get('message', '')

  if not thread_id:
    print("Error: Missing thread_id")  # Debugging line
    return jsonify({"error": "Missing thread_id"}), 400

  print(f"Received message: {user_input} for thread ID: {thread_id}"
        )  # Debugging line

  # Add the user's message to the thread
  client.beta.threads.messages.create(thread_id=thread_id,
                                      role="user",
                                      content=user_input)

  # Run the Assistant
  run = client.beta.threads.runs.create(thread_id=thread_id,
                                        assistant_id=assistant_id)

  # Check if the Run requires action (function call)
  while True:
    run_status = client.beta.threads.runs.retrieve(thread_id=thread_id,
                                                   run_id=run.id)
    print(f"Run status: {run_status.status}")
    if run_status.status == 'completed':
      break
    sleep(1)  # Wait for a second before checking again

  # Retrieve and return the latest message from the assistant
  messages = client.beta.threads.messages.list(thread_id=thread_id)
  response = messages.data[0].content[0].text.value

  print(f"Assistant response: {response}")  # Debugging line
  return jsonify({"response": response})


# Run server
if __name__ == '__main__':
  app.run(host='0.0.0.0', port=8080)
