import anvil.secrets
import anvil.server

#import google.generativeai as genai ### Old library
from google import genai
from google.genai import types
# --- Global Configuration ---
client = None
# Configure the API once when the server module loads.
try:
  # Use anvil.secrets.get() and the name of the secret you defined in Anvil.
  GOOGLE_API_KEY = anvil.secrets.get_secret('gemini_api_key')
  if not GOOGLE_API_KEY:
    raise ValueError("The Google API Key ('gemini_api_key') was not found in Anvil Secrets.")
    #genai.configure(api_key=GOOGLE_API_KEY)
  client = genai.Client(api_key = GOOGLE_API_KEY)
except Exception as e:
  # This error will be visible in the Anvil server logs.
  print(f"CRITICAL ERROR: Could not configure Google API. The extension will not work. Error: {e}")

# --- Model Definition ---
# Define the system prompt and initialize the model in one place.
SYSTEM_PROMPT = ("You are an expert analyst and know everything about data analysis. "
                 "You can interpret data in any form whether it's a single data point or a list of data with keys. "
                 "You are on a mission to provide the best data analysis report when asked. "
                 "You are capable of answering the question without report as well on topics that require you to answer between a finite set of possibilities. "
                 "You must provide all the answers in Spanish.")

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
model  ='gemini-3.1-flash-lite-preview'
#selected_model = 'gemini-1.5-flash'
selected_model = 'gemma-4-31b-it'
selected_model = model

# --- Helper function to format Tableau data for LLM ---
def format_tableau_data_for_llm(data):
  """
    Formats Tableau data (Marks, DataTables, or dict of DataTables) into a concise
    string representation suitable for LLM input, with truncation for large datasets.
    """
  formatted_output = []

  if isinstance(data, list):  # Likely selected marks (list of Mark objects)
    formatted_output.append("Selected Marks:")
    if not data:
      formatted_output.append("  No marks selected.")
    for i, mark in enumerate(data):
      formatted_output.append(f"  Mark {i+1}:")
      if hasattr(mark, 'pairs'):
        # Extract fieldName and value from each pair
        mark_details = {pair.fieldName: pair.value for pair in mark.pairs}
        formatted_output.append(f"    {mark_details}")
      else:
        # Fallback if Mark structure is unexpected
        formatted_output.append(f"    {str(mark)}")

  elif isinstance(data, dict):  # Likely data from multiple worksheets (dict of DataTable objects)
    formatted_output.append("Data from Multiple Worksheets:")
    if not data:
      formatted_output.append("  No data found across worksheets.")
    for sheet_name, sheet_data in data.items():
      formatted_output.append(f"  Worksheet: {sheet_name}")
      if hasattr(sheet_data, 'columns') and hasattr(sheet_data, 'data'): # DataTable object
        columns = [col.fieldName for col in sheet_data.columns]
        formatted_output.append(f"    Columns: {columns}")
        formatted_output.append("    Rows (first 100):")
        # Limit the number of rows to send to avoid excessive token usage
        for i, row in enumerate(sheet_data.data[:100]):
          # Format row as a dictionary for clarity
          row_dict = {columns[j]: value for j, value in enumerate(row)}
          formatted_output.append(f"      {row_dict}")
          if i >= 99:
            formatted_output.append(f"      ... (truncated, {len(sheet_data.data) - 100} more rows)")
            break
        if not sheet_data.data:
          formatted_output.append("      No rows in this worksheet.")
      elif isinstance(sheet_data, list): # Simple list of data (e.g., list of dicts)
        formatted_output.append("    Rows (first 100):")
        for i, row in enumerate(sheet_data[:100]):
          formatted_output.append(f"      {row}")
          if i >= 99:
            formatted_output.append(f"      ... (truncated, {len(sheet_data) - 100} more rows)")
            break
        if not sheet_data:
          formatted_output.append("      No rows in this worksheet.")
      else:
        formatted_output.append(f"    Raw Sheet Data: {str(sheet_data)}") # Fallback for other types

  elif hasattr(data, 'columns') and hasattr(data, 'data'): # Single DataTable object
    formatted_output.append("Data from Worksheet:")
    columns = [col.fieldName for col in data.columns]
    formatted_output.append(f"  Columns: {columns}")
    formatted_output.append("  Rows (first 100):")
    for i, row in enumerate(data.data[:100]):
      row_dict = {columns[j]: value for j, value in enumerate(row)}
      formatted_output.append(f"    {row_dict}")
      if i >= 99:
        formatted_output.append(f"    ... (truncated, {len(data.data) - 100} more rows)")
        break
    if not data.data:
      formatted_output.append("  No rows in this worksheet.")

  else:
    formatted_output.append(f"Raw Data (unrecognized format): {str(data)}") # Generic fallback

  return "\n".join(formatted_output)

@anvil.server.callable
def generateDataSummary(prompt, data, **kwargs):
  if client is None:
    return "Error: El cliente de la API de Google no se pudo inicializar. Revisa los logs del servidor."
  if not prompt:
    return "Error: Please provide a question to analyze the data."
  if not data:
    return "Error: No data to analyze. Please select data in the Tableau dashboard."
  contents = [
    f"User Question: {prompt}",
    "Data for Analysis:",
    format_tableau_data_for_llm(data) # Use the helper function to format data
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