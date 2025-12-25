from http.server import BaseHTTPRequestHandler
import os
import json
import urllib.request
import urllib.error
import traceback

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            # 1. APIキーの読み込み
            api_key = os.environ.get("GEMINI_API_KEY")
            if not api_key:
                raise ValueError("APIキーがVercelに設定されていません")

            # 2. データの受け取り
            content_len = int(self.headers.get('Content-Length', 0))
            if content_len == 0:
                raise ValueError("データが空です")
                
            post_body = self.rfile.read(content_len)
            try:
                body_json = json.loads(post_body)
                image_data = body_json.get('image')
            except:
                raise ValueError("JSONデータの読み込みに失敗しました")

            if not image_data:
                raise ValueError("画像データが見つかりません")

            # 3. Gemini APIへのリクエスト
            # ★ここで最新の 'gemini-2.5-flash' を指定します
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
            
            headers = {'Content-Type': 'application/json'}
            
            # プロンプト変数の定義
            prompt_text = """
            このレシート画像を解析して、以下のJSON形式のみを返してください。Markdown記法は不要です。
            {
                "date": "YYYY-MM-DD",
                "amount": 数値(円マークなし),
                "category": "食費" | "交通費" | "消耗品費" | "その他",
                "memo": "店名など"
            }
            """

            payload = {
                "contents": [{
                    "parts": [
                        # ★ここが以前のエラー原因でした。正しく 'prompt_text' に修正しました。
                        {"text": prompt_text},
                        {"inline_data": {"mime_type": "image/jpeg", "data": image_data}}
                    ]
                }]
            }

            # 標準ライブラリ(urllib)で送信
            req = urllib.request.Request(
                url, 
                data=json.dumps(payload).encode(), 
                headers=headers, 
                method='POST'
            )

            with urllib.request.urlopen(req) as response:
                result = json.loads(response.read().decode())
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(result).encode())

        except urllib.error.HTTPError as e:
            error_content = e.read().decode()
            print(f"Gemini API Error: {error_content}")
            
            self.send_response(e.code)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            # エラー詳細を返す
            self.wfile.write(json.dumps({"error": f"AIエラー ({e.code})", "details": error_content}).encode())

        except Exception as e:
            print(f"Server Error: {traceback.format_exc()}")
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"error": f"システムエラー: {str(e)}"}).encode())