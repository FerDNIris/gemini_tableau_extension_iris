import anvil.secrets
import anvil.server

#import google.generativeai as genai ### Old library
from google import genai
from google.genai import types
# --- Global Configuration ---
# Configure the API once when the server module loads.
try:
    # Use anvil.secrets.get() and the name of the secret you defined in Anvil.
    GOOGLE_API_KEY = anvil.secrets.get_secret('gemini_api_key')
    if not GOOGLE_API_KEY:
        raise ValueError("The Google API Key ('gemini_api_key') was not found in Anvil Secrets.")
    #genai.configure(api_key=GOOGLE_API_KEY)
    client = genai.Client(api_key =GOOGLE_API_KEY)
except Exception as e:
    # This error will be visible in the Anvil server logs.
    print(f"CRITICAL ERROR: Could not configure Google API. The extension will not work. Error: {e}")

# --- Model Definition ---
# Define the system prompt and initialize the model in one place.
SYSTEM_PROMPT = [
  "You are an expert analyst and know everything about data analysis.",
  "You can interpret data in any form whether it's a single data point or a list of data with keys",
  "You are on a mission to provide the best data analysis report when asked",
  "You are capable of answering the question without report as well on topics that require you to answer between a finite set of possibilities",
  "You also need to provide all the answers in spanish because the main client using this speaks in this language, Spanish and nothing more "
]

# Initialize the model to be used by the function.
# Corrected model name to 'gemini-1.5-flash' as 'gemini-2.5-flash' is not a valid model anymore.
"""
old_model = genai.GenerativeModel(
    #model_name='gemini-2.5-flash-lite', 
    #model_name='gemma-4-26b-a4b-it',
    model_name ='gemma-3-27b',
    system_instruction=SYSTEM_PROMPT
)
"""
selected_model = 'gemma-4-31b-it'

@anvil.server.callable
def generateDataSummary(prompt, data):
  if not prompt:
    return "Error: Please provide a question to analyze the data."
  if data.empty:
    return "Error: No data to analyze. Please select data in the Tableau dashboard."
  contents = [
    f"User Question: {prompt}",
    "Data for Analysis:",
    str(data)
  ]
  try:
    response = client.models.generate_content(
      model = selected_model,
      contents = contents,
      config = types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT
      )
    )
    return response.text
  except Exception as e:
    # Safely handle API errors and return a helpful message to the user.
    print(f"An error occurred while calling the Gemini API: {e}")
    return f"Sorry, an error occurred while generating the analysis. Please check the server logs for details. Error: {e}"

"""
def old_generateDataSummary(prompt, data):
  if not prompt:
      return "Error: Please provide a question to analyze the data."
  if not data:
      return "Error: No data to analyze. Please select data in the Tableau dashboard."

  # Construct the content for the model in a structured way, as recommended by the documentation.
  # str(data) converts the Tableau data object (Mark/DataTable) into a readable string.
  contents = [
      f"User Question: {prompt}",
      "Data for Analysis:",
      str(data)
  ]

  try:
    response = old_model.generate_content(contents)
    return response.text
  except Exception as e:
    # Safely handle API errors and return a helpful message to the user.
    print(f"An error occurred while calling the Gemini API: {e}")
    return f"Sorry, an error occurred while generating the analysis. Please check the server logs for details. Error: {e}"
"""