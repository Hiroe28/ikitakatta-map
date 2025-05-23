import streamlit as st
import pandas as pd
import pydeck as pdk
import altair as alt
from datetime import datetime
import uuid
import os
import openai
import urllib.parse
import re

# 自作ロジックモジュールをインポート
import logic

# ページ設定
st.set_page_config(
    page_title="#行きたかったマップ", 
    page_icon="🗺️", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# インスタグラム風のカスタムCSS
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

/* チェックボックスのスタイリング - インスタ風 */
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

/* 入力フィールドのスタイリング - インスタ風 */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea,
.stSelectbox > div > div > select {
    border-radius: 8px;
    border: 1px solid #dbdbdb;
    padding: 0.75rem;
    transition: all 0.3s ease;
    background-color: white;
    color: #262626;
}

.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus,
.stSelectbox > div > div > select:focus {
    border-color: #fd5949;
    box-shadow: 0 0 0 2px rgba(253, 89, 73, 0.2);
    outline: none;
}

/* ボタンのスタイリング - インスタ風、視認性改善 */
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

.stButton > button:active {
    transform: translateY(0px);
}

/* フォーム送信ボタンの特別スタイリング */
button[kind="primary"] {
    background: linear-gradient(135deg, #fd5949 0%, #d6336c 100%) !important;
    color: white !important;
    font-weight: 600 !important;
    text-shadow: none !important;
}

/* 成功メッセージのスタイリング - より控えめに */
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

.success-subtitle {
    font-size: 0.9rem;
    opacity: 0.8;
}

/* AIメッセージボックス - インスタ風 */
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

/* 投稿カードスタイル - インスタ風 */
.post-card {
    background: white;
    border-radius: 12px;
    padding: 1.5rem;
    margin: 1rem 0;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    border: 1px solid #dbdbdb;
    transition: all 0.3s ease;
}

.post-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
}

.post-title {
    font-size: 1.3rem;
    font-weight: bold;
    color: #262626;
    margin-bottom: 1rem;
}

.post-detail {
    margin: 0.5rem 0;
    color: #8e8e8e;
    font-size: 0.9rem;
}

.post-comment {
    background: #f8f8f8;
    padding: 1rem;
    border-radius: 8px;
    margin: 1rem 0;
    color: #262626;
    font-style: italic;
    border-left: 3px solid #fd5949;
}

/* URLリンクのスタイリング */
.event-url-link {
    color: #1DA1F2;
    text-decoration: none;
    font-weight: 500;
    transition: all 0.3s ease;
}

.event-url-link:hover {
    color: #0d8bd9;
    text-decoration: underline;
}

/* タブのスタイリング - インスタ風 */
.stTabs > div > div > div > div {
    background: white;
    color: #262626;
    border: 1px solid #dbdbdb;
    border-radius: 8px 8px 0 0;
    font-weight: 600;
}

.stTabs > div > div > div > div[aria-selected="true"] {
    background: linear-gradient(135deg, #fd5949 0%, #d6336c 100%);
    color: white;
}

/* アニメーション */
@keyframes fadeIn {
    from { opacity: 0; transform: translateY(20px); }
    to { opacity: 1; transform: translateY(0); }
}

.fade-in {
    animation: fadeIn 0.5s ease-out;
}

/* レスポンシブデザイン */
@media (max-width: 768px) {
    .header-title {
        font-size: 2rem;
    }
    
    .header-subtitle {
        font-size: 1rem;
    }
}

/* ソーシャルシェアボタン - インスタ風 */
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

/* セクションヘッダー */
.section-header {
    color: #262626;
    font-size: 1.5rem;
    font-weight: bold;
    margin: 2rem 0 1rem 0;
    padding-bottom: 0.5rem;
    border-bottom: 2px solid #fd5949;
}

/* 情報ボックス */
.info-box {
    background: white;
    border: 1px solid #dbdbdb;
    border-radius: 12px;
    padding: 1.5rem;
    margin: 1rem 0;
    color: #8e8e8e;
    text-align: center;
}

.info-box-icon {
    font-size: 3rem;
    margin-bottom: 1rem;
}

.info-box-title {
    font-size: 1.2rem;
    font-weight: 600;
    color: #262626;
    margin-bottom: 0.5rem;
}

/* フォームラベル */
.form-label {
    color: #262626;
    font-size: 1.1rem;
    font-weight: 600;
    margin: 1.5rem 0 0.5rem 0;
}

.form-sublabel {
    color: #8e8e8e;
    font-size: 0.9rem;
    margin-bottom: 1rem;
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
        "開催時間が合わない"
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

# URLの妥当性チェック関数
def is_valid_url(url):
    """URLの形式をチェックする"""
    if not url:
        return True  # 空文字は許可（任意項目のため）
    
    # 基本的なURL形式チェック
    url_pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    
    return url_pattern.match(url) is not None

# ツイート用テキスト生成関数
def generate_tweet_text(event_name, reasons, event_location):
    """投稿内容からツイート用テキストを生成する"""
    
    # イベント名をハッシュタグ用に変換（スペース削除、特殊文字削除）
    event_hashtag = re.sub(r'[^\w\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]', '', event_name)
    
    # ハッシュタグ（f-stringを使用）
    hashtags = f"#行きたかったマップ #IkitakattaMap #{event_hashtag}"
    
    # 地域タグ
    if event_location and "都" in event_location:
        hashtags += " #東京"
    elif event_location:
        prefecture = event_location.split()[0] if " " in event_location else event_location
        hashtags += f" #{prefecture}"
    
    # ツイート本文
    tweet_text = f"{event_name}に行きたかったけど行けなかった😢 みんなの「行きたかった」の声を集めて、もっと参加しやすい社会にしていこう！ {hashtags}"
    
    # URLエンコード
    encoded_text = urllib.parse.quote(tweet_text)
    
    return {
        "text": tweet_text,
        "url": f"https://twitter.com/intent/tweet?text={encoded_text}"
    }

# データのキャッシュ設定
@st.cache_data(ttl=300)  # 5分間キャッシュ
def cached_load_data():
    return logic.load_data()

def generate_empathy_comment_stream(event_name, reasons, comment):
    """ストリーミング対応のAIコメント生成ジェネレーター"""
    try:
        # OpenAI APIキーをsecrets.tomlから取得
        api_key = st.secrets.get("openai", {}).get("api_key")
        if not api_key:
            # デフォルトメッセージをストリーミング風に返す
            default_message = "お忙しい中、貴重な体験を共有していただきありがとうございます。\n\n行きたかったけど行けなかった気持ち、本当によく分かります。特に子育て中は、自分の時間を作ることすら難しいですよね。\n\nでも、あなたのこの声はとても大切です。一人ひとりの「行きたかった」が集まることで、社会の見えない障壁が見えてきます。\n\nきっと同じ思いをしている方がたくさんいるはずです。あなたの勇気ある投稿が、より参加しやすい社会を作る第一歩になります。"
            for char in default_message:
                yield char
            return
        
        # OpenAIクライアントを初期化
        client = openai.OpenAI(api_key=api_key)
        
        # プロンプト作成
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

参加できなかった理由: {', '.join(reasons)}
ユーザーのコメント: {comment if comment else '(コメントなし)'}

重要：特に子育て中の困難（託児の問題、時間の制約、周囲の理解不足など）に対する深い理解を示し、それが個人の問題ではなく社会の構造的な問題であることを伝えてください。
"""
        
        # AIによるストリーミングコメント生成
        stream = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "あなたは社会課題の解決に取り組む共感力豊かなカウンセラーです。特に子育て中の方や働く方々が直面する困難を深く理解し、個人の体験を社会課題として捉え、集合的な力で変化を起こすことを信じています。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.8,
            max_tokens=1200,
            stream=True
        )
        
        # ストリーミングレスポンスを返す
        for chunk in stream:
            if chunk.choices[0].delta.content is not None:
                yield chunk.choices[0].delta.content
                
    except Exception as e:
        # エラーが発生した場合はデフォルトのコメントを返す
        print(f"AIコメント生成エラー: {e}")
        default_message = "お忙しい中、貴重な体験を共有していただきありがとうございます。\n\n行きたかったけど行けなかった気持ち、本当によく分かります。特に子育て中は、自分の時間を作ることすら難しいですよね。\n\nあなたのこの声はとても大切です。一人ひとりの「行きたかった」が集まることで、より参加しやすい社会を作る力になります。"
        for char in default_message:
            yield char

def main():
    # スプレッドシートの初期化と必要ならマイグレーション
    logic.migrate_csv_if_needed()
    
    # データ読み込み
    df = cached_load_data()
    
    # セッション状態の初期化
    if 'stage' not in st.session_state:
        st.session_state.stage = 'form'  # 'form', 'confirm', 'success'のいずれか
    
    if 'form_data' not in st.session_state:
        st.session_state.form_data = {}
    
    if 'ai_comment' not in st.session_state:
        st.session_state.ai_comment = ""
    
    if 'is_submitting' not in st.session_state:
        st.session_state.is_submitting = False
    
    # フォーム入力データの初期化（戻るボタン用）
    if 'event_name' not in st.session_state:
        st.session_state.event_name = ""
    if 'event_url' not in st.session_state:
        st.session_state.event_url = ""
    if 'comment' not in st.session_state:
        st.session_state.comment = ""
    if 'other_reason' not in st.session_state:
        st.session_state.other_reason = ""
    if 'event_location_search' not in st.session_state:
        st.session_state.event_location_search = ""
    if 'user_location_search' not in st.session_state:
        st.session_state.user_location_search = ""
    
    # ヘッダー
    st.markdown("""
    <div class="header-container">
        <div class="header-title">🗺️ #行きたかったマップ</div>
        <div class="header-subtitle">行きたかったけど行けなかったイベントを共有して、みんなでより参加しやすい社会を作ろう</div>
    </div>
    """, unsafe_allow_html=True)
    
    # タブの作成
    tab1, tab2, tab3 = st.tabs(["✏️ 投稿する", "📋 みんなの声", "🗺️ マップ"])
    
    # タブ1: 投稿フォーム
    with tab1:
        if st.session_state.stage == 'form':
            # 入力フォーム
            with st.form(key="ikitakatta_form"):
                # イベント名
                st.markdown('<div class="form-label">🎯 どのイベントに行きたかったですか？</div>', unsafe_allow_html=True)
                col1, col2 = st.columns([2, 3])
                with col1:
                    event_name = st.text_input("", label_visibility="collapsed", 
                                             value=st.session_state.event_name,
                                             placeholder="例: AI勉強会、Tech Conference")
                with col2:
                    st.markdown("<div style='padding-top: 8px; font-size: 1.2rem; color: #fd5949;'>に行きたかったけど行けなかった！</div>", unsafe_allow_html=True)
                
                # イベントURL（新規追加）
                st.markdown('<div class="form-label">🔗 イベントのURL（任意）</div>', unsafe_allow_html=True)
                st.markdown('<div class="form-sublabel">イベントページやSNS投稿のURLがあれば教えてください</div>', unsafe_allow_html=True)
                event_url = st.text_input("", label_visibility="collapsed", 
                                         value=st.session_state.event_url,
                                         placeholder="例: https://connpass.com/event/...")
                
                st.markdown("---")
                
                # 参加できなかった理由（改善されたカテゴリ別）
                st.markdown('<div class="form-label">🤔 参加できなかった理由は？</div>', unsafe_allow_html=True)
                st.markdown('<div class="form-sublabel">あてはまるものをすべて選んでください</div>', unsafe_allow_html=True)
                
                selected_reasons = []
                
                for category, reasons_list in IMPROVED_REASONS.items():
                    st.markdown(f'<div class="reason-category">{category}</div>', unsafe_allow_html=True)
                    
                    # チェックボックスを2列で配置
                    cols = st.columns(2)
                    for i, reason in enumerate(reasons_list):
                        col_index = i % 2
                        with cols[col_index]:
                            if st.checkbox(reason, key=f"reason_{reason}"):
                                selected_reasons.append(reason)
                
                # その他の理由
                st.markdown('<div class="form-label">✍️ その他の理由があれば教えてください</div>', unsafe_allow_html=True)
                other_reason = st.text_input("", label_visibility="collapsed", 
                                           value=st.session_state.other_reason,
                                           placeholder="具体的な理由があれば...")
                
                if other_reason:
                    selected_reasons.append(f"その他: {other_reason}")
                
                st.markdown("---")
                
                # 思い・コメント
                st.markdown('<div class="form-label">💭 思いや気持ちを聞かせてください（任意）</div>', unsafe_allow_html=True)
                comment = st.text_area("", label_visibility="collapsed", 
                                     height=100, value=st.session_state.comment,
                                     placeholder="どんな気持ちでしたか？どうすれば参加できたと思いますか？")
                
                st.markdown("---")
                
                # イベント開催地（必須）
                st.markdown('<div class="form-label">📍 イベント開催地を教えてください</div>', unsafe_allow_html=True)
                
                col1, col2 = st.columns([4, 1])
                with col1:
                    event_location_search = st.text_input("", label_visibility="collapsed", 
                                                        placeholder="例: 渋谷、新宿、札幌", 
                                                        key="event_location_input", 
                                                        value=st.session_state.event_location_search)
                
                # セッション状態の初期化
                if "event_search_clicked" not in st.session_state:
                    st.session_state.event_search_clicked = False
                if "event_location_results" not in st.session_state:
                    st.session_state.event_location_results = []
                
                with col2:
                    event_search_button = st.form_submit_button("🔍 検索")
                
                # 検索ボタンが押されたかどうかを判定
                if event_search_button and event_location_search and len(event_location_search) >= 2:
                    st.session_state.event_search_clicked = True
                    st.session_state.event_location_results = logic.search_locations(event_location_search)
                
                event_prefecture = ""
                event_municipality = ""
                event_location_selected = None
                location_valid = False
                
                # 検索結果の表示
                if st.session_state.event_search_clicked:
                    if st.session_state.event_location_results:
                        event_location_options = [location for location, _, _ in st.session_state.event_location_results]
                        
                        event_location_selected = st.selectbox(
                            "検索結果から選んでください", 
                            options=event_location_options,
                            key="event_location_selector"
                        )
                        
                        if event_location_selected:
                            event_prefecture, event_municipality = logic.split_location(event_location_selected)
                            location_valid = True
                    else:
                        st.warning("🔍 検索結果がありません。別のキーワードをお試しください。")
                        event_location_selected = None
                else:
                    st.info("📝 地域名を入力して「🔍 検索」ボタンを押してください")
                
                # あなたの居住地（任意）
                st.markdown('<div class="form-label">🏠 あなたの居住地（任意）</div>', unsafe_allow_html=True)
                
                col1, col2 = st.columns([4, 1])
                with col1:
                    user_location_search = st.text_input("", label_visibility="collapsed", 
                                                       placeholder="例: 横浜、大阪、福岡", 
                                                       key="user_location_input", 
                                                       value=st.session_state.user_location_search)
                
                if "user_search_clicked" not in st.session_state:
                    st.session_state.user_search_clicked = False
                if "user_location_results" not in st.session_state:
                    st.session_state.user_location_results = []
                
                with col2:
                    user_search_button = st.form_submit_button("🏠 検索")
                
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
                            key="user_location_select"
                        )
                        
                        if user_location_selected:
                            user_prefecture, user_municipality = logic.split_location(user_location_selected)
                    else:
                        st.warning("🔍 検索結果がありません。別のキーワードをお試しください。")
                
                # イベント日付（非表示）
                event_date = datetime.now().strftime("%Y-%m-%d")
                
                # 送信ボタン
                submit_button = st.form_submit_button("✅ 内容を確認する", use_container_width=True)
                
                if submit_button:
                    # 入力チェック
                    error = False
                    
                    if not event_name:
                        st.error("🎯 イベント名を入力してください")
                        error = True
                    
                    # URLの妥当性チェック
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
                        # フォームデータをセッションに保存
                        st.session_state.form_data = {
                            "event_name": event_name,
                            "event_url": event_url,  # URLを追加
                            "event_prefecture": event_prefecture,
                            "event_municipality": event_municipality,
                            "event_location_selected": event_location_selected,
                            "event_date": event_date,
                            "user_prefecture": user_prefecture,
                            "user_municipality": user_municipality,
                            "user_location_selected": user_location_selected,
                            "selected_reasons": selected_reasons,
                            "other_reason": other_reason,
                            "comment": comment
                        }
                        
                        # 個別のフィールド値もセッションに保存
                        st.session_state.event_name = event_name
                        st.session_state.event_url = event_url
                        st.session_state.comment = comment
                        st.session_state.other_reason = other_reason
                        st.session_state.event_location_search = event_location_search
                        st.session_state.user_location_search = user_location_search
                        
                        # 確認画面へ
                        st.session_state.stage = 'confirm'
                        st.rerun()
        
        elif st.session_state.stage == 'confirm':
            # 確認画面
            st.markdown('<div class="section-header">✅ 投稿内容の確認</div>', unsafe_allow_html=True)
            
            form_data = st.session_state.form_data
            
            # 投稿内容を通常のStreamlitコンポーネントで表示（HTMLタグを使わない）
            st.markdown("### 📝 投稿内容")
            
            st.markdown(f"**「{form_data['event_name']}」に行きたかったけど行けなかった**")
            
            # URLがある場合は表示
            if form_data.get('event_url'):
                st.markdown(f"🔗 **イベントURL:** [{form_data['event_url']}]({form_data['event_url']})")
            
            st.write(f"📍 **開催地:** {form_data['event_location_selected']}")
            
            st.write("🤔 **参加できなかった理由:**")
            for reason in form_data['selected_reasons']:
                st.write(f"・{reason}")
            
            if form_data['comment']:
                st.write(f"💭 **コメント:** {form_data['comment']}")
            
            if form_data.get('user_location_selected'):
                st.write(f"🏠 **あなたの居住地:** {form_data['user_location_selected']}")
            
            st.markdown("---")
            # ボタン
            col1, col2 = st.columns(2)
            with col1:
                if st.button("⬅️ 戻って修正", use_container_width=True):
                    st.session_state.stage = 'form'
                    st.rerun()
            with col2:
                if 'is_submitting' not in st.session_state:
                    st.session_state.is_submitting = False
                
                if st.button("🚀 この内容で投稿する", type="primary", use_container_width=True, disabled=st.session_state.is_submitting):
                    st.session_state.is_submitting = True
                    st.rerun()
            
            # 投稿処理
            if st.session_state.is_submitting and st.session_state.stage == 'confirm':
                with st.spinner("🚀 投稿中..."):
                    success = logic.save_submission(
                        form_data['event_name'], 
                        form_data['event_url'],  # URLを追加
                        form_data['event_prefecture'], 
                        form_data['event_municipality'], 
                        form_data['event_date'],
                        form_data['user_prefecture'], 
                        form_data['user_municipality'], 
                        form_data['selected_reasons'], 
                        form_data['comment']
                    )
                    
                    if success:
                        # ツイート用テキストを生成
                        event_location = f"{form_data['event_prefecture']} {form_data['event_municipality']}".strip()
                        tweet_data = generate_tweet_text(
                            form_data['event_name'], 
                            form_data['selected_reasons'], 
                            event_location
                        )
                        st.session_state.tweet_data = tweet_data
                        
                        # 成功画面へ
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
            # 成功画面 - より控えめに
            st.markdown("""
            <div class="success-container">
                <div class="success-title">✅ 投稿完了</div>
                <div class="success-subtitle">ありがとうございます</div>
            </div>
            """, unsafe_allow_html=True)
            
            form_data = st.session_state.form_data
            
            # 投稿内容の表示
            st.markdown("### 📝 投稿した内容")
            st.markdown(f"**「{form_data['event_name']}」に行きたかったけど行けなかった**")
            
            # URLがあれば表示
            if form_data.get('event_url'):
                st.markdown(f"🔗 **イベントURL:** [{form_data['event_url']}]({form_data['event_url']})")
            
            if form_data['comment']:
                st.write(f"💭 **コメント:** {form_data['comment']}")
            
            st.markdown("---")
            
            # AIメッセージ表示 - より目立つように
            st.markdown('<div class="section-header">💬 あなたへの特別なメッセージ</div>', unsafe_allow_html=True)
            st.markdown('<div style="color: #8e8e8e; margin-bottom: 1rem;">あなたの勇気ある声に対して、心を込めたメッセージをお送りします</div>', unsafe_allow_html=True)
            
            # AIコメント生成フラグの初期化
            if 'ai_comment_generated' not in st.session_state:
                st.session_state.ai_comment_generated = False
            
            # AIコメントの表示領域を作成
            message_placeholder = st.empty()
            
            # AIコメントがまだ生成されていない場合は生成開始
            if not st.session_state.ai_comment_generated:
                # 初期表示：生成中メッセージ
                message_placeholder.markdown('<div class="generating-message">💭 心のこもったメッセージを生成中...</div>', unsafe_allow_html=True)
                
                # ストリーミング表示でAIコメントを生成
                generated_text = ""
                
                try:
                    for chunk in generate_empathy_comment_stream(
                        form_data['event_name'],
                        form_data['selected_reasons'],
                        form_data['comment']
                    ):
                        generated_text += chunk
                        message_placeholder.markdown(f'<div class="ai-message-box">{generated_text}</div>', unsafe_allow_html=True)
                    
                    # 生成完了
                    st.session_state.ai_comment = generated_text
                    st.session_state.ai_comment_generated = True
                    
                except Exception as e:
                    print(f"ストリーミング生成エラー: {e}")
                    default_message = "お忙しい中、貴重な体験を共有していただきありがとうございます。\n\n行きたかったけど行けなかった気持ち、本当によく分かります。特に子育て中は、自分の時間を作ることすら難しいですよね。\n\nあなたのこの声はとても大切です。一人ひとりの「行きたかった」が集まることで、より参加しやすい社会を作る力になります。"
                    
                    message_placeholder.markdown(f'<div class="ai-message-box">{default_message}</div>', unsafe_allow_html=True)
                    
                    st.session_state.ai_comment = default_message
                    st.session_state.ai_comment_generated = True
            
            else:
                # 既に生成済みの場合は保存されたコメントを表示
                message_placeholder.markdown(f'<div class="ai-message-box">{st.session_state.ai_comment}</div>', unsafe_allow_html=True)
            
            st.markdown("---")
            
            # Xでの共有機能
            if 'tweet_data' in st.session_state:
                st.markdown('<div class="section-header">📢 みんなにも共有しよう</div>', unsafe_allow_html=True)
                
                # Xで共有するボタン
                x_button_html = f"""
                <a href="{st.session_state.tweet_data['url']}" target="_blank" class="social-share-button">
                    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="currentColor" style="margin-right:8px;" viewBox="0 0 16 16">
                        <path d="M12.6.75h2.454l-5.36 6.142L16 15.25h-4.937l-3.867-5.07-4.425 5.07H.316l5.733-6.57L0 .75h5.063l3.495 4.633L12.601.75Zm-.86 13.028h1.36L4.323 2.145H2.865l8.875 11.633Z"/>
                    </svg>
                    Xで共有する
                </a>
                """
                st.markdown(x_button_html, unsafe_allow_html=True)
                
                # 共有する投稿内容のプレビュー
                with st.expander("📝 共有される投稿内容"):
                    st.code(st.session_state.tweet_data['text'], language="")
            
            # 新しい投稿を作成するボタン
            col1, col2 = st.columns(2)
            with col1:
                if st.button("📋 みんなの声を見る", use_container_width=True):
                    # タブ2に移動
                    st.switch_page("tab2")
            
            with col2:
                if st.button("✏️ 新しい投稿を作成", type="primary", use_container_width=True):
                    st.session_state.stage = 'form'
                    st.session_state.form_data = {}
                    st.session_state.ai_comment = ""
                    st.session_state.ai_comment_generated = False
                    st.session_state.is_submitting = False
                    if 'tweet_data' in st.session_state:
                        del st.session_state.tweet_data
                    st.rerun()
    
    # タブ2: 投稿一覧
    with tab2:
        st.markdown('<div class="section-header">📋 みんなの声</div>', unsafe_allow_html=True)
        st.markdown("同じ思いを持つ方々の声を聞いてみましょう")
        
        if df.empty:
            st.markdown("""
            <div class="info-box">
                <div class="info-box-icon">📝</div>
                <div class="info-box-title">まだ投稿はありません</div>
                <div>最初の投稿をしてみませんか？</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            # 簡易表示用にデータを整形
            display_df = df.copy()
            
            # reasonsを展開
            display_df["reasons"] = display_df["reasons"].str.split("|")
            display_df["reasons"] = display_df["reasons"].apply(lambda x: ", ".join(x) if isinstance(x, list) else x)
            
            # 開催地情報を結合
            display_df["event_location"] = display_df.apply(
                lambda row: f"{row['event_prefecture']} {row['event_municipality']}" 
                    if 'event_prefecture' in row and 'event_municipality' in row 
                       and row['event_municipality'] and row['event_municipality'] != "選択なし"
                    else (row['event_prefecture'] if 'event_prefecture' in row and row['event_prefecture'] 
                         else row['location']), 
                axis=1
            )
            
            # 表示順を新しい投稿が上になるように逆順に
            display_df = display_df.iloc[::-1].reset_index(drop=True)
            
            # 投稿を美しいカード形式で表示
            for idx, row in display_df.iterrows():
                # 投稿内容を通常のStreamlitコンポーネントで表示
                st.markdown(f"### 「{row['event_name']}」に行きたかったけど行けなかった")
                
                # URLがあれば表示
                if row.get('event_url') and row['event_url'] and row['event_url'].strip():
                    st.markdown(f"🔗 **イベントURL:** [{row['event_url']}]({row['event_url']})")
                
                st.write(f"📍 **開催地:** {row['event_location']}")
                st.write(f"🤔 **理由:** {row['reasons']}")
                
                if row.get('comment') and not pd.isna(row.get('comment')) and str(row.get('comment')).strip():
                    st.write(f"💭 **コメント:** {row['comment']}")
                
                st.markdown("---")
    
    # タブ3: マップ表示
    with tab3:
        st.markdown('<div class="section-header">🗺️ 全国の「行きたかった」声マップ</div>', unsafe_allow_html=True)
        st.markdown("各地域からの声を可視化しています")
        
        if df.empty:
            st.markdown("""
            <div class="info-box">
                <div class="info-box-icon">🗺️</div>
                <div class="info-box-title">まだデータがありません</div>
                <div>投稿が集まるとマップに表示されます</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            # 県別データの集計
            prefecture_counts = logic.count_by_prefecture()
            
            # マップデータの準備
            map_data = []
            for idx, row in prefecture_counts.iterrows():
                prefecture = row["location"]
                count = row["count"]
                
                if prefecture in logic.PREFECTURE_LOCATIONS:
                    lat, lon = logic.PREFECTURE_LOCATIONS[prefecture]
                    map_data.append({
                        "name": prefecture,
                        "count": int(count),
                        "latitude": lat,
                        "longitude": lon
                    })
            
            df_map = pd.DataFrame(map_data)
            
            # マップの表示
            if not df_map.empty:
                view_state = pdk.ViewState(
                    latitude=36.5,  # 日本の中心あたり
                    longitude=138.0,
                    zoom=4,
                    pitch=0
                )
                
                # ポイントのレイヤー
                layer = pdk.Layer(
                    "ScatterplotLayer",
                    data=df_map,
                    get_position=["longitude", "latitude"],
                    get_color=[253, 89, 73, 200],  # インスタ風の赤色
                    get_radius=["count * 8000"],  # 投稿数に応じてサイズ変更
                    pickable=True,
                    opacity=0.8,
                    stroked=True,
                    filled=True,
                    radius_min_pixels=15,
                    radius_max_pixels=120,
                    line_width_min_pixels=2,
                )
                
                # マップを描画
                r = pdk.Deck(
                    layers=[layer],
                    initial_view_state=view_state,
                    map_style="mapbox://styles/mapbox/light-v10",
                    tooltip={
                        "html": "<b>{name}</b><br/>📍 {count}件の「行きたかった」声",
                        "style": {
                            "backgroundColor": "white",
                            "color": "#262626",
                            "fontSize": "14px",
                            "padding": "10px",
                            "borderRadius": "8px",
                            "boxShadow": "0 2px 8px rgba(0,0,0,0.15)"
                        }
                    }
                )
                
                st.pydeck_chart(r)
                
                # 理由別の集計をシンプルに表示
                st.markdown('<div class="section-header">📊 参加できなかった理由の集計</div>', unsafe_allow_html=True)
                reasons_df = logic.count_by_reason()
                
                if not reasons_df.empty:
                    # 詳細なテーブル表示
                    with st.expander("📋 詳細な集計を見る"):
                        st.dataframe(reasons_df, use_container_width=True)

if __name__ == "__main__":
    main()