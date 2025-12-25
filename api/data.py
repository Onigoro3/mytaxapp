from http.server import BaseHTTPRequestHandler
import os
import requests
import traceback

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            # 1. URL取得
            gas_url = os.environ.get("SHEET_API_URL")
            if not gas_url:
                raise ValueError("URL設定エラー: SHEET_API_URL が設定されていません")

            # 2. アプリからのデータを受け取る
            content_len = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_len)

            # 3. そのままGASに転送する (POST)
            # 読み込み(read)、保存(save)、削除(delete) すべてここで処理します
            resp = requests.post(gas_url, data=body, headers={'Content-Type': 'application/json'})

            # 4. GASからの返事をそのままアプリに返す
            self.send_response(resp.status_code)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(resp.content)

        except Exception as e:
            print(f"Error: {traceback.format_exc()}")
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(f'{{"error": "{str(e)}"}}'.encode())