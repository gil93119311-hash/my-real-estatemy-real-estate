import streamlit as st
import pandas as pd
import requests
import xml.etree.ElementTree as ET

# 페이지 설정
st.set_page_config(page_title="부동산 신축 분석기 v5.2 (우회)", layout="wide")

st.title("🏗️ 부동산 신축 사업성 분석기 v5.2")
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
        st.error("좌측 사이드바에 키 2개를 모두 입력해주세요!")
    elif not address:
        st.error("주소를 입력해주세요.")
    else:
        # 헤더 설정 (일반 브라우저처럼 위장)
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        # 1단계: 브이월드 (HTTP로 변경하여 SSL 차단 회피)
        # https -> http 로 변경됨
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
            "key": vworld_key.strip()
        }
        
        try:
            # timeout을 넉넉하게 주고, HTTP로 요청
            res_v = requests.get(vworld_url, params=params_v, headers=headers, timeout=15)
            
            # 응답 상태 확인
            if res_v.status_code != 200:
                st.error(f"🚨 브이월드 접속 거부 (상태코드: {res_v.status_code})")
                st.write("해결책: 잠시 후 다시 시도하거나, 주소를 확인해주세요.")
                st.stop()

            try:
                data_v = res_v.json()
            except:
                st.error("🚨 브이월드 응답 오류: JSON 형식이 아닙니다.")
                st.code(res_v.text)
                st.stop()

            if data_v['response']['status'] == 'OK':
                # 검색 결과가 없는 경우 처리
                if int(data_v['response']['result']['input']['total']) == 0:
                     st.warning("검색 결과가 없습니다. 주소 오타를 확인해주세요.")
                     st.stop()

                pnu_code = data_v['response']['result']['items'][0]['id']
                official_addr = data_v['response']['result']['items'][0]['title']
                
                st.success(f"✅ 주소 확인 완료: {official_addr}")
                st.caption(f"PNU 코드: {pnu_code}")
                
                # 2단계: 공공데이터포털 (HTTP 사용)
                gov_url = "http://apis.data.go.kr/1613000/NSLandUseInfoService/getLandUsePlanInfo"
                params_g = {
                    "serviceKey": requests.utils.unquote(gov_key.strip()),
                    "pnu": pnu_code,
                    "format": "xml"
                }
                
                res_g = requests.get(gov_url, params=params_g, headers=headers, timeout=15)
                
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
                    st.error("XML 데이터 해석 실패")
                    st.code(res_g.text)

            else:
                st.error("주소를 찾을 수 없습니다.")
                
        except Exception as e:
            st.error(f"시스템 접속 오류: {e}")
