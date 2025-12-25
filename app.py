import streamlit as st
import pandas as pd
import json
import datetime
from supabase import create_client
from google import genai
from google.genai import types

# --- 0. アプリ設定 (スマホで見やすくする) ---
st.set_page_config(
    page_title="My確定申告",
    page_icon="💰",
    layout="centered"
)

# --- 1. 秘密鍵(Secrets)の読み込み ---
# Streamlit CloudのSecrets機能からキーを確実に取得します
try:
    GOOGLE_API_KEY = st.secrets["AIzaSyAGA_8Mh5w2b88dQm6hmYLKUAm6acAXsQM"]
    SUPABASE_URL = st.secrets["https://duqygncobzarqglqnlop.supabase.co"]
    SUPABASE_KEY = st.secrets["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImR1cXlnbmNvYnphcnFnbHFubG9wIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjY2MDUwMTksImV4cCI6MjA4MjE4MTAxOX0.Fq6s7fMmT9i47U0MJ2B8pXjTQdpNG56f1rytJYDPpkI"]
except Exception:
    st.error("❌ 設定エラー: Secretsが読み込めません。Streamlit管理画面のSecrets設定を確認してください。")
    st.stop()

# --- 2. データベース接続 (キャッシュ化で高速化) ---
@st.cache_resource
def init_connection():
    try:
        return create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        st.error(f"Supabase接続エラー: {e}")
        return None

supabase = init_connection()

# --- 3. メイン画面レイアウト ---
st.title("💰 My確定申告 (Cloud)")

# --- サイドバー：入力フォーム ---
with st.sidebar:
    st.header("📝 取引入力")
    
    # AIレシート解析
    uploaded_file = st.file_uploader("レシートを撮影/アップロード", type=['png', 'jpg', 'jpeg'])
    
    # デフォルト値
    default_date = datetime.date.today()
    default_amount = 0
    default_desc = ""
    default_cat = "雑費"
    default_type = "支出"

    # 画像がアップされたらGemini 2.5 Flashで解析
    if uploaded_file is not None:
        with st.spinner("🤖 Gemini 2.5 がレシートを解析中..."):
            try:
                client = genai.Client(api_key=GOOGLE_API_KEY)
                image_bytes = uploaded_file.getvalue()
                
                # Geminiへの命令
                prompt = """
                この画像を解析し、以下のJSON形式のみを返してください（Markdownは不要）:
                {"date":"YYYY-MM-DD","amount":数値,"description":"店名や内容","category":"勘定科目","type":"expense"}
                勘定科目は次から選択: 消耗品費, 旅費交通費, 会議費, 通信費, 水道光熱費, 雑費, 仕入高
                """
                
                # 最新モデルを使用
                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=[
                        types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"),
                        types.Part.from_text(text=prompt)
                    ]
                )
                
                # 結果の整形
                text_res = response.text.replace("```json", "").replace("```", "").strip()
                data = json.loads(text_res)
                
                # フォームへの反映処理
                if data.get("date"):
                    default_date = datetime.datetime.strptime(data.get("date"), "%Y-%m-%d").date()
                default_amount = data.get("amount", 0)
                default_desc = data.get("description", "")
                default_cat = data.get("category", "雑費")
                
                st.success("✅ 解析成功！")
                
            except Exception as e:
                st.error(f"解析エラー: {e}")

    # 入力フォーム
    with st.form("entry_form"):
        date = st.date_input("日付", value=default_date)
        tx_type = st.radio("区分", ["収入", "支出"], index=1 if default_type=="expense" else 0, horizontal=True)
        
        options = ["売上高", "仕入高", "消耗品費", "旅費交通費", "通信費", "地代家賃", "水道光熱費", "会議費", "雑費"]
        # カテゴリの自動選択ロジック
        cat_index = options.index(default_cat) if default_cat in options else 8
            
        category = st.selectbox("勘定科目", options, index=cat_index)
        amount = st.number_input("金額 (円)", value=default_amount, step=1)
        description = st.text_input("内容", value=default_desc)
        
        submitted = st.form_submit_button("登録する", use_container_width=True)
        
        if submitted:
            if not supabase:
                st.error("データベースに接続できていません")
            else:
                data = {
                    "date": str(date),
                    "type": "income" if tx_type == "収入" else "expense",
                    "category": category,
                    "amount": int(amount),
                    "description": description
                }
                try:
                    supabase.table("transactions").insert(data).execute()
                    st.toast("登録しました！", icon="🎉")
                    # データを反映させるためにリロード
                    import time
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"登録エラー: {e}")

# --- メイン画面：データ一覧と集計 ---
if supabase:
    try:
        # データ取得
        rows = supabase.table("transactions").select("*").order("date", desc=True).limit(100).execute()
        df = pd.DataFrame(rows.data)

        if not df.empty:
            # 3つの指標（売上・経費・利益）
            st.markdown("### 📊 経営状況")
            col1, col2, col3 = st.columns(3)
            
            income = df[df['type']=='income']['amount'].sum()
            expense = df[df['type']=='expense']['amount'].sum()
            profit = income - expense
            
            col1.metric("売上", f"¥{income:,}")
            col2.metric("経費", f"¥{expense:,}", delta_color="inverse")
            col3.metric("利益", f"¥{profit:,}")

            st.divider()

            # 履歴テーブル
            st.markdown("### 🕒 直近の取引")
            
            # 見やすいようにカラム名を日本語化して表示
            df_display = df[['date', 'type', 'category', 'description', 'amount']].copy()
            df_display.columns = ['日付', '区分', '科目', '内容', '金額']
            # 区分を日本語化
            df_display['区分'] = df_display['区分'].map({'income': '収入', 'expense': '支出'})
            
            st.dataframe(
                df_display, 
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("データがまだありません。サイドバー（スマホなら左上の「>」）から登録してください。")
            
    except Exception as e:
        st.error(f"データ取得エラー: {e}")