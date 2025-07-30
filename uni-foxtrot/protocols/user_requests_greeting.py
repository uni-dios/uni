import random

def user_requests_greeting():
    answers = [
        "Hello! How can I assist you today?",
        "Hi there! What's on your mind?",
        "Hey! How are you doing today?",
        "Hello! It's nice to meet you.",
        "Hi! I'm here to help with any questions you may have.",
        "Hey there! What's up?"
    ]
    return random.choice(answers)

if __name__ == "__main__":
    print(user_requests_greeting())