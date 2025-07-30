from groq import Groq
from dotenv import load_dotenv
from flask import Flask, request, jsonify, render_template
from helpers.dbsqlite import sql

load_dotenv()

client = Groq()

app = Flask(__name__)

def send_chat(user_input):
    
    db_messages = sql("SELECT * FROM messages ORDER BY msg_id ASC")
    messages = []
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

@app.route('/', methods=['GET'])
def chat():
    
    messages = sql("SELECT * FROM messages ORDER BY msg_id ASC")
    
    return render_template('index.html', messages=messages)


@app.route("/uni/send-chat", methods=["POST"])
def send_chat_route():
    user_input = request.form.get("user_prompt")
    
    # Get the response from the chat model.
    response = send_chat(user_input)
    
    # Insert the user's input into the database.
    sql("INSERT INTO messages (msg_role, msg_content) VALUES (?, ?)", ("user", user_input))
    
    # Save the assistant's response to the database.
    sql("INSERT INTO messages (msg_role, msg_content) VALUES (?, ?)", ("assistant", response))

    # Reload all messages from the database.
    db_messages = sql("SELECT * FROM messages ORDER BY msg_id ASC")
    
    # Return our JSON response.
    
    return jsonify({
        "htmls": {
            "#chat-history": render_template("messages.html", messages=db_messages)
        },
        "values": {
            "#user-input": "",
        },
        "js": ';scrollToTheTop();',
    })
    

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5011)
    