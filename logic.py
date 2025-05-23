import pandas as pd
import numpy as np
import json
import os
import hashlib
import uuid
from datetime import datetime
import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import time

# ファイルパス設定
CITY_DATA_FILE = "pref_city_with_kana.json"

# 県庁所在地の緯度経度データ
# データソース: https://www.benricho.org/chimei/latlng_data.html
PREFECTURE_LOCATIONS = {
    "北海道": [43.06417, 141.34694],
    "青森県": [40.82444, 140.74],
    "岩手県": [39.70361, 141.1525],
    "宮城県": [38.26889, 140.87194],
    "秋田県": [39.71861, 140.1025],
    "山形県": [38.24056, 140.36333],
    "福島県": [37.75, 140.46778],
    "茨城県": [36.34139, 140.44667],
    "栃木県": [36.56583, 139.88361],
    "群馬県": [36.39111, 139.06083],
    "埼玉県": [35.85694, 139.64889],
    "千葉県": [35.60472, 140.12333],
    "東京都": [35.68944, 139.69167],
    "神奈川県": [35.44778, 139.6425],
    "新潟県": [37.90222, 139.02361],
    "富山県": [36.69528, 137.21139],
    "石川県": [36.59444, 136.62556],
    "福井県": [36.06528, 136.22194],
    "山梨県": [35.66389, 138.56833],
    "長野県": [36.65139, 138.18111],
    "岐阜県": [35.39111, 136.72222],
    "静岡県": [34.97694, 138.38306],
    "愛知県": [35.18028, 136.90667],
    "三重県": [34.73028, 136.50861],
    "滋賀県": [35.00444, 135.86833],
    "京都府": [35.02139, 135.75556],
    "大阪府": [34.68639, 135.52],
    "兵庫県": [34.69139, 135.18306],
    "奈良県": [34.68528, 135.83278],
    "和歌山県": [34.22611, 135.1675],
    "鳥取県": [35.50361, 134.23833],
    "島根県": [35.47222, 133.05056],
    "岡山県": [34.66167, 133.935],
    "広島県": [34.39639, 132.45944],
    "山口県": [34.18583, 131.47139],
    "徳島県": [34.06583, 134.55944],
    "香川県": [34.34028, 134.04333],
    "愛媛県": [33.84167, 132.76611],
    "高知県": [33.55972, 133.53111],
    "福岡県": [33.60639, 130.41806],
    "佐賀県": [33.24944, 130.29889],
    "長崎県": [32.74472, 129.87361],
    "熊本県": [32.78972, 130.74167],
    "大分県": [33.23806, 131.6125],
    "宮崎県": [31.91111, 131.42389],
    "鹿児島県": [31.56028, 130.55806],
    "沖縄県": [26.2125, 127.68111],
}


# スプレッドシートの列の定義（イベントURL追加）
SHEET_COLUMNS = [
    "id", "event_name", "event_url", "location", "event_date", 
    "reasons", "comment", "submission_date",
    "event_prefecture", "event_municipality", 
    "user_prefecture", "user_municipality",
    "reason_details"
]

# Googleスプレッドシートクライアントを取得する関数
@st.cache_resource
def get_gspread_client():
    """Google Sheets APIクライアントを取得"""
    try:
        # secrets.tomlから認証情報を取得
        credentials_dict = st.secrets["gcp_service_account"]
        
        # 認証情報を作成
        scope = ["https://spreadsheets.google.com/feeds", 
                "https://www.googleapis.com/auth/drive"]
        
        credentials = Credentials.from_service_account_info(
            credentials_dict, scopes=scope)
        
        # gspreadクライアントを作成
        client = gspread.authorize(credentials)
        
        return client
    except Exception as e:
        print(f"Google Sheets認証エラー: {e}")
        st.error(f"Google Sheets認証エラー: {e}")
        return None

# スプレッドシートを取得する関数
@st.cache_resource(ttl=300)  # 5分間キャッシュ（長めに設定）
def get_spreadsheet():
    """スプレッドシートを取得"""
    try:
        client = get_gspread_client()
        if client is None:
            return None
            
        # secrets.tomlからスプレッドシートキーを取得
        spreadsheet_key = st.secrets["spreadsheet_key"]["spreadsheet_key"]
        
        # スプレッドシートを開く
        spreadsheet = client.open_by_key(spreadsheet_key)
        
        return spreadsheet
    except Exception as e:
        print(f"スプレッドシート取得エラー: {e}")
        st.error(f"スプレッドシート取得エラー: {e}")
        return None

# ワークシートの初期化
@st.cache_resource(ttl=300)  # 5分間キャッシュ
def initialize_worksheet():
    """ワークシートが存在しない場合は作成し、ヘッダーを設定"""
    try:
        spreadsheet = get_spreadsheet()
        if spreadsheet is None:
            return None
            
        # "ikitakatta_data"ワークシートを探す
        try:
            worksheet = spreadsheet.worksheet("ikitakatta_data")
        except gspread.WorksheetNotFound:
            # ワークシートが存在しない場合は作成
            worksheet = spreadsheet.add_worksheet(
                title="ikitakatta_data", 
                rows="1000", 
                cols="20"
            )
        
        # 現在のヘッダー行を確認
        try:
            current_header = worksheet.row_values(1)
        except:
            current_header = []
        
        # ヘッダーが設定されていないか、正しくない場合は設定
        if not current_header or current_header != SHEET_COLUMNS:
            print(f"ヘッダーを設定します: {SHEET_COLUMNS}")
            # 既存のデータがある場合は、ワークシートをクリアしてからヘッダーを設定
            if current_header and len(current_header) > 0:
                # データがある場合は警告を出す
                print("警告: 既存のデータがあるワークシートのヘッダーを修正します")
                # ワークシートを完全にクリア
                worksheet.clear()
            
            # 正しいヘッダーを設定
            worksheet.update('A1', [SHEET_COLUMNS])
        
        return worksheet
    except Exception as e:
        print(f"ワークシート初期化エラー: {e}")
        st.error(f"ワークシート初期化エラー: {e}")
        return None

# レート制限対応のリトライ機能
def retry_on_quota_error(func, max_retries=3, delay=2):
    """Google Sheets APIのクォータエラー時にリトライする"""
    for attempt in range(max_retries):
        try:
            return func()
        except gspread.exceptions.APIError as e:
            if e.response.status_code == 429:  # Quota exceeded
                if attempt < max_retries - 1:
                    print(f"レート制限エラー - {delay}秒後にリトライします (試行 {attempt + 1}/{max_retries})")
                    time.sleep(delay)
                    delay *= 2  # 指数バックオフ
                    continue
                else:
                    print("最大リトライ回数に達しました")
                    raise
            else:
                raise
        except Exception as e:
            raise
    return None

def load_city_data():
    try:
        if os.path.exists(CITY_DATA_FILE):
            with open(CITY_DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        else:
            # ファイルが存在しない場合は空の辞書を返す
            return {}
    except Exception as e:
        print(f"市区町村データ読み込みエラー: {e}")
        return {}

# 都道府県に対応する市区町村のリストを取得
def get_municipalities(prefecture):
    city_data = load_city_data()
    
    if prefecture in city_data:
        # JSONデータがある場合はそれを使用
        return ["選択なし"] + sorted(list(city_data[prefecture].keys()))
    else:
        # デフォルトのリスト（主要都市）を返す
        return ["選択なし", "その他"]

# キーワードから都道府県+市区町村の候補を検索する関数
def search_locations(keyword):
    if not keyword or len(keyword) < 2:
        return []
        
    city_data = load_city_data()
    results = []
    
    # 全都道府県から検索
    for prefecture, cities in city_data.items():
        # 都道府県名にキーワードが含まれる場合は全市町村を含める
        prefecture_match = keyword in prefecture
        
        for city_name, city_info in cities.items():
            # 市区町村名、カタカナ、ひらがなのいずれかで部分一致
            if (prefecture_match or 
                keyword in city_name or 
                ('city_kana' in city_info and keyword in city_info['city_kana']) or 
                ('city_hiragana' in city_info and keyword in city_info['city_hiragana'])):
                # 都道府県 + 市区町村 のフォーマットで結果を追加
                full_location = f"{prefecture} {city_name}"
                results.append((full_location, prefecture, city_name))
    
    # 結果がない場合は空のリストを返す
    # 結果が多すぎる場合は最初の50件に制限
    if len(results) > 50:
        results = results[:50]
        
    return results

# 選択された場所文字列から都道府県と市区町村を分離する関数
def split_location(location_string):
    if not location_string or location_string == "直接入力":
        return "", ""
        
    parts = location_string.split(" ", 1)
    if len(parts) == 2:
        return parts[0], parts[1]  # 都道府県, 市区町村
    else:
        return parts[0], ""  # 都道府県のみ

# スプレッドシートからデータを読み込む関数
def load_data():
    """スプレッドシートからデータを読み込む"""
    try:
        def _load_data_inner():
            worksheet = initialize_worksheet()
            if worksheet is None:
                return pd.DataFrame(columns=SHEET_COLUMNS)
            
            # スプレッドシートの全データを取得
            all_values = worksheet.get_all_values()
            
            if not all_values or len(all_values) < 1:
                return pd.DataFrame(columns=SHEET_COLUMNS)
            
            # ヘッダー行を確認・修正
            header_row = all_values[0]
            
            # ヘッダーが期待される列と異なる場合は修正
            if header_row != SHEET_COLUMNS:
                print(f"ヘッダー行を修正します: {header_row} -> {SHEET_COLUMNS}")
                # ヘッダー行を正しい列名に更新
                worksheet.update('A1', [SHEET_COLUMNS])
                # 再度データを取得
                all_values = worksheet.get_all_values()
                header_row = all_values[0]
            
            # データが1行（ヘッダーのみ）の場合
            if len(all_values) == 1:
                return pd.DataFrame(columns=SHEET_COLUMNS)
            
            # DataFrameを作成
            df = pd.DataFrame(all_values[1:], columns=header_row)
            
            # 必要な列が存在しない場合は追加
            for col in SHEET_COLUMNS:
                if col not in df.columns:
                    df[col] = ""
            
            # 列の順序を統一
            df = df[SHEET_COLUMNS]
            
            return df
        
        # リトライ機能付きで実行
        return retry_on_quota_error(_load_data_inner)
        
    except Exception as e:
        print(f"データ読み込みエラー: {e}")
        if "429" in str(e) or "Quota exceeded" in str(e):
            st.warning("⚠️ Google Sheets APIの制限に達しました。しばらく待ってから再度お試しください。")
        else:
            st.error(f"データ読み込みエラー: {e}")
        return pd.DataFrame(columns=SHEET_COLUMNS)

# スプレッドシートにデータを追加する関数
def append_row_to_sheet(row_data):
    """スプレッドシートに新しい行を追加"""
    try:
        def _append_row_inner():
            worksheet = initialize_worksheet()
            if worksheet is None:
                return False
            
            # 行データを列の順序に合わせて整理
            row_values = []
            for col in SHEET_COLUMNS:
                value = row_data.get(col, "")
                # None値を空文字に変換
                if value is None:
                    value = ""
                row_values.append(str(value))
            
            # スプレッドシートに行を追加
            worksheet.append_row(row_values)
            
            return True
        
        # リトライ機能付きで実行
        success = retry_on_quota_error(_append_row_inner)
        
        if success:
            # キャッシュをクリア
            st.cache_data.clear()
        
        return success
        
    except Exception as e:
        print(f"スプレッドシート書き込みエラー: {e}")
        if "429" in str(e) or "Quota exceeded" in str(e):
            st.warning("⚠️ Google Sheets APIの制限に達しました。しばらく待ってから再度お試しください。")
        else:
            st.error(f"スプレッドシート書き込みエラー: {e}")
        return False

# スプレッドシートのデータを更新する関数
def update_row_in_sheet(row_id, updated_data):
    """スプレッドシートの特定の行を更新"""
    try:
        worksheet = initialize_worksheet()
        if worksheet is None:
            return False
        
        # すべてのデータを取得
        all_records = worksheet.get_all_records()
        
        # 該当するIDの行を探す
        for i, record in enumerate(all_records):
            if record.get('id') == row_id:
                # 更新データを適用
                for key, value in updated_data.items():
                    if key in SHEET_COLUMNS:
                        record[key] = value
                
                # 行番号を計算（ヘッダー行が1行目なので+2）
                row_number = i + 2
                
                # 行データを列の順序に合わせて整理
                row_values = []
                for col in SHEET_COLUMNS:
                    value = record.get(col, "")
                    if value is None:
                        value = ""
                    row_values.append(str(value))
                
                # スプレッドシートの行を更新
                worksheet.update(f'A{row_number}:{chr(65 + len(SHEET_COLUMNS) - 1)}{row_number}', [row_values])
                
                # キャッシュをクリア
                st.cache_data.clear()
                
                return True
        
        return False
        
    except Exception as e:
        print(f"スプレッドシート更新エラー: {e}")
        st.error(f"スプレッドシート更新エラー: {e}")
        return False

# スプレッドシートから行を削除する関数
def delete_row_from_sheet(row_id):
    """スプレッドシートから特定の行を削除"""
    try:
        worksheet = initialize_worksheet()
        if worksheet is None:
            return False
        
        # すべてのデータを取得
        all_records = worksheet.get_all_records()
        
        # 該当するIDの行を探す
        for i, record in enumerate(all_records):
            if record.get('id') == row_id:
                # 行番号を計算（ヘッダー行が1行目なので+2）
                row_number = i + 2
                
                # 行を削除
                worksheet.delete_rows(row_number)
                
                # キャッシュをクリア
                st.cache_data.clear()
                
                return True
        
        return False
        
    except Exception as e:
        print(f"スプレッドシート削除エラー: {e}")
        st.error(f"スプレッドシート削除エラー: {e}")
        return False

# CSVファイルが存在しない場合は作成する関数（後方互換性のため残す）
def initialize_csv():
    pass  # スプレッドシート版では何もしない

# 既存のCSVファイルを新しい形式にマイグレーションする関数（後方互換性のため残す）
def migrate_csv_if_needed():
    # スプレッドシートの初期化を実行
    initialize_worksheet()

# 新しい行を追加・保存する（汎用関数）
def save_row(row_data):
    return append_row_to_sheet(row_data)

# 新しい投稿を保存する関数（イベントURL対応）
def save_submission(event_name, event_url, event_prefecture, event_municipality, event_date, 
                   user_prefecture, user_municipality, reasons, comment):
    
    # 「選択なし」の場合は空文字に変換
    if event_municipality == "選択なし":
        event_municipality = ""
    if user_municipality == "選択なし":
        user_municipality = ""
    
    # 新規IDの生成
    event_id = str(uuid.uuid4())
    
    # 新しい行を追加
    new_row = {
        "id": event_id,
        "event_name": event_name,
        "event_url": event_url if event_url else "",  # URLを追加
        "location": event_prefecture,  # 後方互換性のため
        "event_prefecture": event_prefecture,
        "event_municipality": event_municipality if event_municipality else "",
        "event_date": event_date,
        "user_prefecture": user_prefecture if user_prefecture else "",
        "user_municipality": user_municipality if user_municipality else "",
        "reasons": "|".join(reasons),  # 複数の理由を|で区切って保存
        "comment": comment,
        "submission_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "reason_details": ""
    }
    
    return save_row(new_row)

# 県別のイベント投稿数を集計する関数
def count_by_prefecture():
    df = load_data()
    if df.empty:
        return pd.DataFrame(columns=["location", "count"])
    
    # event_prefectureカラムがある場合はそれを使用、なければlocationを使用
    if "event_prefecture" in df.columns and not df["event_prefecture"].isna().all():
        counts = df["event_prefecture"].value_counts().reset_index()
    else:
        counts = df["location"].value_counts().reset_index()
    
    counts.columns = ["location", "count"]
    return counts

# イベント県と居住県のクロス集計を行う関数
def cross_tabulate_prefectures():
    df = load_data()
    if df.empty:
        return None
    
    # 新しいカラム構造に対応
    user_pref_col = "user_prefecture" if "user_prefecture" in df.columns else None
    event_pref_col = "event_prefecture" if "event_prefecture" in df.columns else "location"
    
    if user_pref_col is None or df[user_pref_col].isna().all() or (df[user_pref_col] == "").all():
        return None
    
    # 有効な居住県データがある行のみを対象に
    valid_df = df[(df[user_pref_col].notna()) & (df[user_pref_col] != "")]
    if valid_df.empty:
        return None
    
    # クロス集計
    cross_tab = pd.crosstab(valid_df[user_pref_col], valid_df[event_pref_col])
    return cross_tab

# 理由別の集計を行う関数
def count_by_reason():
    df = load_data()
    if df.empty:
        return pd.DataFrame(columns=["理由", "件数"])
    
    # reasonsの集計
    reasons_count = {}
    for idx, row in df.iterrows():
        if pd.isna(row["reasons"]) or row["reasons"] == "":
            continue
        reasons_list = str(row["reasons"]).split("|")
        for reason in reasons_list:
            if reason in reasons_count:
                reasons_count[reason] += 1
            else:
                reasons_count[reason] = 1
    
    reasons_df = pd.DataFrame({
        "理由": list(reasons_count.keys()),
        "件数": list(reasons_count.values())
    }).sort_values("件数", ascending=False)
    
    return reasons_df

# データハッシュを計算する関数
def calculate_data_hash(df):
    if df.empty:
        return "empty"
    # 最新10件のデータのハッシュを計算
    recent_data = df.tail(10).to_json()
    return hashlib.md5(recent_data.encode()).hexdigest()

# データをIDで検索する関数
def get_row_by_id(row_id):
    df = load_data()
    if df.empty or "id" not in df.columns:
        return None
    
    result = df[df["id"] == row_id]
    if result.empty:
        return None
    
    return result.iloc[0].to_dict()

# データを更新する関数
def update_row(row_id, updated_data):
    return update_row_in_sheet(row_id, updated_data)

# データを削除する関数（管理者用）
def delete_row(row_id):
    return delete_row_from_sheet(row_id)

# スプレッドシートをリセットする関数（デバッグ用）
def reset_spreadsheet():
    """スプレッドシートを完全にリセットして正しいヘッダーを設定"""
    try:
        worksheet = get_spreadsheet().worksheet("ikitakatta_data")
        
        # ワークシートを完全にクリア
        worksheet.clear()
        
        # 正しいヘッダーを設定
        worksheet.update('A1', [SHEET_COLUMNS])
        
        print("スプレッドシートをリセットしました")
        return True
        
    except Exception as e:
        print(f"スプレッドシートリセットエラー: {e}")
        return False