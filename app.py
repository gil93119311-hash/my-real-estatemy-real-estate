import streamlit as st
import pandas as pd
import requests
import xml.etree.ElementTree as ET # XML을 해석하는 도구 추가

# --- 페이지 설정 ---
st.set_page_config(page_title="부동산 신축 분석기 v4.0 (최종)", layout="wide")

st.title("🏗️ 부동산 신축 사업성 분석기 v4.0")
st.markdown("---")

# --- 사이드바: API 키 설정 ---
st.sidebar.header("🔑 시스템 설정")
public_api_key = st.sidebar.text_input("1. 공공데이터포털 키 (Decoding)", type="password")
vworld_key = st.sidebar.text_input("2. 브이월드 키", type="password")

st.sidebar.markdown("---")

# --- 메인 기능: 주소 검색 ---
st.subheader("📍 분석할 땅의 주소를 입력하세요")
address = st.text_input("지번 주소 입력 (예: 서울 동작구 사당동 84-8)", "")

# --- 자동 분석 로직 ---
if st.button("🚀 자동 분석 시작"):
    if not public_api_key or not vworld_key:
        st.error("좌측 사이드바에 API 키 2개를 모두 입력해주세요!")
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
            "key": vworld_key
        }
        
        try:
            res_v = requests.get(vworld_url, params=params_v)
            data_v = res_v.json()
            
            if data_v['response']['status'] == 'OK':
                pnu_code = data_v['response']['result']['items'][0]['id']
                official_addr = data_v['response']['result']['items'][0]['title']
                
                st.success(f"✅ 주소 확인 완료: {official_addr}")
                st.caption(f"PNU 코드: {pnu_code}")
                
                # 2단계: 공공데이터포털 (토지이용계획 - XML 방식)
                gov_url = "http://apis.data.go.kr/1613000/NSLandUseInfoService/getLandUsePlanInfo"
                params_g = {
                    "serviceKey": requests.utils.unquote(public_api_key),
                    "pnu": pnu_code,
                    "format": "xml" # 명시적으로 xml 요청
                }
                
                res_g = requests.get(gov_url, params=params_g)
                
                # 디버깅용: 실제 서버가 뭐라고 답했는지 눈으로 확인하기
                with st.expander("🔍 개발자용: 서버 응답 원본 보기 (클릭)"):
                    st.code(res_g.text)

                # XML 해석 시작
                try:
                    root = ET.fromstring(res_g.content)
                    target_area = "정보 없음"
                    
                    # 응답이 에러 메시지인지 확인
                    header_msg = root.findtext(".//resultMsg")
                    if header_msg and "NORMAL SERVICE" not in header_msg:
                        st.error(f"정부 서버 에러: {header_msg}")
                        st.info("키가 아직 등록되지 않았거나(SERVICE KEY IS NOT REGISTERED), 트래픽이 초과되었습니다.")
                    else:
                        # 정상 데이터에서 용도지역 찾기
                        items = root.findall(".//lndcgrCodeNm")
                        found = False
                        for item in items:
                            if item.text and "지역" in item.text:
                                target_area = item.text
                                found = True
                                break
                        
                        if not found:
                             st.warning("용도지역 정보를 찾을 수 없습니다. (데이터 누락 등)")

                        st.success(f"🏛️ 정부 데이터 조회 성공! 이 땅은 **[{target_area}]** 입니다.")
                        
                        # 자동 값 세팅 로직
                        auto_bc, auto_far = 60, 200 # 기본값
                        
                        if "1종" in target_area: auto_bc, auto_far = 60, 150
                        elif "2종" in target_area: auto_bc, auto_far = 60, 200
                        elif "3종" in target_area: auto_bc, auto_far = 50, 250
                        elif "준주거" in target_area: auto_bc, auto_far = 60, 400
                        elif "상업" in target_area: auto_bc, auto_far = 60, 800
                        
                        st.write(f"👉 **{target_area}** 기준: 건폐율 {auto_bc}%, 용적률 {auto_far}% 적용")
                        
                        # 결과 표시
                        col1, col2 = st.columns(2)
                        with col1: st.metric("건폐율", f"{auto_bc}%")
                        with col2: st.metric("용적률", f"{auto_far}%")

                except ET.ParseError:
                    st.error("XML 데이터 해석 실패. 서버 응답이 올바르지 않습니다.")

            else:
                st.error("주소를 찾을 수 없습니다. (브이월드 검색 실패)")
                
        except Exception as e:
            st.error(f"시스템 오류: {e}")
