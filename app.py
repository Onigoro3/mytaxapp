import streamlit as st
import pandas as pd
import json
import datetime
import os
from supabase import create_client
from google import genai
from google.genai import types

# ==========================================
# クラウドサーバー(Render)の環境変数からキーを読み込む設定
# ==========================================
try:
    # Render等の環境変数から取得
    GOOGLE_API_KEY = os.environ.get("AIzaSyAGA_8Mh5w2b88dQm6hmYLKUAm6acAXsQM")
    SUPABASE_URL = os.environ.get("https://duqygncobzarqglqnlop.supabase.co")
    SUPABASE_KEY = os.environ.get("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImR1cXlnbmNvYnphcnFnbHFubG9wIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjY2MDUwMTksImV4cCI6MjA4MjE4MTAxOX0.Fq6s7fMmT9i47U0MJ2B8pXjTQdpNG56f1rytJYDPpkI")
    
    # もしキーがない場合（ローカルでの実行時など）のエラー回避
    if not GOOGLE_API_KEY:
        st.error("【設定エラー】APIキーが見つかりません。RenderのEnvironment Variables設定を確認してください。")
        st.stop()
except Exception as e:
    st.error(f"設定読み込みエラー: {e}")
    st.stop()
# ==========================================

# --- 1. Supabase & Gemini 接続設定 ---
@st.cache_resource
def init_connection():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

try:
    supabase = init_connection()
except:
    st.error("Supabaseへの接続に失敗しました。URLとKeyを確認してください。")
    st.stop()

# --- 2. 画面レイアウト ---
st.title("💰 My確定申告 (Cloud版)")

# --- サイドバー：入力フォーム ---
with st.sidebar:
    st.header("📝 取引入力")
    
    # AIレシート解析
    uploaded_file = st.file_uploader("レシートをアップロード/撮影", type=['png', 'jpg', 'jpeg'])
    
    # デフォルト値
    default_date = datetime.date.today()
    default_amount = 0
    default_desc = ""
    default_cat = "雑費"
    default_type = "支出"

    # 画像がアップされたらGeminiで解析
    if uploaded_file is not None:
        st.info("🤖 Geminiが解析中...")
        try:
            client = genai.Client(api_key=GOOGLE_API_KEY)
            image_bytes = uploaded_file.getvalue()
            
            prompt = """
            この画像を解析しJSONのみ返して:
            {"date":"YYYY-MM-DD","amount":数値,"description":"店名","category":"消耗品費/旅費交通費/会議費/通信費/水道光熱費/雑費/仕入高","type":"expense"}
            """
            
            # Gemini 2.5 Flashを使用
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[
                    types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"),
                    types.Part.from_text(text=prompt)
                ]
            )
            data = json.loads(response.text.replace("```json", "").replace("```", "").strip())
            
            # フォームに反映
            if data.get("date"):
                default_date = datetime.datetime.strptime(data.get("date"), "%Y-%m-%d").date()
            default_amount = data.get("amount", 0)
            default_desc = data.get("description", "")
            default_cat = data.get("category", "雑費")
            st.success("解析成功！")
            
        except Exception as e:
            st.error(f"解析エラー: {e}")

    # 入力フォーム
    with st.form("entry_form"):
        date = st.date_input("日付", value=default_date)
        tx_type = st.radio("区分", ["収入", "支出"], index=1 if default_type=="expense" else 0)
        
        options = ["売上高", "仕入高", "消耗品費", "旅費交通費", "通信費", "地代家賃", "水道光熱費", "会議費", "雑費"]
        try:
            cat_index = options.index(default_cat)
        except:
            cat_index = 8 # 雑費
            
        category = st.selectbox("勘定科目", options, index=cat_index)
        amount = st.number_input("金額", value=default_amount)
        description = st.text_input("内容", value=default_desc)
        
        submitted = st.form_submit_button("登録する")
        
        if submitted:
            data = {
                "date": str(date),
                "type": "income" if tx_type == "収入" else "expense",
                "category": category,
                "amount": amount,
                "description": description
            }
            try:
                supabase.table("transactions").insert(data).execute()
                st.toast("登録しました！", icon="✅")
                # 画面リロード（データ反映のため）
                st.rerun()
            except Exception as e:
                st.error(f"登録エラー: {e}")

# --- メイン画面：データ一覧と集計 ---
try:
    rows = supabase.table("transactions").select("*").order("date", desc=True).execute()
    df = pd.DataFrame(rows.data)

    if not df.empty:
        col1, col2, col3 = st.columns(3)
        income = df[df['type']=='income']['amount'].sum()
        expense = df[df['type']=='expense']['amount'].sum()
        
        col1.metric("売上", f"¥{income:,}")
        col2.metric("経費", f"¥{expense:,}")
        col3.metric("利益", f"¥{income - expense:,}")

        st.subheader("📊 取引履歴")
        st.dataframe(df[['date', 'type', 'category', 'description', 'amount']], use_container_width=True)
    else:
        st.info("データがまだありません。左側から登録してください。")
except Exception as e:
    st.error(f"データ取得エラー: {e}")