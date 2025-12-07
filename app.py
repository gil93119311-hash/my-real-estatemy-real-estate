import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# --- 페이지 설정 ---
st.set_page_config(page_title="부동산 신축 분석기 v2", layout="wide")

st.title("🏗️ 부동산 신축 사업성 분석기 v2.0")
st.markdown("---")

# --- 사이드바: 입력 조건 ---
with st.sidebar:
    st.header("1. 토지 및 건축 정보")
    land_area = st.number_input("대지면적 (평)", value=35.0, step=0.1)
    
    # 건폐율은 보통 주거지역 60% 가정 (입력 가능하게 변경)
    bc_ratio = st.slider("건폐율 (%) - 바닥 면적", 0, 100, 60)
    # 용적률
    far_ratio = st.slider("용적률 (%) - 전체 층 면적 합계", 0, 400, 200)

    st.header("2. 비용 설정 (단위: 만원)")
    land_price_per_pyung = st.number_input("평당 토지 매입비", value=5000, step=100)
    const_cost_per_pyung = st.number_input("평당 건축비", value=800, step=50)
    
    st.header("3. 세대 구성 설정")
    # 전용률(실사용면적 비율) 가정
    efficiency_ratio = 80 # %
    
    st.subheader("평형대 설정")
    size_1_5 = st.number_input("1.5룸 크기 (평)", value=8.0)
    size_2_0 = st.number_input("투룸 크기 (평)", value=12.0)
    
    st.subheader("구성 비율")
    ratio_1_5 = st.slider("1.5룸 비율 (%)", 0, 100, 50)
    # 투룸 비율은 자동으로 나머지
    ratio_2_0 = 100 - ratio_1_5
    st.info(f"투룸 비율: {ratio_2_0}%")

    st.header("4. 매출 설정")
    sales_price_per_pyung = st.number_input("평당 예상 분양가 (만원)", value=3500)

# --- 계산 로직 ---

# 1. 면적 계산
building_area = land_area * (bc_ratio / 100) # 건축면적 (바닥)
total_floor_area = land_area * (far_ratio / 100) # 연면적 (전체)

# 2. 층수 추정 (단순 계산: 연면적 / 건축면적)
if building_area > 0:
    estimated_floors = total_floor_area / building_area
else:
    estimated_floors = 0

# 3. 세대수 계산 (전용면적 기준)
net_area = total_floor_area * (efficiency_ratio / 100) # 복도/계단 제외한 실 면적
area_for_1_5 = net_area * (ratio_1_5 / 100)
area_for_2_0 = net_area * (ratio_2_0 / 100)

count_1_5 = int(area_for_1_5 / size_1_5) if size_1_5 > 0 else 0
count_2_0 = int(area_for_2_0 / size_2_0) if size_2_0 > 0 else 0
total_units = count_1_5 + count_2_0

# 4. 주차 대수 (서울시 다세대 기준: 대략 세대당 0.7대 or 면적기반. 여기선 단순화하여 세대당 0.8대 가정)
parking_needed = round(total_units * 0.8)

# 5. 사업성 분석 (단위: 억 원으로 변환)
# 토지비 = 평수 * 평당가격(만원) -> 만원 단위 -> 억 단위로 나누기(10000)
total_land_cost = (land_area * land_price_per_pyung) / 10000 
total_const_cost = (total_floor_area * const_cost_per_pyung) / 10000
total_cost = total_land_cost + total_const_cost # 기타비용 제외한 단순 합계

total_sales = (total_floor_area * sales_price_per_pyung) / 10000
net_profit = total_sales - total_cost
roi = (net_profit / total_cost) * 100 if total_cost > 0 else 0

# --- 결과 화면 출력 ---

# [상단] 핵심 지표
col1, col2, col3, col4 = st.columns(4)
col1.metric("예상 연면적", f"{total_floor_area:.1f} 평")
col2.metric("총 사업비", f"{total_cost:.1f} 억")
col3.metric("예상 순수익", f"{net_profit:.1f} 억", delta=f"{roi:.1f}% 수익률")
col4.metric("총 세대수", f"{total_units} 세대")

# [중단] 상세 건축 개요 & 3D
st.subheader("📊 상세 건축 개요 및 시각화")

c1, c2 = st.columns([1, 1])

with c1:
    st.markdown("#### 1. 건축 개요")
    summary_data = {
        "항목": ["대지면적", "건축면적", "연면적", "건폐율 / 용적률", "예상 층수", "필요 주차대수"],
        "내용": [
            f"{land_area} 평",
            f"{building_area:.1f} 평",
            f"{total_floor_area:.1f} 평",
            f"{bc_ratio}% / {far_ratio}%",
            f"지상 {int(estimated_floors)} 층 (필로티 제외)",
            f"약 {parking_needed} 대"
        ]
    }
    st.table(pd.DataFrame(summary_data))

    st.markdown("#### 2. 세대 구성 (예상)")
    unit_data = {
        "타입": ["1.5룸", "투룸"],
        "평형": [f"{size_1_5} 평형", f"{size_2_0} 평형"],
        "세대수": [f"{count_1_5} 세대", f"{count_2_0} 세대"]
    }
    st.table(pd.DataFrame(unit_data))

with c2:
    st.markdown("#### 3. 건물 3D 매스 (부피 예상도)")
    
    # 3D 박스 그리기 (Plotly Mesh3d 사용)
    # 건물 크기 비례 설정 (가로, 세로, 높이)
    # 대지를 정사각형으로 가정: 한 변의 길이 = sqrt(대지면적 * 3.3) meters
    import math
    side_length = math.sqrt(land_area * 3.3058) 
    
    # 건물 바닥 면적 (건폐율 적용)
    bldg_side = side_length * math.sqrt(bc_ratio / 100)
    
    # 건물 높이 (층고 3m 가정 * 층수)
    height = estimated_floors * 3.0

    # 큐브 좌표 생성
    x = [0, bldg_side, bldg_side, 0, 0, bldg_side, bldg_side, 0]
    y = [0, 0, bldg_side, bldg_side, 0, 0, bldg_side, bldg_side]
    z = [0, 0, 0, 0, height, height, height, height]
    
    # 인덱스 연결 (큐브 면 생성)
    i = [7, 0, 0, 0, 4, 4, 6, 6, 4, 0, 3, 2]
    j = [3, 4, 1, 2, 5, 6, 5, 2, 0, 1, 6, 3]
    k = [0, 7, 2, 3, 6, 7, 1, 1, 5, 5, 7, 6]

    fig = go.Figure(data=[
        go.Mesh3d(
            x=x, y=y, z=z,
            i=i, j=j, k=k,
            opacity=0.6,
            color='#4169E1',
            flatshading=True,
            name='건물'
        )
    ])
    
    # 바닥(땅) 추가
    fig.add_trace(go.Mesh3d(
        x=[-5, side_length+5, side_length+5, -5],
        y=[-5, -5, side_length+5, side_length+5],
        z=[0, 0, 0, 0],
        i=[0, 0], j=[1, 2], k=[2, 3],
        color='#D3D3D3', opacity=0.5, name='대지'
    ))

    fig.update_layout(
        scene=dict(
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
            zaxis=dict(visible=True, title='높이(m)'),
            aspectmode='data' # 비율 유지
        ),
        margin=dict(l=0, r=0, b=0, t=0),
        height=400
    )
    
    st.plotly_chart(fig, use_container_width=True)
    st.caption("※ 단순 부피(Mass) 시뮬레이션입니다. 실제 설계와 다를 수 있습니다.")