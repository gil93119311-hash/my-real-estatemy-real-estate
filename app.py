import streamlit as st
import pandas as pd
import requests
import xml.etree.ElementTree as ET
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# --- 페이지 설정 ---
st.set_page_config(page_title="부동산 신축 분석기 v5.5 (순서수정)", layout="wide")

st.title("🏗️ 부동산 신축 사업성 분석기 v5.5")
st.markdown("---")

# --- [중요] 분석 도구(함수)를 먼저 정의합니다 ---
def analyze_land(sess, key, pnu):
    gov_url = "http://apis.data.go.kr/1613000/NSLandUseInfoService/getLandUsePlanInfo"
    params_g = {
        "serviceKey": requests.utils.unquote(key.strip()),
        "pnu": pnu,
        "format": "xml"
    }
    
    try:
        # 정부 서버 접속
        res_g = sess.get(gov_url, params=params_g, timeout=10)
        
        try:
            root = ET.fromstring(res_g.content)
            header_msg = root.findtext(".//resultMsg")
            
            if header_msg and "NORMAL SERVICE" not in header_msg:
                st.error(f"🏛️ 정부 서버 에러: {header_msg}")
                if "SERVICE KEY" in header_msg:
                        st.info("💡 키 등록 대기 중입니다. (1시간 소요)")
            else:
                target_area = "정보 없음"
                items = root.findall(".//lndcgrCodeNm")
                for item in items:
                    if item.text and "지역" in item.text:
                        target_area = item.text
                        break
                
                st.success(f"🏛️ 정부 데이터 조회 성공! 이 땅은 **[{target_area}]** 입니다.")
                
                # 결과값 세팅 (용도지역별 건폐율/용적률)
                auto_bc, auto_far = 60, 200
                if "1종" in target_area: auto_bc, auto_far = 60, 150
                elif "2종" in target_area: auto_bc, auto_far = 60, 200
                elif "3종" in target_area: auto_bc, auto_far = 50, 250
                elif "준주거" in target_area: auto_bc, auto_far = 60, 400
                elif "상업" in target_area: auto_bc, auto_far = 60, 800
                
                st.markdown("---")
                col1, col2 = st.columns(2)
                with col1: st.metric("건폐율 (자동)", f"{auto_bc}%")
                with col2: st.metric("용적률 (자동)", f"{auto_far}%")

        except ET.ParseError:
            st.error("데이터 해석 실패 (XML 오류)")
            st.code(res_g.text)

    except Exception as e:
        st.error(f"정부 서버 접속 오류: {e}")

# --- 좀비 접속기(Session) 설정 ---
session = requests.Session()
retries = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
session.mount('http://', HTTPAdapter(max_retries=retries))
session.mount('https://', HTTPAdapter(max_retries=retries))

# --- 사이드바: API 키 설정 ---
st.sidebar.header("🔑 시스템 설정")
gov_key = st.sidebar.text_input("1. 공공데이터포털 키 (Decoding)", type="password")
vworld_key = st.sidebar.text_input("2. 브이월드 키 (영어+숫자)", type="password")

st.sidebar.markdown("---")

# --- 메인 기능: 탭으로 나누기 ---
tab1, tab2 = st.tabs(["📍 주소로 검색 (자동)", "🔢 PNU 코드로 검색 (수동)"])

# [Tab 1] 주소 검색 모드
with tab1:
    st.subheader("분석할 땅의 주소를 입력하세요")
    address = st.text_input("지번 주소 (예: 서울 동작구 사당동 84-8)", key="addr_input")
    
    if st.button("🚀 주소로 분석 시작"):
        if not gov_key or not vworld_key:
            st.error("키 2개를 모두 입력해주세요!")
        elif not address:
            st.error("주소를 입력해주세요.")
        else:
            # 브이월드 접속 시도
            vworld_url = "http://api.vworld.kr/req/search"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0.4472.124 Safari/537.36",
                "Referer": "https://share.streamlit.io" 
            }
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
                "key": vworld_key.strip()
            }
            
            try:
                # session을 사용하여 재시도 기능 활성화
                res_v = session.get(vworld_url, params=params_v, headers=headers, timeout=10)
                data_v = res_v.json()
                
                if data_v['response']['status'] == 'OK':
                    if int(data_v['response']['result']['input']['total']) == 0:
                         st.warning("검색 결과가 없습니다.")
                         st.stop()

                    pnu_code = data_v['response']['result']['items'][0]['id']
                    official_addr = data_v['response']['result']['items'][0]['title']
                    
                    st.success(f"✅ 주소 확인 완료: {official_addr}")
                    st.info(f"PNU 코드: {pnu_code}")
                    
                    # 함수 호출 (이제 함수가 위에 있어서 에러 안 남)
                    analyze_land(session, gov_key, pnu_code)
                    
                else:
                    st.error("주소를 찾을 수 없습니다. (브이월드 오류)")
            except Exception as e:
                st.error(f"🚨 브이월드 접속 실패: {e}")
                st.warning("주소 검색이 안 되면, 옆에 있는 [PNU 코드로 검색] 탭을 이용하세요!")

# [Tab 2] PNU 수동 입력 모드 (비상용)
with tab2:
    st.subheader("PNU 코드를 직접 입력하세요")
    st.caption("주소 검색이 막혔을 때 사용하는 비상구입니다.")
    st.markdown("사당동 84-8 PNU: **1159010700100840008** (복사해서 쓰세요)")
    manual_pnu = st.text_input("PNU 코드 19자리 입력", max_chars=19)
    
    if st.button("🔧 PNU로 분석 시작"):
        if not gov_key:
            st.error("공공데이터포털 키가 필요합니다!")
        elif len(manual_pnu) < 19:
            st.error("PNU 코드는 19자리 숫자여야 합니다.")
        else:
            # 함수 호출
            analyze_land(session, gov_key, manual_pnu)
