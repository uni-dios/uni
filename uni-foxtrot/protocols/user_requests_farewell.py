import random

def user_requests_farewell():
    answers = [
        "Goodbye!",
        "See you later!",
        "Bye for now!",
        "Farewell!",
        "Until next time!",
        "Take care!",
        "Have a great day!",
        "See you soon!",
        "Bye!",
        "Goodbye for now!"
    ]
    return random.choice(answers)

if __name__ == "__main__":
    print(user_requests_farewell())