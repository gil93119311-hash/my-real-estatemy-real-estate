import streamlit as st
import pandas as pd
import requests
import xml.etree.ElementTree as ET
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# --- 페이지 설정 ---
st.set_page_config(page_title="부동산 신축 분석기 v5.6 (강제조립)", layout="wide")

st.title("🏗️ 부동산 신축 사업성 분석기 v5.6")
st.markdown("---")

# --- [핵심] 분석 도구 (주소 강제 조립 방식) ---
def analyze_land(sess, key, pnu):
    base_url = "http://apis.data.go.kr/1613000/NSLandUseInfoService/getLandUsePlanInfo"
    
    # [중요] 파이썬이 키를 건드리지 못하게 주소를 직접 문자열로 만듭니다.
    # 키에 공백이 있으면 안 되므로 .strip() 사용
    clean_key = key.strip()
    
    # URL 직접 조립 (Nuclear Option)
    final_url = f"{base_url}?serviceKey={clean_key}&pnu={pnu}&format=xml"
    
    try:
        # params를 쓰지 않고 final_url을 그대로 쏩니다.
        res_g = sess.get(final_url, timeout=10)
        
        # 500 에러가 나면 내용을 보여줌
        if res_g.status_code == 500:
             st.error("💥 정부 서버 내부 오류 (500 Error)")
             st.warning("키가 잘못되었거나, 해당 PNU에 대한 데이터가 없습니다.")
             st.caption(f"요청한 주소: {final_url}") # 디버깅용
             return

        try:
            root = ET.fromstring(res_g.content)
            header_msg = root.findtext(".//resultMsg")
            
            if header_msg and "NORMAL SERVICE" not in header_msg:
                st.error(f"🏛️ 정부 서버 에러: {header_msg}")
                if "SERVICE KEY" in header_msg:
                        st.info("💡 키가 아직 등록되지 않았거나, 잘못된 키입니다.")
            else:
                target_area = "정보 없음"
                items = root.findall(".//lndcgrCodeNm")
                for item in items:
                    if item.text and "지역" in item.text:
                        target_area = item.text
                        break
                
                if target_area == "정보 없음":
                    st.warning("데이터는 가져왔으나, '용도지역' 정보가 비어있습니다.")
                else:
                    st.success(f"🏛️ 정부 데이터 조회 성공! 이 땅은 **[{target_area}]** 입니다.")
                
                # 결과값 세팅
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
            st.write(res_g.text)

    except Exception as e:
        st.error(f"접속 오류: {e}")

# --- 좀비 접속기 설정 ---
session = requests.Session()
retries = Retry(total=3, backoff_factor=1, status_forcelist=[502, 503, 504]) # 500은 즉시 확인 위해 뺌
session.mount('http://', HTTPAdapter(max_retries=retries))
session.mount('https://', HTTPAdapter(max_retries=retries))

# --- 사이드바 ---
st.sidebar.header("🔑 시스템 설정")
gov_key = st.sidebar.text_input("1. 공공데이터포털 키 (Decoding)", type="password")
vworld_key = st.sidebar.text_input("2. 브이월드 키 (영어+숫자)", type="password")

st.sidebar.markdown("---")

# --- 메인 탭 ---
tab1, tab2 = st.tabs(["📍 주소로 검색", "🔢 PNU 수동 검색"])

with tab1:
    address = st.text_input("지번 주소 (예: 서울 동작구 사당동 84-8)", key="addr")
    if st.button("🚀 주소 분석"):
        if not vworld_key:
            st.error("브이월드 키가 필요합니다.")
        else:
            # 브이월드 로직
            headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://share.streamlit.io"}
            v_url = "http://api.vworld.kr/req/search"
            params = {
                "service": "search", "request": "search", "version": "2.0",
                "crs": "EPSG:4326", "size": "1", "page": "1", "query": address,
                "type": "address", "category": "parcel", "format": "json",
                "key": vworld_key.strip()
            }
            try:
                res = session.get(v_url, params=params, headers=headers, timeout=5)
                data = res.json()
                if data['response']['status'] == 'OK':
                    pnu = data['response']['result']['items'][0]['id']
                    addr = data['response']['result']['items'][0]['title']
                    st.success(f"주소 확인: {addr}")
                    st.info(f"PNU: {pnu}")
                    analyze_land(session, gov_key, pnu)
                else:
                    st.error("주소를 못 찾았습니다.")
            except Exception as e:
                st.error(f"브이월드 오류: {e}")

with tab2:
    st.subheader("PNU 코드 직접 입력")
    st.markdown("사당동 84-8 PNU: **1159010700100840008**")
    manual_pnu = st.text_input("PNU 입력", max_chars=19)
    if st.button("🔧 PNU 분석"):
        if not gov_key:
            st.error("공공데이터 키를 입력하세요.")
        else:
            analyze_land(session, gov_key, manual_pnu)
