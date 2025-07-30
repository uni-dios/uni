from groq import Groq
from dotenv import load_dotenv
from flask import Flask, request, jsonify, render_template, json
import requests
from helpers.dbsqlite import sql
from datetime import datetime

import re
import os
import json
import importlib
import sys


load_dotenv()

client = Groq()

app = Flask(__name__)


@app.route('/', methods=['GET'])
def chat():

    messages = sql("SELECT * FROM messages WHERE sum_id = 0 ORDER BY msg_id ASC")

    summaries = sql("SELECT * FROM summaries ORDER BY sum_id DESC")

    return render_template('index.html', messages=messages, summaries=summaries)


### Chat Completion with LLM ###

def send_chat_with_llm(user_input):

    summaries = sql("SELECT * FROM summaries ORDER BY sum_id ASC")

    messages = []
    messages.append({
        "role": "system",
        "content": f"The following is a collection of summaries from previous conversations. Use them to inform your responses."
    })

    # Each summary is added to the messages list. This allows the LLM to have context from previous summaries.
    for summary in summaries:
        messages.append({
            "role": "system",
            "content": f"Title: {summary['sum_title']}\nSummary: {summary['sum_content']}\nDate: {summary['sum_created']}"
        })

    messages.append({
        "role": "system",
        "content": f"The summaries have completed. The following is your current conversation history. Use it to inform your responses."
    })

    db_messages = sql("SELECT * FROM messages WHERE sum_id = 0 ORDER BY msg_id ASC")

    first_message = db_messages[0] if db_messages else None
    if first_message:
        messages.append({
            "role": "system",
            "content": f"The first message in this conversation was sent on {first_message['msg_created']} UTC. That is when this conversation started."
        })

    for msg in db_messages:
        if msg['msg_role'] == 'user':
            messages.append({
                "role": "user",
                "content": msg['msg_content']
            })
        elif msg['msg_role'] == 'assistant':
            messages.append({
                "role": "assistant",
                "content": msg['msg_content']
            })

    # Add the new user input to the messages list.
    messages.append({
        "role": "user",
        "content": user_input
    })

    # Call our API:
    chat_completion = client.chat.completions.create(
        messages = messages,
        model="llama-3.3-70b-versatile",
        max_tokens=1024,
        temperature=0.1,
    )

    # Print the completion returned by the LLM.
    return chat_completion.choices[0].message.content


### INTENT MANAGEMENT FUNCTIONS ###

def get_intent_protocol_by_id(int_id):

    intent = sql("SELECT * FROM intents WHERE int_id = ?", (int_id,), single=True)
    return intent['int_protocol'] if intent else None


### REGEX FUNCTIONS ###

def user_requests_repetition():

    current_time = datetime.now().strftime("%I:%M %p")
    # We gather the last intent from the messages.
    last_intent_record = sql("SELECT * FROM messages WHERE sum_id = 0 AND msg_role = 'user' AND int_id != 0 ORDER BY msg_id DESC", single=True)
    print(f"Last Record ID: {last_intent_record['msg_id']}" if last_intent_record else "No last record found.")

    print(f"Last Intent Record: {last_intent_record}" if last_intent_record else "No last intent record found.")

    metadata = json.loads(last_intent_record['msg_metadata']) if last_intent_record and last_intent_record['msg_metadata'] else {}

    intent_protocol = metadata.get('int_protocol', None)
    intent_id = metadata.get('int_id', 0)
    answer = metadata.get('answer', None)

    # Call the protocol function if it exists.
    if intent_protocol:
        
        print(f" >>> Debugging: Intent Protocol: {intent_protocol}")
        intent_function = globals().get(intent_protocol, None)
        
        # Load up the protocol module dynamically if it exists.
        module_path = f"protocols/{intent_protocol}.py"
        
        path_exists = os.path.exists(module_path)
        print(f" >>> Debugging: Path exists: {path_exists}")
        is_callable = callable(intent_function)
        print(f" >>> Debugging: Is callable: {is_callable}")

        if path_exists:
            # Load up the module function in memory
            import importlib.util

            spec = importlib.util.spec_from_file_location(intent_protocol, module_path)
            protocol_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(protocol_module)

            intent_function = getattr(protocol_module, intent_protocol, None)

            print(f" >>> Debugging: Found intent function '{intent_protocol}' in static protocols module.")
            
            # This only works without parameters. Future functions should be updated to handle parameters.
            response = intent_function()
            print(f" >>> Debugging: Response from Intent Function: {response}")
            
            return (response, answer), intent_id

        else:
            return ("I don't know how to do that.", "unknown"), False

    else:
        return ("Sorry, I don't understand what you mean by that.", "unknown"), False


def process_regex_commands(user_input):

    # This is where we would implement the RegEx command processing logic.

    print("\n\n")

    detected_intent_id = 0

    regex_patterns = sql("SELECT * FROM regex_patterns")

    for pattern in regex_patterns:
        # Check if the user input matches the pattern.
        pattern_text = pattern['pat_regex']

        print(f" >>> Debugging: Regex Pattern: {pattern_text}")
        print(f" >>> Debugging: User Input: {user_input}")

        match = re.search(pattern_text, user_input, re.IGNORECASE)

        print(f" >>> Debugging: match: {match}")

        if not match:
            continue

        groups = match.groups() if match.groups() else []
        print(f" >>> Debugging: Groups from match: {groups}")

        # Get the intent ID for the matched pattern.
        detected_intent_id = pattern['int_id']
        print(f" >>> Debugging: Detected Intent ID: {detected_intent_id}")

        if detected_intent_id == 0:
            # This is where our `again` protocol comes into play.
            # Just call the again protocol.
            print(" >>> Debugging: Detected intent ID is 0, calling user_requests_repetition.")
            return user_requests_repetition()

        # Get the intent protocol by ID.
        intent_protocol = get_intent_protocol_by_id(detected_intent_id)
        print(f" >>> Debugging: Intent Protocol: {intent_protocol}")

        if not intent_protocol:
            continue

        # Let's find out if our function has been loaded yet.
        intent_function = globals().get(intent_protocol, None)

        if callable(intent_function):
            print(f" >>> Debugging: Found intent function '{intent_protocol}' in static regex_protocols module.")

            from inspect import signature
            sig = signature(intent_function)
            num_params = len(sig.parameters)
            print(f" >>> Debugging: Number of parameters in intent function: {num_params}")

            groups = match.groups()
            print(f" >>> Debugging: Groups from match: {groups}")

            if num_params == 0:
                response = intent_function()
                print(f" >>> Debugging: Response from Intent Function with no parameters: {response}")
            elif num_params == len(groups):
                response = intent_function(*groups)
                print(f" >>> Debugging: Calling intent function with parameters: {groups}")
            else:
                print(f" >>> Debugging: Number of parameters does not match, calling intent function with no parameters.")
                response = intent_function()

            print(f" >>> Debugging: Response from Intent Function: {response}")
            return (response, response), detected_intent_id

        # If the intent protocol is already loaded, we can directly call it.
        module_name = f"protocols.{intent_protocol}"
        mpodule_path = f"protocols/{intent_protocol}.py"

        if os.path.exists(mpodule_path):
            try:
                if module_name in sys.modules:
                    protocol_module = importlib.reload(sys.modules[module_name])
                else:
                    protocol_module = importlib.import_module(module_name)
                print(f" >>> Debugging: Protocol Module Loaded: {protocol_module}")

                intent_function = getattr(protocol_module, intent_protocol, None)

                if callable(intent_function):
                    print(f" >>> Debugging: Found intent function '{intent_protocol}' in dynamic protocol module.")

                    from inspect import signature
                    sig = signature(intent_function)
                    num_params = len(sig.parameters)
                    print(f" >>> Debugging: Number of parameters in intent function: {num_params}")

                    if num_params == 0:
                        response = intent_function()
                        print(f" >>> Debugging: Response from Intent Function with no parameters: {response}")
                    else:
                        response = intent_function(*match.groups())
                    
                    print(f" >>> Debugging: Response from Intent Function: {response}")
                    return (response, response), detected_intent_id

            except Exception as e:

                print(f" >>> Debugging: Error importing protocol module '{module_name}': {e}")
                return (False, False), False
            
            print(f" >>> Debugging: Protocol Module '{module_name}' does not have the intent function '{intent_protocol}'.")
            
            return (False, False), False
            
        else:

            # Now, we dynamically get the intent function from the protocol module.
            # Remember, the protocol module should have a function named as the intent protocol.

            print(" >>> Debugging: Intent function is not callable or does not exist.")
            return (False, False), False

    return (False, False), False


### LLM CHAT ROUTES ###

@app.route('/uni/send-chat', methods=['POST'])
def send_chat_route():
    
    user_input = request.form.get('user_prompt')
    
    # Remove anything between pairs of "```" triple backtick characters.
    # user_input = re.sub(r'```.*?```', '', user_input, flags=re.DOTALL).strip()
    
    # This is where we interrupt with the RegEx engine to check for any special commands.
    (regex_response, answer), intent_id  = process_regex_commands(user_input)
    print(f" >>> Debugging: regex_response: {regex_response}")
    print(f" >>> Debugging: answer: {answer}")
    print(f" >>> Debugging: intent_id: {intent_id}")

    msg_type = "llm"

    if regex_response:

        msg_type = "regex"
        
        if isinstance(regex_response, tuple) or isinstance(regex_response, list):
            response = regex_response[0]
        else:
            response = regex_response
        
    
    else:
        # Call it as a service on http://127.0.0.1:5012/process_syntactic_parsing
        api_call = f"http://127.0.0.1:5012/process_syntactic_parsing"
        
        # What comes back is this:
        # return jsonify({"message": intent_response, "success": True, "intent_id": intent_id}), 200

        
        response = requests.post(api_call, json={"user_input": user_input})
        
        print(f" >>> Debugging: Response: {response}")
        print(f" >>> Debugging: Response from syntactic parsing API: {response.text}")

        json_response = response.json()

        if testing := False:  # Change this to True to test the syntactic parsing.
            return jsonify({
                "vbox": "Stopping here to test.",
            })

        response = json_response.get("message", "") if json_response else ""
        if response:
            # it expects (syntactic_parse_response, intent_id) = process_syntactic_parsing(user_input)

            msg_type = "syntactic"
            
        else:

            response = send_chat_with_llm(user_input)
            msg_type = "llm"
        
    intent = sql("SELECT * FROM intents WHERE int_id = ?", (intent_id,), single=True)
        
    metadata = {
        "int_id": intent_id,
        "int_protocol": intent['int_protocol'] if intent else None,
        "answer": answer,
    }
    
    metadata = json.dumps(metadata)
    
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    print(f" >>> Debugging: response: {response}")
    
    # Insert both messages into the database.
    sql("INSERT INTO messages (msg_role, msg_content, msg_metadata, int_id, msg_created, msg_updated, msg_type) VALUES (?, ?, ?, ?, ?, ?, ?)", ('user', user_input, metadata, intent_id, current_time, current_time, msg_type))
    sql("INSERT INTO messages (msg_role, msg_content, msg_created, msg_updated, msg_type) VALUES (?, ?, ?, ?, ?)", ('assistant', response, current_time, current_time, msg_type))
    

    # Load all messages from the database and render them in the response.
    messages = sql("SELECT * FROM messages WHERE sum_id = 0 ORDER BY msg_id ASC")

    summaries = sql("SELECT * FROM summaries ORDER BY sum_id DESC")

    return jsonify({
        "htmls": {
            "#messages": render_template('messages.html', messages=messages, summaries=summaries),
        },
        "values": {
            "#user-input": "",
        },
        'js': ';scrollToTheTop();autosize.update($(".autosize"));$("#user-input").focus();',
    })


@app.route('/uni/summarize-conversation-prompt', methods=['POST'])
def summarize_conversation_prompt():
    
    return jsonify({
        "vbox": render_template('summarize_prompt.html'),
        "js": ';autosize($(".autosize")); ',
    })


@app.route('/uni/generate-title', methods=['POST'])
def generate_title():
    
    db_messages = sql("SELECT * FROM messages WHERE sum_id = 0 ORDER BY msg_id ASC")

    message_stream = "\n\n".join([f"{msg['msg_role']}: {msg['msg_content']}" for msg in db_messages])
    
    messages = [
        {"role": "system", "content": "You are a helpful assistant that generates titles for conversations."},
        {"role": "user", "content": f"Generate a concise and descriptive title for the following conversation:\n{message_stream}.\n\nDo not include quotes or any other formatting. The title should be short, ideally no more than 10 words."}
    ]

    title_completion = client.chat.completions.create(
        messages=messages,
        model="llama-3.3-70b-versatile",
        max_tokens=1024,
        temperature=0.1,
    )

    title = title_completion.choices[0].message.content.strip()

    return jsonify({
        'values': {
            '#summary-title': title,
        },
    })


@app.route('/uni/generate-summary', methods=['POST'])
def generate_summary():
    
    db_messages = sql("SELECT * FROM messages WHERE sum_id = 0 ORDER BY msg_id ASC")

    message_stream = "\n\n".join([f"{msg['msg_role']}: {msg['msg_content']}" for msg in db_messages])
    
    messages = [
        {"role": "system", "content": "You are a helpful assistant that generates summaries for conversations."},
        {"role": "user", "content": f"Generate a concise and descriptive summary for the following conversation:\n{message_stream}.\n\nDo not include quotes or any other formatting."}
    ]

    summary_completion = client.chat.completions.create(
        messages=messages,
        model="llama-3.3-70b-versatile",
        max_tokens=1024,
        temperature=0.1,
    )

    summary = summary_completion.choices[0].message.content.strip()

    return jsonify({
        'values': {
            '#summary-content': summary,
        },
        "js": ';autosize.update($(".autosize"));',
    })


@app.route('/uni/show_summary/<int:summary_id>', methods=['POST'])
def show_summary(summary_id):
    
    summary = sql("SELECT * FROM summaries WHERE sum_id = ?", (summary_id,), single=True)

    messages = sql("SELECT * FROM messages WHERE sum_id = ?", (summary_id,))

    return jsonify({
        "vbox": render_template('summary.html', summary=summary, messages=messages),
    })


@app.route('/uni/summarize-conversation', methods=['POST'])
def summarize_conversation():
    
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    summary_title = request.form['summary_title']
    summary_content = request.form['summary_content']

    # Insert the summary into the database.
    sum_id = sql("INSERT INTO summaries (sum_title, sum_content, sum_created, sum_updated) VALUES (?, ?, ?, ?)", (summary_title, summary_content, current_time, current_time))

    # Update the messages to mark them as summarized and link them to the summary ID.
    sql("UPDATE messages SET sum_id = ?, msg_updated = ? WHERE sum_id = 0", (sum_id, current_time))

    return jsonify({
        'redirect': '/',
    })


### L. E. A. R. N. Engine Routes ###
@app.route('/uni/open-learning-center', methods=['POST'])
def open_learning_center():
    return jsonify({
        "vbox": render_template('learning_center.html'),
        "js": ';autosize($(".autosize"));',
    })



def detect_if_regex_or_constituency_parsing(messages, learning_phrase):
    
    messages.append({"role": "system", "content": """You are a helpful assistant that determines if a phrase can be handled as a RegEx pattern or Constituency Parsing pattern."""})
    messages.append({"role": "user", "content": f"""Can the following phrase be handled as a RegEx pattern or Constituency Parsing pattern?
If it's short, and seems like a simple command, it should be a RegEx pattern.
If it's more complex, or deals with attributes of entities belonging to the user, like his cats, or computers, it should be a Constituency Parsing pattern.

The phrase is: {learning_phrase}

Only respond with "RegEx" or "Constituency Parsing" based on your analysis of the phrase, without the quotes.
"""})

    # Process the learning phrase
    # First, we ask the LLM if this can be handled s a RegEx pattern or Constituency Parsing pattern?
    
    # Get the database examples for RegEx patterns and Constituency Parsing patterns.
    
    llm_response = client.chat.completions.create(
        messages=messages,
        model="llama-3.3-70b-versatile",
        max_tokens=1024,
        temperature=0.3,
    )
    
    llm_response_content = llm_response.choices[0].message.content.strip()

    return messages, llm_response_content


def generate_initial_regex_pattern(messages, learning_phrase):
    
    regex_patterns = sql("SELECT * FROM regex_patterns")
    
    # Generate a RegEx pattern for the learning phrase.
    current_regex_patterns = [pattern['pat_regex'] for pattern in regex_patterns]

    messages.append({"role": "system", "content": "You are a helpful assistant that generates RegEx patterns. These are the currently existing RegEx patterns: " + ", ".join(current_regex_patterns)})
    
    messages.append({"role": "user", "content": f"""Generate a similar RegEx pattern that matches the following phrase: {learning_phrase})

Make sure that you only output the pattern. Include robust variations. For example, use the existing patterns as a reference. Only return back the pattern itself, without any additional text or explanation. Do not include improper grammar patterns. Make sure the RegEx is correct as well. Match groups should be used where appropriate, and the pattern should be robust enough to match variations of the phrase. Use `\\s+` like the other patterns for space characters between words. Always include the space at the beginning for each optional word or word group. 

For example, for the phrase "Hello, there!", we would use "hello", "hi", and "hey" as they are common greeting phrase starters. We would then add an optional comma right after, and then an optional group of words that start with a space character to make it easier to parse. The pattern would most likely follow this pattern in this case: `^(hello|hi|hey)(,)?(\\s+there|\\s+you)?$` This patterns fits our rules. The word `here` doesn't make sense to be optional, as it's strange to say, "hello here". It starts with a mandatory key word, has an optional comma, followed by a group of optional words with their own space character for easy parsing. Don't forget optional punctuation at the end.

Output must be in json format like this:

{{
    "pattern": "^words in the pattern( with optional text)?$",
    "groups": ["group1", "group2", ...],
}}

No ticks or special characters around the pattern. Just the proper JSON formatted pattern itself and the groups it matches. Use escape characters on special characters like quotes, backslashes, etc. in the pattern.

Make sure that JSON values have double quotes around them, not single quotes. The groups should be the names of the groups in the RegEx pattern.
"""})
    
    llm_response = client.chat.completions.create(
        messages=messages,
        model="llama-3.3-70b-versatile",
        max_tokens=1024,
        temperature=0.0,
    )
    
    pattern_response = llm_response.choices[0].message.content.strip()
    return messages, pattern_response


def match_original_learning_phrase(messages, learning_phrase, pattern_response, groups=[]):


    messages.append({"role": "user", "content": f"Is the following RegEx pattern correct? {pattern_response}\n\nCan it be used to match the learning phrase: {learning_phrase}? The detected groups are: {", ".join(groups) if groups else "None"}. Only reply with the correct RegEx pattern."})

    llm_response = client.chat.completions.create(
        messages=messages,
        model="llama-3.3-70b-versatile",
        max_tokens=1024,
        temperature=0.0,
    )

    llm_response_content = llm_response.choices[0].message.content.strip()
    return messages, llm_response_content


def get_positive_examples_from_llm(messages, pattern_response):
    
    # These patterns then get tested against a variety of positive and negative examples to ensure they work as expected. These tests can also be generated by the LLM based on the phrase provided. For example, for the phrase "Hello!", the tests could be:
    # - Positive: "Hello!", "Hi!", "Hey!", "Greetings!"
    # - Negative: "Goodbye!", "See you later!", "Farewell!", "Highlander!", "Hey is for horses!", "What's up?", "I said, hi!", etc...

    messages.append({"role": "user", "content": f"""Generate a set of positive examples for the following RegEx pattern: {pattern_response}.

Make sure to include variations of the learning phrase that should match the pattern.

Return back the examples as a list of positive examples, like this:

`["Example one", "Example two", ...]` for positive examples and `["Example one", "Example two", ...]` for negative examples."""})
    
    llm_response = client.chat.completions.create(
        messages=messages,
        model="llama-3.3-70b-versatile",
        max_tokens=4000,
        temperature=0.0,
    )

    positive_examples = llm_response.choices[0].message.content.strip()
    return messages, positive_examples


def get_negative_examples_from_llm(messages, pattern_response):
    
    messages.append({"role": "user", "content": f"""Generate a set of negative examples for the following RegEx pattern: {pattern_response}.

Make sure to include variations of the learning phrase that should not match the pattern.

Return back the examples as a list of negative examples, like this:

`["Example one", "Example two", ...]` for positive examples and `["Example one", "Example two", ...]` for negative examples."""})

    llm_response = client.chat.completions.create(
        messages=messages,
        model="llama-3.3-70b-versatile",
        max_tokens=1024,
        temperature=0.0,
    )
    
    negative_examples = llm_response.choices[0].message.content.strip()
    return messages, negative_examples


def get_function_name_and_intent(messages, learning_phrase):
    
    current_intents = sql("SELECT * FROM intents WHERE int_protocol LIKE 'user_request_%'")
    intents_text = ", ".join([intent['int_protocol'] for intent in current_intents])
    
    messages.append({
        "role": "user",
        "content": """Come up with a good function name that encompasses the intent of the user request. If the user is asking for time, use `user_requests_current_time`. If user asks to perform some function, the intent name should be more like `user_request_[some_function]`. Current intents are the following: """ + intents_text + """. Make sure the name of the function is not used anywhere else. Just return the function name in lower case with underscores, without any quotes or other formatting. For example, if the user is asking for the weather, the function name should be `user_requests_current_weather`. Only return back the code as a standalone file."""})
    
    llm_response = client.chat.completions.create(
        messages=messages,
        model="llama-3.3-70b-versatile",
        max_tokens=1024,
        temperature=0.0,
    )
    
    llm_response_content = llm_response.choices[0].message.content.strip()
    
    return messages, llm_response_content


def generate_code_from_intent(messages, llm_response_content):
    messages.append({
        "role": "assistant",
        "content": f"""Generate an output of code that will be directly stored in a file. The code should be a properly formatted code block using triple backticks on the lines before and after. The code is composed of required imports, only if any, the function body defined with the name {llm_response_content}, and a closing guard. The function body implements the intent of the user request. The code should be in Python 3.10+ syntax, and should not include any comments or explanations. The code should be ready to be executed as a standalone file. Do not include any additional text or explanation, just the code itself.
        
Do NOT match the regex inside the function. That is handled before the function is even called. The functions simply generates and answer and responds.

The function should generate a list of human readable formatted answers that are relevant to the intent of the user request. One random answer should be returned from the list of answers. The function should not return any other data, just the answer itself as a string.

Do not get the API key from the OS environment. It will be a variable in the code itself. Do not use `os.getenv` to get the API key. Set the API key as `api_key = 'your_api_key_here'` or something similar. We do not use variables from the OS environment for the purpose of this demo.

If the user asks for something dynamic, like the weather, we need to account for that in our pattern as well. We use API calls to get the weather information in the code when creating the Python protocol file. When creating the function, we will use API calls to get the weather information. Default the city name to London.

The returning function should have no parameters passed into the function.

Do not use any non utf-8 characters. Try using HTML characters for special characters, such as the degree symbol.

Wrap non group words in `?:...` so they don't produce extra groups.

The __main__ clause should print out what the function returns for testing purposes.

The list should be generated on multiple lines, depending on the variety of answers that can be generated. The function should not return any other data, just the answer itself as a string.""",
    })
    
    llm_response = client.chat.completions.create(
        messages=messages,
        model="meta-llama/llama-4-scout-17b-16e-instruct",
        max_tokens=4000,
        temperature=0.0,
    )
    
    llm_response_content = llm_response.choices[0].message.content.strip()
    
    # Erase everything up to the line with triple ticks, including the line itself. Afterwards, get the content until the end of the code block marked by another set of triple ticks "```"
    lines = llm_response_content.splitlines()
    code_block = ""
    in_code_block = False
    for line in lines:
        if line.startswith("```"):
            if in_code_block:
                break  # End of code block
            else:
                in_code_block = True  # Start of code block
                continue
        if in_code_block:
            code_block += line + "\n"

    return code_block


def code_verification_response(messages, code_block, intent_name):
    
    # If the code block has requirements inside, like an API key or registration, let the user know.
    
    messages.append({
        "role": "user",
        "content": f"""Does the code block require any additional information from the user, like an API key, registration, or other requirements? If so, please return a message that explains what the user needs to do to use this code block. If not, just return 'No'.""",
    })
    
    print(f" >>> Debugging: Code Block for verification: {code_block}")
    
    llm_response = client.chat.completions.create(
        messages=messages,
        max_tokens=1024,
        model="llama-3.3-70b-versatile",
        temperature=0.0,
    )
    
    llm_response_content = llm_response.choices[0].message.content.strip()
    
    print(f" >>> Debugging: Additional Info: {llm_response_content}")
    
    messages.append({
        "role": "assistant",
        "content": llm_response_content,
    })
    
    # Send another request to extract the parts of the code that need replacement. For example, location, or API key or any other data. Only replace the value. Extract the parts that need replacement with the LLM.
    
    messages.append({
        "role": "user",
        "content": f"""Extract the parts of the code block that need replacement with user input. For example, if the code block has an API key, or a location, or any other data that needs to be replaced with user input, extract those parts and return them as a list of strings. If there are no parts that need replacement, return an empty list. Only return the list of strings without any additional text or explanation. The code block is: \n\n{code_block}.\n\nOnly output the list of strings, without any additional text or explanation, as such `["\"London\"", "\"your_openweathermap_api_key\""]`. This ensures that we match the parts that need replacement with user input. If there are no parts that need replacement, return an empty list as `[]`. Thank you.""",
    })
    
    llm_response = client.chat.completions.create(
        messages=messages,
        max_tokens=1024,
        model="llama-3.3-70b-versatile",
        temperature=0.0,
    )
    
    llm_response_content = llm_response.choices[0].message.content.strip()
    
    print(f" >>> Debugging: Parts that need replacement: {llm_response_content}")
    
    # Convert what comes back as JSON list.
    try:
        json_list = json.loads(llm_response_content)
    except json.JSONDecodeError:
        json_list = []
        
    print(f" >>> Debugging: JSON List: {json_list}")

    messages.append({
        "role": "assistant",
        "content": f"""The parts that need replacement are: {json_list}."""
    })


    return json_list


def test_protocol(messages, intent_name):
    # Now, we test the file to see if the protocol returns anything.
    try:
        # Dynamically import the protocol file based on the intent name.
        print(f" >>> Debugging: Importing protocol module for intent: {intent_name}")
        
        module_name = f"protocols.{intent_name}"
        
        print(f" >>> Debugging: Module Name: {module_name}")
        
        if module_name in sys.modules:
            protocol = importlib.reload(sys.modules[module_name])
        else:
            protocol = importlib.import_module(module_name)
            
        print(f" >>> Debugging: Protocol module imported successfully: {protocol}")
        
        # Call the function with no parameters dynamically based on the intent name.
        response = getattr(protocol, intent_name)()

        print(f" >>> Debugging: Protocol response: {response}")
        
        messages.append({
            "role": "assistant",
            "content": f"""The test returns:\n\n{response}.""",
        })
        
    except Exception as e:
        # If the request is something that the system cannot handle, it should return a message saying that it cannot handle the request.
        
        print(f" >>> Debugging: Error while importing protocol: {e}")
        
        messages.append({
            "role": "assistant",
            "content": f"""There was an error while importing the protocol: {e}. Please check the code and try again.""",
        })


def save_the_protocol_file(messages, intent_name, code_block):
    os.makedirs('protocols', exist_ok=True)

    with open(f'protocols/{intent_name}.py', 'w', encoding='utf-8') as f:
        f.write(code_block)
    
    print(f" >>> Debugging: Saved the protocol file for intent: {intent_name}")

    messages.append({
        "role": "user",
        "content": f"""Let's test the function and code by calling it."""
    })


@app.route('/uni/send-learning-phrase', methods=['POST'])
def send_learning_phrase():
    
    learning_phrase = request.form['learning_phrase']
    
    messages = []

    ###############################################
    ### DETECT_IF_REGEX_OR_CONSTITUENCY_PARSING ###
    ###############################################
    messages, llm_response_content = detect_if_regex_or_constituency_parsing(messages, learning_phrase)

    messages.append({"role": "assistant", "content": llm_response_content})
    print(f" >>> Debugging: LLM Response Content: {llm_response_content}")

    # If simple enough, it should be a RegEx pattern. More complex, or dealing with attributes of entities belonging to the user, like his cats, or computers should be a Constituency Parsing pattern.

    
    if llm_response_content == "RegEx":
        
        # If regex pattern, as the LLM to generate a RegEx pattern for it that is similar to existing patterns from our database. For example, for the phrase, "Hello!" the system should understand that it's a greeting and generate a RegEx pattern like `^hello!$` or `^hi!$` or other greeting patterns such as `^hey!$` or `^greetings!$`.

        ######################################
        ### GENERATE_INITIAL_REGEX_PATTERN ###
        ######################################
        print(f" >>> Debugging: Generating Initial RegEx Pattern for Learning Phrase: {learning_phrase}")
        messages, pattern_response = generate_initial_regex_pattern(messages, learning_phrase)
        pattern_response = pattern_response.replace('\\', '\\\\')  # Escape backslashes for JSON compatibility.
        
        print(type(pattern_response))

        print(f" >>> Debugging: Generated Pattern Response: {pattern_response}")

        pattern_response_json = json.loads(pattern_response)
        pattern_text = pattern_response_json.get("pattern", "")
        pattern_groups = pattern_response_json.get("groups", [])

        print(f" >>> Debugging: Generated RegEx Pattern: {pattern_text}")
        print(f" >>> Debugging: Generated RegEx Groups: {", ".join(pattern_groups) if pattern_groups else "None"}")
        messages.append({"role": "assistant", "content": pattern_response})
        
        # Next. We ask the LLM if the pattern is correct and if it can be used to match the learning phrase. If it is a RegEx pattern, we can test it against the learning phrase. It should be able to generate the correct RegEx pattern.
        
        ######################################
        ### MATCH ORIGINAL LEARNING PHRASE ###
        ######################################
        print(f" >>> Debugging: Matching Original Learning Phrase: {learning_phrase} with Pattern: {pattern_text}")
        messages, llm_response_content = match_original_learning_phrase(messages, learning_phrase, pattern_text, groups=pattern_groups)
        
        # Test against the original sentence.
        if re.search(pattern_text, learning_phrase):
            print(" >>> Debugging: The generated RegEx pattern matches the learning phrase.")
            
        
        # Future code. If it doesn't pass, go back and request to generate again.
        messages.append({"role": "assistant", "content": llm_response_content})
        
        # We pass the original test, but now we need to generate some similar tests.
        
        ######################################
        ### GET_POSITIVE_EXAMPLES_FROM_LLM ###
        ######################################
        messages, positive_examples = get_positive_examples_from_llm(messages, pattern_text)
        print(f" >>> Debugging: Generated Positive Examples: {positive_examples}")

        pos_examples_json = json.loads(positive_examples)

        # Let's loop through the positive examples and validate them against the RegEx pattern.
        for example in pos_examples_json:
            if not re.search(pattern_response, example):
                print(f" >>> Debugging: Example '{example}' does not match the RegEx pattern '{pattern_response}'")
            else:
                print(f" >>> Debugging: Example '{example}' matches the RegEx pattern '{pattern_response}'")

        messages.append({"role": "assistant", "content": positive_examples})

        # Now we generate negative examples.

        ######################################
        ### GET_NEGATIVE_EXAMPLES_FROM_LLM ###
        ######################################
        messages, negative_examples = get_negative_examples_from_llm(messages, pattern_text)
        print(f" >>> Debugging: Generated Negative Examples: {negative_examples}")

        neg_examples_json = json.loads(negative_examples)

        messages.append({"role": "assistant", "content": negative_examples})
        
        for example in neg_examples_json:
            if not re.search(pattern_text, example):
                print(f" >>> Debugging: Example PASS '{example}' does not match the RegEx pattern '{pattern_text}'")
            else:
                print(f" >>> Debugging: Example FAIL '{example}' matches the RegEx pattern '{pattern_text}'")
                # We can log this or handle it as needed.

        # If the tests pass, then, we ask the question if the request is something that the system can handle? In the case of asking for the weather, the system would understand that it could possibly generate code, save as a file, connect it to a protocol, and then execute it to get the weather information. Upon success, the user can validate the pattern and "teach it" to the system by saving all extracted information.
        
        # Detect intent first.

        ####################################
        ### GET_FUNCTION_NAME_AND_INTENT ###
        ####################################
        messages, intent_name = get_function_name_and_intent(messages, learning_phrase)
        print(f" >>> Debugging: Detected Function Name and Intent: {intent_name}")

        messages.append({
            "role": "assistant",
            "content": intent_name,
        })
        
        #################################
        ### GENERATE_CODE_FROM_INTENT ###
        #################################
        code_block = generate_code_from_intent(messages, intent_name)
        code_block = code_block.strip("```python").strip("```").strip()
        code_block = code_block.strip()
        print(f" >>> Debugging: Generated Code Block: {code_block}")

        messages.append({
            "role": "assistant",
            "content": code_block,
        })
        
        # Save the output to a file under "protocols" directory. If it doesn't exist, create it.
        ##############################
        ### SAVE_THE_PROTOCOL_FILE ###
        ##############################
        save_the_protocol_file(messages, intent_name, code_block)
        
        # Add a step where we look in the file to see if the user has to provide information. Signup, API Keys, or other requirements.
        
        replacement_list = code_verification_response(messages, code_block, intent_name)
        print(f" >>> Debugging: Replacement List: {replacement_list}")
        
        # If the replacement list is empty, test the protocol file to see if it works as expected.

        print(" >>> Debugging: No replacements needed. Testing the protocol file.")
        
        test_protocol(messages, intent_name)
        
        # If the test succeeds, we need to store the intent and the protocol record in the regex_patterns table.

        new_intent_id = sql("INSERT INTO intents (int_protocol, int_name) VALUES (?, ?)", (intent_name, intent_name, ))
        
        pattern_text = pattern_text.replace("\\\\", "\\")

        sql("INSERT INTO regex_patterns (pat_regex, int_id) VALUES (?, ?)", (pattern_text, new_intent_id))

        # Save message stream to a temp file.
        os.makedirs('temp', exist_ok=True)
        with open(f"temp/{intent_name}_messages.json", 'w', encoding='utf-8') as f:
            json.dump(messages, f, indent=4)

        if not replacement_list:
            
            return jsonify({
                "htmls": {
                    "#user_requirements_form": "Success testing the protocol file.",
                },
            })
            
        else:

            form_html = render_template("api_requirements.html", replacements=replacement_list, file_name=intent_name)
        
            return jsonify({
                'success': True,
                'message': 'Learning phrase submitted successfully.',
                'htmls': {
                    '#user_requirements_form': form_html
                },
            })


    elif llm_response_content == "Constituency Parsing":
        
        # If constituency parsing, we should ask the LLM to generate a sentence structure that can be used to identify the phrase in the user's messages. For example, for the phrase, "I have a cat", the system should understand that it's a possession intent and generate a sentence structure like `S -> NP VP`, where NP is the noun phrase and VP is the verb phrase.
        
        # We can extract intents and entities, and the intent names should follow the current provided standard of functions. For greetings, it would be something like, "user_greeting" and for weather check it would be something like "user_requests_current_weather". Parameters should be handled as well if necessary, such as for location, or day, or date range.
        
        # We do this one later. It's more complicated. We'll have to use things like "subect, root verb, and object", along with parts of sentence. "I have a cat." would essentially be parsed as:
        # subject = "I"
        # intent_verb = "have" (root)
        # intent = "user_informs_of_possession"
        # quantifier = 1 (if "a" or "an" is present)
        # object = any recognized subject, mixed in with a category lexicon like WordNet to identify actions performed on the objects.
        pass
    

    return jsonify({
        'success': True,
        'message': 'Learning phrase submitted successfully.',
    })


@app.route('/uni/send-api-requirements', methods=['POST'])
def send_api_requirements():
    
    requirements = request.form
    
    file_name = ""
    requirements_list = []
    
    for req in requirements:
        print(f" >>> Debugging: Requirement: {req} - Value: {requirements[req]}")
        
        if req == "file_name":
            file_name = requirements[req]
    
        else:
            # name and ID are like this: api_requirement_your_openweathermap_api_key
            # We store the key value of requirements in a list.
            requirements_list.append({
                "key": req,
                "value": requirements[req],
            })
            
            print(f" >>> Debugging: Requirement Key: {req}, Value: {requirements[req]}")
    
    print(f" >>> Debugging: File Name: {file_name}")
    print(f" >>> Debugging: Requirements List: {requirements_list}")
    
    # Now we can open up the file and replace the placeholders with the values from the requirements list.
    file_path = f"protocols/{file_name}.py"

    # Get the file content. Assume the file exists.
    with open(file_path, 'r', encoding='utf-8') as file:
        file_content = file.read()
    
        
    # Replace the placeholders in the file content with the values from the requirements list.
    for req in requirements_list:
        
        if not req['key'] or req['key'] == "" or req['key'] == "undefined" or req['key'] == "submit":
            print(f" >>> Debugging: Skipping requirement with empty key or value: {req}")
            continue
        
        replace_me = req['key'].replace("api_requirement_", "").strip()
        replace_value = req['value']

        print(f" >>> Debugging: Replacing placeholder {replace_me} with value: {replace_value}")

        file_content = file_content.replace(replace_me, replace_value)

    # Save the modified file content back to the file.
    with open(file_path, 'w', encoding='utf-8') as file:
        file.write(file_content)
        
    intent_name = file_name
    
    # Load messages from the temp file.
    with open(f"temp/{intent_name}_messages.json", 'r', encoding='utf-8') as f:
        messages = json.load(f)
    
    test_protocol(messages, file_name)
    
    return jsonify({
        'success': True,
        'message': 'API requirements sent successfully.',
        'vbox': "Success!",
    })

### TEMPLATE FILTERS ###

@app.template_filter('datetimeformat')
def datetimeformat(value):
    return value.strftime("%a %b %#d, %Y @ %#I:%M %p")


@app.template_filter('escape_html_chars')
def escape_html_chars(text):

    if not text:
        return text

    # Check if the text has an image tag in it. If so, avoid that tag.
    if "<img" in text:
        return text


    return text.replace("<", "&lt;").replace(">", "&gt;")


def detect_code_language(code):

    if re.search(r'\bdef\b|\bimport\b|\bclass\b|\bself\b|#', code):
        return "python"
    elif re.search(r'<[a-zA-Z]+>|<\/[a-zA-Z]+>', code):
        return "html"
    elif re.search(r'{.*?}|[a-z-]+:\s*[^;]+;', code):
        return "css"
    elif re.search(r'\bfunction\b|\bvar\b|\blet\b|\bconst\b|=>', code):
        return "javascript"
    else:
        return "unknown"


@app.template_filter('singleticks')
def singleticks(text):

    def process_non_code_blocks(match):

        # Get the block from the match.
        block = match.group(0)

        # If the block starts with a code block, ignore it.
        if block.startswith("<code>"):

            # Ignore code blocks
            return block  # Ignore code blocks

        # Use regex to identify code blocks created by `singleticks` and other text
        return re.sub(r'`(.*?)`', r'<code>\1</code>', block)

    # Use regex to identify code blocks created by `tripleticks` and other text
    return re.sub(r'(<code>.*?</code>|[^<]+)', process_non_code_blocks, text, flags=re.DOTALL)


@app.template_filter('tripleticks')
def tripleticks(text):

    lines = text.splitlines()
    in_code_block = False
    result = []
    buffer = []  # To accumulate code content for language detection

    for line in lines:
        if line.startswith("```"):
            if in_code_block:
                language = detect_code_language("\n".join(buffer))
                result.append(f'<code class="{language}">' + "\n".join(buffer) + "</code>")
                buffer = []
                in_code_block = False
            else:
                in_code_block = True
        elif in_code_block:
            buffer.append(line)
        else:
            result.append(line)

    if in_code_block and buffer:
        language = detect_code_language("\n".join(buffer))
        result.append(f'<code class="{language}">' + "\n".join(buffer) + "</code>")

    return "\n".join(result)


@app.template_filter('replace_tabs_and_spaces')
def replace_tabs_and_spaces_raw(text):

    if not text:
        return text

    lines = text.splitlines()
    result = []

    for line in lines:
        # Replace spaces at the beginning of the line with &nbsp;
        leading_spaces = len(line) - len(line.lstrip(' '))
        line = '&nbsp;' * leading_spaces + line.lstrip(' ')

        # Replace \t with a tab element or two &nbsp;
        line = line.replace('\t', '&nbsp;&nbsp;&nbsp;&nbsp;')

        result.append(line)

    return '\n'.join(result)


@app.template_filter('bold_asterisks')
def bold_asterisks(text):

    if not text:
        return text

    return_text = text
    return_text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', return_text)
    # Make LI tags
    return_text = return_text.replace("&nbsp;&nbsp;&nbsp;&nbsp;* ", "&nbsp;&nbsp;&nbsp;&nbsp;<i class=\"fas fa-circle\"></i> ")
    # return_text = return_text.replace("* ", "<i class=\"fas fa-circle\"></i> ")

    return return_text



if __name__ == "__main__":
    app.run(debug=False, host='0.0.0.0', port=5011)