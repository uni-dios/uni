import requests
import random

api_key = '97a61e4c8433843e2a9efd9062df69ab'

def user_requests_current_weather():
    city = 'London'
    url = f'http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric'
    response = requests.get(url)
    data = response.json()
    weather = data['weather'][0]['description']
    temperature = data['main']['temp']
    feels_like = data['main']['feels_like']
    humidity = data['main']['humidity']

    answers = [
        f'The current weather in {city} is {weather} with a temperature of {temperature}&#8451; (feels like {feels_like}&#8451;). The humidity is {humidity}%.',
        f'It\'s currently {weather} in {city} with a temperature of {temperature}&#8451; and a humidity of {humidity}%.',
        f'The weather in {city} is {weather} today with a temperature of {temperature}&#8451; (feels like {feels_like}&#8451;) and {humidity}% humidity.',
        f'In {city}, the current weather conditions are {weather} with a temperature of {temperature}&#8451; and {humidity}% humidity.',
        f'Currently, {city} is experiencing {weather} weather with a temperature of {temperature}&#8451; and a humidity level of {humidity}%.'
    ]

    return random.choice(answers)

if __name__ == '__main__':
    print(user_requests_current_weather())