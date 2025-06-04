import streamlit as st
import streamlit.components.v1 as components  # 追加：確実なスクロール制御のため
import pandas as pd
import pydeck as pdk
import altair as alt
from datetime import datetime
import uuid
import os
import openai
import urllib.parse
import re
import requests
from bs4 import BeautifulSoup

# 自作モジュールをインポート
import logic
import map_utils
import ui_components

# ページ設定
st.set_page_config(
    page_title="#行きたかったマップ", 
    page_icon="🗺️", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# インスタグラム風のカスタムCSS（既存のものを使用）
st.markdown("""
<style>
/* 全体のスタイリング */
.main {
    padding-top: 1rem;
    background-color: #fafafa;
}

/* ヘッダーのスタイリング - インスタ風 */
.header-container {
    background: linear-gradient(135deg, #fd5949 0%, #d6336c 100%);
    padding: 2rem;
    border-radius: 20px;
    color: white;
    text-align: center;
    margin-bottom: 2rem;
    box-shadow: 0 4px 20px rgba(253, 89, 73, 0.3);
}

.header-title {
    font-size: 3rem;
    font-weight: bold;
    margin-bottom: 0.5rem;
    text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
}

.header-subtitle {
    font-size: 1.2rem;
    opacity: 0.95;
    margin-bottom: 0;
}

/* カードスタイル - インスタ風 */
.reason-category {
    font-weight: bold;
    font-size: 1.1rem;
    margin: 1.5rem 0 1rem 0;
    color: #262626;
    border-bottom: 2px solid #fd5949;
    padding-bottom: 0.5rem;
}

/* マップコンテナ */
.map-container {
    background: white;
    border-radius: 12px;
    padding: 1rem;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    margin-bottom: 1rem;
}

/* 投稿リストコンテナ */
.posts-container {
    background: white;
    border-radius: 12px;
    padding: 1rem;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    max-height: 600px;
    overflow-y: auto;
}

/* ナビゲーションボタン */
.nav-button {
    background: #667eea;
    color: white;
    padding: 0.5rem 1rem;
    border-radius: 8px;
    text-decoration: none;
    display: inline-block;
    margin: 0.25rem;
    transition: all 0.3s ease;
}

.nav-button:hover {
    background: #5a6fd8;
    text-decoration: none;
    color: white;
}

/* セクションヘッダー */
.section-header {
    color: #262626;
    font-size: 1.5rem;
    font-weight: bold;
    margin: 2rem 0 1rem 0;
    padding-bottom: 0.5rem;
    border-bottom: 2px solid #fd5949;
}

/* Threads風投稿プレビューボックス */
.threads-post-box {
    background: white;
    border: 1px solid #e1e5e9;
    border-radius: 16px;
    padding: 1.5rem;
    margin: 1rem 0;
    box-shadow: 0 2px 12px rgba(0,0,0,0.08);
    transition: all 0.3s ease;
    position: relative;
}

.threads-post-box:hover {
    box-shadow: 0 4px 20px rgba(0,0,0,0.12);
    transform: translateY(-2px);
}

.threads-header {
    display: flex;
    align-items: center;
    margin-bottom: 1rem;
    gap: 12px;
}

.threads-avatar {
    width: 48px;
    height: 48px;
    border-radius: 50%;
    background: linear-gradient(135deg, #fd5949 0%, #d6336c 100%);
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
    font-weight: bold;
    font-size: 18px;
}

.threads-username {
    font-weight: 600;
    color: #262626;
    font-size: 15px;
}

.threads-content {
    line-height: 1.6;
    color: #262626;
    font-size: 15px;
    margin-bottom: 1rem;
    white-space: pre-line;
}

.threads-meta {
    display: flex;
    align-items: center;
    gap: 1rem;
    color: #8e8e8e;
    font-size: 13px;
    margin-top: 1rem;
    padding-top: 1rem;
    border-top: 1px solid #f0f0f0;
}

.threads-post-label {
    position: absolute;
    top: -10px;
    left: 1rem;
    background: linear-gradient(135deg, #fd5949 0%, #d6336c 100%);
    color: white;
    padding: 0.3rem 0.8rem;
    border-radius: 12px;
    font-size: 0.8rem;
    font-weight: 600;
    box-shadow: 0 2px 8px rgba(253, 89, 73, 0.3);
}

/* 投稿プレビューボックス */
.post-preview-box {
    background: #f8f9fa;
    border: 2px solid #e9ecef;
    border-radius: 12px;
    padding: 1.5rem;
    margin: 1rem 0;
    position: relative;
}

.post-preview-label {
    background: #fd5949;
    color: white;
    padding: 0.3rem 0.8rem;
    border-radius: 20px;
    font-size: 0.9rem;
    font-weight: 600;
    position: absolute;
    top: -12px;
    left: 1rem;
}

.post-content {
    margin-top: 0.5rem;
    line-height: 1.6;
    color: #262626;
}

.generating-post {
    color: #8e8e8e;
    font-style: italic;
    text-align: center;
    padding: 2rem;
    background: white;
    border-radius: 12px;
    border: 1px solid #dbdbdb;
}

/* Threads風投稿カード */
.threads-card {
    background: white;
    border: 1px solid #e1e5e9;
    border-radius: 16px;
    padding: 1.5rem;
    margin: 1rem 0;
    box-shadow: 0 2px 8px rgba(0,0,0,0.06);
    transition: all 0.3s ease;
}

.threads-card:hover {
    box-shadow: 0 4px 16px rgba(0,0,0,0.1);
    transform: translateY(-1px);
}

.threads-card-header {
    display: flex;
    align-items: center;
    margin-bottom: 1rem;
    gap: 12px;
}

.threads-card-avatar {
    width: 40px;
    height: 40px;
    border-radius: 50%;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
    font-weight: bold;
    font-size: 14px;
}

.threads-card-user {
    font-weight: 600;
    color: #262626;
    font-size: 14px;
}

.threads-card-time {
    color: #8e8e8e;
    font-size: 12px;
}

.threads-card-content {
    line-height: 1.5;
    color: #262626;
    font-size: 14px;
    margin-bottom: 1rem;
    white-space: pre-line;
}

.threads-card-meta {
    display: flex;
    align-items: center;
    gap: 1rem;
    color: #8e8e8e;
    font-size: 12px;
    padding-top: 0.5rem;
    border-top: 1px solid #f0f0f0;
}

.event-tag {
    background: #e3f2fd;
    color: #1976d2;
    padding: 0.2rem 0.6rem;
    border-radius: 12px;
    font-size: 11px;
    font-weight: 500;
    margin-right: 0.5rem;
}

.location-tag {
    background: #f3e5f5;
    color: #7b1fa2;
    padding: 0.2rem 0.6rem;
    border-radius: 12px;
    font-size: 11px;
    font-weight: 500;
}

.load-more-button {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 0.8rem 2rem;
    border-radius: 25px;
    border: none;
    font-weight: 600;
    font-size: 14px;
    transition: all 0.3s ease;
    box-shadow: 0 2px 8px rgba(102, 126, 234, 0.3);
    cursor: pointer;
}

.load-more-button:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 16px rgba(102, 126, 234, 0.4);
}

/* その他既存のスタイル */
.stCheckbox > label {
    background: white;
    padding: 0.8rem 1rem;
    border-radius: 12px;
    margin: 0.3rem 0;
    transition: all 0.3s ease;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    border: 1px solid #dbdbdb;
    color: #262626;
}

.stCheckbox > label:hover {
    transform: translateY(-1px);
    box-shadow: 0 2px 8px rgba(0,0,0,0.15);
    border-color: #fd5949;
}

.stButton > button {
    background: linear-gradient(135deg, #fd5949 0%, #d6336c 100%);
    color: white !important;
    border: none;
    border-radius: 8px;
    padding: 0.75rem 1.5rem;
    font-weight: 600;
    font-size: 14px;
    transition: all 0.3s ease;
    box-shadow: 0 2px 8px rgba(253, 89, 73, 0.3);
    text-shadow: none;
}

.stButton > button:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(253, 89, 73, 0.4);
}

button[kind="primary"] {
    background: linear-gradient(135deg, #fd5949 0%, #d6336c 100%) !important;
    color: white !important;
    font-weight: 600 !important;
    text-shadow: none !important;
}

.success-container {
    background: #e8f5e8;
    border-radius: 8px;
    padding: 1rem 1.5rem;
    text-align: center;
    color: #2e7d32;
    margin: 1rem 0;
    border: 1px solid #4caf50;
}

.success-title {
    font-size: 1.1rem;
    font-weight: 600;
    margin-bottom: 0.3rem;
}

.ai-message-box {
    background: white;
    border-radius: 12px;
    padding: 1.5rem;
    margin: 1rem 0;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    border: 1px solid #dbdbdb;
    white-space: pre-line;
    line-height: 1.6;
    color: #262626;
}

.generating-message {
    color: #8e8e8e;
    font-style: italic;
    text-align: center;
    padding: 2rem;
    background: white;
    border-radius: 12px;
    border: 1px solid #dbdbdb;
}

.social-share-button {
    background: linear-gradient(135deg, #1DA1F2 0%, #0d8bd9 100%);
    color: white;
    padding: 1rem 1.5rem;
    border-radius: 12px;
    text-decoration: none;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.3s ease;
    box-shadow: 0 2px 8px rgba(29, 161, 242, 0.3);
    margin: 1rem 0;
    font-weight: 600;
}

.social-share-button:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(29, 161, 242, 0.4);
    text-decoration: none;
    color: white;
}

.edit-suggestion {
    background: #fff3cd;
    border: 1px solid #ffeaa7;
    border-radius: 8px;
    padding: 1rem;
    margin: 0.5rem 0;
    color: #856404;
    font-size: 0.9rem;
}

.form-label {
    font-size: 1.2rem;
    font-weight: bold;
    color: #262626;
    margin: 1.5rem 0 0.5rem 0;
}

.form-sublabel {
    color: #8e8e8e;
    font-size: 0.9rem;
    margin-bottom: 1rem;
}

.info-box {
    background: white;
    border: 1px solid #e1e5e9;
    border-radius: 12px;
    padding: 2rem;
    text-align: center;
    margin: 2rem 0;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}

.info-box-icon {
    font-size: 3rem;
    margin-bottom: 1rem;
}

.info-box-title {
    font-size: 1.3rem;
    font-weight: bold;
    color: #262626;
    margin-bottom: 0.5rem;
}

/* スクロール位置調整用 */
.scroll-top {
    position: relative;
    top: -100px;
    visibility: hidden;
}
</style>
""", unsafe_allow_html=True)

# 改善された理由のリスト（カテゴリ別に整理）
IMPROVED_REASONS = {
    "👶 子育て・家族関連": [
        "子どもの預け先がない",
        "託児サービスがない/高額",
        "子どもが病気・体調不良",
        "授乳・おむつ替えの設備不足",
        "子連れ参加が困難な雰囲気",
        "家族の介護が必要",
        "家族の理解・協力が得られない"
    ],
    "💼 仕事・時間関連": [
        "仕事の都合がつかない",
        "会社で許可が降りなかった", 
        "残業・緊急対応が入った",
        "シフト勤務で調整困難",
        "有給取得が難しい",
        "参加が難しい時間"
    ],
    "💰 経済・アクセス関連": [
        "参加費が高額",
        "交通費が負担",
        "遠方で参加困難",
        "交通アクセスが悪い",
        "宿泊費が負担"
    ],
    "📢 情報・その他": [
        "開催情報を知るのが遅かった",
        "申込み締切に間に合わなかった",
        "定員に達していた",
        "自分の体調不良",
        "天候不良",
        "その他"
    ]
}

# ユーティリティ関数
def is_valid_url(url):
    """URLの形式をチェックする"""
    if not url:
        return True

    url_pattern = re.compile(
        r'^https?://'                                     # http:// または https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+'  # ドメイン名（例: www.example.com）
        r'[A-Z]{2,6}\.?|'                                  # TLD（例: .com, .net）
        r'localhost|'                                      # localhost
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'              # IP アドレス
        r'(?::\d+)?'                                       # ポート番号（任意）
        r'(?:/?|[/?]\S+)$',                                # パス部分
        re.IGNORECASE
    )

    return re.match(url_pattern, url) is not None

@st.cache_data(ttl=3600)  # 1時間キャッシュ
def get_url_metadata(url):
    """URLからメタデータ（タイトル、説明、画像）を取得"""
    if not url or not is_valid_url(url):
        return None
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # タイトル取得
        title = None
        title_tag = soup.find('title')
        if title_tag:
            title = title_tag.get_text().strip()
        
        # OGタイトル取得（優先）
        og_title = soup.find('meta', property='og:title')
        if og_title:
            title = og_title.get('content', '').strip()
        
        # 説明取得
        description = None
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc:
            description = meta_desc.get('content', '').strip()
        
        # OG説明取得（優先）
        og_desc = soup.find('meta', property='og:description')
        if og_desc:
            description = og_desc.get('content', '').strip()
        
        # 画像取得
        image_url = None
        og_image = soup.find('meta', property='og:image')
        if og_image:
            image_url = og_image.get('content', '').strip()
            # 相対URLの場合は絶対URLに変換
            if image_url and not image_url.startswith('http'):
                from urllib.parse import urljoin
                image_url = urljoin(url, image_url)
        
        return {
            'title': title,
            'description': description,
            'image': image_url,
            'url': url
        }
        
    except Exception as e:
        print(f"URL メタデータ取得エラー: {e}")
        return None

def display_url_preview(metadata):
    """URLプレビューカードを表示"""
    if not metadata:
        return
    
    st.markdown(f"""
    <div style="
        border: 1px solid #e1e5e9;
        border-radius: 12px;
        padding: 1rem;
        margin: 1rem 0;
        background: white;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    ">
        <div style="display: flex; gap: 1rem;">
            {'<div style="flex-shrink: 0;"><img src="' + metadata['image'] + '" style="width: 80px; height: 80px; object-fit: cover; border-radius: 8px;" /></div>' if metadata.get('image') else ''}
            <div style="flex: 1;">
                <div style="font-weight: bold; margin-bottom: 0.5rem; color: #262626;">
                    {metadata.get('title', 'イベント情報')}
                </div>
                {f'<div style="color: #8e8e8e; font-size: 0.9rem; line-height: 1.4;">{metadata["description"][:100]}{"..." if len(metadata.get("description", "")) > 100 else ""}</div>' if metadata.get('description') else ''}
                <div style="color: #667eea; font-size: 0.8rem; margin-top: 0.5rem;">
                    🔗 {metadata['url']}
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

def generate_tweet_text_from_post_content(post_content, event_location):
    """生成された投稿内容からツイート用テキストを生成する"""
    # ハッシュタグを追加
    hashtags = "#行きたかったマップ #IkitakattaMap"
    
    if event_location and event_location != "オンライン・Web開催":
        if "都" in event_location:
            hashtags += " #東京"
        else:
            prefecture = event_location.split()[0] if " " in event_location else event_location
            hashtags += f" #{prefecture}"
    else:
        hashtags += " #オンラインイベント"
    
    # 投稿内容が長い場合は短縮
    max_length = 280 - len(hashtags) - 5  # 余裕を持たせる
    
    if len(post_content) > max_length:
        tweet_text = post_content[:max_length-3] + "..." + " " + hashtags
    else:
        tweet_text = post_content + " " + hashtags
    
    encoded_text = urllib.parse.quote(tweet_text)
    
    return {
        "text": tweet_text,
        "url": f"https://twitter.com/intent/tweet?text={encoded_text}"
    }

# データのキャッシュ設定
@st.cache_data(ttl=300)
def cached_load_data():
    return logic.load_data()

# AIコメント生成関連（既存のコードを使用）
NG_WORDS = ["寄り添", "共感", "お察し", "深く理解", "寄り添いたい"]

def generate_empathy_comment_stream(event_name, reasons, comment):
    """ストリーミング対応のAIコメント生成ジェネレーター"""
    try:
        api_key = st.secrets.get("openai", {}).get("api_key")
        if not api_key:
            default_message = "お忙しい中、貴重な体験を共有していただきありがとうございます。\n\n行きたかったけど行けなかった気持ち、本当によく分かります。特に子育て中は、自分の時間を作ることすら難しいですよね。\n\nでも、あなたのこの声はとても大切です。一人ひとりの「行きたかった」が集まることで、社会の見えない障壁が見えてきます。\n\nきっと同じ思いをしている方がたくさんいるはずです。あなたの勇気ある投稿が、より参加しやすい社会を作る第一歩になります。"
            for char in default_message:
                yield char
            return
        
        client = openai.OpenAI(api_key=api_key)
        
        prompt = f"""
「{event_name}」に行きたかったけど行けなかった方への、深い共感と希望のメッセージを作成してください。

このメッセージの目的：
1. まず、行けなかった気持ちに深く共感し、寄り添う
2. 特に子育て中や働く方々の困難を理解していることを示す
3. 個人の問題ではなく、社会的な課題であることを伝える
4. 声を集めることで改善につながる可能性と希望を伝える
5. その人の勇気ある行動を讃える

メッセージの構成：
- 第1段落：感情への深い共感（特に子育て中の困難への理解）
- 第2段落：社会的な背景への理解と、個人のせいではないことの確認
- 第3段落：声を集めることの意義と、変化への具体的な希望
- 第4段落：その人への感謝と、勇気への讃辞

トーン：
- 温かく共感的でありながら、希望と力強さを感じられる
- 特に子育て中の方への深い理解を示す
- 社会変革への可能性を前向きに伝える
- その人の行動の価値を認める
- 以下の語句を一切使わない：{", ".join(NG_WORDS)}

参加できなかった理由: {', '.join(reasons)}
ユーザーのコメント: {comment if comment else '(コメントなし)'}

重要：特に子育て中の困難（託児の問題、時間の制約、周囲の理解不足など）に対する深い理解を示し、それを個人の問題ではなく社会の構造的な問題として変えていこうということを伝えてください。
"""
        
        stream = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "あなたは社会課題の解決に取り組む共感力豊かなカウンセラーです。特に子育て中の方や働く方々が直面する困難を深く理解し、個人の体験を社会課題として捉え、集合的な力で変化を起こすことを信じています。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.8,
            max_tokens=1200,
            stream=True
        )
        
        for chunk in stream:
            if chunk.choices[0].delta.content is not None:
                yield chunk.choices[0].delta.content
                
    except Exception as e:
        print(f"AIコメント生成エラー: {e}")
        default_message = "お忙しい中、貴重な体験を共有していただきありがとうございます。\n\n行きたかったけど行けなかった気持ち、本当によく分かります。特に子育て中は、自分の時間を作ることすら難しいですよね。\n\nあなたのこの声はとても大切です。一人ひとりの「行きたかった」が集まることで、より参加しやすい社会を作る力になります。"
        for char in default_message:
            yield char

def generate_engaging_post_stream(event_name, reasons, comment, event_location):
    """個人の生々しい感情を表現する投稿内容をストリーミング生成（コメント重視）"""
    try:
        api_key = st.secrets.get("openai", {}).get("api_key")
        if not api_key:
            # デフォルトの投稿文（より個人的で感情的）
            reason_text = "、".join(reasons[:3])
            default_post = f"楽しみにしていた #{event_name}。でも{reason_text}で泣く泣く断念…😭"
            for char in default_post:
                yield char
            return
        
        client = openai.OpenAI(api_key=api_key)
        
        # 理由を整理（最大3つまで）
        main_reasons = reasons[:3] if len(reasons) > 3 else reasons
        reason_text = "、".join(main_reasons)
        
        # コメントの存在に応じてプロンプトを調整
        if comment and comment.strip():
            comment_instruction = f"""
【重要：ユーザーコメントの活用】
ユーザーが以下のコメントを書いています：
「{comment}」

このコメントの内容や感情を必ず投稿文に反映してください。
コメントに書かれている具体的な状況や気持ちを、投稿文の中心にしてください。
"""
        else:
            comment_instruction = "ユーザーのコメントはありませんが、理由から感情を推測して表現してください。"
        
        prompt = f"""
SNSの個人投稿として、本人の生々しい感情を表現する短い投稿文を作成してください。

【イベント情報】
- イベント名: {event_name}
- 開催地: {event_location}
- 参加できなかった理由: {reason_text}

{comment_instruction}

【投稿文の要件】
1. 文字数: 80-150文字程度（短くて印象的）
2. 視点: 完全に一人称・本人視点のみ
3. 感情: 悲しさ、悔しさ、がっかり感をストレートに表現
4. トーン: 率直で生々しい感情表現
5. 理由の反映: 提供された複数の理由をできるだけ自然に含める
6. コメント重視: ユーザーのコメントがある場合は、その内容を最優先で反映

【スタイル指針】
- 「楽しみにしていた」「でも」「泣く泣く」のような感情的な言葉を使用
- 絵文字は1-2個程度（😭、😢、💔など悲しい系）
- ハッシュタグでイベント名を含める（#{event_name}）
- 改行は最小限、シンプルに
- カッコ（）は絶対に使わない
- 理由は自然な文章の流れで複数含める
- ユーザーのコメントがある場合は、その感情や状況を中心に構成

【絶対に避けるべき表現】
- カッコ「」や（）の使用
- 第三者への呼びかけ（「みんなで」「一緒に」など）
- 前向きすぎるメッセージ
- 社会問題への言及
- 励ましや応援のメッセージ
- 「私たち」「みなさん」などの複数形表現

【求める感情表現の例】
- がっかり感
- 悔しさ
- 残念な気持ち
- 諦めざるを得なかった感情
- ユーザーのコメントに書かれた具体的な感情

【参考スタイル】
「楽しみにしていた #{event_name}。でも仕事の都合がつかず、託児サービスも見つからなくて泣く泣く断念…本当に悔しい😭」

本人の個人的で率直な感情のみを表現し、他の人への言及や社会的メッセージは一切含めないでください。
複数の理由を自然な文章で表現してください。
ユーザーのコメントがある場合は、その内容を投稿文の核として使用してください。
"""
        
        stream = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "あなたは個人の感情表現の専門家です。第三者視点は一切使わず、本人の生々しく率直な感情のみを短い文章で表現することが得意です。前向きなメッセージや社会的な呼びかけは絶対に含めません。カッコは絶対に使いません。複数の理由を自然に組み込むことができます。ユーザーのコメントがある場合は、それを最優先で反映します。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=200,
            stream=True
        )
        
        for chunk in stream:
            if chunk.choices[0].delta.content is not None:
                yield chunk.choices[0].delta.content
                
    except Exception as e:
        print(f"投稿文生成エラー: {e}")
        # エラー時のデフォルト投稿文
        reason_text = "、".join(reasons[:3])
        if comment and comment.strip():
            default_post = f"楽しみにしていた #{event_name}。{comment[:50]}{'...' if len(comment) > 50 else ''}😭"
        else:
            default_post = f"楽しみにしていた #{event_name}。でも{reason_text}で泣く泣く断念…😭"
        for char in default_post:
            yield char

def display_threads_style_posts(df, title="📱 みんなの投稿", posts_per_page=20):
    """Threads風の投稿一覧を表示（「次の○件を読み込む」ボタン付き）"""
    if df.empty:
        st.markdown("""
        <div class="info-box">
            <div class="info-box-icon">📝</div>
            <div class="info-box-title">まだ投稿はありません</div>
            <div>最初の投稿をしてみませんか？</div>
        </div>
        """, unsafe_allow_html=True)
        return
    
    # 表示順を新しい投稿が上になるように
    display_df = df.iloc[::-1].reset_index(drop=True)
    
    # 件数表示を修正（重複を除去）
    st.markdown(f"### {title}（{len(display_df)}件）")
    
    # 表示する投稿数の管理
    if 'displayed_posts_count' not in st.session_state:
        st.session_state.displayed_posts_count = posts_per_page
    
    # 表示する投稿数を制限
    posts_to_show = min(st.session_state.displayed_posts_count, len(display_df))
    current_posts = display_df.iloc[:posts_to_show]
    
    # Threads風投稿カード表示
    for idx, row in current_posts.iterrows():
        # 生成された投稿文を優先表示
        main_content = ""
        if row.get('generated_post') and str(row['generated_post']).strip():
            main_content = str(row['generated_post'])
        else:
            # フォールバック: イベント名と理由から生成
            event_name = row['event_name']
            if len(event_name) > 30:
                event_name = event_name[:30] + "..."
            main_content = f"「{event_name}」に行きたかったけど行けなかった..."
        
        # 開催地情報
        if row['event_prefecture'] == "オンライン・Web開催":
            location_text = "🌐 オンライン"
        else:
            location_text = f"📍 {row['event_prefecture']}"
            if row.get('event_municipality') and row['event_municipality'] not in ["", "選択なし"]:
                if len(row['event_municipality']) > 8:
                    location_text += f" {row['event_municipality'][:8]}..."
                else:
                    location_text += f" {row['event_municipality']}"
        
        # 投稿時間の整理
        post_time = ""
        if row.get('submission_date'):
            try:
                from datetime import datetime
                if isinstance(row['submission_date'], str):
                    post_date = datetime.strptime(row['submission_date'][:19], "%Y-%m-%d %H:%M:%S")
                else:
                    post_date = row['submission_date']
                post_time = post_date.strftime("%m/%d %H:%M")
            except:
                post_time = str(row['submission_date'])[:16]
        
        # Threads風カード（タグ表示を修正）
        st.markdown(f'''
        <div class="threads-card">
            <div class="threads-card-header">
                <div class="threads-card-avatar">📝</div>
                <div>
                    <div class="threads-card-user">匿名ユーザー</div>
                    <div class="threads-card-time">{post_time}</div>
                </div>
            </div>
            <div class="threads-card-content">
                {main_content}
            </div>
            <div class="threads-card-meta">
                <span>{location_text}</span>
                <span>💬 #行きたかったマップ</span>
            </div>
        </div>
        ''', unsafe_allow_html=True)
    
    # 「次の○件を読み込む」ボタン
    remaining_posts = len(display_df) - posts_to_show
    if remaining_posts > 0:
        st.markdown("<div style='text-align: center; margin: 2rem 0;'>", unsafe_allow_html=True)
        load_count = min(posts_per_page, remaining_posts)
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button(f"📄 次の{load_count}件を読み込む（残り{remaining_posts}件）", use_container_width=True):
                st.session_state.displayed_posts_count += posts_per_page
                st.rerun()
        
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        # 全て表示済みの場合
        if len(display_df) > posts_per_page:
            st.markdown("<div style='text-align: center; margin: 2rem 0; color: #8e8e8e;'>", unsafe_allow_html=True)
            st.markdown("✅ 全ての投稿を表示しました")
            st.markdown("</div>", unsafe_allow_html=True)

# フォームデータの復元関数（既存のコードを使用）
def restore_form_data():
    """session_stateからフォームデータを復元"""
    if 'form_data' in st.session_state and st.session_state.form_data:
        form_data = st.session_state.form_data
        
        if "event_name" in form_data:
            st.session_state["event_name_input"] = form_data["event_name"]
        if "event_url" in form_data:
            st.session_state["event_url_input"] = form_data["event_url"]
        if "other_reason" in form_data:
            st.session_state["other_reason_input"] = form_data["other_reason"]
        if "comment" in form_data:
            st.session_state["comment_input"] = form_data["comment"]
            
        if "selected_reasons" in form_data:
            for reason in form_data["selected_reasons"]:
                if not reason.startswith("その他:"):
                    st.session_state[f"reason_{reason}"] = True
                else:
                    other_text = reason.replace("その他: ", "")
                    st.session_state["other_reason_input"] = other_text
        
        if "event_location_search" in form_data:
            st.session_state["event_location_input"] = form_data["event_location_search"]
        if "user_location_search" in form_data:
            st.session_state["user_location_input"] = form_data["user_location_search"]
            
        if "event_search_clicked" in form_data:
            st.session_state.event_search_clicked = form_data["event_search_clicked"]
        if "event_location_results" in form_data:
            st.session_state.event_location_results = form_data["event_location_results"]
        if "user_search_clicked" in form_data:
            st.session_state.user_search_clicked = form_data["user_search_clicked"]
        if "user_location_results" in form_data:
            st.session_state.user_location_results = form_data["user_location_results"]

def handle_user_location_search():
    """居住地検索のEnterキー対応"""
    if st.session_state.user_location_input and len(st.session_state.user_location_input) >= 2:
        st.session_state.user_search_clicked = True
        st.session_state.user_location_results = logic.search_locations(st.session_state.user_location_input)

def handle_event_location_search():
    """イベント開催地検索のEnterキー対応"""
    if st.session_state.event_location_input and len(st.session_state.event_location_input) >= 2:
        st.session_state.event_search_clicked = True
        st.session_state.event_location_results = logic.search_locations(st.session_state.event_location_input)

# scroll_to_top関数を削除（不要になったため）

def main():
    # 初期化
    logic.migrate_csv_if_needed()
    df = cached_load_data()
    
    # セッション状態の初期化
    if 'stage' not in st.session_state:
        st.session_state.stage = 'form'
    if 'form_data' not in st.session_state:
        st.session_state.form_data = {}
    if 'ai_comment' not in st.session_state:
        st.session_state.ai_comment = ""
    if 'is_submitting' not in st.session_state:
        st.session_state.is_submitting = False
    if 'confirmation_shown' not in st.session_state:
        st.session_state.confirmation_shown = False
    
    # 投稿生成関連の状態
    if 'generated_post_content' not in st.session_state:
        st.session_state.generated_post_content = ""
    if 'post_content_generated' not in st.session_state:
        st.session_state.post_content_generated = False
    if 'user_edited_post' not in st.session_state:
        st.session_state.user_edited_post = ""
    
    # マップ関連の状態
    if 'selected_prefecture' not in st.session_state:
        st.session_state.selected_prefecture = None
    if 'selected_municipality' not in st.session_state:
        st.session_state.selected_municipality = None
    if 'map_mode' not in st.session_state:
        st.session_state.map_mode = 'prefecture'  # 'prefecture' or 'municipality'
    
    # 検索状態の初期化
    if "event_search_clicked" not in st.session_state:
        st.session_state.event_search_clicked = False
    if "event_location_results" not in st.session_state:
        st.session_state.event_location_results = []
    if "user_search_clicked" not in st.session_state:
        st.session_state.user_search_clicked = False
    if "user_location_results" not in st.session_state:
        st.session_state.user_location_results = []
    
    # タブ選択状態の初期化
    if 'active_tab' not in st.session_state:
        st.session_state.active_tab = 0  # デフォルトは最初のタブ（投稿一覧）
    
    # 投稿一覧の表示件数管理
    if 'displayed_posts_count' not in st.session_state:
        st.session_state.displayed_posts_count = 20
    
    # ヘッダー
    st.markdown("""
    <div class="header-container">
        <div class="header-title">🗺️ #行きたかったマップ</div>
        <div class="header-subtitle">行きたかったけど行けなかったイベントを共有して、みんなでより参加しやすい社会を作ろう</div>
    </div>
    """, unsafe_allow_html=True)
    
    # タブの作成（選択状態を管理）- 投稿一覧をトップに
    tab_names = ["📱 投稿一覧", "✏️ 投稿する", "🗺️ マップ&分析"]
    
    # タブボタン風の表示
    cols = st.columns(len(tab_names))
    for i, (col, tab_name) in enumerate(zip(cols, tab_names)):
        with col:
            is_active = (i == st.session_state.active_tab)
            button_type = "primary" if is_active else "secondary"
            # ユニークなキーを生成
            button_key = f"main_tab_{i}"
            if st.button(tab_name, key=button_key, type=button_type, use_container_width=True):
                if i != st.session_state.active_tab:
                    st.session_state.active_tab = i
                    # タブ切り替え時に表示件数をリセット
                    if i == 0:
                        st.session_state.displayed_posts_count = 20
                    st.rerun()
    
    st.markdown("---")
    
    # アクティブなタブに応じてコンテンツを表示
    if st.session_state.active_tab == 0:
        # タブ1: Threads風投稿一覧
        st.markdown('<div class="section-header">📱 みんなの「行きたかった」投稿</div>', unsafe_allow_html=True)
        
        if df.empty:
            st.markdown("""
            <div class="info-box">
                <div class="info-box-icon">📝</div>
                <div class="info-box-title">まだ投稿はありません</div>
                <div>最初の投稿をしてみませんか？</div>
            </div>
            """, unsafe_allow_html=True)
            
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                if st.button("✏️ 投稿してみる", type="primary", use_container_width=True):
                    st.session_state.active_tab = 1  # 投稿フォームに移動
                    st.rerun()
        else:
            # フィルタオプション
            with st.expander("🔍 フィルタオプション", expanded=False):
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    # 都道府県フィルタ
                    prefectures = ["すべて"] + sorted(df['event_prefecture'].unique().tolist())
                    selected_pref = st.selectbox("都道府県", prefectures)
                
                with col2:
                    # 期間フィルタ
                    time_options = ["すべて", "最近1週間", "最近1ヶ月", "最近3ヶ月"]
                    selected_time = st.selectbox("期間", time_options)
                
                with col3:
                    # 理由フィルタ
                    all_reasons = []
                    for reasons_str in df['reasons'].dropna():
                        all_reasons.extend(str(reasons_str).split('|'))
                    unique_reasons = ["すべて"] + sorted(list(set(all_reasons)))[:10]  # 上位10件のみ
                    selected_reason = st.selectbox("理由", unique_reasons)
            
            # フィルタ適用
            filtered_df = df.copy()
            
            if selected_pref != "すべて":
                filtered_df = filtered_df[filtered_df['event_prefecture'] == selected_pref]
            
            if selected_reason != "すべて":
                filtered_df = filtered_df[filtered_df['reasons'].str.contains(selected_reason, na=False)]
            
            if selected_time != "すべて":
                filtered_df_temp = filtered_df.copy()
                filtered_df_temp['submission_date'] = pd.to_datetime(filtered_df_temp['submission_date'], errors='coerce')
                current_time = datetime.now()
                
                if selected_time == "最近1週間":
                    cutoff = current_time - pd.Timedelta(days=7)
                elif selected_time == "最近1ヶ月":
                    cutoff = current_time - pd.Timedelta(days=30)
                elif selected_time == "最近3ヶ月":
                    cutoff = current_time - pd.Timedelta(days=90)
                
                filtered_df = filtered_df_temp[filtered_df_temp['submission_date'] > cutoff]
            
            # フィルタが変更された場合、表示件数をリセット
            filter_key = f"{selected_pref}_{selected_time}_{selected_reason}"
            if 'last_filter_key' not in st.session_state or st.session_state.last_filter_key != filter_key:
                st.session_state.displayed_posts_count = 20
                st.session_state.last_filter_key = filter_key
            
            # Threads風投稿一覧を表示
            display_threads_style_posts(filtered_df, f"📱 投稿一覧", posts_per_page=20)
            
            # 投稿ボタン
            st.markdown("---")
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                if st.button("✏️ あなたも投稿してみる", type="primary", use_container_width=True):
                    st.session_state.active_tab = 1  # 投稿フォームに移動
                    st.rerun()
    
    elif st.session_state.active_tab == 1:
        # タブ2: 投稿フォーム
        if st.session_state.stage == 'form':
            if st.session_state.form_data and not st.session_state.confirmation_shown:
                restore_form_data()
            
            # イベント名
            st.markdown('<div class="form-label">🎯 どのイベントに行きたかったですか？</div>', unsafe_allow_html=True)
            col1, col2 = st.columns([2, 3])
            with col1:
                event_name = st.text_input(
                    "イベント名", 
                    label_visibility="collapsed",
                    placeholder="例: AI勉強会、Tech Conference",
                    key="event_name_input",
                    disabled=st.session_state.confirmation_shown
                )
            with col2:
                st.markdown("<div style='padding-top: 8px; font-size: 1.2rem; color: #fd5949;'>に行きたかったけど行けなかった！</div>", unsafe_allow_html=True)
            
            # イベントURL
            st.markdown('<div class="form-label">🔗 イベントのURL（任意）</div>', unsafe_allow_html=True)
            st.markdown('<div class="form-sublabel">イベントページやSNS投稿のURLがあれば教えてください</div>', unsafe_allow_html=True)
            event_url = st.text_input(
                "イベントURL", 
                label_visibility="collapsed",
                placeholder="例: https://connpass.com/event/...",
                key="event_url_input",
                disabled=st.session_state.confirmation_shown
            )
            
            st.markdown("---")
            
            # 参加できなかった理由
            st.markdown('<div class="form-label">🤔 参加できなかった理由は？</div>', unsafe_allow_html=True)
            st.markdown('<div class="form-sublabel">あてはまるものをすべて選んでください</div>', unsafe_allow_html=True)
            
            selected_reasons = []
            
            for category, reasons_list in IMPROVED_REASONS.items():
                st.markdown(f'<div class="reason-category">{category}</div>', unsafe_allow_html=True)
                
                cols = st.columns(2)
                for i, reason in enumerate(reasons_list):
                    col_index = i % 2
                    with cols[col_index]:
                        if st.checkbox(reason, key=f"reason_{reason}", disabled=st.session_state.confirmation_shown):
                            selected_reasons.append(reason)
            
            # その他の理由
            st.markdown('<div class="form-label">✍️ その他の理由があれば教えてください</div>', unsafe_allow_html=True)
            other_reason = st.text_input(
                "その他の理由", 
                label_visibility="collapsed",
                placeholder="具体的な理由があれば...",
                key="other_reason_input",
                disabled=st.session_state.confirmation_shown
            )
            
            if other_reason:
                selected_reasons.append(f"その他: {other_reason}")
            
            st.markdown("---")
            
            # 思い・コメント
            st.markdown('<div class="form-label">💭 思いや気持ちを聞かせてください（任意）</div>', unsafe_allow_html=True)
            st.markdown('<div class="form-sublabel">⭐ この内容が投稿文のメインになります。具体的な状況や感情を書いてください</div>', unsafe_allow_html=True)
            comment = st.text_area(
                "コメント", 
                label_visibility="collapsed", 
                height=120,
                placeholder="例：「すごく楽しみにしていたのに、子どもが熱を出してしまって...」「有給申請したけど会社で却下されて本当にがっかり」など、具体的な状況や気持ちを教えてください",
                key="comment_input",
                disabled=st.session_state.confirmation_shown
            )
            
            st.markdown("---")
            
            # 開催地選択
            st.markdown('<div class="form-label">📍 イベント開催地を教えてください</div>', unsafe_allow_html=True)
            
            current_location_type = st.radio(
                "開催形式",
                options=["地域検索（市町村名がわかる場合）", "オンライン・Web開催", "都道府県のみわかる"],
                horizontal=True,
                key="location_type_radio",
                disabled=st.session_state.confirmation_shown
            )
            
            # 変数の初期化
            event_prefecture = ""
            event_municipality = ""
            event_location_selected = None
            location_valid = False
            event_location_search = ""
            
            if current_location_type == "オンライン・Web開催":
                event_prefecture = "オンライン・Web開催"
                event_municipality = ""
                event_location_selected = "オンライン・Web開催"
                location_valid = True
                st.success("🌐 オンライン・Web開催として記録されます")
            
            elif current_location_type == "都道府県のみわかる":
                prefectures = list(logic.PREFECTURE_LOCATIONS.keys())
                selected_pref = st.selectbox(
                    "都道府県を選択してください",
                    options=prefectures,
                    index=None,
                    placeholder="都道府県を選んでください",
                    key="prefecture_select",
                    disabled=st.session_state.confirmation_shown
                )
                
                if selected_pref:
                    event_prefecture = selected_pref
                    event_municipality = ""
                    event_location_selected = selected_pref
                    location_valid = True
                    st.success(f"📍 {selected_pref}として記録されます")
                else:
                    if not st.session_state.confirmation_shown:
                        st.info("📍 都道府県を選択してください")
            
            else:
                # 地域検索の場合
                col1, col2 = st.columns([4, 1])
                with col1:
                    event_location_search = st.text_input(
                        "イベント開催地検索", 
                        label_visibility="collapsed", 
                        placeholder="例: 渋谷、新宿、しぶや、しんじゅく", 
                        key="event_location_input",
                        on_change=handle_event_location_search,
                        disabled=st.session_state.confirmation_shown
                    )
                
                with col2:
                    event_search_button = st.button("🔍 検索", key="event_search_btn", disabled=st.session_state.confirmation_shown)
                
                if event_search_button and event_location_search and len(event_location_search) >= 2:
                    st.session_state.event_search_clicked = True
                    st.session_state.event_location_results = logic.search_locations(event_location_search)
                
                if st.session_state.event_search_clicked:
                    if st.session_state.event_location_results:
                        event_location_options = [location for location, _, _ in st.session_state.event_location_results]
                        
                        event_location_selected = st.selectbox(
                            "検索結果から選んでください", 
                            options=event_location_options,
                            key="event_location_selector",
                            disabled=st.session_state.confirmation_shown
                        )
                        
                        if event_location_selected:
                            event_prefecture, event_municipality = logic.split_location(event_location_selected)
                            location_valid = True
                    else:
                        if not st.session_state.confirmation_shown:
                            st.warning("🔍 検索結果がありません。別のキーワードをお試しください。")
                        event_location_selected = None
                else:
                    if not st.session_state.confirmation_shown:
                        st.info("📝 地域名を入力して「🔍 検索」ボタンを押すか、Enterキーを押してください")
            
            # あなたの居住市町村名（任意）
            st.markdown('<div class="form-label">🏠 あなたの居住地（任意）</div>', unsafe_allow_html=True)
            
            user_location_search = ""
            
            col1, col2 = st.columns([4, 1])
            with col1:
                user_location_search = st.text_input(
                    "居住地検索", 
                    label_visibility="collapsed", 
                    placeholder="例: 横浜、大阪、福岡", 
                    key="user_location_input",
                    on_change=handle_user_location_search,
                    disabled=st.session_state.confirmation_shown
                )
            
            with col2:
                user_search_button = st.button("🏠 検索", key="user_search_btn", disabled=st.session_state.confirmation_shown)
            
            if user_search_button and user_location_search and len(user_location_search) >= 2:
                st.session_state.user_search_clicked = True
                st.session_state.user_location_results = logic.search_locations(user_location_search)
            
            user_prefecture = ""
            user_municipality = ""
            user_location_selected = None
            
            if st.session_state.user_search_clicked:
                if st.session_state.user_location_results:
                    user_location_options = [location for location, _, _ in st.session_state.user_location_results]
                    
                    user_location_selected = st.selectbox(
                        "居住地の検索結果から選んでください", 
                        options=user_location_options,
                        key="user_location_select",
                        disabled=st.session_state.confirmation_shown
                    )
                    
                    if user_location_selected:
                        user_prefecture, user_municipality = logic.split_location(user_location_selected)
                else:
                    if not st.session_state.confirmation_shown:
                        st.warning("🔍 検索結果がありません。別のキーワードをお試しください。")
            else:
                if not st.session_state.confirmation_shown:
                    st.info("📝 地域名を入力して「🏠 検索」ボタンを押すか、Enterキーを押してください")
            
            # 送信ボタン（確認前のみ表示）
            if not st.session_state.confirmation_shown:
                event_date = datetime.now().strftime("%Y-%m-%d")
                
                if st.button("✅ 内容を確認する", type="primary", use_container_width=True):
                    error = False
                    
                    if not event_name:
                        st.error("🎯 イベント名を入力してください")
                        error = True
                    
                    if event_url and not is_valid_url(event_url):
                        st.error("🔗 有効なURLを入力してください（http://またはhttps://で始まる形式）")
                        error = True
                    
                    if not location_valid:
                        st.error("📍 イベント開催地を選択してください")
                        error = True
                    
                    if not selected_reasons:
                        st.error("🤔 参加できなかった理由を選択してください")
                        error = True
                    
                    if not error:
                        st.session_state.form_data = {
                            "event_name": event_name,
                            "event_url": event_url,
                            "event_prefecture": event_prefecture,
                            "event_municipality": event_municipality,
                            "event_location_selected": event_location_selected,
                            "event_date": event_date,
                            "user_prefecture": user_prefecture,
                            "user_municipality": user_municipality,
                            "user_location_selected": user_location_selected,
                            "selected_reasons": selected_reasons,
                            "other_reason": other_reason,
                            "comment": comment,
                            "event_location_search": event_location_search,
                            "user_location_search": user_location_search,
                            "event_search_clicked": st.session_state.event_search_clicked,
                            "event_location_results": st.session_state.event_location_results,
                            "user_search_clicked": st.session_state.user_search_clicked,
                            "user_location_results": st.session_state.user_location_results,
                        }
                        
                        # 投稿生成状態をリセット
                        st.session_state.generated_post_content = ""
                        st.session_state.post_content_generated = False
                        st.session_state.user_edited_post = ""
                        
                        st.session_state.confirmation_shown = True
                        st.rerun()
            
            # 確認セクション（フォームの下に表示）
            if st.session_state.confirmation_shown:
                st.markdown("---")
                st.markdown('<div class="section-header">✅ 投稿内容の確認</div>', unsafe_allow_html=True)
                
                form_data = st.session_state.form_data
                
                # 投稿文の生成と表示
                st.markdown('<div class="section-header">📱 SNS投稿プレビュー</div>', unsafe_allow_html=True)
                st.markdown('<div style="color: #8e8e8e; margin-bottom: 1rem;">入力いただいた内容から、共感を呼ぶ投稿文を自動生成します</div>', unsafe_allow_html=True)
                
                post_placeholder = st.empty()
                
                # 投稿文生成
                if not st.session_state.post_content_generated:
                    post_placeholder.markdown('<div class="generating-post">✨ 共感を呼ぶ投稿文を生成中...</div>', unsafe_allow_html=True)
                    
                    generated_text = ""
                    
                    try:
                        for chunk in generate_engaging_post_stream(
                            form_data['event_name'],
                            form_data['selected_reasons'],
                            form_data['comment'],
                            form_data['event_location_selected']
                        ):
                            generated_text += chunk
                            # Threads風プレビュー表示
                            post_placeholder.markdown(f'''
                            <div class="threads-post-box">
                                <div class="threads-post-label">🚀 投稿プレビュー</div>
                                <div class="threads-header">
                                    <div class="threads-avatar">📝</div>
                                    <div class="threads-username">あなた</div>
                                </div>
                                <div class="threads-content">{generated_text}</div>
                                <div class="threads-meta">
                                    <span>📱 SNS投稿</span>
                                    <span>🎯 #行きたかったマップ</span>
                                </div>
                            </div>
                            ''', unsafe_allow_html=True)
                        
                        st.session_state.generated_post_content = generated_text
                        st.session_state.post_content_generated = True
                        
                    except Exception as e:
                        print(f"投稿文生成エラー: {e}")
                        default_post = f"楽しみにしていた #{form_data['event_name']}。でも{', '.join(form_data['selected_reasons'][:2])}で泣く泣く断念…😭"
                        
                        post_placeholder.markdown(f'''
                        <div class="threads-post-box">
                            <div class="threads-post-label">🚀 投稿プレビュー</div>
                            <div class="threads-header">
                                <div class="threads-avatar">📝</div>
                                <div class="threads-username">あなた</div>
                            </div>
                            <div class="threads-content">{default_post}</div>
                            <div class="threads-meta">
                                <span>📱 SNS投稿</span>
                                <span>🎯 #行きたかったマップ</span>
                            </div>
                        </div>
                        ''', unsafe_allow_html=True)
                        
                        st.session_state.generated_post_content = default_post
                        st.session_state.post_content_generated = True
                
                else:
                    # 既に生成済みの場合は表示
                    display_content = st.session_state.user_edited_post if st.session_state.user_edited_post else st.session_state.generated_post_content
                    post_placeholder.markdown(f'''
                    <div class="threads-post-box">
                        <div class="threads-post-label">🚀 投稿プレビュー</div>
                        <div class="threads-header">
                            <div class="threads-avatar">📝</div>
                            <div class="threads-username">あなた</div>
                        </div>
                        <div class="threads-content">{display_content}</div>
                        <div class="threads-meta">
                            <span>📱 SNS投稿</span>
                            <span>🎯 #行きたかったマップ</span>
                        </div>
                    </div>
                    ''', unsafe_allow_html=True)
                
                # 再生成ボタンを投稿プレビューの直下に配置
                if st.session_state.post_content_generated:
                    col_regen1, col_regen2, col_regen3 = st.columns([1, 2, 1])
                    with col_regen2:
                        if st.button("🔄 投稿文を再生成", use_container_width=True):
                            st.session_state.post_content_generated = False
                            st.session_state.user_edited_post = ""
                            st.rerun()
                
                # 投稿文の編集機能
                if st.session_state.post_content_generated:
                    st.markdown("### ✏️ 投稿文の編集（任意）")
                    
                    edit_content = st.text_area(
                        "投稿文を編集できます",
                        value=st.session_state.user_edited_post if st.session_state.user_edited_post else st.session_state.generated_post_content,
                        height=150,
                        key="post_edit_area"
                    )
                    
                    if edit_content != (st.session_state.user_edited_post if st.session_state.user_edited_post else st.session_state.generated_post_content):
                        st.session_state.user_edited_post = edit_content
                    
                    st.markdown('''
                    <div class="edit-suggestion">
                        💡 投稿文は自由に編集できます！<br>
                        より多くの人に共感してもらえる内容に調整してみてください。
                    </div>
                    ''', unsafe_allow_html=True)
                
                st.markdown("---")
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("⬅️ 戻って修正", use_container_width=True):
                        st.session_state.confirmation_shown = False
                        st.session_state.post_content_generated = False
                        st.session_state.user_edited_post = ""
                        st.rerun()
                with col2:
                    if 'is_submitting' not in st.session_state:
                        st.session_state.is_submitting = False
                    
                    if st.button("🚀 この内容で投稿する", type="primary", use_container_width=True, disabled=st.session_state.is_submitting):
                        st.session_state.is_submitting = True
                        st.rerun()
                
                if st.session_state.is_submitting and st.session_state.confirmation_shown:
                    with st.spinner("🚀 投稿中..."):
                        # 最終的な投稿文を決定（ユーザー編集版 or 生成版）
                        final_post_content = st.session_state.user_edited_post if st.session_state.user_edited_post else st.session_state.generated_post_content
                        
                        # 修正されたlogic.pyの save_submission を呼び出し
                        success = logic.save_submission(
                            form_data['event_name'], 
                            form_data['event_url'],
                            form_data['event_prefecture'], 
                            form_data['event_municipality'], 
                            form_data['event_date'],
                            form_data['user_prefecture'], 
                            form_data['user_municipality'], 
                            form_data['selected_reasons'], 
                            form_data['comment'],
                            final_post_content  # 生成された投稿文を追加
                        )
                        
                        if success:
                            # ツイート用データ生成
                            tweet_data = generate_tweet_text_from_post_content(
                                final_post_content,
                                form_data['event_location_selected']
                            )
                            st.session_state.tweet_data = tweet_data
                            st.session_state.final_post_content = final_post_content
                            
                            st.session_state.stage = 'success'
                            st.session_state.ai_comment = ""
                            st.session_state.ai_comment_generated = False
                            st.cache_data.clear()
                            st.session_state.is_submitting = False
                            st.rerun()
                        else:
                            st.error("❌ 投稿に失敗しました。しばらく時間をおいてから再度お試しください。")
                            st.session_state.is_submitting = False
        
        elif st.session_state.stage == 'success':
            # 成功画面
            st.markdown("""
            <div class="success-container">
                <div class="success-title">✅ 投稿完了</div>
                <div class="success-subtitle">ありがとうございます</div>
            </div>
            """, unsafe_allow_html=True)
            
            form_data = st.session_state.form_data
            
            # 生成された投稿文を表示
            if 'final_post_content' in st.session_state:
                st.markdown("### 🚀 あなたの投稿")
                st.markdown(f'''
                <div class="threads-post-box">
                    <div class="threads-post-label">✨ 完成した投稿</div>
                    <div class="threads-header">
                        <div class="threads-avatar">📝</div>
                        <div class="threads-username">あなた</div>
                    </div>
                    <div class="threads-content">{st.session_state.final_post_content}</div>
                    <div class="threads-meta">
                        <span>📱 SNS投稿</span>
                        <span>🎯 #行きたかったマップ</span>
                        <span>✅ 投稿完了</span>
                    </div>
                </div>
                ''', unsafe_allow_html=True)
            
            st.markdown("### 📝 投稿した詳細データ")
            st.markdown(f"**「{form_data['event_name']}」に行きたかったけど行けなかった**")
            
            if form_data.get('event_url'):
                st.markdown(f"🔗 **イベントURL:** [{form_data['event_url']}]({form_data['event_url']})")
                
                # URLプレビューの表示
                url_metadata = get_url_metadata(form_data['event_url'])
                if url_metadata:
                    display_url_preview(url_metadata)
            
            if form_data['comment']:
                st.write(f"💭 **元のコメント:** {form_data['comment']}")
            
            st.markdown("---")
            
            # AIメッセージ表示
            st.markdown('<div class="section-header">💬 あなたへの特別なメッセージ</div>', unsafe_allow_html=True)
            st.markdown('<div style="color: #8e8e8e; margin-bottom: 1rem;">あなたの勇気ある声に対して、心を込めたメッセージをお送りします</div>', unsafe_allow_html=True)
            
            if 'ai_comment_generated' not in st.session_state:
                st.session_state.ai_comment_generated = False
            
            message_placeholder = st.empty()
            
            if not st.session_state.ai_comment_generated:
                message_placeholder.markdown('<div class="generating-message">💭 心のこもったメッセージを生成中...</div>', unsafe_allow_html=True)
                
                generated_text = ""
                
                try:
                    for chunk in generate_empathy_comment_stream(
                        form_data['event_name'],
                        form_data['selected_reasons'],
                        form_data['comment']
                    ):
                        generated_text += chunk
                        message_placeholder.markdown(f'<div class="ai-message-box">{generated_text}</div>', unsafe_allow_html=True)
                    
                    st.session_state.ai_comment = generated_text
                    st.session_state.ai_comment_generated = True
                    
                except Exception as e:
                    print(f"ストリーミング生成エラー: {e}")
                    default_message = "お忙しい中、貴重な体験を共有していただきありがとうございます。\n\n行きたかったけど行けなかった気持ち、本当によく分かります。特に子育て中は、自分の時間を作ることすら難しいですよね。\n\nあなたのこの声はとても大切です。一人ひとりの「行きたかった」が集まることで、より参加しやすい社会を作る力になります。"
                    
                    message_placeholder.markdown(f'<div class="ai-message-box">{default_message}</div>', unsafe_allow_html=True)
                    
                    st.session_state.ai_comment = default_message
                    st.session_state.ai_comment_generated = True
            
            else:
                message_placeholder.markdown(f'<div class="ai-message-box">{st.session_state.ai_comment}</div>', unsafe_allow_html=True)
            
            st.markdown("---")
            
            # Xでの共有機能
            if 'tweet_data' in st.session_state:
                st.markdown('<div class="section-header">📢 みんなにも共有しよう</div>', unsafe_allow_html=True)
                
                x_button_html = f"""
                <a href="{st.session_state.tweet_data['url']}" target="_blank" class="social-share-button">
                    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="currentColor" style="margin-right:8px;" viewBox="0 0 16 16">
                        <path d="M12.6.75h2.454l-5.36 6.142L16 15.25h-4.937l-3.867-5.07-4.425 5.07H.316l5.733-6.57L0 .75h5.063l3.495 4.633L12.601.75Zm-.86 13.028h1.36L4.323 2.145H2.865l8.875 11.633Z"/>
                    </svg>
                    Xで共有する
                </a>
                """
                st.markdown(x_button_html, unsafe_allow_html=True)
                
                with st.expander("📝 共有される投稿内容"):
                    st.code(st.session_state.tweet_data['text'], language="")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                # 投稿一覧表示ボタン
                if st.button("📱 投稿一覧を見る", use_container_width=True):
                    st.session_state.active_tab = 0  # 投稿一覧タブに切り替え
                    st.session_state.displayed_posts_count = 20  # 表示件数をリセット
                    st.rerun()
            
            with col2:
                # マップ表示ボタン（タブ切り替え）
                if st.button("🗺️ マップを見る", use_container_width=True):
                    st.session_state.active_tab = 2  # マップタブに切り替え
                    st.rerun()
            
            with col3:
                if st.button("✏️ 新しい投稿を作成", type="primary", use_container_width=True):
                    st.session_state.stage = 'form'
                    st.session_state.form_data = {}
                    st.session_state.ai_comment = ""
                    st.session_state.ai_comment_generated = False
                    st.session_state.is_submitting = False
                    st.session_state.confirmation_shown = False  # 確認状態もリセット
                    st.session_state.event_search_clicked = False
                    st.session_state.event_location_results = []
                    st.session_state.user_search_clicked = False
                    st.session_state.user_location_results = []
                    # 投稿生成関連の状態もリセット
                    st.session_state.generated_post_content = ""
                    st.session_state.post_content_generated = False
                    st.session_state.user_edited_post = ""
                    if 'tweet_data' in st.session_state:
                        del st.session_state.tweet_data
                    if 'final_post_content' in st.session_state:
                        del st.session_state.final_post_content
                    st.rerun()
    
    elif st.session_state.active_tab == 2:
        # タブ3: マップ&分析
        st.markdown('<div class="section-header">🗺️ 全国の声とマップ</div>', unsafe_allow_html=True)
        
        if df.empty:
            st.markdown("""
            <div class="info-box">
                <div class="info-box-icon">📝</div>
                <div class="info-box-title">まだ投稿はありません</div>
                <div>最初の投稿をしてみませんか？</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            # メインコンテンツ：マップと投稿一覧
            map_col, list_col = st.columns([1.2, 1])
            
            with map_col:
                if st.session_state.map_mode == 'prefecture':
                    # 都道府県レベルのマップ
                    st.markdown("### 🗺️ 都道府県別の分布")
                    
                    prefecture_data = logic.count_by_prefecture()
                    
                    if not prefecture_data.empty:
                        # マップの作成と表示
                        deck = map_utils.create_prefecture_map(prefecture_data, st.session_state.selected_prefecture)
                        
                        if deck:
                            # 選択機能を有効にして表示
                            map_result = st.pydeck_chart(
                                deck, 
                                use_container_width=True,
                                on_select="rerun",
                                key="prefecture_map"
                            )
                            
                            # 選択データの処理（session_stateから取得）
                            selected_prefecture, _ = map_utils.get_selected_object_from_session_state(
                                "prefecture_map", 
                                prefecture_data, 
                                "prefecture"
                            )
                            
                            # 新しい都道府県が選択された場合
                            if (selected_prefecture and 
                                selected_prefecture != st.session_state.selected_prefecture and
                                selected_prefecture in prefecture_data['prefecture'].values):
                                
                                # 選択状態を更新
                                st.session_state.selected_prefecture = selected_prefecture
                                st.session_state.selected_municipality = None
                                st.session_state.map_mode = 'municipality'
                                
                                # タブ状態を維持してrerun
                                if st.session_state.get('can_rerun', True):
                                    st.session_state.can_rerun = False
                                    # active_tabを明示的に2に設定してタブ切り替えを防ぐ
                                    st.session_state.active_tab = 2
                                    st.rerun()
                            
                            # rerunフラグをリセット
                            if not st.session_state.get('can_rerun', True):
                                st.session_state.can_rerun = True
                    else:
                        st.info("🗺️ 表示する都道府県データがありません")
                
                elif st.session_state.map_mode == 'municipality':
                    # 市区町村レベルのマップ
                    col_title, col_back = st.columns([3, 1])
                    
                    with col_title:
                        if st.session_state.selected_municipality:
                            st.markdown(f"### 🏘️ {st.session_state.selected_prefecture} > {st.session_state.selected_municipality}")
                        else:
                            st.markdown(f"### 🏘️ {st.session_state.selected_prefecture}の市区町村別分布")
                    
                    with col_back:
                        # 戻るボタン（常に全国に戻る）
                        if st.button("⬅️ 全国に戻る", key="back_to_all"):
                            st.session_state.selected_prefecture = None
                            st.session_state.selected_municipality = None
                            st.session_state.map_mode = 'prefecture'
                            # タブ状態を維持
                            st.session_state.active_tab = 2
                            st.rerun()
                    
                    municipality_data = logic.count_by_municipality_in_prefecture(st.session_state.selected_prefecture)
                    
                    if not municipality_data.empty:
                        deck = map_utils.create_municipality_map(
                            municipality_data, 
                            st.session_state.selected_prefecture,
                            st.session_state.selected_municipality
                        )
                        
                        if deck:
                            # 選択機能を有効にして表示
                            map_result = st.pydeck_chart(
                                deck, 
                                use_container_width=True,
                                on_select="rerun",
                                key="municipality_map"
                            )
                            
                            # 選択データの処理（session_stateから取得）
                            _, selected_municipality = map_utils.get_selected_object_from_session_state(
                                "municipality_map", 
                                municipality_data, 
                                "municipality"
                            )
                            
                            # 新しい市区町村が選択された場合
                            if (selected_municipality and 
                                selected_municipality != st.session_state.selected_municipality and
                                selected_municipality in municipality_data['municipality'].values):
                                
                                # 選択状態を更新（rerunは避けてズーム状態を保持）
                                st.session_state.selected_municipality = selected_municipality
                                
                                # マップの色更新のための最小限のrerun（頻度制限付き）
                                if st.session_state.get('can_rerun_muni', True):
                                    st.session_state.can_rerun_muni = False
                                    # active_tabを明示的に2に設定してタブ切り替えを防ぐ
                                    st.session_state.active_tab = 2
                                    # 短時間での連続rerunを防ぐ
                                    import time
                                    if not hasattr(st.session_state, 'last_muni_rerun') or \
                                       time.time() - st.session_state.last_muni_rerun > 0.5:
                                        st.session_state.last_muni_rerun = time.time()
                                        st.rerun()
                            
                            # rerunフラグをリセット
                            if not st.session_state.get('can_rerun_muni', True):
                                st.session_state.can_rerun_muni = True
                    else:
                        st.info(f"🗺️ {st.session_state.selected_prefecture}の市区町村データがありません")
            
            with list_col:
                # 選択された地域に基づいて投稿をフィルタ
                if st.session_state.selected_municipality:
                    # 特定市区町村の投稿
                    location_filtered_df = logic.get_posts_by_municipality(
                        st.session_state.selected_prefecture, 
                        st.session_state.selected_municipality
                    )
                    title = f"📍 {st.session_state.selected_municipality}の投稿"
                elif st.session_state.selected_prefecture:
                    # 特定都道府県の投稿
                    location_filtered_df = logic.get_posts_by_prefecture(st.session_state.selected_prefecture)
                    title = f"📍 {st.session_state.selected_prefecture}の投稿"
                else:
                    # 全国の投稿
                    location_filtered_df = df
                    title = "📍 全国の投稿"
                
                # 投稿一覧の表示
                ui_components.display_post_cards(location_filtered_df, title, posts_per_page=8)

if __name__ == "__main__":
    main()