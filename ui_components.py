import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime
import logic

def display_statistics_cards(stats):
    """統計情報をカード形式で表示"""
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("📊 総投稿数", f"{stats['total_posts']}件")
    
    with col2:
        st.metric("🎪 イベント数", f"{stats['unique_events']}件")
    
    with col3:
        st.metric("📍 都道府県", f"{stats['prefectures']}箇所")
    
    with col4:
        st.metric("🌐 オンライン", f"{stats['online_posts']}件")
    
    with col5:
        st.metric("🆕 最近7日", f"{stats['recent_posts']}件")

def display_filter_sidebar(df):
    """サイドバーにフィルタUIを表示"""
    with st.sidebar:
        st.markdown("### 🔍 フィルタ機能")
        
        # 理由フィルタ
        all_reasons = []
        for reasons_str in df['reasons'].dropna():
            all_reasons.extend(str(reasons_str).split('|'))
        unique_reasons = ["すべて"] + sorted(list(set(all_reasons)))
        selected_reason = st.selectbox("🤔 理由", unique_reasons, key="reason_filter")
        
        # オンライン開催を含むかどうか
        include_online = st.checkbox("🌐 オンライン開催を含む", value=True)
        
        # 日付範囲
        st.markdown("### 📅 期間")
        date_options = ["すべて", "最近1週間", "最近1ヶ月", "最近3ヶ月"]
        selected_period = st.selectbox("期間", date_options)
        
        return {
            'selected_reason': selected_reason,
            'include_online': include_online,
            'selected_period': selected_period
        }

def apply_filters(df, filters):
    """フィルタを適用してデータを絞り込む"""
    filtered_df = df.copy()
    
    # オンライン開催フィルタ
    if not filters['include_online']:
        filtered_df = filtered_df[filtered_df['event_prefecture'] != 'オンライン・Web開催']
    
    # 理由フィルタ
    if filters['selected_reason'] != "すべて":
        filtered_df = filtered_df[filtered_df['reasons'].str.contains(filters['selected_reason'], na=False)]
    
    # 期間フィルタ
    if filters['selected_period'] != "すべて":
        filtered_df = apply_date_filter(filtered_df, filters['selected_period'])
    
    return filtered_df

def apply_date_filter(df, period):
    """日付フィルタを適用"""
    if df.empty:
        return df
    
    df_temp = df.copy()
    df_temp['submission_date'] = pd.to_datetime(df_temp['submission_date'], errors='coerce')
    
    current_time = datetime.now()
    
    if period == "最近1週間":
        cutoff = current_time - pd.Timedelta(days=7)
    elif period == "最近1ヶ月":
        cutoff = current_time - pd.Timedelta(days=30)
    elif period == "最近3ヶ月":
        cutoff = current_time - pd.Timedelta(days=90)
    else:
        return df_temp
    
    return df_temp[df_temp['submission_date'] > cutoff]

def display_post_cards(posts_df, title="投稿一覧", posts_per_page=10):
    """投稿をカード形式で表示（ページネーション付き）"""
    if posts_df.empty:
        st.info("📝 該当する投稿が見つかりません")
        return
    
    # 表示順を新しい投稿が上になるように
    display_df = posts_df.iloc[::-1].reset_index(drop=True)
    
    st.markdown(f"### {title} ({len(display_df)}件)")
    
    # ページネーション
    total_posts = len(display_df)
    total_pages = (total_posts + posts_per_page - 1) // posts_per_page
    
    if total_pages > 1:
        page = st.selectbox(
            "ページ選択", 
            range(1, total_pages + 1),
            format_func=lambda x: f"ページ {x} ({total_posts}件中)",
            key=f"page_selector_{title}",
            label_visibility="collapsed"
        )
        st.caption(f"ページ {page} / {total_pages} ({total_posts}件中)")
        start_idx = (page - 1) * posts_per_page
        end_idx = start_idx + posts_per_page
        page_df = display_df.iloc[start_idx:end_idx]
    else:
        page_df = display_df
    
    # 投稿カード表示
    for idx, row in page_df.iterrows():
        with st.container():
            # イベント名（強調表示）
            st.markdown(f"**🎪 {row['event_name']}**")
            
            # 開催地情報
            if row['event_prefecture'] == "オンライン・Web開催":
                st.caption("🌐 オンライン・Web開催")
            else:
                location_text = row['event_prefecture']
                if row.get('event_municipality') and row['event_municipality'] not in ["", "選択なし"]:
                    location_text += f" {row['event_municipality']}"
                st.caption(f"📍 {location_text}")
            
            # イベントURL
            if row.get('event_url') and row['event_url'].strip():
                st.markdown(f"🔗 [イベントページ]({row['event_url']})")
            
            # 理由
            reasons = row['reasons'].split('|') if isinstance(row['reasons'], str) else []
            if reasons:
                reasons_text = ", ".join(reasons[:3])  # 最初の3つの理由のみ表示
                if len(reasons) > 3:
                    reasons_text += f" など{len(reasons)}件"
                st.write(f"🤔 **理由:** {reasons_text}")
            
            # コメント
            if row.get('comment') and not pd.isna(row.get('comment')) and str(row.get('comment')).strip():
                comment_text = str(row['comment'])
                if len(comment_text) > 100:
                    comment_text = comment_text[:100] + "..."
                st.write(f"💭 {comment_text}")
            
            # 投稿日時
            if row.get('submission_date'):
                st.caption(f"🕒 {row['submission_date']}")
            
            st.markdown("---")

def display_reason_analysis(filtered_df):
    """理由別の分析を表示"""
    if filtered_df.empty:
        st.info("📊 表示するデータがありません")
        return
    
    # 理由の集計
    all_reasons = []
    for reasons_str in filtered_df['reasons'].dropna():
        all_reasons.extend(str(reasons_str).split('|'))
    
    if not all_reasons:
        st.info("📊 理由データがありません")
        return
    
    reasons_count = pd.Series(all_reasons).value_counts()
    top_reasons = reasons_count.head(10)
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # 横棒グラフ
        chart_data = pd.DataFrame({
            '理由': top_reasons.index,
            '件数': top_reasons.values
        })
        
        chart = alt.Chart(chart_data).mark_bar(color='#fd5949').encode(
            x=alt.X('件数:Q', title='投稿数'),
            y=alt.Y('理由:N', sort='-x', title='参加できなかった理由'),
            tooltip=['理由:N', '件数:Q']
        ).properties(
            title='参加障壁の分析（上位10項目）',
            height=300
        )
        
        st.altair_chart(chart, use_container_width=True)
    
    with col2:
        # 詳細テーブル
        st.markdown("**📋 詳細データ**")
        detailed_df = pd.DataFrame({
            '理由': reasons_count.index,
            '件数': reasons_count.values,
            '割合': (reasons_count.values / len(filtered_df) * 100).round(1)
        })
        detailed_df['割合'] = detailed_df['割合'].astype(str) + '%'
        
        st.dataframe(
            detailed_df.head(15),
            use_container_width=True,
            hide_index=True
        )

def display_navigation_breadcrumb(selected_prefecture=None, selected_municipality=None):
    """パンくずナビゲーションを表示"""
    breadcrumb_parts = ["🏠 日本全国"]
    
    if selected_prefecture:
        breadcrumb_parts.append(f"📍 {selected_prefecture}")
        
        if selected_municipality:
            breadcrumb_parts.append(f"🏘️ {selected_municipality}")
    
    breadcrumb = " > ".join(breadcrumb_parts)
    st.markdown(f"**{breadcrumb}**")

def display_map_instructions():
    """マップの使い方を表示"""
    with st.expander("🗺️ マップの使い方", expanded=False):
        st.markdown("""
        **マップの操作方法:**
        
        1. **都道府県表示（初期状態）**
           - 各都道府県の投稿数が円の大きさで表示されます
           - 県をクリックすると、その県の市区町村レベルに切り替わります
        
        2. **市区町村表示**
           - 選択した都道府県内の市区町村別投稿数が表示されます
           - 市区町村をクリックすると、その地域の投稿のみが右側に表示されます
        
        3. **投稿一覧連動**
           - マップで地域を選択すると、右側の投稿一覧が自動的にフィルタされます
           - サイドバーのフィルタと組み合わせて使えます
        
        **色の意味:**
        - 🔴 赤色：都道府県レベル（通常）
        - 🟣 紫色：市区町村レベル（通常）
        - 🟠 オレンジ：選択中の地域
        """)

def display_summary_stats(selected_prefecture=None, selected_municipality=None, filtered_df=None):
    """選択地域のサマリー統計を表示"""
    if filtered_df is None or filtered_df.empty:
        return
    
    st.markdown("### 📊 選択地域の概要")
    
    # 基本統計
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("投稿数", len(filtered_df))
    
    with col2:
        unique_events = filtered_df['event_name'].nunique()
        st.metric("イベント数", unique_events)
    
    with col3:
        if selected_municipality:
            unique_venues = 1
        elif selected_prefecture:
            unique_venues = filtered_df['event_municipality'].nunique()
        else:
            unique_venues = filtered_df['event_prefecture'].nunique()
        st.metric("開催地数", unique_venues)
    
    with col4:
        # 最も多い理由
        all_reasons = []
        for reasons_str in filtered_df['reasons'].dropna():
            all_reasons.extend(str(reasons_str).split('|'))
        
        if all_reasons:
            top_reason = pd.Series(all_reasons).value_counts().index[0]
            st.metric("主な理由", top_reason[:10] + "..." if len(top_reason) > 10 else top_reason)

def create_export_buttons(filtered_df, area_name="データ"):
    """データエクスポート用のボタンを作成"""
    if filtered_df.empty:
        return
    
    st.markdown("### 📥 データエクスポート")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # CSV エクスポート
        csv = filtered_df.to_csv(index=False, encoding='utf-8-sig')
        st.download_button(
            label="📊 CSV ダウンロード",
            data=csv,
            file_name=f"{area_name}_投稿データ_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
    
    with col2:
        # 統計レポート
        report = create_simple_report(filtered_df, area_name)
        st.download_button(
            label="📋 統計レポート",
            data=report,
            file_name=f"{area_name}_統計レポート_{datetime.now().strftime('%Y%m%d')}.txt",
            mime="text/plain"
        )
    
    with col3:
        # 理由一覧
        all_reasons = []
        for reasons_str in filtered_df['reasons'].dropna():
            all_reasons.extend(str(reasons_str).split('|'))
        
        reasons_text = "\n".join([f"{reason}: {count}件" 
                                 for reason, count in pd.Series(all_reasons).value_counts().items()])
        
        st.download_button(
            label="📝 理由一覧",
            data=reasons_text,
            file_name=f"{area_name}_理由一覧_{datetime.now().strftime('%Y%m%d')}.txt",
            mime="text/plain"
        )

def create_simple_report(df, area_name):
    """簡易統計レポートを作成"""
    if df.empty:
        return "データがありません"
    
    # 理由の集計
    all_reasons = []
    for reasons_str in df['reasons'].dropna():
        all_reasons.extend(str(reasons_str).split('|'))
    
    reasons_count = pd.Series(all_reasons).value_counts() if all_reasons else pd.Series()
    
    report = f"""
{area_name} 統計レポート
生成日時: {datetime.now().strftime('%Y年%m月%d日 %H:%M')}

【基本統計】
- 総投稿数: {len(df)}件
- ユニークイベント数: {df['event_name'].nunique()}件
- 開催地数: {df['event_prefecture'].nunique()}箇所

【参加できなかった理由 TOP10】
"""
    
    if not reasons_count.empty:
        for i, (reason, count) in enumerate(reasons_count.head(10).items(), 1):
            percentage = (count / len(df)) * 100
            report += f"{i:2d}. {reason}: {count}件 ({percentage:.1f}%)\n"
    
    report += f"""
【最新の投稿】
"""
    
    # 最新の投稿5件
    recent_posts = df.sort_values('submission_date', ascending=False).head(5)
    for i, (_, post) in enumerate(recent_posts.iterrows(), 1):
        report += f"{i}. {post['event_name']} (理由: {post['reasons'].split('|')[0] if post['reasons'] else 'なし'})\n"
    
    return report