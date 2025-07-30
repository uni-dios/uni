from groq import Groq
from dotenv import load_dotenv
from flask import Flask, request, jsonify, render_template
from helpers.dbsqlite import sql
from datetime import datetime

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

    # Return the response.

    return response

@app.route("/uni/send-chat", methods=["POST"])
def send_chat_route():
    user_input = request.form.get("user_prompt")
    
    # Get the response from the chat model.
    response = send_chat_with_llm(user_input)
    
    # Insert the user's input into the database.
    sql("INSERT INTO messages (msg_role, msg_content) VALUES (?, ?)", ("user", user_input))
    
    # Save the assistant's response to the database.
    sql("INSERT INTO messages (msg_role, msg_content) VALUES (?, ?)", ("assistant", response))

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
        "js": ';scrollToTheTop();$("#user-input").focus()',
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

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5011)
    