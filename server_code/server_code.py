import anvil.secrets
import anvil.server
#### Mudando a la nueva librería
import google.generativeai as genai_old
from google import genai 
from google.genai import types 

GOOGLE_API_KEY = anvil.secrets.get_secret('gemini_api_key')

client = genai.Client(GOOGLE_API_KEY)

genai_old.configure(api_key=GOOGLE_API_KEY)
model_old = genai_old.GenerativeModel(model_name='gemini-1.5-flash', system_instruction=[
        "You are an expert analyst and know everything about data analysis",
        "You can interpret data in any form whether it's a single data point or a list of data with keys",
        "You are on a mission to provide the best data analysis report when asked",
        "You are capable of answering the question without report as well on topics that require you to answer between a finite set of possibilities",
    ])

system_prompt = [
  "You are an expert analyst and know everything about data analysis",
  "You can interpret data in any form whether it's a single data point or a list of data with keys",
  "You are on a mission to provide the best data analysis report when asked",
  "You are capable of answering the question without report as well on topics that require you to answer between a finite set of possibilities"
  ]



@anvil.server.callable
def generateDataSummaryOld(prompt, data):
  revised_prompt = f'''
  {prompt} + "\n\n" + {data}
  '''
  response = model_old.generate_content(revised_prompt)
  return response.text


def generateDataSummary(prompt, data):
  revised_prompt = f'''
  {prompt} + "\n\n" + {data}
  '''
  response = client.models.generate_content(
    model = 'gemini-2.5-flash', 
    contents = revised_prompt,
    config = types.GenerateContentConfig(
        system_instruction = system_prompt
    )
  )
  return response.text




