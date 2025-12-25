from google import genai

# ここにGeminiのAPIキーを入れてください
API_KEY = "AIzaSyAGA_8Mh5w2b88dQm6hmYLKUAm6acAXsQM"

client = genai.Client(api_key=API_KEY)

print("=== 利用可能なFlashモデル一覧 ===")
try:
    # "flash" という名前が含まれるモデルだけを表示します
    for m in client.models.list():
        if "flash" in m.name.lower():
            print(f"モデル名: {m.name}")
except Exception as e:
    print(f"エラー: {e}")