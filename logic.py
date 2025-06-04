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
from collections import defaultdict

# ファイルパス設定
CITY_DATA_FILE = "pref_city_with_coordinates.json"

# 県庁所在地の緯度経度データ
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

# スプレッドシートの列の定義（generated_postを追加）
SHEET_COLUMNS = [
    "id", "event_name", "event_url", "location", "event_date", 
    "reasons", "comment", "submission_date",
    "event_prefecture", "event_municipality", 
    "user_prefecture", "user_municipality",
    "generated_post",  # 追加: 生成された投稿文
    "reason_details"
]

# Googleスプレッドシート関連の関数は既存のものを使用
@st.cache_resource
def get_gspread_client():
    """Google Sheets APIクライアントを取得"""
    try:
        credentials_dict = st.secrets["gcp_service_account"]
        scope = ["https://spreadsheets.google.com/feeds", 
                "https://www.googleapis.com/auth/drive"]
        credentials = Credentials.from_service_account_info(
            credentials_dict, scopes=scope)
        client = gspread.authorize(credentials)
        return client
    except Exception as e:
        print(f"Google Sheets認証エラー: {e}")
        st.error(f"Google Sheets認証エラー: {e}")
        return None

@st.cache_resource(ttl=300)
def get_spreadsheet():
    """スプレッドシートを取得"""
    try:
        client = get_gspread_client()
        if client is None:
            return None
        spreadsheet_key = st.secrets["spreadsheet_key"]["spreadsheet_key"]
        spreadsheet = client.open_by_key(spreadsheet_key)
        return spreadsheet
    except Exception as e:
        print(f"スプレッドシート取得エラー: {e}")
        st.error(f"スプレッドシート取得エラー: {e}")
        return None

@st.cache_resource(ttl=300)
def initialize_worksheet():
    """ワークシートが存在しない場合は作成し、ヘッダーを設定"""
    try:
        spreadsheet = get_spreadsheet()
        if spreadsheet is None:
            return None
        try:
            worksheet = spreadsheet.worksheet("ikitakatta_data")
        except gspread.WorksheetNotFound:
            worksheet = spreadsheet.add_worksheet(
                title="ikitakatta_data", 
                rows="1000", 
                cols="20"
            )
        
        try:
            current_header = worksheet.row_values(1)
        except:
            current_header = []
        
        if not current_header or current_header != SHEET_COLUMNS:
            print(f"ヘッダーを設定します: {SHEET_COLUMNS}")
            if current_header and len(current_header) > 0:
                print("警告: 既存のデータがあるワークシートのヘッダーを修正します")
                worksheet.clear()
            worksheet.update('A1', [SHEET_COLUMNS])
        
        return worksheet
    except Exception as e:
        print(f"ワークシート初期化エラー: {e}")
        st.error(f"ワークシート初期化エラー: {e}")
        return None

def retry_on_quota_error(func, max_retries=3, delay=2):
    """Google Sheets APIのクォータエラー時にリトライする"""
    for attempt in range(max_retries):
        try:
            return func()
        except gspread.exceptions.APIError as e:
            if e.response.status_code == 429:
                if attempt < max_retries - 1:
                    print(f"レート制限エラー - {delay}秒後にリトライします (試行 {attempt + 1}/{max_retries})")
                    time.sleep(delay)
                    delay *= 2
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
    """座標付き市区町村データを読み込む"""
    try:
        if os.path.exists(CITY_DATA_FILE):
            with open(CITY_DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        else:
            print(f"警告: {CITY_DATA_FILE} が見つかりません。既存の県庁所在地データを使用します。")
            return {}
    except Exception as e:
        print(f"市区町村データ読み込みエラー: {e}")
        return {}

def get_municipalities(prefecture):
    """都道府県に対応する市区町村のリストを取得"""
    city_data = load_city_data()
    
    if prefecture in city_data:
        return ["選択なし"] + sorted(list(city_data[prefecture].keys()))
    else:
        return ["選択なし", "その他"]

def get_municipality_coordinates(prefecture, municipality):
    """市町村の座標を取得"""
    city_data = load_city_data()
    
    if prefecture in city_data:
        if municipality in city_data[prefecture]:
            coord_data = city_data[prefecture][municipality]
            return coord_data.get('latitude'), coord_data.get('longitude')
        
        # 部分一致を試す
        for city_name, coord_data in city_data[prefecture].items():
            if municipality in city_name or city_name in municipality:
                return coord_data.get('latitude'), coord_data.get('longitude')
    
    return None, None

def search_locations(keyword):
    """キーワードから都道府県+市区町村の候補を検索する関数"""
    if not keyword or len(keyword) < 2:
        return []
        
    city_data = load_city_data()
    results = []
    prefecture_only_results = []
    
    for prefecture, cities in city_data.items():
        prefecture_match = keyword in prefecture
        
        if prefecture_match:
            prefecture_only_results.append((prefecture, prefecture, ""))
        
        for city_name, city_info in cities.items():
            if (prefecture_match or 
                keyword in city_name or 
                ('city_kana' in city_info and keyword in city_info['city_kana']) or 
                ('city_hiragana' in city_info and keyword in city_info['city_hiragana'])):
                full_location = f"{prefecture} {city_name}"
                results.append((full_location, prefecture, city_name))
    
    final_results = prefecture_only_results + results
    
    if len(final_results) > 50:
        final_results = final_results[:50]
        
    return final_results

def split_location(location_string):
    """選択された場所文字列から都道府県と市区町村を分離する関数"""
    if not location_string or location_string == "直接入力":
        return "", ""
    
    if location_string == "オンライン・Web開催":
        return "オンライン・Web開催", ""
        
    parts = location_string.split(" ", 1)
    if len(parts) == 2:
        return parts[0], parts[1]
    else:
        return parts[0], ""

# データ読み込み・保存関連の関数（既存）
def load_data():
    """スプレッドシートからデータを読み込む"""
    try:
        def _load_data_inner():
            worksheet = initialize_worksheet()
            if worksheet is None:
                return pd.DataFrame(columns=SHEET_COLUMNS)
            
            all_values = worksheet.get_all_values()
            
            if not all_values or len(all_values) < 1:
                return pd.DataFrame(columns=SHEET_COLUMNS)
            
            header_row = all_values[0]
            
            if header_row != SHEET_COLUMNS:
                print(f"ヘッダー行を修正します: {header_row} -> {SHEET_COLUMNS}")
                worksheet.update('A1', [SHEET_COLUMNS])
                all_values = worksheet.get_all_values()
                header_row = all_values[0]
            
            if len(all_values) == 1:
                return pd.DataFrame(columns=SHEET_COLUMNS)
            
            df = pd.DataFrame(all_values[1:], columns=header_row)
            
            for col in SHEET_COLUMNS:
                if col not in df.columns:
                    df[col] = ""
            
            df = df[SHEET_COLUMNS]
            return df
        
        return retry_on_quota_error(_load_data_inner)
        
    except Exception as e:
        print(f"データ読み込みエラー: {e}")
        if "429" in str(e) or "Quota exceeded" in str(e):
            st.warning("⚠️ Google Sheets APIの制限に達しました。しばらく待ってから再度お試しください。")
        else:
            st.error(f"データ読み込みエラー: {e}")
        return pd.DataFrame(columns=SHEET_COLUMNS)

def append_row_to_sheet(row_data):
    """スプレッドシートに新しい行を追加"""
    try:
        def _append_row_inner():
            worksheet = initialize_worksheet()
            if worksheet is None:
                return False
            
            row_values = []
            for col in SHEET_COLUMNS:
                value = row_data.get(col, "")
                if value is None:
                    value = ""
                row_values.append(str(value))
            
            worksheet.append_row(row_values)
            return True
        
        success = retry_on_quota_error(_append_row_inner)
        
        if success:
            st.cache_data.clear()
        
        return success
        
    except Exception as e:
        print(f"スプレッドシート書き込みエラー: {e}")
        if "429" in str(e) or "Quota exceeded" in str(e):
            st.warning("⚠️ Google Sheets APIの制限に達しました。しばらく待ってから再度お試しください。")
        else:
            st.error(f"スプレッドシート書き込みエラー: {e}")
        return False

# 新しい関数：地域別データ集計

def count_by_prefecture():
    """都道府県別の投稿数を集計"""
    df = load_data()
    if df.empty:
        return pd.DataFrame(columns=["prefecture", "count", "latitude", "longitude"])
    
    # Web開催を除く
    regional_df = df[df['event_prefecture'] != 'オンライン・Web開催']
    
    if regional_df.empty:
        return pd.DataFrame(columns=["prefecture", "count", "latitude", "longitude"])
    
    counts = regional_df['event_prefecture'].value_counts().reset_index()
    counts.columns = ["prefecture", "count"]
    
    # 座標を追加
    counts['latitude'] = counts['prefecture'].apply(
        lambda pref: PREFECTURE_LOCATIONS.get(pref, [None, None])[0]
    )
    counts['longitude'] = counts['prefecture'].apply(
        lambda pref: PREFECTURE_LOCATIONS.get(pref, [None, None])[1]
    )
    
    # 座標がないものを除外
    counts = counts.dropna(subset=['latitude', 'longitude'])
    
    return counts

def count_by_municipality_in_prefecture(prefecture):
    """特定都道府県内の市区町村別投稿数を集計"""
    df = load_data()
    if df.empty:
        return pd.DataFrame(columns=["municipality", "count", "latitude", "longitude", "prefecture"])
    
    # 指定都道府県のデータのみ
    pref_df = df[df['event_prefecture'] == prefecture]
    
    if pref_df.empty:
        return pd.DataFrame(columns=["municipality", "count", "latitude", "longitude", "prefecture"])
    
    # 市区町村別の集計
    municipal_counts = defaultdict(int)
    coordinates = {}
    
    for _, row in pref_df.iterrows():
        municipality = row.get('event_municipality', '')
        
        if not municipality or municipality == "選択なし":
            # 市区町村不明の場合は県庁所在地
            key = f"{prefecture}（詳細不明）"
            municipal_counts[key] += 1
            if prefecture in PREFECTURE_LOCATIONS:
                coordinates[key] = PREFECTURE_LOCATIONS[prefecture]
        else:
            municipal_counts[municipality] += 1
            lat, lon = get_municipality_coordinates(prefecture, municipality)
            if lat is not None and lon is not None:
                coordinates[municipality] = (lat, lon)
    
    # DataFrame作成
    result_data = []
    for municipality, count in municipal_counts.items():
        if municipality in coordinates:
            lat, lon = coordinates[municipality]
            result_data.append({
                "municipality": municipality,
                "count": count,
                "latitude": lat,
                "longitude": lon,
                "prefecture": prefecture  # 追加：都道府県情報
            })
    
    return pd.DataFrame(result_data)

def get_posts_by_prefecture(prefecture):
    """特定都道府県の投稿を取得"""
    df = load_data()
    if df.empty:
        return df
    
    return df[df['event_prefecture'] == prefecture]

def get_posts_by_municipality(prefecture, municipality):
    """特定市区町村の投稿を取得"""
    df = load_data()
    if df.empty:
        return df
    
    pref_df = df[df['event_prefecture'] == prefecture]
    
    if municipality and municipality != "選択なし":
        return pref_df[pref_df['event_municipality'] == municipality]
    else:
        # 市区町村不明のもの
        return pref_df[(pref_df['event_municipality'] == "") | 
                      (pref_df['event_municipality'] == "選択なし") |
                      (pref_df['event_municipality'].isna())]

def get_online_posts():
    """オンライン開催の投稿を取得"""
    df = load_data()
    if df.empty:
        return df
    
    return df[df['event_prefecture'] == 'オンライン・Web開催']

def count_by_reason():
    """理由別の集計を行う関数"""
    df = load_data()
    if df.empty:
        return pd.DataFrame(columns=["理由", "件数"])
    
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

def get_basic_statistics():
    """基本統計情報を取得"""
    df = load_data()
    
    if df.empty:
        return {
            'total_posts': 0,
            'unique_events': 0,
            'prefectures': 0,
            'online_posts': 0,
            'recent_posts': 0
        }
    
    total_posts = len(df)
    unique_events = df['event_name'].nunique()
    prefectures = len(df[df['event_prefecture'] != 'オンライン・Web開催']['event_prefecture'].unique())
    online_posts = len(df[df['event_prefecture'] == 'オンライン・Web開催'])
    
    # 最近7日間の投稿数
    df_temp = df.copy()
    df_temp['submission_date'] = pd.to_datetime(df_temp['submission_date'], errors='coerce')
    recent_cutoff = datetime.now() - pd.Timedelta(days=7)
    recent_posts = len(df_temp[df_temp['submission_date'] > recent_cutoff])
    
    return {
        'total_posts': total_posts,
        'unique_events': unique_events,
        'prefectures': prefectures,
        'online_posts': online_posts,
        'recent_posts': recent_posts
    }

# 修正されたsave_submission関数（generated_postパラメータを追加）
def save_submission(event_name, event_url, event_prefecture, event_municipality, event_date, 
                   user_prefecture, user_municipality, reasons, comment, generated_post=""):
    
    if event_municipality == "選択なし":
        event_municipality = ""
    if user_municipality == "選択なし":
        user_municipality = ""
    
    if event_prefecture == "オンライン・Web開催":
        event_municipality = ""
        location_value = "オンライン・Web開催"
    else:
        location_value = event_prefecture
    
    event_id = str(uuid.uuid4())
    
    new_row = {
        "id": event_id,
        "event_name": event_name,
        "event_url": event_url if event_url else "",
        "location": location_value,
        "event_prefecture": event_prefecture,
        "event_municipality": event_municipality if event_municipality else "",
        "event_date": event_date,
        "user_prefecture": user_prefecture if user_prefecture else "",
        "user_municipality": user_municipality if user_municipality else "",
        "reasons": "|".join(reasons),
        "comment": comment,
        "generated_post": generated_post,  # 追加: 生成された投稿文
        "submission_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "reason_details": ""
    }
    
    return append_row_to_sheet(new_row)

def migrate_csv_if_needed():
    initialize_worksheet()

def calculate_data_hash(df):
    if df.empty:
        return "empty"
    recent_data = df.tail(10).to_json()
    return hashlib.md5(recent_data.encode()).hexdigest()