import json, os, datetime

MEM_FILE="v8_experience.json"

class SelfLearningBrain:
    def __init__(self):
        self.data=self.load()
    
    def load(self):
        # Also learn from your old V7 memory if exists
        old_weights={"vwap":1.0,"ema":1.0,"rsi":1.0,"pcr":1.0,"vix":1.0,"cpr":1.0,"oi":1.0}
        if os.path.exists("intraday_memory.json"):
            try:
                with open("intraday_memory.json") as f:
                    old=json.load(f)
                    # If old bot had many BUY success, boost vwap
                    buys=len([t for t in old.get("trades",[]) if "BUY" in t.get("signal","")])
                    if buys>5: old_weights["vwap"]=1.3
            except: pass
        
        if os.path.exists(MEM_FILE):
            try:
                with open(MEM_FILE,'r') as f: return json.load(f)
            except: pass
        return {"trades":[],"weights":old_weights,"regime_perf":{},"total_reward":0}
    
    def save(self):
        with open(MEM_FILE,'w') as f: json.dump(self.data,f,indent=2)
    
    def get_score(self, features, regime):
        w=self.data["weights"]
        score=sum(features.get(k,0)*w.get(k,1.0) for k in features)
        wr=self.data["regime_perf"].get(regime,{}).get("win_rate",0.5)
        score*=(0.7+wr) # 0.7 to 1.7x based on past regime success
        conf=min(95,int(50+abs(score)*16))
        return score, conf
    
    def learn(self, features, regime, strategy, pnl):
        reward=1 if pnl>0 else -1
        if pnl<-40: reward=-1.5
        lr=0.06
        for k in features:
            self.data["weights"][k]+=lr*reward*features[k]
            self.data["weights"][k]=max(0.2,min(3.0,self.data["weights"][k]))
        if regime not in self.data["regime_perf"]:
            self.data["regime_perf"][regime]={"wins":0,"loss":0,"win_rate":0.5}
        if pnl>0: self.data["regime_perf"][regime]["wins"]+=1
        else: self.data["regime_perf"][regime]["loss"]+=1
        tot=self.data["regime_perf"][regime]["wins"]+self.data["regime_perf"][regime]["loss"]
        self.data["regime_perf"][regime]["win_rate"]=self.data["regime_perf"][regime]["wins"]/tot
        
        self.data["trades"].append({
            "time":datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
            "regime":regime,"strategy":strategy,"features":features,
            "pnl":pnl,"reward":reward,"weights":self.data["weights"].copy()
        })
        self.data["trades"]=self.data["trades"][-500:]
        self.data["total_reward"]+=reward
        self.save()
        return self.data["weights"]
