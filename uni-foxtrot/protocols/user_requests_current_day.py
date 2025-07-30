from datetime import datetime
import random

def user_requests_current_day(prev_answer=None):
    current_day = datetime.now().strftime("%A")
    
    if prev_answer == current_day:
        # If the previous answer is the same as the current day, we can return a simple response.
        responses = [
            f"Today is still {current_day}.",
            f"It hasn't changed, it's still {current_day}.",
            f"The day remains unchanged at {current_day}.",
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

if __name__ == "__main__":
    print(user_requests_current_day())