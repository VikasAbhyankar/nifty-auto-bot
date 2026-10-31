# NIFTY FUTURE AUTO BOT - GITHUB CLOUD
import yfinance as yf
import pandas as pd
import numpy as np
import torch, torch.nn as nn
from sklearn.preprocessing import MinMaxScaler
import requests, os

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

symbol = "^NSEI"
df = yf.download(symbol, period="3y", interval="1d", auto_adjust=False)
if isinstance(df.columns, pd.MultiIndex):
    df.columns = df.columns.get_level_values(0)
df = df[['Close','High','Low','Volume']].dropna()

df['SMA20'] = df['Close'].rolling(20).mean()
delta = df['Close'].diff()
gain = (delta.where(delta > 0, 0)).rolling(14).mean()
loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
df['RSI'] = 100 - (100 / (1 + gain/loss))
df['Return'] = df['Close'].pct_change()
df.dropna(inplace=True)

scaler = MinMaxScaler()
scaled = scaler.fit_transform(df[['Close','SMA20','RSI','Return']])
SEQ=30; X,y=[],[]
for i in range(SEQ, len(scaled)):
    X.append(scaled[i-SEQ:i]); y.append(scaled[i,0])
X=torch.tensor(np.array(X), dtype=torch.float32)
y=torch.tensor(np.array(y), dtype=torch.float32).view(-1,1)

class NiftyLSTM(nn.Module):
    def __init__(self):
        super().__init__()
        self.lstm = nn.LSTM(4,64,2,batch_first=True,dropout=0.2)
        self.fc = nn.Sequential(nn.Linear(64,32), nn.ReLU(), nn.Linear(32,1))
    def forward(self,x):
        out,_=self.lstm(x); return self.fc(out[:,-1])

model=NiftyLSTM(); opt=torch.optim.Adam(model.parameters(), lr=0.001)
loss_fn=nn.MSELoss()
for _ in range(30):
    opt.zero_grad(); loss=loss_fn(model(X),y); loss.backward(); opt.step()

with torch.no_grad():
    nxt=model(X[-1].unsqueeze(0)).item()
    dummy=np.zeros((1,4)); dummy[0,0]=nxt
    next_price=scaler.inverse_transform(dummy)[0,0]

current=float(df['Close'].iloc[-1]); chg=(next_price-current)/current*100
signal="HOLD"
if chg>0.6: signal="STRONG BUY - LONG"
elif chg>0.2: signal="BUY"
elif chg<-0.6: signal="STRONG SELL - SHORT"
elif chg<-0.2: signal="SELL"

msg=f"🚀 NIFTY FUTURE AUTO BOT 9:15 AM\nDate: {pd.Timestamp.now()}\nCurrent: {current:.2f}\nPredicted: {next_price:.2f} ({chg:.2f}%)\nSIGNAL: {signal}"
requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", params={"chat_id":CHAT_ID,"text":msg})
print(msg)