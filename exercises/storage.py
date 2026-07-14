import json

def load_stocks():
    with open("stocks.json", "r") as file:
        return json.load(file)

def save_stocks(stocks):
    with open("stocks.json", "w") as file:
        json.dump(stocks, file)