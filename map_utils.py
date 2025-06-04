import pydeck as pdk
import pandas as pd
import streamlit as st
import logic
import math

def create_prefecture_map(prefecture_data, selected_prefecture=None):
    """都道府県レベルのマップを作成"""
    if prefecture_data.empty:
        return None
    
    # ビューステートの設定
    if selected_prefecture:
        # 特定都道府県が選択されている場合、その県にフォーカス
        selected_data = prefecture_data[prefecture_data['prefecture'] == selected_prefecture]
        if not selected_data.empty:
            center_lat = selected_data.iloc[0]['latitude']
            center_lon = selected_data.iloc[0]['longitude']
            zoom_level = 7
        else:
            # 日本全体
            center_lat, center_lon, zoom_level = 36.5, 138.0, 4
    else:
        # 日本全体
        center_lat, center_lon, zoom_level = 36.5, 138.0, 4
    
    view_state = pdk.ViewState(
        latitude=center_lat,
        longitude=center_lon,
        zoom=zoom_level,
        pitch=0
    )
    
    # データに色と適切な半径を追加
    map_data = prefecture_data.copy()
    
    def get_color(pref, count, max_count):
        if pref == selected_prefecture:
            return [255, 165, 0, 255]  # オレンジ色（選択中）
        else:
            # 投稿数に応じて色の濃さを調整
            if max_count > 0:
                intensity = min(count / max_count, 1.0)
                # 薄い赤から濃い赤へのグラデーション
                base_color = 200 + int(55 * intensity)  # 200-255の範囲
                return [base_color, 89, 73, 220]
            else:
                return [253, 89, 73, 200]
    
    def calculate_radius(count, max_count):
        """投稿数に基づいて適切な半径を計算（ピクセル単位）"""
        min_radius = 25
        max_radius = 100
        
        if max_count > 0:
            normalized = count / max_count
        else:
            normalized = 0
        
        # 平方根を使って視覚的にバランスの取れたサイズ調整
        radius = min_radius + (max_radius - min_radius) * math.sqrt(normalized)
        return int(radius)
    
    # 最大投稿数を取得
    max_count = map_data['count'].max()
    
    map_data['color'] = map_data.apply(lambda row: get_color(row['prefecture'], row['count'], max_count), axis=1)
    map_data['radius_pixels'] = map_data['count'].apply(lambda x: calculate_radius(x, max_count))
    
    # レイヤーリスト
    layers = []
    
    # 円レイヤー
    circle_layer = pdk.Layer(
        "ScatterplotLayer",
        id="prefecture_layer",
        data=map_data,
        get_position=["longitude", "latitude"],
        get_color="color",
        get_radius="radius_pixels",
        pickable=True,
        opacity=0.8,
        stroked=True,
        filled=True,
        radius_scale=1,
        radius_min_pixels=20,
        radius_max_pixels=120,
        line_width_min_pixels=3,
        get_line_color=[255, 255, 255, 255],
    )
    layers.append(circle_layer)
    
    # 数字表示レイヤー
    text_layer = pdk.Layer(
        "TextLayer",
        id="prefecture_text_layer",
        data=map_data,
        get_position=["longitude", "latitude"],
        get_text="count",
        get_size=16,
        get_color=[255, 255, 255, 255],  # 白い文字
        get_angle=0,
        get_text_anchor='"middle"',
        get_alignment_baseline='"center"',
        pickable=False,
        font_family='"Arial Black", Arial, sans-serif',
        font_weight="bold"
    )
    layers.append(text_layer)
    
    # マップ作成
    deck = pdk.Deck(
        layers=layers,
        initial_view_state=view_state,
        map_style="mapbox://styles/mapbox/light-v10",
        tooltip={
            "html": "<b>{prefecture}</b><br/>📍 {count}件の「行きたかった」声<br/><small>クリックで詳細表示</small>",
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
    
    return deck

def create_municipality_map(municipality_data, prefecture, selected_municipality=None):
    """市区町村レベルのマップを作成"""
    if municipality_data.empty:
        return None
    
    # 都道府県の中心とズームレベルを設定
    if prefecture in logic.PREFECTURE_LOCATIONS:
        center_lat, center_lon = logic.PREFECTURE_LOCATIONS[prefecture]
        zoom_level = 8
    else:
        center_lat, center_lon, zoom_level = 36.5, 138.0, 4
    
    view_state = pdk.ViewState(
        latitude=center_lat,
        longitude=center_lon,
        zoom=zoom_level,
        pitch=0
    )
    
    # データに色と適切な半径を追加
    map_data = municipality_data.copy()
    
    def get_color(municipality, count, max_count):
        if municipality == selected_municipality:
            return [255, 165, 0, 255]  # オレンジ色（選択中）
        else:
            # 投稿数に応じて色の濃さを調整
            if max_count > 0:
                intensity = min(count / max_count, 1.0)
                # 薄い紫から濃い紫へのグラデーション
                red = 67 + int(100 * intensity)
                green = 56 + int(50 * intensity)
                blue = 202 + int(53 * intensity)
                return [min(red, 167), min(green, 106), min(blue, 255), 220]
            else:
                return [67, 56, 202, 200]
    
    def calculate_radius(count, max_count):
        """投稿数に基づいて適切な半径を計算（ピクセル単位）"""
        min_radius = 20
        max_radius = 70
        
        if max_count > 0:
            normalized = count / max_count
        else:
            normalized = 0
        
        radius = min_radius + (max_radius - min_radius) * math.sqrt(normalized)
        return int(radius)
    
    # 最大投稿数を取得
    max_count = map_data['count'].max()
    
    map_data['color'] = map_data.apply(lambda row: get_color(row['municipality'], row['count'], max_count), axis=1)
    map_data['radius_pixels'] = map_data['count'].apply(lambda x: calculate_radius(x, max_count))
    
    # レイヤーリスト
    layers = []
    
    # 円レイヤー
    circle_layer = pdk.Layer(
        "ScatterplotLayer",
        id="municipality_layer",
        data=map_data,
        get_position=["longitude", "latitude"],
        get_color="color",
        get_radius="radius_pixels",
        pickable=True,
        opacity=0.8,
        stroked=True,
        filled=True,
        radius_scale=1,
        radius_min_pixels=15,
        radius_max_pixels=80,
        line_width_min_pixels=2,
        get_line_color=[255, 255, 255, 255],
    )
    layers.append(circle_layer)
    
    # 数字表示レイヤー
    text_layer = pdk.Layer(
        "TextLayer",
        id="municipality_text_layer",
        data=map_data,
        get_position=["longitude", "latitude"],
        get_text="count",
        get_size=14,
        get_color=[255, 255, 255, 255],  # 白い文字
        get_angle=0,
        get_text_anchor='"middle"',
        get_alignment_baseline='"center"',
        pickable=False,
        font_family='"Arial Black", Arial, sans-serif',
        font_weight="bold"
    )
    layers.append(text_layer)
    
    # マップ作成
    deck = pdk.Deck(
        layers=layers,
        initial_view_state=view_state,
        map_style="mapbox://styles/mapbox/light-v10",
        tooltip={
            "html": "<b>{municipality}</b><br/>📍 {count}件の投稿<br/><small>クリックで投稿を表示</small>",
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
    
    return deck

def get_selected_object_from_session_state(key, map_data, map_type="prefecture"):
    """セッションステートから選択されたオブジェクトを取得"""
    if key not in st.session_state:
        return None, None
    
    selection_data = st.session_state[key]
    
    # selection_dataの構造を確認
    if selection_data and 'selection' in selection_data:
        selections = selection_data['selection']
        
        if selections:
            try:
                # Streamlit 1.45.0の新しい構造に対応
                layer_key = f"{map_type}_layer"
                
                # objects から直接データを取得する方法
                if 'objects' in selections and layer_key in selections['objects']:
                    objects_list = selections['objects'][layer_key]
                    if objects_list and len(objects_list) > 0:
                        selected_object = objects_list[0]  # 最初の選択オブジェクト
                        
                        if map_type == "prefecture":
                            return selected_object.get('prefecture'), None
                        elif map_type == "municipality":
                            return None, selected_object.get('municipality')
                
                # indices を使ってmap_dataから取得する方法（フォールバック）
                elif 'indices' in selections and layer_key in selections['indices']:
                    indices_list = selections['indices'][layer_key]
                    if indices_list and len(indices_list) > 0:
                        selected_index = indices_list[0]  # 最初のインデックス
                        
                        if selected_index < len(map_data):
                            selected_item = map_data.iloc[selected_index]
                            
                            if map_type == "prefecture":
                                return selected_item['prefecture'], None
                            elif map_type == "municipality":
                                return None, selected_item['municipality']
                
            except (KeyError, IndexError, TypeError) as e:
                print(f"選択データ取得エラー: {e}")
                return None, None
    
    return None, None

# 以下の関数は現在のStreamlitでは使用不可のため削除
# def get_current_zoom_level(key):
# def should_switch_to_municipality_mode(current_zoom):
# def should_switch_to_prefecture_mode(current_zoom):

def display_debug_info(key):
    """デバッグ情報を表示（開発時用）"""
    if key in st.session_state:
        with st.expander(f"🐛 Debug Info - {key}", expanded=False):
            st.json(st.session_state[key])
    else:
        st.info(f"No selection data for {key}")

def handle_map_click(map_data, click_data, map_type="prefecture"):
    """マップクリックイベントを処理（レガシー関数 - 新版では使用しない）"""
    # この関数は新しいStreamlitでは使用されません
    # get_selected_object_from_session_state を使用してください
    return None, None

def create_reason_chart(filtered_df):
    """理由別の統計チャートを作成"""
    if filtered_df.empty:
        return None
    
    # 理由の集計
    all_reasons = []
    for reasons_str in filtered_df['reasons'].dropna():
        all_reasons.extend(str(reasons_str).split('|'))
    
    if not all_reasons:
        return None
    
    reasons_count = pd.Series(all_reasons).value_counts()
    
    # 上位10項目
    top_reasons = reasons_count.head(10)
    
    chart_data = pd.DataFrame({
        '理由': top_reasons.index,
        '件数': top_reasons.values
    })
    
    return chart_data

def display_map_controls():
    """マップ制御UI要素を表示"""
    with st.sidebar:
        st.markdown("### 🗺️ マップ表示設定")
        
        show_prefecture_labels = st.checkbox("都道府県名を表示", value=True)
        show_count_labels = st.checkbox("投稿数を表示", value=True)
        
        st.markdown("### 📊 表示オプション")
        
        min_posts = st.slider("最小投稿数", 1, 10, 1, help="指定数以上の投稿がある地域のみ表示")
        
        return {
            'show_prefecture_labels': show_prefecture_labels,
            'show_count_labels': show_count_labels,
            'min_posts': min_posts
        }

def get_map_bounds(data, buffer=0.1):
    """データの範囲からマップの境界を計算"""
    if data.empty:
        return None
    
    min_lat = data['latitude'].min() - buffer
    max_lat = data['latitude'].max() + buffer
    min_lon = data['longitude'].min() - buffer
    max_lon = data['longitude'].max() + buffer
    
    return {
        'min_lat': min_lat,
        'max_lat': max_lat,
        'min_lon': min_lon,
        'max_lon': max_lon,
        'center_lat': (min_lat + max_lat) / 2,
        'center_lon': (min_lon + max_lon) / 2
    }