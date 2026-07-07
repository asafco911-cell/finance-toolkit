import json

def load_stocks():
    try:
        with open("stocks.json", "r") as file:
            return json.load(file)
    except FileNotFoundError:
        print("stocks.json not found — returning empty list.")
        return [] 