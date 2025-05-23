import streamlit as st
import pandas as pd
import numpy as np
import pydeck as pdk
import altair as alt
import plotly.express as px
import plotly.graph_objects as go
import json
import os
import uuid
from datetime import datetime, timedelta
import openai
import time
import re
from collections import defaultdict

# 自作ロジックモジュールをインポート
import logic

# ページ設定
st.set_page_config(
    page_title="#行きたかったマップ 管理ダッシュボード", 
    page_icon="🗺️", 
    layout="wide"
)

# カスタムCSS
st.markdown("""
<style>
.main-header {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    padding: 25px;
    border-radius: 15px;
    color: white;
    text-align: center;
    margin-bottom: 30px;
    box-shadow: 0 4px 15px rgba(0,0,0,0.2);
}

.alert-high {
    background: linear-gradient(90deg, #ff6b6b, #ffa726);
    color: white;
    padding: 15px;
    border-radius: 8px;
    margin: 10px 0;
    font-weight: bold;
}

.info-box {
    background: linear-gradient(90deg, #3498db, #2980b9);
    color: white;
    padding: 15px;
    border-radius: 8px;
    margin: 10px 0;
}

.stakeholder-card {
    background: #f8f9fa;
    border: 1px solid #dee2e6;
    border-radius: 10px;
    padding: 20px;
    margin: 10px 0;
    box-shadow: 0 2px 4px rgba(0,0,0,0.05);
}

.urgent-post {
    background: #fff3cd;
    border-left: 4px solid #ffc107;
    padding: 15px;
    margin: 10px 0;
    border-radius: 5px;
}

.threshold-info {
    background: #e3f2fd;
    padding: 10px;
    border-radius: 5px;
    margin: 10px 0;
    font-size: 0.9em;
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
        <h1>🗺️ 行きたかったマップ 管理ダッシュボード</h1>
        <p>社会変革のためのデータ分析・戦略プラットフォーム</p>
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

# AI設定の管理
def get_ai_settings():
    """AI設定を取得"""
    if 'ai_settings' not in st.session_state:
        st.session_state.ai_settings = {
            'model': 'gpt-4o-mini',
            'temperature': 0.7,
            'max_tokens': 1500,
            'report_tone': 'professional',
            'report_length': 'medium'
        }
    return st.session_state.ai_settings

def update_ai_settings(new_settings):
    """AI設定を更新"""
    st.session_state.ai_settings.update(new_settings)

# ダッシュボード用メトリクス計算
def calculate_dashboard_metrics(df):
    """ダッシュボード用の主要メトリクスを計算"""
    if df.empty:
        return {
            'total_posts': 0,
            'unique_events': 0,
            'unique_prefectures': 0,
            'recent_posts': 0,
            'top_reason': 'データなし',
            'growth_rate': 0,
            'urgency_score': 0,
            'social_impact_score': 0
        }
    
    total_posts = len(df)
    unique_events = df['event_name'].nunique()
    unique_prefectures = df['event_prefecture'].nunique()
    
    # 過去7日間の投稿数
    df_temp = df.copy()
    df_temp['submission_date'] = pd.to_datetime(df_temp['submission_date'])
    recent_cutoff = datetime.now() - timedelta(days=7)
    recent_posts = len(df_temp[df_temp['submission_date'] > recent_cutoff])
    
    # 成長率（過去30日 vs その前30日）
    last_30_days = datetime.now() - timedelta(days=30)
    prev_30_days = datetime.now() - timedelta(days=60)
    
    current_period = len(df_temp[df_temp['submission_date'] > last_30_days])
    previous_period = len(df_temp[(df_temp['submission_date'] > prev_30_days) & (df_temp['submission_date'] <= last_30_days)])
    
    growth_rate = ((current_period - previous_period) / max(previous_period, 1)) * 100 if previous_period > 0 else 0
    
    # 最多の理由
    reasons_count = defaultdict(int)
    for reasons_str in df['reasons'].dropna():
        for reason in str(reasons_str).split('|'):
            reasons_count[reason.strip()] += 1
    
    top_reason = max(reasons_count.items(), key=lambda x: x[1])[0] if reasons_count else 'データなし'
    
    # 緊急度スコア（構造的問題の深刻度）
    structural_keywords = ['子育て', '介護', '病気', '経済的', '会社で許可']
    urgent_count = 0
    for reasons_str in df['reasons'].dropna():
        if any(keyword in str(reasons_str) for keyword in structural_keywords):
            urgent_count += 1
    
    urgency_score = (urgent_count / total_posts) * 100 if total_posts > 0 else 0
    
    # 社会インパクトスコア（影響の広がり）
    social_impact_score = min(100, (unique_prefectures * 2) + (total_posts * 0.5) + (unique_events * 1.5))
    
    return {
        'total_posts': total_posts,
        'unique_events': unique_events,
        'unique_prefectures': unique_prefectures,
        'recent_posts': recent_posts,
        'top_reason': top_reason,
        'growth_rate': growth_rate,
        'urgency_score': urgency_score,
        'social_impact_score': social_impact_score
    }

# 緊急対応が必要な投稿の抽出
def get_urgent_posts(df):
    """緊急対応が必要な投稿を抽出"""
    
    # 緊急性の基準
    structural_keywords = ['子育て', '介護', '病気', '体調不良', '経済的理由']
    urgent_comment_keywords = ['困っ', '辛い', '厳しい', '無理', '限界', '苦しい']
    
    # 過去1ヶ月の投稿に限定
    df_temp = df.copy()
    df_temp['submission_date'] = pd.to_datetime(df_temp['submission_date'])
    one_month_ago = datetime.now() - timedelta(days=30)
    recent_df = df_temp[df_temp['submission_date'] > one_month_ago]
    
    urgent_posts = []
    
    for _, row in recent_df.iterrows():
        urgency_score = 0
        urgency_reasons = []
        
        # 理由による緊急性判定
        reasons = str(row['reasons']).lower()
        for keyword in structural_keywords:
            if keyword in reasons:
                urgency_score += 2
                urgency_reasons.append(f"構造的問題: {keyword}")
        
        # コメントによる緊急性判定
        comment = str(row.get('comment', '')).lower()
        for keyword in urgent_comment_keywords:
            if keyword in comment:
                urgency_score += 1
                urgency_reasons.append(f"切実な表現: {keyword}")
        
        # 複数理由による緊急性判定
        if '|' in str(row['reasons']):
            reason_count = len(str(row['reasons']).split('|'))
            if reason_count >= 3:
                urgency_score += 1
                urgency_reasons.append(f"複合要因: {reason_count}個")
        
        # 緊急度3以上を緊急案件とする
        if urgency_score >= 3:
            urgent_posts.append({
                'post': row,
                'urgency_score': urgency_score,
                'urgency_reasons': urgency_reasons
            })
    
    # 緊急度順でソート
    urgent_posts.sort(key=lambda x: x['urgency_score'], reverse=True)
    
    return urgent_posts

# データフィルタリング関数
def filter_data_by_criteria(df, stakeholder_type, target_selection, min_posts=10, months_back=2):
    """しきい値に基づいてデータをフィルタリング"""
    
    # 期間でフィルタリング
    df_temp = df.copy()
    df_temp['submission_date'] = pd.to_datetime(df_temp['submission_date'])
    cutoff_date = datetime.now() - timedelta(days=months_back * 30)
    filtered_df = df_temp[df_temp['submission_date'] > cutoff_date]
    
    # ステークホルダータイプによる対象フィルタリング
    if stakeholder_type == "event_organizer":
        # イベント別
        if target_selection != "全体":
            filtered_df = filtered_df[filtered_df['event_name'] == target_selection]
    
    elif stakeholder_type == "government":
        # 自治体別（event_municipality）
        if target_selection != "全体":
            filtered_df = filtered_df[filtered_df['event_municipality'] == target_selection]
    
    elif stakeholder_type in ["corporate", "media"]:
        # 都道府県別（event_prefecture）
        if target_selection != "全体":
            filtered_df = filtered_df[filtered_df['event_prefecture'] == target_selection]
    
    # 最小投稿数のチェック
    data_sufficient = len(filtered_df) >= min_posts
    
    return filtered_df, data_sufficient

def get_target_options(df, stakeholder_type, min_posts=1, months_back=2):
    """ステークホルダータイプに応じた対象選択肢を取得（期間フィルタリング含む）"""
    
    # 期間でフィルタリング
    df_temp = df.copy()
    df_temp['submission_date'] = pd.to_datetime(df_temp['submission_date'])
    cutoff_date = datetime.now() - timedelta(days=months_back * 30)
    df_filtered = df_temp[df_temp['submission_date'] > cutoff_date]
    
    if stakeholder_type == "event_organizer":
        # イベント名の選択肢（期間内の投稿数で判定）
        events = df_filtered['event_name'].value_counts()
        return ["全体"] + [event for event, count in events.items() if count >= min_posts]
    
    elif stakeholder_type == "government":
        # 市区町村の選択肢（期間内の投稿数で判定）
        municipalities = df_filtered['event_municipality'].dropna().value_counts()
        return ["全体"] + [muni for muni, count in municipalities.items() if muni and muni != "" and count >= min_posts]
    
    elif stakeholder_type in ["corporate", "media"]:
        # 都道府県の選択肢（期間内の投稿数で判定）
        prefectures = df_filtered['event_prefecture'].value_counts()
        return ["全体"] + [pref for pref, count in prefectures.items() if count >= min_posts]
    
    return ["全体"]

# グラフ生成関数群
def create_target_charts(filtered_df, df_all, target_description):
    """対象データのグラフを生成し、分析結果を返す"""
    
    charts_data = {}
    
    # 1. 参加障壁の分布グラフ
    reasons_count = defaultdict(int)
    for reasons_str in filtered_df['reasons'].dropna():
        for reason in str(reasons_str).split('|'):
            reasons_count[reason.strip()] += 1
    
    reasons_df = pd.DataFrame([
        {'理由': reason, '件数': count} 
        for reason, count in sorted(reasons_count.items(), key=lambda x: x[1], reverse=True)
    ])
    
    if not reasons_df.empty:
        fig_reasons = px.bar(
            reasons_df.head(8),
            x='件数',
            y='理由',
            orientation='h',
            title=f"{target_description} の参加障壁分布",
            color_discrete_sequence=['#667eea']
        )
        fig_reasons.update_layout(height=400)
        charts_data['reasons_chart'] = fig_reasons
        charts_data['top_reason'] = reasons_df.iloc[0]['理由']
        charts_data['top_reason_count'] = reasons_df.iloc[0]['件数']
        charts_data['top_reason_pct'] = (reasons_df.iloc[0]['件数'] / len(filtered_df)) * 100
    
    # 2. 全体との比較グラフ
    all_reasons_count = defaultdict(int)
    for reasons_str in df_all['reasons'].dropna():
        for reason in str(reasons_str).split('|'):
            all_reasons_count[reason.strip()] += 1
    
    comparison_data = []
    for reason, count in list(reasons_count.items())[:5]:
        target_rate = (count / len(filtered_df)) * 100
        all_rate = (all_reasons_count.get(reason, 0) / len(df_all)) * 100
        
        comparison_data.append({
            '理由': reason,
            '対象データ': target_rate,
            '全体データ': all_rate,
            '差分': target_rate - all_rate
        })
    
    if comparison_data:
        comparison_df = pd.DataFrame(comparison_data)
        
        fig_comparison = px.bar(
            comparison_df,
            x='理由',
            y=['対象データ', '全体データ'],
            title=f"{target_description} vs 全体比較",
            barmode='group'
        )
        fig_comparison.update_layout(height=300)
        charts_data['comparison_chart'] = fig_comparison
        charts_data['significant_differences'] = [
            row for _, row in comparison_df.iterrows() 
            if abs(row['差分']) > 10
        ]
    
    # 3. 時系列トレンドグラフ
    df_temp = filtered_df.copy()
    df_temp['submission_date'] = pd.to_datetime(df_temp['submission_date'])
    df_temp['年月'] = df_temp['submission_date'].dt.to_period('M')
    
    monthly_counts = df_temp.groupby('年月').size().reset_index(name='投稿数')
    monthly_counts['年月'] = monthly_counts['年月'].astype(str)
    
    if len(monthly_counts) > 1:
        fig_trend = px.line(
            monthly_counts,
            x='年月',
            y='投稿数',
            title=f"{target_description} の月次推移",
            markers=True
        )
        fig_trend.update_layout(height=250)
        charts_data['trend_chart'] = fig_trend
        
        # トレンド分析
        if len(monthly_counts) >= 2:
            recent_trend = monthly_counts.iloc[-1]['投稿数'] - monthly_counts.iloc[-2]['投稿数']
            charts_data['trend_direction'] = '増加' if recent_trend > 0 else '減少' if recent_trend < 0 else '横ばい'
            charts_data['trend_change'] = abs(recent_trend)
    
    # 4. 緊急度分析
    structural_keywords = ['子育て', '介護', '病気', '経済的', '会社で許可']
    urgent_count = 0
    for reasons_str in filtered_df['reasons'].dropna():
        if any(keyword in str(reasons_str) for keyword in structural_keywords):
            urgent_count += 1
    
    charts_data['urgency_stats'] = {
        'urgent_posts': urgent_count,
        'urgency_rate': (urgent_count / len(filtered_df)) * 100,
        'urgency_level': '高' if (urgent_count / len(filtered_df)) * 100 > 50 else '中' if (urgent_count / len(filtered_df)) * 100 > 30 else '低'
    }
    
    return charts_data

def generate_chart_analysis_text(charts_data, target_description):
    """グラフデータを基に分析テキストを生成"""
    
    analysis_text = f"## 📊 {target_description} データ分析結果\n\n"
    
    # 基本統計
    if 'top_reason' in charts_data:
        analysis_text += f"**主要な参加障壁**: {charts_data['top_reason']} ({charts_data['top_reason_count']}件, {charts_data['top_reason_pct']:.1f}%)\n\n"
    
    # 全体との比較
    if 'significant_differences' in charts_data and charts_data['significant_differences']:
        analysis_text += "**全体との主な相違点**:\n"
        for diff in charts_data['significant_differences']:
            symbol = "⬆️" if diff['差分'] > 0 else "⬇️"
            analysis_text += f"- {diff['理由']}: 対象{diff['対象データ']:.1f}% vs 全体{diff['全体データ']:.1f}% {symbol}\n"
        analysis_text += "\n"
    
    # トレンド分析
    if 'trend_direction' in charts_data:
        analysis_text += f"**最近の傾向**: {charts_data['trend_direction']}傾向（前月比{charts_data['trend_change']}件）\n\n"
    
    # 緊急度
    if 'urgency_stats' in charts_data:
        urgency = charts_data['urgency_stats']
        analysis_text += f"**緊急度**: {urgency['urgency_level']}レベル（構造的問題{urgency['urgent_posts']}件, {urgency['urgency_rate']:.1f}%）\n\n"
    
    return analysis_text

def generate_stakeholder_report_with_charts(filtered_df, df_all, stakeholder_type, target_selection, min_posts, months_back, chart_analysis_text):
    """グラフデータを含むステークホルダー別レポートを生成"""
    
    ai_settings = get_ai_settings()
    client = get_openai_client()
    
    if not client:
        return "AIレポート生成が利用できません。OpenAI APIキーを確認してください。"
    
    # 対象の説明
    target_description = ""
    if stakeholder_type == "event_organizer":
        target_description = f"イベント「{target_selection}」"
    elif stakeholder_type == "government":
        target_description = f"{target_selection}地域"
    elif stakeholder_type in ["corporate", "media"]:
        target_description = f"{target_selection}"
    
    # ステークホルダー別のプロンプト構築
    prompts = {
        "event_organizer": {
            "system": "あなたはイベント企画の専門コンサルタントです。提供されたグラフ分析結果を参照し、特定のイベントについての具体的な改善策を提案してください。",
            "focus": "参加者増加、実装の容易さ、コスト対効果",
            "output_format": "エグゼクティブサマリー、グラフ分析の解釈、具体的改善アクション、実装スケジュール、期待効果"
        },
        "government": {
            "system": "あなたは公共政策の専門家です。提供されたグラフ分析結果を基に、特定地域の住民が抱える社会参加の障壁について政策提言を行ってください。",
            "focus": "政策的対応の必要性、予算確保の根拠、実現可能性",
            "output_format": "政策提言書、グラフデータに基づく地域課題分析、具体的施策案、予算規模、期待される社会的インパクト"
        },
        "corporate": {
            "system": "あなたは企業のCSR・人事担当コンサルタントです。提供されたグラフ分析結果を踏まえ、地域の社会参加支援について企業価値向上に繋がる施策を提案してください。",
            "focus": "CSR価値、従業員満足度、ブランドイメージ向上",
            "output_format": "CSR提案書、グラフデータに基づくビジネス価値分析、従業員支援策、投資対効果、実施計画"
        },
        "media": {
            "system": "あなたは社会問題専門のジャーナリストです。提供されたグラフ分析結果を活用し、地域の社会参加の障壁について社会の注目を集める記事を作成してください。",
            "focus": "社会的インパクト、人間ドラマ、データの説得力",
            "output_format": "プレスリリース、グラフデータに基づく見出し案、統計による裏付け、取材提案、社会への訴求ポイント"
        }
    }
    
    if stakeholder_type not in prompts:
        return "無効なステークホルダータイプです。"
    
    prompt_config = prompts[stakeholder_type]
    
    # 投稿サンプル
    sample_posts = "\n## 💬 代表的な投稿例\n"
    samples = filtered_df.sample(min(3, len(filtered_df))) if len(filtered_df) > 0 else pd.DataFrame()
    
    for i, (_, row) in enumerate(samples.iterrows(), 1):
        sample_posts += f"\n**【投稿{i}】**\n"
        sample_posts += f"- イベント: {row['event_name']}\n"
        sample_posts += f"- 理由: {row['reasons'].replace('|', ', ')}\n"
        if row.get('comment') and row['comment'].strip():
            sample_posts += f"- 声: 「{row['comment'][:150]}{'...' if len(row['comment']) > 150 else ''}」\n"
        sample_posts += f"- 投稿日: {row['submission_date']}\n"
    
    # 最終プロンプト
    final_prompt = f"""
以下は{target_description}に関するデータ分析結果です。このグラフ分析結果を必ず参照し、データに基づいた提案を行ってください。

{chart_analysis_text}

{sample_posts}

**重要**: 上記のグラフ分析結果に含まれる具体的な数値（投稿数、割合、トレンド、比較データ等）を必ず引用し、それに基づいた{prompt_config['focus']}に重点を置いた{prompt_config['output_format']}を作成してください。

レポートの品質要件:
- トーン: {ai_settings['report_tone']}
- 長さ: {ai_settings['report_length']}
- グラフ分析結果の具体的な数値を必ず引用
- データに基づいた実用的で具体的な提案
- 実現可能性を考慮した内容
- グラフの傾向や比較結果を戦略的に活用した提案

特に以下の点を必ず含めてください:
1. グラフ分析結果の解釈と意味
2. 全体データとの比較による特徴の明確化
3. トレンド分析による緊急性の評価
4. データが示す具体的な改善機会の特定
"""
    
    try:
        response = client.chat.completions.create(
            model=ai_settings['model'],
            messages=[
                {"role": "system", "content": prompt_config['system']},
                {"role": "user", "content": final_prompt}
            ],
            temperature=ai_settings['temperature'],
            max_tokens=ai_settings['max_tokens']
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"レポート生成エラー: {e}"

# メイン関数
def main():
    # 認証確認
    if not check_password():
        return
    
    # ヘッダー
    st.markdown('''
    <div class="main-header">
        <h1>🗺️ 行きたかったマップ 管理ダッシュボード</h1>
        <p>個人の声を社会変革の力に変えるプラットフォーム</p>
    </div>
    ''', unsafe_allow_html=True)
    
    # データ初期化と読み込み
    logic.migrate_csv_if_needed()
    df = logic.load_data()
    
    # メトリクス計算
    metrics = calculate_dashboard_metrics(df)
    
    # タブ状態の初期化と管理
    if 'active_tab_index' not in st.session_state:
        st.session_state.active_tab_index = 0
    
    # サイドバーでクイックメトリクス表示
    with st.sidebar:
        st.header("📊 社会インパクト指標")
        
        # 緊急度による色分け
        if metrics['urgency_score'] > 50:
            urgency_color = "🔴"
        elif metrics['urgency_score'] > 30:
            urgency_color = "🟡"
        else:
            urgency_color = "🟢"
        
        st.metric("総投稿数", f"{metrics['total_posts']:,}", f"+{metrics['recent_posts']} (7日間)")
        st.metric("影響イベント数", f"{metrics['unique_events']:,}")
        st.metric("影響地域", f"{metrics['unique_prefectures']}都道府県")
        st.metric("社会インパクト", f"{metrics['social_impact_score']:.0f}/100")
        st.metric("構造的問題度", f"{urgency_color} {metrics['urgency_score']:.1f}%")
        
        # アラート表示
        if metrics['urgency_score'] > 40:
            st.markdown('<div class="alert-high">⚠️ 構造的な社会課題が顕在化しています</div>', unsafe_allow_html=True)
        
        if metrics['growth_rate'] > 50:
            st.markdown('<div class="info-box">📈 急速に問題が拡大しています</div>', unsafe_allow_html=True)
    
    # データがない場合のガイド
    if df.empty:
        st.markdown('<div class="info-box">📝 データ収集を開始しましょう。投稿が集まることで社会変革への道筋が見えてきます。</div>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("""
            ### 🚀 データ収集戦略
            1. **SNS拡散**: ハッシュタグ #行きたかったマップ
            2. **イベント主催者連携**: 終了時アナウンス
            3. **コミュニティ協力**: 既存ネットワーク活用
            """)
        
        with col2:
            st.markdown("""
            ### 📈 成功の指標
            - **50件**: トレンド分析開始可能
            - **200件**: 地域別分析可能  
            - **500件**: 政策提言の説得力獲得
            """)
        return
    
    # タブ作成（状態管理付き）
    tab_names = ["📈 現状ダッシュボード", "📝 ステークホルダー別レポート", "⚙️ システム設定"]
    
    # カスタムタブの実装（session_stateで管理）
    selected_tab = st.radio("", tab_names, index=st.session_state.active_tab_index, horizontal=True, label_visibility="collapsed")
    st.session_state.active_tab_index = tab_names.index(selected_tab)
    
    # タブ内容の表示
    if st.session_state.active_tab_index == 0:
        show_dashboard_tab(df, metrics)
    elif st.session_state.active_tab_index == 1:
        show_stakeholder_report_tab(df)
    elif st.session_state.active_tab_index == 2:
        show_system_settings_tab(df, metrics)

def show_dashboard_tab(df, metrics):
    """現状ダッシュボードタブの内容"""
    st.header("📈 社会課題の現状ダッシュボード")
    
    # KPIカードの表示
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        delta_color = "normal" if metrics['growth_rate'] >= 0 else "inverse"
        st.metric("投稿数", f"{metrics['total_posts']:,}", 
                 f"{metrics['growth_rate']:+.1f}% (月間)", delta_color=delta_color)
    
    with col2:
        st.metric("対象イベント", f"{metrics['unique_events']:,}")
    
    with col3:
        st.metric("影響地域", f"{metrics['unique_prefectures']}都道府県")
    
    with col4:
        st.metric("最多の障壁", metrics['top_reason'])
    
    st.markdown("---")
    
    # 主要分析グラフ
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("🚧 参加障壁の構造分析")
        reasons_df = logic.count_by_reason()
        if not reasons_df.empty:
            # 構造的問題と個人的問題の分類
            structural_reasons = ['子育て・保育の問題', '会社で許可が降りなかった', '経済的理由', '家族の介護']
            
            reasons_df['問題種別'] = reasons_df['理由'].apply(
                lambda x: '構造的問題' if x in structural_reasons else '個人的制約'
            )
            
            fig = px.bar(
                reasons_df.head(8), 
                x='件数', 
                y='理由',
                color='問題種別',
                orientation='h',
                title="参加障壁の分析（構造的問題 vs 個人的制約）"
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("🗾 地域への影響度")
        prefecture_counts = logic.count_by_prefecture().head(10)
        
        if not prefecture_counts.empty:
            fig = px.pie(
                prefecture_counts, 
                values='count', 
                names='location',
                title="都道府県別影響分布"
            )
            st.plotly_chart(fig, use_container_width=True)
    
    # トレンド分析
    st.subheader("📊 社会課題の推移")
    df_trend = df.copy()
    df_trend['submission_date'] = pd.to_datetime(df_trend['submission_date'])
    df_trend['年月'] = df_trend['submission_date'].dt.to_period('M')
    
    monthly_counts = df_trend.groupby('年月').size().reset_index(name='投稿数')
    monthly_counts['年月'] = monthly_counts['年月'].astype(str)
    
    if len(monthly_counts) > 1:
        fig = px.line(
            monthly_counts, 
            x='年月', 
            y='投稿数',
            title="月別投稿推移（社会課題の深刻化トレンド）",
            markers=True
        )
        fig.update_layout(height=300)
        st.plotly_chart(fig, use_container_width=True)
    
    # 緊急対応が必要な投稿
    st.subheader("🚨 緊急対応が必要な事例")
    
    # 緊急性判定基準の説明
    with st.expander("📋 緊急性判定基準"):
        st.markdown("""
        **緊急度判定スコア（3点以上を緊急案件とする）:**
        
        - **構造的問題キーワード**: +2点
          - 子育て、介護、病気、体調不良、経済的理由
        
        - **切実な表現**: +1点  
          - 困っ、辛い、厳しい、無理、限界、苦しい
        
        - **複合要因**: +1点
          - 3つ以上の理由を同時に抱える場合
        
        **対象期間**: 過去1ヶ月以内の投稿
        """)
    
    urgent_posts = get_urgent_posts(df)
    
    if urgent_posts:
        st.markdown(f"**緊急対応案件: {len(urgent_posts)}件**")
        
        for urgent_post in urgent_posts[:5]:  # 上位5件表示
            post = urgent_post['post']
            score = urgent_post['urgency_score']
            reasons = urgent_post['urgency_reasons']
            
            st.markdown(f'''
            <div class="urgent-post">
                <h4>🚨 緊急度 {score}点: {post['event_name']} ({post['event_prefecture']})</h4>
                <p><strong>理由:</strong> {post['reasons'].replace('|', ', ')}</p>
                {f'<p><strong>声:</strong> "{post["comment"][:150]}{"..." if len(str(post["comment"])) > 150 else ""}"</p>' if post.get('comment') and post['comment'].strip() else ''}
                <p><strong>緊急性要因:</strong> {', '.join(reasons)}</p>
                <p><strong>投稿日:</strong> {post['submission_date']}</p>
            </div>
            ''', unsafe_allow_html=True)
    else:
        st.info("現在、緊急対応が必要な事例はありません。")

def show_stakeholder_report_tab(df):
    """ステークホルダー別レポートタブの内容"""
    st.header("📝 ステークホルダー別戦略レポート")
    
    # 設定の初期化（session_stateで管理してタブ移動を防ぐ）
    if 'report_min_posts' not in st.session_state:
        st.session_state.report_min_posts = 10
    if 'report_months_back' not in st.session_state:
        st.session_state.report_months_back = 2
    if 'report_stakeholder' not in st.session_state:
        st.session_state.report_stakeholder = "event_organizer"
    
    # レポート生成条件の設定
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.subheader("📋 レポート生成条件")
    
    with col2:
        with st.expander("⚙️ 設定"):
            min_posts = st.number_input(
                "最小投稿数", 
                min_value=1, max_value=50, 
                value=st.session_state.report_min_posts,
                help="この件数以上の投稿がある対象のみ選択肢に表示されます"
            )
            months_back = st.number_input(
                "対象期間（月）", 
                min_value=1, max_value=12, 
                value=st.session_state.report_months_back
            )
            
            # 設定の更新（session_stateに保存）
            st.session_state.report_min_posts = min_posts
            st.session_state.report_months_back = months_back
    
    # しきい値情報の表示
    st.markdown(f'''
    <div class="threshold-info">
        <strong>📊 現在の設定:</strong> 過去{months_back}ヶ月間で{min_posts}件以上の投稿がある対象のみレポート生成可能
    </div>
    ''', unsafe_allow_html=True)
    
    # ステークホルダー選択
    col1, col2 = st.columns(2)
    
    with col1:
        stakeholder_options = {
            "event_organizer": "🎪 イベント主催者",
            "government": "🏛️ 自治体・行政",
            "corporate": "🏢 企業・団体",
            "media": "📺 メディア・報道"
        }
        
        selected_stakeholder = st.selectbox(
            "対象ステークホルダー",
            options=list(stakeholder_options.keys()),
            format_func=lambda x: stakeholder_options[x],
            index=list(stakeholder_options.keys()).index(st.session_state.report_stakeholder)
        )
        
        # ステークホルダー選択をsession_stateに保存
        st.session_state.report_stakeholder = selected_stakeholder
    
    with col2:
        # ステークホルダーに応じた対象選択
        target_options = get_target_options(df, selected_stakeholder, min_posts, months_back)
        
        if selected_stakeholder == "event_organizer":
            target_label = "対象イベント"
        elif selected_stakeholder == "government":
            target_label = "対象市区町村"
        else:
            target_label = "対象地域"
        
        target_selection = st.selectbox(target_label, target_options)
    
    # データ状況の確認
    if target_selection != "全体":
        filtered_df, data_sufficient = filter_data_by_criteria(
            df, selected_stakeholder, target_selection, min_posts, months_back
        )
        
        # データ状況の表示
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("対象投稿数", len(filtered_df))
        with col2:
            st.metric("必要投稿数", min_posts)
        with col3:
            if data_sufficient:
                st.success("✅ 生成可能")
            else:
                st.error("❌ 不足")
    
    # ステークホルダー別の説明
    stakeholder_descriptions = {
        "event_organizer": {
            "icon": "🎪",
            "title": "イベント主催者向け改善提案",
            "description": "特定イベントの参加障壁を分析し、次回開催時の改善策を提案します",
            "key_points": ["託児サービス導入", "開催時間最適化", "オンライン配信", "参加費調整", "交通アクセス改善"],
            "note": f"※ 過去{months_back}ヶ月間で{min_posts}件以上の投稿があるイベントが対象"
        },
        "government": {
            "icon": "🏛️",
            "title": "自治体向け政策提言",
            "description": "特定地域の住民が抱える社会参加の障壁を分析し、政策立案の根拠を提供します",
            "key_points": ["一時保育制度拡充", "企業連携促進", "公共交通改善", "子育て支援予算", "働き方改革推進"],
            "note": f"※ 過去{months_back}ヶ月間で{min_posts}件以上の投稿がある市区町村が対象"
        },
        "corporate": {
            "icon": "🏢",
            "title": "企業向けCSR提案",
            "description": "地域の社会課題解決を通じて、企業価値向上に繋がる施策を提案します",
            "key_points": ["従業員研修支援", "託児費補助", "業務時間調整", "会場提供", "地域貢献活動"],
            "note": f"※ 過去{months_back}ヶ月間で{min_posts}件以上の投稿がある都道府県が対象"
        },
        "media": {
            "icon": "📺",
            "title": "メディア向けプレスリリース",
            "description": "地域の社会参加障壁について、社会の注目を集めるニュース素材を提供します",
            "key_points": ["データの社会的意義", "人間ドラマ", "構造的問題の可視化", "政策提言", "成功事例"],
            "note": f"※ 過去{months_back}ヶ月間で{min_posts}件以上の投稿がある都道府県が対象"
        }
    }
    
    desc = stakeholder_descriptions[selected_stakeholder]
    
    # ステークホルダー情報カード
    st.markdown(f'''
    <div class="stakeholder-card">
        <h3>{desc["icon"]} {desc["title"]}</h3>
        <p>{desc["description"]}</p>
        <strong>主要な提案内容:</strong>
        <ul>
            {"".join([f"<li>{point}</li>" for point in desc["key_points"]])}
        </ul>
        <p><em>{desc["note"]}</em></p>
    </div>
    ''', unsafe_allow_html=True)
    
    # レポート生成履歴
    if 'report_history' not in st.session_state:
        st.session_state.report_history = []
    
    # レポート生成
    if st.button("📋 戦略レポートを生成", type="primary"):
        with st.spinner(f"{stakeholder_options[selected_stakeholder]}向けレポートを生成中..."):
            
            # データフィルタリング
            filtered_df, data_sufficient = filter_data_by_criteria(
                df, selected_stakeholder, target_selection, min_posts, months_back
            )
            
            if not data_sufficient:
                st.error(f"""
                **データ不足のため、レポート生成できません**
                
                - 対象期間: 過去{months_back}ヶ月
                - 対象: {target_selection}
                - 実際の投稿数: {len(filtered_df)}件  
                - 必要な投稿数: {min_posts}件以上
                """)
            else:
                # 対象の説明
                target_description = ""
                if selected_stakeholder == "event_organizer":
                    target_description = f"イベント「{target_selection}」"
                elif selected_stakeholder == "government":
                    target_description = f"{target_selection}地域"
                elif selected_stakeholder in ["corporate", "media"]:
                    target_description = f"{target_selection}"
                
                # グラフ生成
                charts_data = create_target_charts(filtered_df, df, target_description)
                
                # グラフ分析テキスト生成
                chart_analysis_text = generate_chart_analysis_text(charts_data, target_description)
                
                # AIレポート生成
                ai_report = generate_stakeholder_report_with_charts(
                    filtered_df, df, selected_stakeholder, target_selection, 
                    min_posts, months_back, chart_analysis_text
                )
                
                # 結果をセッションに保存
                st.session_state.generated_report = {
                    'charts_data': charts_data,
                    'chart_analysis': chart_analysis_text,
                    'ai_report': ai_report,
                    'target_description': target_description
                }
                st.session_state.current_report_params = {
                    'stakeholder': selected_stakeholder,
                    'target': target_selection,
                    'min_posts': min_posts,
                    'months_back': months_back,
                    'timestamp': datetime.now()
                }
                
                # 履歴に追加
                st.session_state.report_history.append({
                    'stakeholder': stakeholder_options[selected_stakeholder],
                    'target': target_selection,
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M')
                })
    
    # 生成されたレポートの表示
    if hasattr(st.session_state, 'generated_report'):
        st.markdown("### 📄 生成された戦略レポート")
        st.markdown("---")
        
        report_data = st.session_state.generated_report
        
        # 1. グラフ表示セクション
        st.subheader("📊 データ分析")
        
        charts_data = report_data['charts_data']
        
        # 参加障壁分布グラフ
        if 'reasons_chart' in charts_data:
            st.plotly_chart(charts_data['reasons_chart'], use_container_width=True)
        
        # 全体比較グラフ
        col1, col2 = st.columns(2)
        with col1:
            if 'comparison_chart' in charts_data:
                st.plotly_chart(charts_data['comparison_chart'], use_container_width=True)
        
        with col2:
            if 'trend_chart' in charts_data:
                st.plotly_chart(charts_data['trend_chart'], use_container_width=True)
        
        # 2. AI生成レポート表示
        st.subheader("🤖 AI分析レポート")
        st.markdown(report_data['ai_report'])
        
        # アクションボタン
        col1, col2, col3 = st.columns(3)
        
        params = st.session_state.get('current_report_params', {})
        stakeholder_name = stakeholder_options.get(params.get('stakeholder', ''), 'stakeholder')
        target_name = params.get('target', 'all')
        timestamp = params.get('timestamp', datetime.now()).strftime('%Y%m%d_%H%M')
        
        with col1:
            # レポート全体（グラフ分析+AIレポート）をダウンロード
            full_report = f"""# {stakeholder_name} 向け戦略レポート
## 対象: {target_name}
生成日時: {timestamp}

{report_data['chart_analysis']}

---

{report_data['ai_report']}
"""
            st.download_button(
                "📥 完全レポートをダウンロード",
                full_report,
                file_name=f"{stakeholder_name}_{target_name}_{timestamp}.md",
                mime="text/markdown"
            )
        
        with col2:
            if st.button("📧 メール下書きを作成"):
                email_draft = f"""
件名: 【{stakeholder_name}】{target_name}における社会課題解決のための協力提案

お世話になっております。

添付の資料は、「行きたかったマップ」プラットフォームで収集した
過去{params.get('months_back', 2)}ヶ月間の投稿データを詳細分析した結果です。

{target_name}における社会参加の障壁について、データとグラフによる分析結果と
具体的な改善提案を含んでおります。

{stakeholder_name}として、社会課題解決にご協力いただければと思います。

詳細については添付資料をご覧ください。

よろしくお願いいたします。
                """
                st.text_area("メール下書き", email_draft, height=200)
        
        with col3:
            if st.button("🔄 条件変更して再生成"):
                st.info("上記の設定を変更して「戦略レポートを生成」を押してください")
    
    # レポート履歴の表示
    if st.session_state.report_history:
        st.subheader("📚 レポート生成履歴")
        
        history_df = pd.DataFrame(st.session_state.report_history)
        st.dataframe(history_df, use_container_width=True)

def show_system_settings_tab(df, metrics):
    """システム設定タブの内容"""
    st.header("⚙️ システム設定")
    
    # AI設定
    st.subheader("🤖 AI設定")
    
    ai_settings = get_ai_settings()
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("### レポート生成設定")
        
        model_options = {
            "gpt-4o-mini": "GPT-4o Mini（高速・低コスト）",
            "gpt-4o": "GPT-4o（バランス型）",
            "gpt-4o-turbo": "GPT-4o Turbo（高品質・低速）"
        }
        
        selected_model = st.selectbox(
            "AIモデル",
            options=list(model_options.keys()),
            index=list(model_options.keys()).index(ai_settings['model']),
            format_func=lambda x: model_options[x]
        )
        
        temperature = st.slider(
            "創造性レベル",
            0.0, 1.0, ai_settings['temperature'], 0.1,
            help="0.0=保守的、1.0=創造的"
        )
        
        max_tokens = st.selectbox(
            "レポート長さ",
            [800, 1200, 1500, 2000],
            index=[800, 1200, 1500, 2000].index(ai_settings['max_tokens'])
        )
    
    with col2:
        st.write("### レポート品質設定")
        
        report_tone = st.selectbox(
            "レポートトーン",
            ["professional", "academic", "conversational"],
            index=["professional", "academic", "conversational"].index(ai_settings['report_tone']),
            format_func=lambda x: {"professional": "ビジネス向け", "academic": "学術的", "conversational": "親しみやすい"}[x]
        )
        
        report_length = st.selectbox(
            "レポート詳細度",
            ["short", "medium", "detailed"],
            index=["short", "medium", "detailed"].index(ai_settings['report_length']),
            format_func=lambda x: {"short": "簡潔", "medium": "標準", "detailed": "詳細"}[x]
        )
        
        if st.button("設定を保存"):
            new_settings = {
                'model': selected_model,
                'temperature': temperature,
                'max_tokens': max_tokens,
                'report_tone': report_tone,
                'report_length': report_length
            }
            update_ai_settings(new_settings)
            st.success("AI設定を保存しました！")
    
    # モデル性能比較
    st.subheader("📊 AIモデル性能比較")
    
    model_comparison = pd.DataFrame({
        'モデル': ['GPT-4o Mini', 'GPT-4o', 'GPT-4o Turbo'],
        '速度': ['高速', '中速', '低速'],
        'コスト': ['低', '中', '高'],
        '品質': ['標準', '高', '最高'],
        '推奨用途': ['日常分析', 'バランス重視', '重要なレポート']
    })
    
    st.dataframe(model_comparison, use_container_width=True)
    
    st.markdown("---")
    
    # データ管理
    st.subheader("🗄️ データ管理")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📥 データバックアップ"):
            if not df.empty:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_data = df.to_csv(index=False).encode('utf-8-sig')
                
                st.download_button(
                    "💾 バックアップをダウンロード",
                    backup_data,
                    file_name=f"ikitakatta_backup_{timestamp}.csv",
                    mime="text/csv"
                )
            else:
                st.warning("バックアップするデータがありません")
    
    with col2:
        if st.button("🔄 データ同期"):
            try:
                logic.migrate_csv_if_needed()
                st.success("データ同期が完了しました")
            except Exception as e:
                st.error(f"同期エラー: {e}")
    
    with col3:
        if st.button("🧹 キャッシュクリア"):
            st.cache_data.clear()
            st.cache_resource.clear()
            st.success("キャッシュをクリアしました")
    
    # システム情報
    st.subheader("ℹ️ システム情報")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("### プラットフォーム情報")
        st.write("- データソース: Google Spreadsheet")
        st.write(f"- 総データ数: {metrics['total_posts']:,}件")
        st.write(f"- 最終更新: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        st.write(f"- バージョン: v2.2")
    
    with col2:
        st.write("### 使用状況")
        client = get_openai_client()
        if client:
            st.write("✅ OpenAI API: 接続済み")
            st.write(f"- 使用モデル: {ai_settings['model']}")
            st.write(f"- レポート品質: {ai_settings['report_tone']}")
        else:
            st.write("❌ OpenAI API: 未接続")
            st.write("- secrets.tomlを確認してください")

if __name__ == "__main__":
    main()