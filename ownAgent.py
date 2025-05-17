
#need to create the reAct loop
#use cohere??
import re
import cohere
import json
co = cohere.Client('vjYSOGW1eb5SG7D8Sqk8cZX4ecmxpdfJC0dhbLza') 
import inspect
import psycopg2
from dotenv import load_dotenv
import os
import requests


# Load environment variables from .env
load_dotenv()

# Fetch variables
USER = os.getenv("user")
PASSWORD = os.getenv("password")
HOST = os.getenv("host")
PORT = os.getenv("port")
DBNAME = os.getenv("dbname")





#@tool
def fetch_schools_from_supabase() -> list:
    """
    Tool that allows you to fetch data of schools from the database.

    This function does not take any arguments. Any provided arguments should be ignored.
    All available schools are returned by default.

    Returns:
        list: A list containing information about all schools.
    """
    try:
        connection = psycopg2.connect(
            user=USER,
            password=PASSWORD,
            host=HOST,  # Need to fetch all these from Supabase details, and add to .env file
            port=PORT,
            dbname=DBNAME
        )
        print("Connection successful!")

        # Create a cursor to execute SQL queries
        cursor = connection.cursor()

        # Example query
        cursor.execute("SELECT * FROM schoolslatest")
        result = cursor.fetchall() #fetchone()
        print("Current Time:", result)

        # Close the cursor and connection
        cursor.close()
        connection.close()
        print("Connection closed.")

        #then need to return the schoolslatest list from result variable
        return result

    except Exception as e:
        print(f"Failed to connect: {e}")













def extract_action(response):
    # Regular expression to capture the action
    match = re.search(r'Action:\s*(.*)', response)
    if match:
        return match.group(1).strip()  # Extracted action string
    return None

def llm_reason(state):

    prompt = f"This is the existing context: {state['query']}. Think: What is the best way to achieve this? Action: (please provide a function call or action). The functions available to you are: (1) call_translation_api and (2) get_weather. return functions strictly as names, with no parameters or function brackets."

    response = co.chat(
    model="command-r",          # or "command-r-plus" / "command-r7b-12-2024" if you have access
    message=prompt,
    max_tokens=500,              # Set max output length
    )
    print("response.text inside of llm_reason is: " + str(response.text))

    return response.text



def call_translation_api(language, text_to_translate):
    if type(language) == str and type(text_to_translate) == str:
        return "your fake translation function has been successful!"

def get_weather(location: str):
    if type(location) == str:
        return f"the weather at {location} will be sunny! "


def get_function_parameters(func):
    """Retrieve the parameter names and default values of a function."""
    signature = inspect.signature(func)
    parameters = signature.parameters
    param_dict = {}
    for param_name, param in parameters.items():
        # Check if the parameter has a default value
        if param.default is param.empty:
            param_dict[param_name] = None  # Required parameter
        else:
            param_dict[param_name] = param.default  # Optional parameter with default value
    return param_dict

def determine_parameters(state, function):

    print("chosen function inside of determine_parameters is: " + str(function))

    function_params = get_function_parameters(function)
    print("Function parameters:", function_params)

    prompt = (
        f"You need to select the correct information in the user's query to be used as parameters for the function. "
        f"The function parameters are: {function_params}. "
        f"If the function parameters list is empty or contains only 'None', strictly return an empty dictionary: {{}}. "
        f"Do not infer any parameters from the user's query if the function takes no arguments. "
        f"The user's query is: {state['query']}. "
        "Return parameters in the format of: {\"parameter1\": \"chosen_parameter\", \"parameter2\": \"chosen_parameter2\"}, using the correct parameter names. if the parameters have int type hints, return them without string markers"
        )



    response = co.chat(
    model="command-r",          # or "command-r-plus" / "command-r7b-12-2024" if you have access
    message=prompt,
    max_tokens=500,              # Set max output length
    )
    print("response inside of determine__parameters is: " + str(response.text))

    try:
        parameters = json.loads(response.text)
        
        # If the function takes no arguments, force an empty dictionary
        if not function_params:
            print("Function has no parameters. Clearing any inferred parameters.")
            parameters = {}

    except json.JSONDecodeError:
        print("Failed to parse response as JSON. Returning empty dictionary.")
        parameters = {}


    return parameters #json.loads(response.text)


def perform_action(state, action):

  #for purpose of just testing and getting something to work, need to check if either action matches defined functions
  #if it does, call fake functions and return their response
  
  #you could probably make it dynamic, for function in function_list:

  match action:
    case 'call_translation_api':
        #need to now find right values for function parameters from user query
        parameters_for_function = determine_parameters(state, call_translation_api)
        print("parameters_for_function are: " + str(parameters_for_function))
        print("Type before API call:", type(parameters_for_function))
        result = call_translation_api(parameters_for_function['language_input'], parameters_for_function['text_to_translate'])
        print("result from call_translation_api is: " + str(result))
        return result
    case 'get_weather':
        parameters_for_function = determine_parameters(state, get_weather)
        print("parameters_for_function are: " + str(parameters_for_function))
        result = get_weather(parameters_for_function['location'])
        print("result from get_weather is: " + str(result))
        return result 

def assess_result(state):
    result = state.get('result')
    query = state.get('query')


    prompt = f"You need to assess whether the result sufficiently answers the user's query. Query: {query}. Result: {result}. If it does, return: 'Sufficient'. Otherwise, return: 'Insufficient'. You should return these without punctuation, simply one-word. "
    response = co.chat(
    model="command-r",          # or "command-r-plus" / "command-r7b-12-2024" if you have access
    message=prompt,
    max_tokens=500,              # Set max output length
    )
    print("response.text inside of assess_result functions is: ", response.text)
    cleaned_response = response.text.strip().rstrip("!.?")
    return cleaned_response




def is_goal_achieved(state):
    # Check if the result exists and is meaningful
    if state.get("result"):
        #use cohere llm to assess where value of 'result' sufficienty answers query
        #if so, return True, otherwise return False
        response = assess_result(state)
        print("response boolean inside of is_goal_achieved is: " + str(response))
        # Check the response strictly for "Sufficient" and "Insufficient"
        if response == 'Sufficient':
            print("Goal Achieved!")
            return True  
        elif response == 'Insufficient':
            print("Result insufficient.")
            return False
        else:
            print(f"Unexpected response: {response}")
    return False

def react_loop(input_text, max_iteration):
    state = { "query": input_text, "result": None }
    max_iteration = max_iteration
    iteration = 0

    print("state inside of react_loop is: " + str(state))

    while iteration < max_iteration:
        #step 1 - ask the LLM for reasoning and action
        response = llm_reason(state)  
        print("response inside of react_loop, after llm_reason is: " + str(response))

        action = response

         # Step 2: Extract action
        #action = extract_action(response)
        #print("action is:" + str(action))
        
        if action:
            print(f"Executing: {action}")
            # Step 3: Perform the action
            result = perform_action(state, action)  #need function for this
            print("result after perform_action is: " + str(result))
            # Step 4: Update state
            state["result"] = result
            
            # Check for completion
            if is_goal_achieved(state): #need something to do this
                print("Task Complete:", state["result"])
                return state["result"]
            else:
                print("No valid action found. Revisiting reasoning.")
        
        iteration += 1
        print("iteration is ... " + str(iteration))
    
    print("Failed to complete task after max iterations.")
    return None

#result = react_loop("What is the weather in London?", 10)
#print("result from react_loop functions is: "+ str(result))



class Agent():
    state = { "query": None, "result": None }

    def __init__(self, max_iteration=5):
        self.max_iteration = max_iteration
        #self.description = description
    
    def run(self, input_text):
        self.state["query"] = input_text
        
        print("state inside of Agent instance is: " + str(self.state))
        iteration = 0
        
        while iteration < self.max_iteration:
            #step 1 - ask the LLM for reasoning and action
            response = llm_reason(self.state)  
            print("response inside of react_loop, after llm_reason is: " + str(response))
            action = response

         # Step 2: Extract action
        #action = extract_action(response)
        #print("action is:" + str(action))
            if action:
                print(f"Executing: {action}")
            # Step 3: Perform the action
                result = perform_action(self.state, action)  #need function for this
                print("result after perform_action is: " + str(result))
            # Step 4: Update state
                self.state["result"] = result
            
            # Check for completion
                if is_goal_achieved(self.state): #need something to do this
                    print("Task Complete:", self.state["result"])
                    return self.state["result"]
                else:
                    print("No valid action found. Revisiting reasoning.")
        
                    iteration += 1
                    print("iteration is ... " + str(iteration))
    
        print("Failed to complete task after max iterations.")
        return None

trialAgent = Agent(4)
#result = trialAgent.run("what is the weather in London?")
#print("returned result from trialAgent is: " + str(result))

#next step - make functions dynamic, allow user to pass functions on Agent instance creation
#presumabky need to ad function parametr to perform_action: then use determine_parameters to get requried parameters
#then pass chosen parameters into function as an array of arguments, so its dynamic and variable based on however many 
#arguments the function requires

def llm_reason2(state, available_functions):
    
    print("llm_reason2 function was called.")
    print("available_functions inside of llm_reason2: " + str(available_functions))

    prompt = f"""This is the user's: {state['query']}. You've already done: {state['result']}. Think: What is the best way to achieve this? Think step by step. Break down complex expressions into simple operations. 
Evaluate one part at a time. Think: Does the query require calling a function, or can the answer be provided directly by you? Action: (please provide a function call or action). The functions available to you are: {available_functions}. Return only one function name, strictly as a single word, without parameters or brackets, or if no function is needed, return 'direct_response'."""

   



    print("prompt inside of llm_reason 2 is: " + str(prompt))

    response = co.chat(
    model="command-r",          # or "command-r-plus" / "command-r7b-12-2024" if you have access
    message=prompt,
    max_tokens=500,              # Set max output length
    )
    print("response.text inside of llm_reason is: " + str(response.text))

    return response.text

def add(a: int, b:int) -> int:
    a = int(a)
    b = int(b)
    print(f"value of params after being turned into ints: {a}, and {b}")
    return a + b

def multiply(a: int, b: int) -> int:
    a = int(a)
    b = int(b)
    return a * b






def perform_action2(available_functions, state, action):

  #for purpose of just testing and getting something to work, need to check if either action matches defined functions
  #if it does, call fake functions and return their response
  
  #you could probably make it dynamic, for function in function_list:
  print("action inside of perform_action2 is: " + str(action))
  print("available_functions inside of perform_action2 is: " + str(available_functions))
  #this prints 'add', so just function name

  #print("function in action is:" + (str(function)))
  if action == 'direct_response':
    print("Generating a direct response from LLM.")
    prompt = f"Provide a direct answer to the query: {state['query']}. The full context is: {state['result']}"
    response = co.chat(
        model="command-r",
        message=prompt,
        max_tokens=100,
    )
    return response.text.strip()
  
  # Find the function object based on the action name
  func = next((f for f in available_functions if f.__name__ == action), None)

  if func is None:
    print(f"Error: No function found with the name {action}")


    #if the action isn't a function call, just llm query, then need to carry it out here

    return None

  print(f"Found function: {func}")
  
  parameters_for_function = determine_parameters(state, func)
  print("paramaters_for_function valiue: " + str(parameters_for_function))
  #need to compare find right function from available_function using value of action
  #then need to use llm to assemble value for params from query (state.query)
  print("type of parameters_for_function is: ")
  print(type(parameters_for_function))

  #need to unpack parameters_for_functions, so can be passed to function
  action_result = func(**parameters_for_function)
  print("result from action_result inside of perform_action2 is: " + str(action_result))
  return action_result




def get_news(query: str):
    print("query passed to get_news by agent is: " + str(query))
    api_key = '4828a727596840cebc75e9f7f3ae239f'
    returned_item = requests.get(f'https://newsapi.org/v2/everything?q={query}&apiKey={api_key}')
    returned_item_jsoned = returned_item.json()
    #print("value of returned_item is: " + str(returned_item_jsoned))
    return returned_item_jsoned['articles']




class Agent2():
    state = { "query": None,"working_notes": None, "result": None }

    def __init__(self, description, available_functions, max_iteration=5):
        self.max_iteration = max_iteration
        self.description = description
        self.available_functions = available_functions
        print("Available functions before calling llm_reason2: ", self.available_functions)
    
    def run(self, input_text):
        self.state["query"] = input_text
        
        print("state inside of Agent instance is: " + str(self.state))
        iteration = 0
        
        print(f"iteration: {iteration}, max_iteration: {self.max_iteration}", flush=True)
        while iteration < self.max_iteration:
            #step 1 - ask the LLM for reasoning and action
            print("Calling llm_reason2 from Agent...", flush=True)
            response = llm_reason2(self.state, self.available_functions)  #need to pass availabke_functions to allow it to see
            print("response inside of react_loop, after llm_reason is: " + str(response))
            action = response

         # Step 2: Extract action
        #action = extract_action(response)
        #print("action is:" + str(action))
            if action:
                print(f"Executing: {action}")
            # Step 3: Perform the action
                result = perform_action2(self.available_functions, self.state, action)  #need dynamic function for this, then done
                print("result after perform_action is: " + str(result))
            # Step 4: Update state
                self.state["result"] = result
            
            #probably need a step to allow llm to assemble answer from working_notes
            
            # Check for completion
                if is_goal_achieved(self.state): #need something to do this
                    #if goal is achieved, make state['result'] equal value of assembled_answer
                    print("Task Complete:", self.state["result"])
                    return self.state["result"]
                else:
                    print("No valid action found. Revisiting reasoning.")

                    #push failed answer to working_notes key of state, as "Failed answer from iteration {iteration} was: assembled_answer"
        
                    iteration += 1
                    print("iteration is ... " + str(iteration))
    
        print("Failed to complete task after max iterations.")
        return None

trialAgent2 = Agent2("An agent to answer user's queries", [add, get_weather, fetch_schools_from_supabase, multiply, get_news], 3)
result2 = trialAgent2.run("In which city is York?")
print("returned result from trialAgent2 is: " + str(result2))

#this works with mathematic add function (provided you convert arguments generated by llm to integers)
#and works for weather function
#both dynamiclly passed by user to instance of Agent class

#works with direct_response, too

#and work on fixing problem with multi-part workflow, or understanding parameter types for functions

#borrow the openai Function Calling standard? pass tools as array with name, parameter descriptions
#that references tools defined elsewhere above

#add basic functions to get info on a stock and news

