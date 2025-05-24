import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import openai
from collections import defaultdict

# 自作ロジックモジュールをインポート
import logic

# ページ設定
st.set_page_config(
    page_title="#行きたかったマップ 社会課題ダッシュボード", 
    page_icon="🗺️", 
    layout="wide"
)

# カスタムCSS（シンプル化）
st.markdown("""
<style>
.main-header {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    padding: 20px;
    border-radius: 10px;
    color: white;
    text-align: center;
    margin-bottom: 20px;
}

.action-card {
    background: white;
    border: 1px solid #e1e5e9;
    border-radius: 8px;
    padding: 20px;
    margin: 10px 0;
    box-shadow: 0 2px 4px rgba(0,0,0,0.05);
}

.priority-high {
    border-left: 4px solid #dc3545;
    background-color: #fff5f5;
}

.priority-medium {
    border-left: 4px solid #ffc107;
    background-color: #fffdf5;
}

.priority-low {
    border-left: 4px solid #28a745;
    background-color: #f5fff5;
}

.metric-box {
    background: #f8f9fa;
    padding: 15px;
    border-radius: 8px;
    text-align: center;
    margin: 5px 0;
}

.stakeholder-section {
    background: #f8f9fa;
    padding: 20px;
    border-radius: 10px;
    margin: 15px 0;
}
</style>
""", unsafe_allow_html=True)

# 管理者認証
def check_password():
    """管理者パスワードを確認する"""
    if "password_correct" not in st.session_state:
        st.session_state.password_correct = False

    if st.session_state.password_correct:
        return True

    st.markdown('''
    <div class="main-header">
        <h1>🗺️ 行きたかったマップ 社会課題ダッシュボード</h1>
        <p>どこにアプローチすべきかを見つける - アクション指向ダッシュボード</p>
    </div>
    ''', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.subheader("🔐 管理者ログイン")
        password = st.text_input("パスワードを入力してください", type="password")
        
        if st.button("ログイン", use_container_width=True):
            admin_password = st.secrets.get("admin", {}).get("password", "admin123")
            if password == admin_password:
                st.session_state.password_correct = True
                st.rerun()
            else:
                st.error("パスワードが違います")
                return False
    
    return False

# OpenAIクライアント取得
@st.cache_resource
def get_openai_client():
    """OpenAI クライアントを取得"""
    try:
        api_key = st.secrets.get("openai", {}).get("api_key")
        if not api_key:
            return None
        return openai.OpenAI(api_key=api_key)
    except Exception as e:
        st.error(f"OpenAI クライアント初期化エラー: {e}")
        return None

# 期間でデータをフィルタリング
def filter_by_period(df, months_back=2):
    """指定した期間でデータをフィルタリング"""
    if df.empty:
        return df
    
    df_temp = df.copy()
    df_temp['submission_date'] = pd.to_datetime(df_temp['submission_date'])
    cutoff_date = datetime.now() - timedelta(days=months_back * 30)
    return df_temp[df_temp['submission_date'] > cutoff_date]

# 基本統計の計算
def calculate_basic_stats(df):
    """基本統計を計算"""
    if df.empty:
        return {
            'total_posts': 0,
            'unique_events': 0,
            'affected_prefectures': 0,
            'affected_municipalities': 0,
            'growth_rate': 0
        }
    
    total_posts = len(df)
    unique_events = df['event_name'].nunique()
    affected_prefectures = df['event_prefecture'].nunique()
    affected_municipalities = df['event_municipality'].dropna().nunique()
    
    # 前月比の成長率計算
    df_temp = df.copy()
    df_temp['submission_date'] = pd.to_datetime(df_temp['submission_date'])
    
    last_month = datetime.now() - timedelta(days=30)
    prev_month = datetime.now() - timedelta(days=60)
    
    current_count = len(df_temp[df_temp['submission_date'] > last_month])
    prev_count = len(df_temp[(df_temp['submission_date'] > prev_month) & 
                            (df_temp['submission_date'] <= last_month)])
    
    growth_rate = ((current_count - prev_count) / max(prev_count, 1)) * 100 if prev_count > 0 else 0
    
    return {
        'total_posts': total_posts,
        'unique_events': unique_events,
        'affected_prefectures': affected_prefectures,
        'affected_municipalities': affected_municipalities,
        'growth_rate': growth_rate
    }

# 理由を社会課題カテゴリに分類
def categorize_reasons(reasons_text):
    """理由を社会課題カテゴリに分類"""
    categories = {
        '子育て・ケア': ['子ども', '託児', '授乳', 'おむつ', '子育て', '介護'],
        '労働・時間': ['仕事', '会社', '残業', 'シフト', '有給', '時間'],
        '経済・費用': ['参加費', '交通費', '宿泊費', '高額', '負担'],
        '情報・機会': ['情報', '締切', '定員', '知る'],
        '健康・その他': ['体調', '病気', '天候', 'その他']
    }
    
    result_categories = []
    reasons_lower = str(reasons_text).lower()
    
    for category, keywords in categories.items():
        if any(keyword in reasons_lower for keyword in keywords):
            result_categories.append(category)
    
    return result_categories if result_categories else ['その他']

# イベント主催者向けデータ分析
def analyze_for_event_organizers(df, min_posts=5):
    """イベント主催者向けの分析データを生成"""
    event_analysis = []
    
    # イベント別の集計
    event_counts = df['event_name'].value_counts()
    
    for event_name, count in event_counts.items():
        if count < min_posts:
            continue
            
        event_df = df[df['event_name'] == event_name]
        
        # 理由の分析
        all_reasons = []
        for reasons_str in event_df['reasons'].dropna():
            all_reasons.extend(str(reasons_str).split('|'))
        
        reason_counts = pd.Series(all_reasons).value_counts()
        top_reason = reason_counts.index[0] if len(reason_counts) > 0 else 'データなし'
        
        # 優先度の判定
        if count >= 15:
            priority = "高"
        elif count >= 10:
            priority = "中"
        else:
            priority = "低"
        
        # 開催地の分析
        locations = event_df['event_prefecture'].value_counts()
        main_location = locations.index[0] if len(locations) > 0 else 'データなし'
        
        event_analysis.append({
            'event_name': event_name,
            'post_count': count,
            'priority': priority,
            'top_reason': top_reason,
            'main_location': main_location,
            'reason_diversity': len(reason_counts),
            'latest_post': event_df['submission_date'].max()
        })
    
    return sorted(event_analysis, key=lambda x: x['post_count'], reverse=True)

# 自治体向けデータ分析
def analyze_for_government(df, min_posts=3):
    """自治体向けの分析データを生成"""
    municipal_analysis = []
    
    # 市区町村別の集計（空文字を除く）
    municipal_df = df[df['event_municipality'].notna() & (df['event_municipality'] != '')]
    municipal_counts = municipal_df['event_municipality'].value_counts()
    
    for municipality, count in municipal_counts.items():
        if count < min_posts:
            continue
            
        muni_df = municipal_df[municipal_df['event_municipality'] == municipality]
        
        # 理由の分析
        all_reasons = []
        for reasons_str in muni_df['reasons'].dropna():
            all_reasons.extend(str(reasons_str).split('|'))
        
        reason_counts = pd.Series(all_reasons).value_counts()
        top_reason = reason_counts.index[0] if len(reason_counts) > 0 else 'データなし'
        
        # カテゴリ分析
        categories = defaultdict(int)
        for reasons_str in muni_df['reasons'].dropna():
            cats = categorize_reasons(reasons_str)
            for cat in cats:
                categories[cat] += 1
        
        top_category = max(categories.items(), key=lambda x: x[1])[0] if categories else 'その他'
        
        # 優先度の判定
        if count >= 10:
            priority = "高"
        elif count >= 6:
            priority = "中"
        else:
            priority = "低"
        
        # 都道府県の取得
        prefecture = muni_df['event_prefecture'].iloc[0] if len(muni_df) > 0 else 'データなし'
        
        municipal_analysis.append({
            'municipality': municipality,
            'prefecture': prefecture,
            'post_count': count,
            'priority': priority,
            'top_reason': top_reason,
            'top_category': top_category,
            'event_count': muni_df['event_name'].nunique(),
            'latest_post': muni_df['submission_date'].max()
        })
    
    return sorted(municipal_analysis, key=lambda x: x['post_count'], reverse=True)

# 都道府県・企業向けデータ分析
def analyze_for_corporate(df, min_posts=5):
    """都道府県・企業向けの分析データを生成"""
    prefecture_analysis = []
    
    # 都道府県別の集計
    pref_counts = df['event_prefecture'].value_counts()
    
    for prefecture, count in pref_counts.items():
        if count < min_posts or prefecture == 'オンライン・Web開催':
            continue
            
        pref_df = df[df['event_prefecture'] == prefecture]
        
        # カテゴリ分析
        categories = defaultdict(int)
        for reasons_str in pref_df['reasons'].dropna():
            cats = categorize_reasons(reasons_str)
            for cat in cats:
                categories[cat] += 1
        
        top_category = max(categories.items(), key=lambda x: x[1])[0] if categories else 'その他'
        
        # 優先度の判定
        if count >= 20:
            priority = "高"
        elif count >= 10:
            priority = "中"
        else:
            priority = "低"
        
        # 主要な問題
        all_reasons = []
        for reasons_str in pref_df['reasons'].dropna():
            all_reasons.extend(str(reasons_str).split('|'))
        
        reason_counts = pd.Series(all_reasons).value_counts()
        top_reason = reason_counts.index[0] if len(reason_counts) > 0 else 'データなし'
        
        prefecture_analysis.append({
            'prefecture': prefecture,
            'post_count': count,
            'priority': priority,
            'top_category': top_category,
            'top_reason': top_reason,
            'event_count': pref_df['event_name'].nunique(),
            'municipality_count': pref_df['event_municipality'].nunique(),
            'latest_post': pref_df['submission_date'].max()
        })
    
    return sorted(prefecture_analysis, key=lambda x: x['post_count'], reverse=True)

# メディア向けデータ分析
def analyze_for_media(df):
    """メディア向けの分析データを生成"""
    media_stories = []
    
    # カテゴリ別の問題集計
    categories = defaultdict(int)
    for reasons_str in df['reasons'].dropna():
        cats = categorize_reasons(reasons_str)
        for cat in cats:
            categories[cat] += 1
    
    # 急増している問題の検出
    df_temp = df.copy()
    df_temp['submission_date'] = pd.to_datetime(df_temp['submission_date'])
    
    # 直近30日 vs 前30日の比較
    recent_30 = datetime.now() - timedelta(days=30)
    prev_30 = datetime.now() - timedelta(days=60)
    
    recent_df = df_temp[df_temp['submission_date'] > recent_30]
    prev_df = df_temp[(df_temp['submission_date'] > prev_30) & (df_temp['submission_date'] <= recent_30)]
    
    recent_categories = defaultdict(int)
    prev_categories = defaultdict(int)
    
    for reasons_str in recent_df['reasons'].dropna():
        cats = categorize_reasons(reasons_str)
        for cat in cats:
            recent_categories[cat] += 1
    
    for reasons_str in prev_df['reasons'].dropna():
        cats = categorize_reasons(reasons_str)
        for cat in cats:
            prev_categories[cat] += 1
    
    # 各カテゴリの分析
    for category, recent_count in recent_categories.items():
        prev_count = prev_categories.get(category, 0)
        total_count = categories[category]
        
        # 成長率
        growth_rate = ((recent_count - prev_count) / max(prev_count, 1)) * 100 if prev_count > 0 else 0
        
        # ニュース価値の判定
        if growth_rate > 50 and recent_count >= 5:
            news_value = "高"
            story_angle = f"急増中: {growth_rate:.0f}%増加"
        elif total_count >= 15:
            news_value = "中"
            story_angle = f"継続課題: {total_count}件の声"
        elif total_count >= 8:
            news_value = "低"
            story_angle = f"注目課題: {total_count}件の声"
        else:
            continue
        
        media_stories.append({
            'category': category,
            'total_count': total_count,
            'recent_count': recent_count,
            'growth_rate': growth_rate,
            'news_value': news_value,
            'story_angle': story_angle,
            'prefecture_spread': len(df[df['reasons'].str.contains('|'.join([r for r in df['reasons'] if category in str(r)]), na=False)]['event_prefecture'].unique()) if not df.empty else 0
        })
    
    return sorted(media_stories, key=lambda x: (x['news_value'] == '高', x['total_count']), reverse=True)

# 詳細グラフ生成
def create_detailed_charts(target_df, df_all, target_name, target_type):
    """詳細なグラフを生成"""
    charts_data = {}
    
    # 1. 理由別分布グラフ
    all_reasons = []
    for reasons_str in target_df['reasons'].dropna():
        all_reasons.extend(str(reasons_str).split('|'))
    
    if all_reasons:
        reason_counts = pd.Series(all_reasons).value_counts()
        reason_df = pd.DataFrame({
            '理由': reason_counts.index[:8],
            '件数': reason_counts.values[:8]
        })
        
        fig_reasons = px.bar(
            reason_df,
            x='件数',
            y='理由',
            orientation='h',
            title=f"{target_name} の参加障壁分析",
            color_discrete_sequence=['#667eea']
        )
        fig_reasons.update_layout(height=400, font=dict(size=12))
        charts_data['reasons_chart'] = fig_reasons
        charts_data['top_reason'] = reason_df.iloc[0]['理由']
        charts_data['top_reason_count'] = reason_df.iloc[0]['件数']
    
    # 2. カテゴリ別分析グラフ
    categories = defaultdict(int)
    for reasons_str in target_df['reasons'].dropna():
        cats = categorize_reasons(reasons_str)
        for cat in cats:
            categories[cat] += 1
    
    if categories:
        cat_df = pd.DataFrame([
            {'カテゴリ': cat, '件数': count}
            for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True)
        ])
        
        fig_categories = px.pie(
            cat_df,
            values='件数',
            names='カテゴリ',
            title=f"{target_name} の課題カテゴリ分布"
        )
        fig_categories.update_layout(height=400, font=dict(size=12))
        charts_data['categories_chart'] = fig_categories
    
    # 3. 時系列トレンドグラフ
    if len(target_df) > 1:
        trend_df = target_df.copy()
        trend_df['submission_date'] = pd.to_datetime(trend_df['submission_date'])
        trend_df['年月'] = trend_df['submission_date'].dt.to_period('M').astype(str)
        
        monthly_counts = trend_df.groupby('年月').size().reset_index(name='投稿数')
        
        if len(monthly_counts) > 1:
            fig_trend = px.line(
                monthly_counts,
                x='年月',
                y='投稿数',
                title=f"{target_name} の月次投稿推移",
                markers=True
            )
            fig_trend.update_layout(height=300, font=dict(size=12))
            charts_data['trend_chart'] = fig_trend
    
    # 4. 全体比較データ
    if target_type in ['event', 'municipality', 'prefecture']:
        target_rate = len(target_df) / len(df_all) * 100
        charts_data['target_stats'] = {
            'total_posts': len(target_df),
            'percentage': target_rate,
            'unique_reasons': len(set(all_reasons)) if all_reasons else 0
        }
    
    return charts_data

# 詳細レポート生成
def generate_detailed_report(target_type, target_name, analysis_data, target_df, df_all, charts_data):
    """詳細なレポートを生成"""
    client = get_openai_client()
    
    if not client:
        return "AIレポート生成が利用できません。OpenAI APIキーを確認してください。"
    
    # グラフ分析テキスト生成
    chart_analysis = "## 📊 データ分析結果\n\n"
    
    if 'top_reason' in charts_data:
        chart_analysis += f"**主要な課題**: {charts_data['top_reason']} ({charts_data['top_reason_count']}件)\n\n"
    
    if 'target_stats' in charts_data:
        stats = charts_data['target_stats']
        chart_analysis += f"**投稿状況**: 総{stats['total_posts']}件（全体の{stats['percentage']:.1f}%）\n"
        chart_analysis += f"**課題の多様性**: {stats['unique_reasons']}種類の異なる課題\n\n"
    
    # サンプル投稿
    samples = target_df.sample(min(3, len(target_df))) if len(target_df) > 0 else pd.DataFrame()
    sample_text = "## 💬 代表的な声\n\n"
    for i, (_, row) in enumerate(samples.iterrows(), 1):
        sample_text += f"**【事例{i}】**\n"
        sample_text += f"- イベント: {row['event_name']}\n"
        sample_text += f"- 課題: {row['reasons'].replace('|', ', ')}\n"
        if row.get('comment') and str(row['comment']).strip():
            sample_text += f"- 詳細: {str(row['comment'])[:100]}{'...' if len(str(row['comment'])) > 100 else ''}\n"
        sample_text += "\n"
    
    # ステークホルダー別プロンプト
    stakeholder_prompts = {
        "event": {
            "title": "イベント主催者向け改善提案レポート",
            "system": "あなたはイベント企画の専門コンサルタントです。データに基づいて具体的な改善策を提案してください。",
            "prompt": f"""
# {target_name} 参加障壁分析レポート

{chart_analysis}

{sample_text}

## 📋 改善提案の依頼

上記のデータ分析結果を基に、イベント主催者向けの具体的な改善策を以下の形式で提案してください：

1. **エグゼクティブサマリー** (100文字程度)
2. **主要課題の分析** (200文字程度)
3. **具体的改善策** (3つの提案、各150文字程度)
4. **実装スケジュール案** (100文字程度)
5. **期待される効果** (100文字程度)

実装の容易さと効果の高さを重視し、予算規模も考慮した現実的な提案をお願いします。
"""
        },
        "municipality": {
            "title": "自治体向け制度改善提案レポート",
            "system": "あなたは公共政策の専門家です。データに基づいて制度改善策を提案してください。",
            "prompt": f"""
# {target_name} 地域社会課題分析レポート

{chart_analysis}

{sample_text}

## 📋 制度改善提案の依頼

上記のデータ分析結果を基に、自治体向けの制度改善策を以下の形式で提案してください：

1. **政策提言サマリー** (100文字程度)
2. **地域課題の分析** (200文字程度)
3. **具体的制度改善策** (3つの提案、各150文字程度)
4. **予算規模の想定** (100文字程度)
5. **期待される社会的効果** (100文字程度)

自治体の予算と実現可能性を考慮し、住民サービス向上に繋がる提案をお願いします。
"""
        },
        "prefecture": {
            "title": "企業・団体向け社会貢献提案レポート", 
            "system": "あなたは企業のCSR・社会貢献の専門コンサルタントです。データに基づいて社会貢献策を提案してください。",
            "prompt": f"""
# {target_name} 社会課題解決機会分析レポート

{chart_analysis}

{sample_text}

## 📋 社会貢献施策提案の依頼

上記のデータ分析結果を基に、企業・団体向けの社会貢献策を以下の形式で提案してください：

1. **CSR提案サマリー** (100文字程度)
2. **社会課題の分析** (200文字程度)  
3. **具体的社会貢献策** (3つの提案、各150文字程度)
4. **投資対効果の想定** (100文字程度)
5. **企業価値向上の効果** (100文字程度)

企業のブランド価値向上と従業員満足度向上を考慮した提案をお願いします。
"""
        }
    }
    
    if target_type not in stakeholder_prompts:
        return "不明な対象タイプです。"
    
    config = stakeholder_prompts[target_type]
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # コスト効率重視
            messages=[
                {"role": "system", "content": config["system"]},
                {"role": "user", "content": config["prompt"]}
            ],
            temperature=0.7,
            max_tokens=1500
        )
        
        # レポートのヘッダーと結合
        full_report = f"""# {config['title']}
## 対象: {target_name}
### 生成日時: {datetime.now().strftime('%Y年%m月%d日 %H:%M')}

---

{response.choices[0].message.content}

---

## 📊 補足データ
- 分析対象投稿数: {len(target_df)}件
- 分析期間: {target_df['submission_date'].min()} ～ {target_df['submission_date'].max()}
- データソース: 行きたかったマップ プラットフォーム
"""
        
        return full_report
        
    except Exception as e:
        return f"レポート生成エラー: {e}"

def main():
    # 認証確認
    if not check_password():
        return
    
    # ヘッダー
    st.markdown('''
    <div class="main-header">
        <h1>🗺️ 行きたかったマップ 社会課題ダッシュボード</h1>
        <p>どこにアプローチすべきかを見つける - アクション指向ダッシュボード</p>
    </div>
    ''', unsafe_allow_html=True)
    
    # データ読み込み
    logic.migrate_csv_if_needed()
    df_all = logic.load_data()
    
    # 期間設定
    st.sidebar.header("📅 分析期間設定")
    months_back = st.sidebar.slider("過去何ヶ月分を分析？", 1, 12, 2)
    
    # 期間でフィルタリング
    df = filter_by_period(df_all, months_back)
    
    # 基本統計
    stats = calculate_basic_stats(df)
    
    # サイドバーに基本統計表示
    st.sidebar.markdown("### 📊 基本統計")
    st.sidebar.metric("総投稿数", f"{stats['total_posts']}件")
    st.sidebar.metric("対象イベント数", f"{stats['unique_events']}件")
    st.sidebar.metric("影響都道府県", f"{stats['affected_prefectures']}都道府県")
    st.sidebar.metric("影響市区町村", f"{stats['affected_municipalities']}市区町村")
    st.sidebar.metric("前月比", f"{stats['growth_rate']:+.1f}%")
    
    if df.empty:
        st.warning(f"過去{months_back}ヶ月間のデータがありません。期間を長くするか、データの投稿をお待ちください。")
        return
    
    # メインコンテンツ
    st.header(f"📋 アプローチ先分析（過去{months_back}ヶ月間）")
    
    # ステークホルダー別のタブ
    tab1, tab2, tab3, tab4 = st.tabs([
        "🎪 イベント主催者", "🏛️ 自治体", "🏢 都道府県・企業", "📺 メディア"
    ])
    
    # イベント主催者タブ
    with tab1:
        st.subheader("🎯 アプローチすべきイベント主催者")
        
        min_posts_event = st.selectbox("最小投稿数", [3, 5, 8, 10], index=1, key="event_min")
        event_analysis = analyze_for_event_organizers(df, min_posts_event)
        
        if not event_analysis:
            st.info(f"過去{months_back}ヶ月間で{min_posts_event}件以上の投稿があるイベントはありません。")
        else:
            # レポート生成状態を管理
            if 'show_event_report' not in st.session_state:
                st.session_state.show_event_report = False
            if 'current_event_report' not in st.session_state:
                st.session_state.current_event_report = {}
            
            for i, event in enumerate(event_analysis[:10]):  # 上位10件表示
                priority_class = f"priority-{event['priority'].lower()}" if event['priority'] in ['高', '中', '低'] else "priority-low"
                
                with st.container():
                    st.markdown(f'''
                    <div class="action-card {priority_class}">
                        <h4>🎪 {event['event_name']}</h4>
                        <p><strong>投稿数:</strong> {event['post_count']}件 | <strong>優先度:</strong> {event['priority']} | <strong>主な開催地:</strong> {event['main_location']}</p>
                        <p><strong>主な課題:</strong> {event['top_reason']}</p>
                        <p><strong>問題の多様性:</strong> {event['reason_diversity']}種類の課題</p>
                    </div>
                    ''', unsafe_allow_html=True)
                
                col1, col2 = st.columns([3, 1])
                with col2:
                    if st.button(f"📋 詳細レポート生成", key=f"event_{i}"):
                        with st.spinner("詳細レポート生成中..."):
                            # 対象データの抽出
                            target_df = df[df['event_name'] == event['event_name']]
                            
                            # グラフ生成
                            charts_data = create_detailed_charts(target_df, df, event['event_name'], "event")
                            
                            # 詳細レポート生成
                            detailed_report = generate_detailed_report("event", event['event_name'], event, target_df, df, charts_data)
                            
                            # セッションに保存
                            st.session_state.current_event_report = {
                                'event_name': event['event_name'],
                                'target_df': target_df,
                                'charts_data': charts_data,
                                'detailed_report': detailed_report
                            }
                            st.session_state.show_event_report = True
            
            # レポート表示（画面全体を使用）
            if st.session_state.show_event_report and st.session_state.current_event_report:
                st.markdown("---")
                report_data = st.session_state.current_event_report
                
                # レポート表示（大きなエリア）
                st.subheader(f"📄 {report_data['event_name']} 詳細分析レポート")
                
                # 閉じるボタン
                col_close1, col_close2 = st.columns([6, 1])
                with col_close2:
                    if st.button("❌ レポートを閉じる", key="close_event_report"):
                        st.session_state.show_event_report = False
                        st.rerun()
                
                # グラフ表示
                if 'reasons_chart' in report_data['charts_data']:
                    st.plotly_chart(report_data['charts_data']['reasons_chart'], use_container_width=True)
                
                col_chart1, col_chart2 = st.columns(2)
                with col_chart1:
                    if 'categories_chart' in report_data['charts_data']:
                        st.plotly_chart(report_data['charts_data']['categories_chart'], use_container_width=True)
                with col_chart2:
                    if 'trend_chart' in report_data['charts_data']:
                        st.plotly_chart(report_data['charts_data']['trend_chart'], use_container_width=True)
                
                # レポート本文表示（大きなエリア）
                st.markdown(report_data['detailed_report'])
                
                # ダウンロード機能
                col_dl1, col_dl2, col_dl3 = st.columns(3)
                with col_dl1:
                    st.download_button(
                        "📥 Markdownダウンロード",
                        report_data['detailed_report'],
                        file_name=f"イベント分析_{report_data['event_name']}_{datetime.now().strftime('%Y%m%d')}.md",
                        mime="text/markdown"
                    )
                with col_dl2:
                    # メール用テンプレート
                    email_template = f"""
件名: 【{report_data['event_name']}】参加障壁改善のご提案

{report_data['event_name']} 運営事務局 様

お疲れ様です。

「行きたかったマップ」プラットフォームにて、{report_data['event_name']}に関する参加者の声を分析いたしました。

添付の分析レポートをご確認いただき、今後のイベント運営改善の参考にしていただければと思います。

主な発見事項:
- 投稿数: {len(report_data['target_df'])}件
- 主要課題: {report_data['charts_data'].get('top_reason', '複数の課題')}
- 課題の多様性: {report_data['charts_data'].get('target_stats', {}).get('unique_reasons', 0)}種類

詳細は添付レポートをご覧ください。

何かご質問がございましたら、お気軽にお声かけください。

よろしくお願いいたします。
                    """
                    st.download_button(
                        "📧 メール用テンプレート",
                        email_template,
                        file_name=f"メール_{report_data['event_name']}_{datetime.now().strftime('%Y%m%d')}.txt",
                        mime="text/plain"
                    )
                with col_dl3:
                    # HTMLレポート
                    html_report = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{report_data['event_name']} 分析レポート</title>
    <style>
        body {{ font-family: 'Helvetica', 'Arial', sans-serif; margin: 40px; line-height: 1.6; }}
        h1 {{ color: #333; border-bottom: 2px solid #667eea; }}
        h2 {{ color: #667eea; }}
        .highlight {{ background-color: #f0f8ff; padding: 10px; border-left: 4px solid #667eea; }}
    </style>
</head>
<body>
{report_data['detailed_report'].replace('#', '').replace('**', '<strong>').replace('**', '</strong>')}
</body>
</html>
                    """
                    st.download_button(
                        "🌐 HTMLレポート",
                        html_report,
                        file_name=f"レポート_{report_data['event_name']}_{datetime.now().strftime('%Y%m%d')}.html",
                        mime="text/html"
                    )
    
    # 自治体タブ
    with tab2:
        st.subheader("🎯 アプローチすべき自治体")
        
        min_posts_gov = st.selectbox("最小投稿数", [2, 3, 5, 8], index=1, key="gov_min")
        gov_analysis = analyze_for_government(df, min_posts_gov)
        
        if not gov_analysis:
            st.info(f"過去{months_back}ヶ月間で{min_posts_gov}件以上の投稿がある市区町村はありません。")
        else:
            # レポート生成状態を管理
            if 'show_gov_report' not in st.session_state:
                st.session_state.show_gov_report = False
            if 'current_gov_report' not in st.session_state:
                st.session_state.current_gov_report = {}
                
            for i, muni in enumerate(gov_analysis[:10]):
                priority_class = f"priority-{muni['priority'].lower()}" if muni['priority'] in ['高', '中', '低'] else "priority-low"
                
                with st.container():
                    st.markdown(f'''
                    <div class="action-card {priority_class}">
                        <h4>🏛️ {muni['municipality']}（{muni['prefecture']}）</h4>
                        <p><strong>投稿数:</strong> {muni['post_count']}件 | <strong>優先度:</strong> {muni['priority']} | <strong>対象イベント:</strong> {muni['event_count']}件</p>
                        <p><strong>主な課題カテゴリ:</strong> {muni['top_category']}</p>
                        <p><strong>具体的な課題:</strong> {muni['top_reason']}</p>
                    </div>
                    ''', unsafe_allow_html=True)
                
                col1, col2 = st.columns([3, 1])
                with col2:
                    if st.button(f"📋 詳細レポート生成", key=f"gov_{i}"):
                        with st.spinner("詳細レポート生成中..."):
                            # 対象データの抽出
                            target_df = df[df['event_municipality'] == muni['municipality']]
                            
                            # グラフ生成
                            charts_data = create_detailed_charts(target_df, df, muni['municipality'], "municipality")
                            
                            # 詳細レポート生成
                            detailed_report = generate_detailed_report("municipality", muni['municipality'], muni, target_df, df, charts_data)
                            
                            # セッションに保存
                            st.session_state.current_gov_report = {
                                'municipality': muni['municipality'],
                                'prefecture': muni['prefecture'],
                                'target_df': target_df,
                                'charts_data': charts_data,
                                'detailed_report': detailed_report
                            }
                            st.session_state.show_gov_report = True
            
            # レポート表示（画面全体を使用）
            if st.session_state.show_gov_report and st.session_state.current_gov_report:
                st.markdown("---")
                report_data = st.session_state.current_gov_report
                
                # レポート表示（大きなエリア）
                st.subheader(f"📄 {report_data['municipality']}（{report_data['prefecture']}）社会課題分析レポート")
                
                # 閉じるボタン
                col_close1, col_close2 = st.columns([6, 1])
                with col_close2:
                    if st.button("❌ レポートを閉じる", key="close_gov_report"):
                        st.session_state.show_gov_report = False
                        st.rerun()
                
                # グラフ表示
                if 'reasons_chart' in report_data['charts_data']:
                    st.plotly_chart(report_data['charts_data']['reasons_chart'], use_container_width=True)
                
                col_chart1, col_chart2 = st.columns(2)
                with col_chart1:
                    if 'categories_chart' in report_data['charts_data']:
                        st.plotly_chart(report_data['charts_data']['categories_chart'], use_container_width=True)
                with col_chart2:
                    if 'trend_chart' in report_data['charts_data']:
                        st.plotly_chart(report_data['charts_data']['trend_chart'], use_container_width=True)
                
                # レポート本文表示
                st.markdown(report_data['detailed_report'])
                
                # ダウンロード機能
                col_dl1, col_dl2, col_dl3 = st.columns(3)
                with col_dl1:
                    st.download_button(
                        "📥 Markdownダウンロード",
                        report_data['detailed_report'],
                        file_name=f"自治体分析_{report_data['municipality']}_{datetime.now().strftime('%Y%m%d')}.md",
                        mime="text/markdown"
                    )
                with col_dl2:
                    # メール用テンプレート
                    email_template = f"""
件名: 【{report_data['municipality']}】地域社会課題解決のご提案

{report_data['municipality']} 担当部署 様

お疲れ様です。

「行きたかったマップ」プラットフォームにて、{report_data['municipality']}地域の社会参加に関する課題を分析いたしました。

添付の分析レポートをご確認いただき、今後の住民サービス向上の参考にしていただければと思います。

主な発見事項:
- 投稿数: {len(report_data['target_df'])}件
- 主要課題: {report_data['charts_data'].get('top_reason', '複数の課題')}

詳細は添付レポートをご覧ください。

何かご質問がございましたら、お気軽にお声かけください。

よろしくお願いいたします。
                    """
                    st.download_button(
                        "📧 メール用テンプレート",
                        email_template,
                        file_name=f"メール_{report_data['municipality']}_{datetime.now().strftime('%Y%m%d')}.txt",
                        mime="text/plain"
                    )
                with col_dl3:
                    # HTMLレポート
                    html_report = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{report_data['municipality']} 社会課題分析レポート</title>
    <style>
        body {{ font-family: 'Helvetica', 'Arial', sans-serif; margin: 40px; line-height: 1.6; }}
        h1 {{ color: #333; border-bottom: 2px solid #667eea; }}
        h2 {{ color: #667eea; }}
        .highlight {{ background-color: #f0f8ff; padding: 10px; border-left: 4px solid #667eea; }}
    </style>
</head>
<body>
{report_data['detailed_report'].replace('#', '').replace('**', '<strong>').replace('**', '</strong>')}
</body>
</html>
                    """
                    st.download_button(
                        "🌐 HTMLレポート",
                        html_report,
                        file_name=f"レポート_{report_data['municipality']}_{datetime.now().strftime('%Y%m%d')}.html",
                        mime="text/html"
                    )
    
    # 都道府県・企業タブ
    with tab3:
        st.subheader("🎯 アプローチすべき都道府県・企業")
        
        min_posts_corp = st.selectbox("最小投稿数", [5, 8, 10, 15], index=1, key="corp_min")
        corp_analysis = analyze_for_corporate(df, min_posts_corp)
        
        if not corp_analysis:
            st.info(f"過去{months_back}ヶ月間で{min_posts_corp}件以上の投稿がある都道府県はありません。")
        else:
            # レポート生成状態を管理
            if 'show_corp_report' not in st.session_state:
                st.session_state.show_corp_report = False
            if 'current_corp_report' not in st.session_state:
                st.session_state.current_corp_report = {}
                
            for i, pref in enumerate(corp_analysis[:10]):
                priority_class = f"priority-{pref['priority'].lower()}" if pref['priority'] in ['高', '中', '低'] else "priority-low"
                
                with st.container():
                    st.markdown(f'''
                    <div class="action-card {priority_class}">
                        <h4>🏢 {pref['prefecture']}</h4>
                        <p><strong>投稿数:</strong> {pref['post_count']}件 | <strong>優先度:</strong> {pref['priority']}</p>
                        <p><strong>対象イベント:</strong> {pref['event_count']}件 | <strong>関連市区町村:</strong> {pref['municipality_count']}箇所</p>
                        <p><strong>主な課題カテゴリ:</strong> {pref['top_category']}</p>
                        <p><strong>具体的な課題:</strong> {pref['top_reason']}</p>
                    </div>
                    ''', unsafe_allow_html=True)
                
                col1, col2 = st.columns([3, 1])
                with col2:
                    if st.button(f"📋 詳細レポート生成", key=f"corp_{i}"):
                        with st.spinner("詳細レポート生成中..."):
                            # 対象データの抽出
                            target_df = df[df['event_prefecture'] == pref['prefecture']]
                            
                            # グラフ生成
                            charts_data = create_detailed_charts(target_df, df, pref['prefecture'], "prefecture")
                            
                            # 詳細レポート生成
                            detailed_report = generate_detailed_report("prefecture", pref['prefecture'], pref, target_df, df, charts_data)
                            
                            # セッションに保存
                            st.session_state.current_corp_report = {
                                'prefecture': pref['prefecture'],
                                'target_df': target_df,
                                'charts_data': charts_data,
                                'detailed_report': detailed_report,
                                'event_count': pref['event_count'],
                                'municipality_count': pref['municipality_count']
                            }
                            st.session_state.show_corp_report = True
            
            # レポート表示（画面全体を使用）
            if st.session_state.show_corp_report and st.session_state.current_corp_report:
                st.markdown("---")
                report_data = st.session_state.current_corp_report
                
                # レポート表示（大きなエリア）
                st.subheader(f"📄 {report_data['prefecture']} 社会貢献機会分析レポート")
                
                # 閉じるボタン
                col_close1, col_close2 = st.columns([6, 1])
                with col_close2:
                    if st.button("❌ レポートを閉じる", key="close_corp_report"):
                        st.session_state.show_corp_report = False
                        st.rerun()
                
                # グラフ表示
                if 'reasons_chart' in report_data['charts_data']:
                    st.plotly_chart(report_data['charts_data']['reasons_chart'], use_container_width=True)
                
                col_chart1, col_chart2 = st.columns(2)
                with col_chart1:
                    if 'categories_chart' in report_data['charts_data']:
                        st.plotly_chart(report_data['charts_data']['categories_chart'], use_container_width=True)
                with col_chart2:
                    if 'trend_chart' in report_data['charts_data']:
                        st.plotly_chart(report_data['charts_data']['trend_chart'], use_container_width=True)
                
                # レポート本文表示
                st.markdown(report_data['detailed_report'])
                
                # ダウンロード機能
                col_dl1, col_dl2, col_dl3 = st.columns(3)
                with col_dl1:
                    st.download_button(
                        "📥 Markdownダウンロード",
                        report_data['detailed_report'],
                        file_name=f"企業分析_{report_data['prefecture']}_{datetime.now().strftime('%Y%m%d')}.md",
                        mime="text/markdown"
                    )
                with col_dl2:
                    # メール用テンプレート
                    email_template = f"""
件名: 【{report_data['prefecture']}】社会貢献・CSR機会のご提案

{report_data['prefecture']} 関連企業・団体 様

お疲れ様です。

「行きたかったマップ」プラットフォームにて、{report_data['prefecture']}地域の社会課題解決機会を分析いたしました。

添付の分析レポートをご確認いただき、今後の社会貢献活動・CSR施策の参考にしていただければと思います。

主な発見事項:
- 投稿数: {len(report_data['target_df'])}件
- 主要課題: {report_data['charts_data'].get('top_reason', '複数の課題')}
- 対象イベント: {report_data['event_count']}件
- 関連市区町村: {report_data['municipality_count']}箇所

詳細は添付レポートをご覧ください。

何かご質問がございましたら、お気軽にお声かけください。

よろしくお願いいたします。
                    """
                    st.download_button(
                        "📧 メール用テンプレート",
                        email_template,
                        file_name=f"メール_{report_data['prefecture']}_{datetime.now().strftime('%Y%m%d')}.txt",
                        mime="text/plain"
                    )
                with col_dl3:
                    # HTMLレポート
                    html_report = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{report_data['prefecture']} 社会貢献機会分析レポート</title>
    <style>
        body {{ font-family: 'Helvetica', 'Arial', sans-serif; margin: 40px; line-height: 1.6; }}
        h1 {{ color: #333; border-bottom: 2px solid #667eea; }}
        h2 {{ color: #667eea; }}
        .highlight {{ background-color: #f0f8ff; padding: 10px; border-left: 4px solid #667eea; }}
    </style>
</head>
<body>
{report_data['detailed_report'].replace('#', '').replace('**', '<strong>').replace('**', '</strong>')}
</body>
</html>
                    """
                    st.download_button(
                        "🌐 HTMLレポート",
                        html_report,
                        file_name=f"レポート_{report_data['prefecture']}_{datetime.now().strftime('%Y%m%d')}.html",
                        mime="text/html"
                    )
    
    # メディアタブ
    with tab4:
        st.subheader("🎯 メディアに提案すべき社会課題")
        
        media_analysis = analyze_for_media(df)
        
        if not media_analysis:
            st.info("現在、特に報道価値の高い課題は検出されていません。")
        else:
            for i, story in enumerate(media_analysis[:8]):
                if story['news_value'] == '高':
                    priority_class = "priority-high"
                    icon = "🔥"
                elif story['news_value'] == '中':
                    priority_class = "priority-medium"
                    icon = "⚠️"
                else:
                    priority_class = "priority-low"
                    icon = "📰"
                
                with st.container():
                    st.markdown(f'''
                    <div class="action-card {priority_class}">
                        <h4>{icon} {story['category']}の課題</h4>
                        <p><strong>ニュース価値:</strong> {story['news_value']} | <strong>ストーリー角度:</strong> {story['story_angle']}</p>
                        <p><strong>総投稿数:</strong> {story['total_count']}件 | <strong>直近30日:</strong> {story['recent_count']}件</p>
                        <p><strong>地域への広がり:</strong> {story['prefecture_spread']}都道府県</p>
                    </div>
                    ''', unsafe_allow_html=True)
    
    # 全体サマリー
    st.markdown("---")
    st.subheader("📊 全体サマリー")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        event_count = len(analyze_for_event_organizers(df, 5))
        st.markdown(f'''
        <div class="metric-box">
            <h3>{event_count}</h3>
            <p>アプローチ対象<br>イベント数</p>
        </div>
        ''', unsafe_allow_html=True)
    
    with col2:
        gov_count = len(analyze_for_government(df, 3))
        st.markdown(f'''
        <div class="metric-box">
            <h3>{gov_count}</h3>
            <p>アプローチ対象<br>自治体数</p>
        </div>
        ''', unsafe_allow_html=True)
    
    with col3:
        corp_count = len(analyze_for_corporate(df, 8))
        st.markdown(f'''
        <div class="metric-box">
            <h3>{corp_count}</h3>
            <p>アプローチ対象<br>都道府県数</p>
        </div>
        ''', unsafe_allow_html=True)
    
    with col4:
        media_count = len([s for s in analyze_for_media(df) if s['news_value'] in ['高', '中']])
        st.markdown(f'''
        <div class="metric-box">
            <h3>{media_count}</h3>
            <p>報道価値のある<br>課題数</p>
        </div>
        ''', unsafe_allow_html=True)

if __name__ == "__main__":
    main()