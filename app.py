import streamlit as st
import pandas as pd
import requests
import xml.etree.ElementTree as ET
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# --- 페이지 설정 ---
st.set_page_config(page_title="부동산 신축 분석기 v5.8 (서비스통합)", layout="wide")

st.title("🏗️ 부동산 신축 사업성 분석기 v5.8")
st.markdown("---")

# --- 분석 도구 (두 가지 서비스 모두 지원) ---
def analyze_land(sess, key, pnu, service_type):
    # 서비스 종류에 따라 주소와 파라미터가 다름
    if service_type == "plan":
        # [계획] 용도지역(주거/상업 등) 확인용 -> 우리가 필요한 것!
        base_url = "http://apis.data.go.kr/1613000/NSLandUseInfoService/getLandUsePlanInfo"
        op_name = "토지이용계획"
    else:
        # [규제] 행위제한(문화재/보호구역) 확인용 -> 현재 선생님이 가진 키
        base_url = "http://apis.data.go.kr/1613000/arLandUseInfoService/getLandUseAttr"
        op_name = "토지이용규제"

    clean_key = key.strip()
    final_url = f"{base_url}?serviceKey={clean_key}&pnu={pnu}&format=xml"
    
    try:
        res = sess.get(final_url, timeout=10)
        
        if res.status_code == 500:
             st.error(f"💥 {op_name} 서버 500 에러")
             st.warning("원인: 키가 이 서비스용이 아니거나, 데이터가 없습니다.")
             return

        if res.status_code == 404:
             st.error(f"🚫 {op_name} 주소 오류 (API not found)")
             st.warning("원인: 신청하신 서비스 이름과 코드의 주소가 맞지 않습니다.")
             return

        try:
            root = ET.fromstring(res.content)
            header_msg = root.findtext(".//resultMsg")
            
            if header_msg and "NORMAL SERVICE" not in header_msg:
                st.error(f"🏛️ 정부 서버 메시지: {header_msg}")
                if "SERVICE KEY" in header_msg:
                        st.info("💡 키가 등록되지 않았거나, 다른 서비스의 키를 넣었습니다.")
            else:
                # 결과 찾기 (서비스마다 태그가 다름)
                target_area = "정보 없음"
                
                # 계획 서비스용 태그
                items_plan = root.findall(".//lndcgrCodeNm")
                # 규제 서비스용 태그
                items_reg = root.findall(".//lnduseAttrNm") 
                
                items = items_plan + items_reg
                
                found_list = []
                for item in items:
                    if item.text:
                        found_list.append(item.text)
                        if "지역" in item.text or "주거" in item.text or "상업" in item.text:
                            target_area = item.text
                
                if found_list:
                    st.success(f"✅ {op_name} 조회 성공!")
                    st.write(f"📜 발견된 정보: {', '.join(found_list)}")
                    
                    if service_type == "plan":
                        st.info(f"👉 핵심 용도지역: **[{target_area}]**")
                        # 자동 계산 로직 (계획 서비스일 때만 작동)
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
                        st.warning("⚠️ 현재 '규제' 정보를 조회했습니다. 건폐율/용적률 자동 계산을 하려면 '계획' 서비스를 신청해서 키를 바꿔주세요.")
                else:
                    st.warning("데이터 조회는 성공했으나, 내용이 비어있습니다.")
                    st.code(res.text)

        except ET.ParseError:
            st.error("XML 해석 실패")
            st.write(res.text)

    except Exception as e:
        st.error(f"접속 오류: {e}")

# --- 세션 설정 ---
session = requests.Session()
retries = Retry(total=3, backoff_factor=1, status_forcelist=[502, 503, 504])
session.mount('http://', HTTPAdapter(max_retries=retries))
session.mount('https://', HTTPAdapter(max_retries=retries))

# --- 사이드바 ---
st.sidebar.header("🔑 시스템 설정")
gov_key = st.sidebar.text_input("1. 공공데이터포털 키 (Decoding)", type="password")
vworld_key = st.sidebar.text_input("2. 브이월드 키 (영어+숫자)", type="password")

st.sidebar.markdown("---")

# --- 메인 기능 ---
st.subheader("🛠️ 서비스 선택 및 분석")

# 탭으로 기능 분리
tab_plan, tab_reg, tab_pnu = st.tabs(["🟦 계획 서비스 (정석)", "🟧 규제 서비스 (현재 키 테스트)", "🔢 PNU 수동 입력"])

# [Tab 1] 계획 서비스 (새로 신청해야 함)
with tab_plan:
    st.info("새로 신청한 '토지이용계획정보서비스' 키가 필요합니다.")
    addr1 = st.text_input("주소 입력", "서울 동작구 사당동 84-8", key="addr1")
    if st.button("🚀 계획 정보 조회 (용도지역)"):
        # 브이월드 -> PNU -> 계획 서비스
        if not vworld_key or not gov_key:
            st.error("키를 입력하세요.")
        else:
            # (간략화된 브이월드 호출)
            try:
                h = {"User-Agent": "Mozilla/5.0", "Referer": "https://share.streamlit.io"}
                p_v = {"service": "search", "request": "search", "version": "2.0", "size": "1", "query": addr1, "type": "address", "category": "parcel", "format": "json", "key": vworld_key.strip()}
                r_v = session.get("http://api.vworld.kr/req/search", params=p_v, headers=h, timeout=5).json()
                if r_v['response']['status'] == 'OK':
                    pnu = r_v['response']['result']['items'][0]['id']
                    analyze_land(session, gov_key, pnu, "plan") # plan 모드 호출
                else: st.error("주소 검색 실패")
            except Exception as e: st.error(f"오류: {e}")

# [Tab 2] 규제 서비스 (현재 키 작동 확인용)
with tab_reg:
    st.caption("선생님이 현재 가진 키로 '연결'이 되는지 테스트하는 곳입니다.")
    addr2 = st.text_input("주소 입력", "서울 동작구 사당동 84-8", key="addr2")
    if st.button("🔧 규제 정보 조회 (테스트)"):
        if not vworld_key or not gov_key:
            st.error("키를 입력하세요.")
        else:
            try:
                h = {"User-Agent": "Mozilla/5.0", "Referer": "https://share.streamlit.io"}
                p_v = {"service": "search", "request": "search", "version": "2.0", "size": "1", "query": addr2, "type": "address", "category": "parcel", "format": "json", "key": vworld_key.strip()}
                r_v = session.get("http://api.vworld.kr/req/search", params=p_v, headers=h, timeout=5).json()
                if r_v['response']['status'] == 'OK':
                    pnu = r_v['response']['result']['items'][0]['id']
                    analyze_land(session, gov_key, pnu, "regulation") # regulation 모드 호출
                else: st.error("주소 검색 실패")
            except Exception as e: st.error(f"오류: {e}")

# [Tab 3] 수동 입력
with tab_pnu:
    pnu_in = st.text_input("PNU 코드 (19자리)", "1159010700100840008")
    service_sel = st.radio("사용할 서비스", ["plan (계획 - 용도지역)", "regulation (규제 - 현재키)"])
    if st.button("실행"):
        mode = "plan" if "plan" in service_sel else "regulation"
        analyze_land(session, gov_key, pnu_in, mode)
