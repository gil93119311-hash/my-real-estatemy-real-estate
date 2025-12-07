import streamlit as st
import pandas as pd
import requests
import xml.etree.ElementTree as ET
import urllib3

# 보안 경고 무시
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(page_title="부동산 신축 분석기 v5.3 (최종)", layout="wide")

st.title("🏗️ 부동산 신축 사업성 분석기 v5.3")
st.markdown("---")

# --- 사이드바: API 키 설정 ---
st.sidebar.header("🔑 시스템 설정")
gov_key = st.sidebar.text_input("1. 공공데이터포털 키 (Decoding)", type="password")
vworld_key = st.sidebar.text_input("2. 브이월드 키 (영어+숫자)", type="password")

st.sidebar.markdown("---")

# --- 메인 기능: 주소 검색 ---
st.subheader("📍 분석할 땅의 주소를 입력하세요")
address = st.text_input("지번 주소 입력 (예: 서울 동작구 사당동 84-8)", "")

if st.button("🚀 자동 분석 시작"):
    if not gov_key or not vworld_key:
        st.error("키 2개를 모두 입력해주세요!")
    elif not address:
        st.error("주소를 입력해주세요.")
    else:
        # v5.3 핵심: Referer 헤더 추가 (브이월드에 등록한 주소인 척 함)
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0.4472.124 Safari/537.36",
            "Referer": "https://3tjvfebbzjxocjubecwmho.streamlit.app" 
        }
        
        # 1단계: 브이월드 (HTTPS + verify=False + Referer)
        vworld_url = "https://api.vworld.kr/req/search"
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
            res_v = requests.get(vworld_url, params=params_v, headers=headers, verify=False, timeout=10)
            
            if res_v.status_code != 200:
                st.error(f"🚨 브이월드 접속 거부 ({res_v.status_code})")
                st.write("팁: 브이월드 사이트에서 'URL 추가'를 했는지 확인해주세요.")
                st.stop()

            data_v = res_v.json()
            if data_v['response']['status'] == 'OK':
                if int(data_v['response']['result']['input']['total']) == 0:
                     st.warning("검색 결과가 없습니다. 주소를 확인해주세요.")
                     st.stop()

                pnu_code = data_v['response']['result']['items'][0]['id']
                official_addr = data_v['response']['result']['items'][0]['title']
                
                st.success(f"✅ 주소 확인 완료: {official_addr}")
                st.caption(f"PNU 코드: {pnu_code}")
                
                # 2단계: 공공데이터포털
                gov_url = "http://apis.data.go.kr/1613000/NSLandUseInfoService/getLandUsePlanInfo"
                params_g = {
                    "serviceKey": requests.utils.unquote(gov_key.strip()),
                    "pnu": pnu_code,
                    "format": "xml"
                }
                
                res_g = requests.get(gov_url, params=params_g, headers=headers, verify=False, timeout=10)
                
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
                        
                        # 값 세팅
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
                    st.error("XML 데이터 해석 실패")

            else:
                st.error("주소를 찾을 수 없습니다.")
                
        except Exception as e:
            st.error(f"시스템 접속 오류: {e}")
