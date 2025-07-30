import random

def user_requests_gratitude_expression():
    answers = [
        'You\'re welcome!',
        'No problem!',
        'Anytime!',
        'Glad I could help!',
        'It\'s my pleasure!',
        'Don\'t mention it!',
        'Not a problem!',
        'I\'m happy to help!',
        'You\'re welcome, anytime!',
    ]
    return random.choice(answers)

if __name__ == '__main__':
    print(user_requests_gratitude_expression())