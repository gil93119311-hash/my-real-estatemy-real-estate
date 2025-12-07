import streamlit as st
import pandas as pd
import requests
import xml.etree.ElementTree as ET

st.set_page_config(page_title="부동산 신축 분석기 v4.1 (디버깅)", layout="wide")

st.title("🏗️ 부동산 신축 사업성 분석기 v4.1")
st.markdown("---")

# --- 사이드바: API 키 설정 ---
st.sidebar.header("🔑 시스템 설정")
# 순서가 섞이지 않게 명확히 표시
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
        # 1단계: 브이월드 (주소 -> PNU 변환)
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
            "key": vworld_key.strip() # 공백 제거 안전장치
        }
        
        try:
            res_v = requests.get(vworld_url, params=params_v, timeout=10)
            
            # 브이월드 응답 디버깅
            try:
                data_v = res_v.json()
            except:
                st.error("🚨 브이월드 에러: JSON 응답이 아닙니다.")
                st.warning("키가 잘못되었거나 서버 문제입니다. 아래 내용을 확인하세요.")
                st.code(res_v.text) # 에러 내용 원본 출력
                st.stop()

            if data_v['response']['status'] == 'OK':
                pnu_code = data_v['response']['result']['items'][0]['id']
                official_addr = data_v['response']['result']['items'][0]['title']
                
                st.success(f"✅ 주소 확인 완료: {official_addr}")
                st.caption(f"PNU 코드: {pnu_code}")
                
                # 2단계: 공공데이터포털 (토지이용계획)
                gov_url = "http://apis.data.go.kr/1613000/NSLandUseInfoService/getLandUsePlanInfo"
                params_g = {
                    "serviceKey": requests.utils.unquote(gov_key.strip()),
                    "pnu": pnu_code,
                    "format": "xml"
                }
                
                res_g = requests.get(gov_url, params=params_g, timeout=10)
                
                # 공공데이터 응답 디버깅
                try:
                    root = ET.fromstring(res_g.content)
                    header_msg = root.findtext(".//resultMsg")
                    
                    if header_msg and "NORMAL SERVICE" not in header_msg:
                        st.error(f"🏛️ 정부 서버 에러: {header_msg}")
                        st.info("해결책: 키가 아직 등록 중입니다. 1시간 뒤 다시 시도하세요.")
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
                        
                        col1, col2 = st.columns(2)
                        with col1: st.metric("건폐율", f"{auto_bc}%")
                        with col2: st.metric("용적률", f"{auto_far}%")
                        
                except ET.ParseError:
                    st.error("XML 해석 실패 (공공데이터포털 응답 오류)")
                    st.code(res_g.text)

            else:
                st.error("주소를 찾을 수 없습니다. (브이월드 검색 결과 없음)")
                st.write(f"서버 응답: {data_v}")
                
        except Exception as e:
            st.error(f"시스템 접속 오류: {e}")
