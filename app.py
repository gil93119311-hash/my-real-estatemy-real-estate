import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests

# --- 페이지 설정 ---
st.set_page_config(page_title="부동산 신축 분석기 v3.0 (자동화)", layout="wide")

st.title("🏗️ 부동산 신축 사업성 분석기 v3.0")
st.markdown("---")

# --- 사이드바: API 키 설정 ---
st.sidebar.header("🔑 시스템 설정")
# 매번 입력하기 귀찮으면 value="여기에_키_입력" 처럼 따옴표 안에 키를 넣어두셔도 됩니다.
public_api_key = st.sidebar.text_input("1. 공공데이터포털 키 (Decoding)", type="password")
vworld_key = st.sidebar.text_input("2. 브이월드 키", type="password")

st.sidebar.markdown("---")

# --- 메인 기능: 주소 검색 ---
st.subheader("📍 분석할 땅의 주소를 입력하세요")
address = st.text_input("지번 주소 입력 (예: 서울 강남구 삼성동 123)", "")

# --- 자동 분석 로직 ---
if st.button("🚀 자동 분석 시작"):
    if not public_api_key or not vworld_key:
        st.error("좌측 사이드바에 API 키 2개를 모두 입력해주세요!")
    elif not address:
        st.error("주소를 입력해주세요.")
    else:
        # 1단계: 브이월드에게 PNU(땅 코드) 물어보기
        vworld_url = "http://api.vworld.kr/req/search"
        params_v = {
            "service": "search",
            "request": "search",
            "version": "2.0",
            "crs": "EPSG:4326",
            "size": "1",
            "page": "1",
            "query": address,
            "type": "address",
            "category": "parcel",
            "format": "json",
            "key": vworld_key
        }
        
        try:
            res_v = requests.get(vworld_url, params=params_v)
            data_v = res_v.json()
            
            if data_v['response']['status'] == 'OK':
                # PNU 코드와 공식 주소 추출
                pnu_code = data_v['response']['result']['items'][0]['id'] # 브이월드는 id가 PNU임
                official_addr = data_v['response']['result']['items'][0]['title']
                
                st.success(f"✅ 주소 확인 완료: {official_addr}")
                st.info(f"땅 고유 코드(PNU): {pnu_code}")
                
                # 2단계: 공공데이터포털에게 용도지역 물어보기
                # (토지이용계획정보 API)
                gov_url = "http://apis.data.go.kr/1613000/NSLandUseInfoService/getLandUsePlanInfo"
                params_g = {
                    "serviceKey": requests.utils.unquote(public_api_key),
                    "pnu": pnu_code,
                    "format": "json"
                }
                
                res_g = requests.get(gov_url, params=params_g)
                
                # 용도지역 찾기 로직
                target_area = "정보 없음"
                try:
                    items = res_g.json()['landUsePlanInfoList']
                    # 데이터 중에서 '지역지구명'만 쏙 뽑아내기
                    for item in items:
                        if "지역" in item['lndcgrCodeNm']: # 용도지역 관련 코드만 필터링
                            target_area = item['lndcgrCodeNm']
                            break # 첫 번째 발견된 주요 지역 정보 사용
                except:
                    target_area = "데이터 조회 실패 (또는 해당 정보 없음)"

                st.success(f"🏛️ 정부 데이터 조회 성공! 이 땅은 **[{target_area}]** 입니다.")
                
                # 3단계: 조회된 정보로 기본값 세팅 (예시)
                # 용도지역에 따른 건폐율/용적률 자동 추천
                auto_bc = 60 # 기본값
                auto_far = 200 # 기본값
                
                if "1종" in target_area:
                    auto_bc, auto_far = 60, 150
                elif "2종" in target_area:
                    auto_bc, auto_far = 60, 200
                elif "3종" in target_area:
                    auto_bc, auto_far = 50, 250
                elif "준주거" in target_area:
                    auto_bc, auto_far = 60, 400
                elif "상업" in target_area:
                    auto_bc, auto_far = 60, 800
                
                st.write(f"👉 **{target_area}** 법규에 따라 건폐율 {auto_bc}%, 용적률 {auto_far}%를 자동 적용합니다.")

                # --- 결과 보여주기 (기존 계산기 UI 연동) ---
                st.markdown("---")
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("대지면적 (예상)", "35 평 (자동연동 예정)")
                with col2:
                    st.metric("추천 용적률", f"{auto_far}%")

            else:
                st.error("주소를 찾을 수 없습니다. 정확한 지번 주소로 입력해 주세요.")
                
        except Exception as e:
            st.error(f"오류가 발생했습니다: {e}")
            st.warning("아직 API 키가 서버에 등록되지 않았을 수 있습니다. 1시간 뒤 다시 시도해보세요.")
