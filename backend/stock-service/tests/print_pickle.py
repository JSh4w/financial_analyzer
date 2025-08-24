import pickle 


with open("logs/daily_log.p", "rb") as f:
    x= pickle.load(f)

for key, value in x.items():
    if key == "AAPL":
        for data in value:
            print(data.p, data.t)