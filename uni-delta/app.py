from groq import Groq
from dotenv import load_dotenv
from flask import Flask, request, jsonify, render_template, json
from helpers.dbsqlite import sql
from datetime import datetime
import re

import random


load_dotenv()

client = Groq()

app = Flask(__name__)


@app.route('/', methods=['GET'])
def chat():
    
    messages = sql("SELECT * FROM messages WHERE sum_id = 0 ORDER BY msg_id ASC")
    
    summaries = sql("SELECT * FROM summaries ORDER BY sum_id DESC")
    
    return render_template('index.html', messages=messages, summaries=summaries)


def send_chat_with_llm(user_input):
    
    summaries = sql("SELECT * FROM summaries ORDER BY sum_id DESC")
    
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
            "content": f"The first message in this conversation was sent on { first_message['msg_created'] }. That is when this current conversation started."
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
        messages=messages,
        model="llama-3.3-70b-versatile",
        max_tokens=1024,
        temperature=0.1,
    )

    response = chat_completion.choices[0].message.content
    return response


def get_intent_id_by_protocol(intent_protocol):
    
    # Make camel case and replace spaces with underscores for the intent name.
    intent_name = intent_protocol.replace("-", "_").lower().capitalize()
    
    intent = sql("SELECT * FROM intents WHERE int_protocol = ?", (intent_protocol,), single=True)
    
    if not intent:
        int_id = sql("INSERT INTO intents(int_protocol, int_name) VALUES (?, ?)", (intent_protocol, intent_name, ))
    else:
        int_id = intent['int_id']
    
    
    return int_id


def get_intent_protocol_by_id(int_id):
    
    intent = sql("SELECT * FROM intents WHERE int_id = ?", (int_id,), single=True)
    
    return intent['int_protocol']


def user_requests_current_time(prev_answer = None):

    current_time = datetime.now().strftime("%I:%M %p")
    
    if prev_answer == current_time:
        # If the previous answer is the same as the current time, we can return a simple response.
        responses = [
            f"The time is still {current_time}.",
            f"It hasn't changed, it's still {current_time}.",
            f"The time remains unchanged at {current_time}.",
            f"It's still {current_time} as before.",
            f"No change in time, it's still {current_time}.",
        ]
    else:
        # Let's come up with different responses using human language.
        responses = [
            f"The current time is {current_time}.",
            f"Right now, it is {current_time}.",
            f"Currently, the time is {current_time}.",
            f"It is now {current_time}.",
            f"The time at the moment is {current_time}.",
        ]

    return f"{random.choice(responses)}", current_time


def user_requests_current_day(prev_answer=None):

    current_day = datetime.now().strftime("%A")

    if prev_answer == current_day:
        # If the previous answer is the same as the current day, we can return a simple response.
        responses = [
            f"Today is still {current_day}.",
            f"It hasn't changed, it's still {current_day}.",
            f"The day remains unchanged at {current_day}.",
            f"It's still {current_day} as before.",
            f"It's still {current_day} as before.",
            f"No change in day, it's still {current_day}.",
        ]
    else:
        # Let's come up with different responses using human language.
        responses = [
            f"Today is {current_day}.",
            f"Right now, it is {current_day}.",
            f"Currently, it is {current_day}.",
            f"It is now {current_day}.",
            f"The day today is {current_day}.",
        ]

    return f"{random.choice(responses)}", current_day


def user_requests_current_date(prev_answer=None):

    current_date = datetime.now().strftime("%B %d, %Y")

    if prev_answer == current_date:
        # If the previous answer is the same as the current date, we can return a simple response.
        responses = [
            f"Today's date is still {current_date}.",
            f"It hasn't changed, it's still {current_date}.",
            f"The date remains unchanged at {current_date}.",
            f"It's still {current_date} as before.",
            f"No change in date, it's still {current_date}.",
        ]
    else:
        responses = [
            f"Today's date is {current_date}.",
            f"Right now, it is {current_date}.",
            f"Currently, it is {current_date}.",
            f"It is now {current_date}.",
            f"The date today is {current_date}.",
        ]
        
    return f"{random.choice(responses)}", current_date


def process_regex_commands(user_input):

    # This is where we would implement the RegEx command processing logic.

    detected_intent_id = 0
    
    if re.search(r'what\s+time\s+is\s+it(((\s+right)?\s+now)?)', user_input, re.IGNORECASE) or re.search(r'what(\'s|\s+is)\s+the\s+time(\s+now)?', user_input, re.IGNORECASE):
        detected_intent_id = get_intent_id_by_protocol("user_requests_current_time")
        return user_requests_current_time(), detected_intent_id
        
    elif re.search(r'what\s+day\s+is\s+it(\s+today)?', user_input, re.IGNORECASE):
        detected_intent_id = get_intent_id_by_protocol("user_requests_current_day")
        return user_requests_current_day(), detected_intent_id

    elif re.search(r'what(\'s|\s+is)\s+the\s+date(\s+today)?', user_input, re.IGNORECASE):
        detected_intent_id = get_intent_id_by_protocol("user_requests_current_date")
        return user_requests_current_date(), detected_intent_id

    elif re.search(r'^(((what|how)\s+about)|and)\s+now\W*', user_input, re.IGNORECASE) or re.search(r'^((do\s+it|run(\s+it)?|execute(\s+it)?)?(\s+it)?\s+)?again', user_input, re.IGNORECASE) or re.search(r'^again$', user_input, re.IGNORECASE):

        # We gather the last intent from the messages.
        last_intent_record = sql("SELECT * FROM messages WHERE sum_id = 0 AND msg_role = 'user' AND int_id != 0 ORDER BY msg_id DESC", single=True)
        
        # Debugging.
        print(f"Last Record ID: {last_intent_record['msg_id']}" if last_intent_record else "No last record found.")

        metadata = json.loads(last_intent_record['msg_metadata']) if last_intent_record and last_intent_record['msg_metadata'] else {}
        
        intent_protocol = metadata.get('int_protocol', None)
        intent_id = metadata.get('int_id', 0)
        answer = metadata.get('answer', None)

        # Call the protocol function if it exists.
        if intent_protocol:
            intent_function = globals().get(intent_protocol, None)
            if callable(intent_function):
                response = intent_function(answer)
                return (response, answer), intent_id

            else:
                return ("I don't know how to do that.", "unknown"), False

        else:
            return ("Sorry, I don't understand what you mean by that.", "unknown"), False

    else:
        return (False, False), False
    

@app.route("/uni/send-chat", methods=["POST"])
def send_chat_route():
    
    user_input = request.form.get("user_prompt")
    
    # This is where we interrupt with the RegEx engine to check for any special commands.
    (regex_response, answer), intent_id  = process_regex_commands(user_input)
    print(f"Regex Response: {regex_response}")
    
    intent = sql("SELECT * FROM intents WHERE int_id = ?", (intent_id,), single=True)
    
    if regex_response:
        response = regex_response
        msg_type = "regex"
    else:
        response = send_chat_with_llm(user_input)
        msg_type = "llm"
        
    metadata = {
        "int_id": intent_id,
        "int_protocol": intent['int_protocol'] if intent else None,
        "answer": answer,
    }
    
    metadata = json.dumps(metadata)
    
    # Insert the user's input into the database.
    sql("INSERT INTO messages (msg_role, msg_content, msg_metadata, int_id, msg_type) VALUES (?, ?, ?, ?, ?)", ("user", user_input, metadata, intent_id, msg_type, ))
    
    # Save the assistant's response to the database.
    sql("INSERT INTO messages (msg_role, msg_content, msg_type) VALUES (?, ?, ?)", ("assistant", response, msg_type, ))

    # Reload all messages from the database.
    db_messages = sql("SELECT * FROM messages WHERE sum_id = 0 ORDER BY msg_id ASC")
    
    summaries = sql("SELECT * FROM summaries ORDER BY sum_id DESC")
    
    # Return our JSON response.
    
    return jsonify({
        "htmls": {
            "#messages": render_template("messages.html", messages=db_messages, summaries=summaries)
        },
        "values": {
            "#user-input": "",
        },
        "js": ';scrollToTheTop();autosize.update($(".autosize"));$("#user-input").focus()',
    })


@app.route('/uni/summarize-conversation-prompt', methods=['POST'])
def summarize_conversation_prompt():
    
    return jsonify({
        "vbox": render_template('summarize_prompt.html'),
        "js": 'autosize($(".autosize"));',
    })
    
    
@app.route('/uni/generate-title', methods=['POST'])
def generate_title():
    
    db_messages = sql("SELECT * FROM messages WHERE sum_id = 0 ORDER BY msg_id ASC")

    message_stream = "\n\n".join([f"{msg['msg_role']}: {msg['msg_content']}" for msg in db_messages])

    messages = [
        {
            "role": "system", 
            "content": "You are a helpful assistant that generates titles for conversations."
        }, {
            "role": "user", 
            "content": f"""Generate a concise and descriptive title for the following conversation:\n{message_stream}.\n\nDo not include quotes or any other formatting. The title should be short, ideally no more than 10 words."""
        }
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
        {
            "role": "system", 
            "content": "You are a helpful assistant that generates summaries for conversations."
        }, {
            "role": "user", 
            "content": f"Generate a concise and descriptive summary for the following conversation:\n{message_stream}.\n\nDo not include quotes or any other formatting."
        }
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
        "js": 'autosize($(".autosize"));',
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
    
    summary_title = request.form['summary_title']
    summary_content = request.form['summary_content']

    # Insert the summary into the database.
    sum_id = sql("INSERT INTO summaries (sum_title, sum_content) VALUES (?, ?)", (summary_title, summary_content, ))

    # Update the messages to mark them as summarized and link them to the summary ID.
    sql("UPDATE messages SET sum_id = ? WHERE sum_id = 0", (sum_id,))

    return jsonify({
        'redirect': '/',
    })


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
    app.run(debug=True, host="0.0.0.0", port=5011)
    