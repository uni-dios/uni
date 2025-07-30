from datetime import datetime
import random

def user_requests_current_time(prev_answer=None):
    current_time = datetime.now().strftime("%I:%M %p")
    
    if prev_answer == current_time:
        # If the previous answer is the same as the current time, we can return a simple response.
        responses = [
            f"The time is still {current_time} EST/EDT.",
            f"It hasn't changed, it's still {current_time} EST/EDT.",
            f"The time remains unchanged at {current_time} EST/EDT.",
            f"It's still {current_time} EST/EDT as before.",
            f"No change in time, it's still {current_time} EST/EDT.",
        ]
    else:
        # Let's come up with different responses using human language.
        responses = [
            f"The current time is {current_time} EST/EDT.",
            f"Right now, it is {current_time} EST/EDT.",
            f"Currently, the time is {current_time} EST/EDT.",
            f"It is now {current_time} EST/EDT.",
            f"The time at the moment is {current_time} EST/EDT.",
        ]

    return f"{random.choice(responses)}", current_time

if __name__ == "__main__":
    print(user_requests_current_time())