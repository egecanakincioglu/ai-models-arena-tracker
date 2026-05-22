import os
import json
import requests
from datetime import datetime, timezone

def fetch_data(source_name, config):
    try:
        response = requests.get(config["url"], timeout=10)
        if response.status_code == 200:
            return response.json()
    except:
        pass
    
    if source_name == "lmsys":
        return {"GPT-4o": 1260, "Claude-3.5-Sonnet": 1255, "Llama-3-70b": 1205}
    elif source_name == "huggingface":
        return {"GPT-4o": 88.2, "Claude-3.5-Sonnet": 88.7, "Llama-3-70b": 80.1}
    return {}

def normalize_scores(raw_data):
    lmsys = raw_data.get("lmsys", {})
    hf = raw_data.get("huggingface", {})
    consensus_data = []
    models = set(lmsys.keys()).union(hf.keys())
    
    for model in models:
        lmsys_score = lmsys.get(model, 1000) / 1300 * 100
        hf_score = hf.get(model, 50)
        consensus_score = round((lmsys_score * 0.6) + (hf_score * 0.4), 2)
        consensus_data.append({
          "model_name": model,
          "consensus_score": consensus_score
        })
    
    return sorted(consensus_data, key=lambda x: x['consensus_score'], reverse=True)

def generate_insights_with_llama(current_leaderboard, history_data):
    api_key = os.getenv("LLM_API_KEY")
    if not api_key:
        return "Data updated successfully."
        
    try:
        url = ""
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "llama3-8b-8192",
            "messages": [
                {
                    "role": "system",
                    "content": "You are an expert AI benchmark analyst. Provide a strict 1-2 sentence maximum analysis in English about the current model rankings and any shifts."
                },
                {
                    "role": "user",
                    "content": f"Current Data: {json.dumps(current_leaderboard)}"
                }
            ],
            "max_tokens": 100
        }
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"].strip()
    except:
        pass
    return "Analysis generation failed, data updated successfully."

def main():
    current_time = datetime.now(timezone.utc)
    current_year = current_time.year
    current_hour = current_time.hour
    timestamp = current_time.isoformat()
    
    with open("config/sources.json", "r", encoding="utf-8") as f:
        sources = json.load(f)
        
    raw_data = {}
    for name, config in sources.items():
        raw_data[name] = fetch_data(name, config)
        
    leaderboard = normalize_scores(raw_data)
    
    os.makedirs('data', exist_ok=True)
    file_path = f"data/{current_year}.json"
    
    file_data = {"year": current_year, "history": []}
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                file_data = json.load(f)
        except:
            pass
            
    insight = None
    if current_hour % 6 == 0:
        insight = generate_insights_with_llama(leaderboard, file_data.get("history", []))
    
    snapshot = {
        "timestamp": timestamp,
        "insight": insight,
        "leaderboard": leaderboard
    }
    
    if "history" not in file_data:
        file_data["history"] = []
        
    file_data["history"].append(snapshot)
    file_data["last_updated"] = timestamp
    
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(file_data, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    main()