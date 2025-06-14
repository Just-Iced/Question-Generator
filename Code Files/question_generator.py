# -*- coding: utf-8 -*-
"""Question Generator w/ Faithfulness Test.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/13pBwaC0QEc1G0MTSfqE2abbOONi6jQ-c

# Question Generation AI
An AI to generate questions based on data in its folder
"""

# Download PDF and store it in a data folder
!mkdir -p 'data'
!wget 'https://downloads.ctfassets.net/nnc41duedoho/63cHBOAVpOAQGOOMBFhFbL/0cc93af0c5ce6b5278dfccfa6e53cf4c/driver-full.pdf' -O 'data/DriversManual.pdf'

# Install Pip packages

!pip install --upgrade --force-reinstall llama-index-embeddings-fastembed
# Install Ollama related packages
!pip install --upgrade llama-index-core llama-index llama-index-llms-ollama llama-index-embeddings-huggingface llama-index llama-index-llms-openai
# Install all other packages
!pip install --upgrade nest_asyncio spacy

print("\n\n\n\n\nDone installing pip packages.")

# Commented out IPython magic to ensure Python compatibility.
# Run only if running through Google Colab
!pip install colab-xterm
# %load_ext colabxterm
# %xterm
# RUN THESE IN THE CONSOLE

"""
sudo apt-get install lshw
curl -fsSL https://ollama.com/install.sh | sh
OLLAMA_HOST=127.0.0.1:11434 ollama serve & ollama pull phi3
"""

# Commented out IPython magic to ensure Python compatibility.
# Run only if on my local runtime, will break if ran anytime else
# %cd "C:\Users\Justice\Documents\Programming Projects\Python\AI\Question Generator"
import os
print(os.getcwd())

from llama_index.core.evaluation import RelevancyEvaluator
from llama_index.core import SimpleDirectoryReader, VectorStoreIndex, Settings
from llama_index.core.llama_dataset.generator import RagDatasetGenerator
from llama_index.embeddings.fastembed import FastEmbedEmbedding
from llama_index.llms.ollama import Ollama
from os.path import isfile

import nest_asyncio
nest_asyncio.apply()

# Read all data in the 'data' folder
reader = SimpleDirectoryReader("data/")
documents = reader.load_data()

# Create the LLM
llm = Ollama(model="llama3",
             temperature=0.3,
             # Increase the amount of time before the LLM returns a timeout response
             request_timeout=1000)

# Change the settings for the LLM to run fast at the start.
Settings.llm = llm
Settings.chunk_size *= 2
Settings.context_window *= 2
# Make the embedding model
Settings.embed_model = FastEmbedEmbedding(model_name="BAAI/bge-small-en-v1.5")

def get_eval_questions(questions_file):
  # Only generate the questions if they haven't been generated yet
  if not isfile(questions_file):
    try:
      # Make the dataset based on the documents in the 'data' folder
      data_gen = RagDatasetGenerator.from_documents(
        documents,
        llm = Settings.llm,
        # Increase to generate more questions
        num_questions_per_chunk = 2,
        workers = 8,
        question_gen_query="You are an instructor making question based on the data provided. Please make the best questions you can, otherwise you will be fired.",
        show_progress = True)

      # Generate the questions, takes longer based on the length of the dataset
      eval_questions = data_gen.generate_questions_from_nodes()

      # Save the questions to a json to avoid generating questions multiple times
      eval_questions.save_json(questions_file)
      return eval_questions

    # Only happens if the LLM took too long to generate a response
    except Exception:
      # Reduce the power of the LLM
      Settings.chunk_size /= 2
      Settings.context_window /= 2
      # Try again if the chunk size is large enough
      if Settings.chunk_size >= 128:
        print(f"\nThe LLM either took too long to generate a response, or had too much power dedicated to it. \nRetrying with lower performance, now running at {round(100 / (1024 / Settings.chunk_size))}% speed")
        # Rerun the function with the lowered performance
        get_eval_questions(questions_file)
  # If there is a file
  else:
    from llama_index.core.llama_dataset import LabelledRagDataset
    # Get the questions that have already been generated
    eval_questions = LabelledRagDataset.from_json(questions_file)
    return eval_questions
  # If the LLM cannot process the data in the smallest chunk sizes, or some random error occurs, return None
  return None


# Get the questions, then print the questions to the console
eval_questions = get_eval_questions("questions.json")
if eval_questions == None:
    print("Sorry, but your metadata is too large for your current system. Please decrease the amount of data to read, or upgrade your system.")
    import sys
    sys.exit()

# Create the relevancy evaluator, make sure it's a different LLM to ensure there's no 'favouritism'
Settings.llm = Ollama(model="llama3")
evaluator_llm = RelevancyEvaluator(llm=Settings.llm)

# Make the vector index and query engine
vector_index = VectorStoreIndex.from_documents(documents)
query_engine = vector_index.as_query_engine()

# Choose a random question from the list
for question in eval_questions:
  question = question.query
  # Query the engine
  response = query_engine.query(question)

  # Evaluate the result for relevancy
  eval_result = evaluator_llm.evaluate_response(
      query = question,
      response = response
  )

  # Print out the results
  print(f"Question: {question}\nResponse: {response}\nEvaluation Result: {round(eval_result.score * 100)}/100\nFeedback:{eval_result.feedback}\n")

  if eval_result.score > 0.6:
    import json
    with open("evaluations.json", "w") as f:
      evaluations = json.load(open("evaluations.json", "r"))

