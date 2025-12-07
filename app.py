import streamlit as st
import pandas as pd
import requests
import xml.etree.ElementTree as ET
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import urllib3

# 보안 경고 무시 (HTTPS 강제 접속용)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- 페이지 설정 ---
st.set_page_config(page_title="부동산 신축 분석기 v5.9 (최종)", layout="wide")

st.title("🏗️ 부동산 신축 사업성 분석기 v5.9")
st.markdown("---")

# --- 세션(접속기) 설정 ---
session = requests.Session()
retries = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
session.mount('http://', HTTPAdapter(max_retries=retries))
session.mount('https://', HTTPAdapter(max_retries=retries))

# --- 분석 도구 ---
def analyze_land(sess, key, pnu, service_type):
    # 서비스 분기
    if service_type == "plan":
        # [계획] 용도지역 확인 (새로 신청한 키 필요)
        base_url = "http://apis.data.go.kr/1613000/NSLandUseInfoService/getLandUsePlanInfo"
        op_name = "토지이용계획"
    else:
        # [규제] 행위제한 확인 (현재 가진 키)
        base_url = "http://apis.data.go.kr/1613000/arLandUseInfoService/getLandUseAttr"
        op_name = "토지이용규제"

    clean_key = key.strip()
    final_url = f"{base_url}?serviceKey={clean_key}&pnu={pnu}&format=xml"
    
    try:
        res = sess.get(final_url, timeout=10)
        
        if res.status_code != 200:
             st.error(f"💥 {op_name} 서버 에러 ({res.status_code})")
             return

        try:
            root = ET.fromstring(res.content)
            header_msg = root.findtext(".//resultMsg")
            
            if header_msg and "NORMAL SERVICE" not in header_msg:
                st.error(f"🏛️ 정부 서버 메시지: {header_msg}")
            else:
                # 결과 찾기
                target_area = "정보 없음"
                found_list = []
                
                # 모든 태그 뒤져보기
                for elem in root.iter():
                    if elem.text and len(elem.text) > 1:
                        # 용도지역 관련 키워드 찾기
                        if any(x in elem.text for x in ["지역", "지구", "구역"]):
                            found_list.append(elem.text)
                            if "주거" in elem.text or "상업" in elem.text or "녹지" in elem.text:
                                target_area = elem.text

                if found_list:
                    st.success(f"✅ {op_name} 조회 성공!")
                    st.write(f"📜 발견된 규제/지역: {', '.join(list(set(found_list)))}")
                    
                    if service_type == "plan":
                        st.info(f"👉 핵심 용도지역: **[{target_area}]**")
                        # 자동 계산
                        auto_bc, auto_far = 60, 200
                        if "1종" in target_area: auto_bc, auto_far = 60, 150
                        elif "2종" in target_area: auto_bc, auto_far = 60, 200
                        elif "3종" in target_area: auto_bc, auto_far = 50, 250
                        elif "준주거" in target_area: auto_bc, auto_far = 60, 400
                        elif "상업" in target_area: auto_bc, auto_far = 60, 800
                        
                        col1, col2 = st.columns(2)
                        with col1: st.metric("건폐율", f"{auto_bc}%")
                        with col2: st.metric("용적률", f"{auto_far}%")
                    else:
                        st.warning("⚠️ 현재 '규제' 정보만 조회했습니다. (건폐율 자동계산 불가)")
                else:
                    st.warning("조회는 성공했으나, 표시할 데이터가 없습니다.")

        except ET.ParseError:
            st.error("XML 해석 실패")

    except Exception as e:
        st.error(f"접속 오류: {e}")

# --- 사이드바 ---
st.sidebar.header("🔑 시스템 설정")
gov_key = st.sidebar.text_input("1. 공공데이터포털 키 (Decoding)", type="password")
vworld_key = st.sidebar.text_input("2. 브이월드 키 (영어+숫자)", type="password")

st.sidebar.markdown("---")

# --- 메인 기능 ---
st.subheader("🛠️ 서비스 선택 및 분석")

tab_reg, tab_plan, tab_pnu = st.tabs(["🟧 규제 서비스 (현재 키)", "🟦 계획 서비스 (새 키)", "🔢 PNU 수동 입력"])

# 공통 브이월드 함수
def get_pnu_from_vworld(addr, key):
    # HTTPS 강제 사용 및 헤더 추가
    url = "https://api.vworld.kr/req/search"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0.4472.124 Safari/537.36",
        "Referer": "https://share.streamlit.io"
    }
    params = {
        "service": "search", "request": "search", "version": "2.0", "size": "1",
        "query": addr, "type": "address", "category": "parcel", "format": "json",
        "key": key.strip()
    }
    # verify=False로 SSL 에러 무시
    res = session.get(url, params=params, headers=headers, verify=False, timeout=10)
    return res.json()

# [Tab 1] 규제 서비스 (현재 키 테스트)
with tab_reg:
    st.caption("현재 가지고 계신 '규제' 키로 테스트합니다.")
    addr1 = st.text_input("주소 입력", "서울 동작구 사당동 84-8", key="a1")
    if st.button("🔧 규제 정보 조회"):
        if not vworld_key or not gov_key:
            st.error("키를 입력하세요.")
        else:
            try:
                data = get_pnu_from_vworld(addr1, vworld_key)
                if data['response']['status'] == 'OK':
                    pnu = data['response']['result']['items'][0]['id']
                    st.success(f"주소 변환 성공! PNU: {pnu}")
                    analyze_land(session, gov_key, pnu, "regulation")
                else:
                    st.error("브이월드 주소 검색 실패 (수동 입력 탭을 이용하세요)")
            except Exception as e:
                st.error(f"브이월드 접속 오류: {e}")
                st.info("💡 팁: 옆의 [🔢 PNU 수동 입력] 탭을 사용하면 바로 분석 가능합니다.")

# [Tab 2] 계획 서비스 (새 키 필요)
with tab_plan:
    st.caption("새로 신청한 '토지이용계획' 키가 필요합니다.")
    addr2 = st.text_input("주소 입력", "서울 동작구 사당동 84-8", key="a2")
    if st.button("🚀 계획 정보 조회"):
        if not vworld_key or not gov_key:
            st.error("키를 입력하세요.")
        else:
            try:
                data = get_pnu_from_vworld(addr2, vworld_key)
                if data['response']['status'] == 'OK':
                    pnu = data['response']['result']['items'][0]['id']
                    st.success(f"주소 변환 성공! PNU: {pnu}")
                    analyze_land(session, gov_key, pnu, "plan")
                else:
                    st.error("브이월드 주소 검색 실패")
            except Exception as e:
                st.error(f"오류: {e}")

# [Tab 3] 수동 입력 (비상용)
with tab_pnu:
    st.info("브이월드 오류 시 여기를 쓰세요. 정부 데이터 키만 맞으면 작동합니다.")
    pnu_in = st.text_input("PNU 코드 (19자리)", "1159010700100840008")
    service_sel = st.radio("사용할 서비스", ["regulation (현재 키)", "plan (새 키)"])
    if st.button("실행"):
        mode = "plan" if "plan" in service_sel else "regulation"
        analyze_land(session, gov_key, pnu_in, mode)
