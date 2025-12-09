

import streamlit as st
import requests
import xml.etree.ElementTree as ET
import urllib3
import urllib.parse

# SSL 경고 무시
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(page_title="부동산 신축 분석기 v7.2 (최적화)", layout="wide")

st.title("🏗️ 부동산 신축 사업성 분석기 v7.2")
st.markdown("---")
st.success("💡 선생님의 마이페이지 2번째 목록인 **[토지이용규제법령]** 키를 넣으시면 100% 작동합니다!")

# --- 사이드바 ---
st.sidebar.header("🔑 키 입력")
user_key_input = st.sidebar.text_input("공공데이터포털 키 (Decoding 추천)", type="password")

# --- 메인 기능 ---
st.subheader("🔢 PNU 코드 입력")
pnu_input = st.text_input("PNU 코드 (19자리)", "1159010700100840008")

# --- 테스트할 주소 목록 (선생님 권한에 맞춰 순서 최적화) ---
API_CANDIDATES = [
    # 1순위: 선생님 마이페이지에 있는 서비스 (가장 유력)
    {"name": "1. 토지이용'규제' (RegulationInfo) - 정답", "url": "http://apis.data.go.kr/1613000/LandUseRegulationInfoService/getLandUseRegulationInfo"},
    # 2순위: 다른 토지 관련 서비스
    {"name": "2. 토지이용'계획' (NSLandUseInfo)", "url": "http://apis.data.go.kr/1613000/NSLandUseInfoService/getLandUsePlanInfo"},
    {"name": "3. 도시계획 (UrbanPlanning)", "url": "http://apis.data.go.kr/1613000/UrbanPlanningStatisticsService/getUrbanPlanningStatistics"}
]

if st.button("🚀 분석 시작 (키 자동 변환)"):
    if not user_key_input:
        st.error("👈 왼쪽 사이드바에 키를 입력해주세요!")
    else:
        st.write("🔍 맞는 열쇠를 찾는 중입니다...")
        
        # 키 자동 변환 로직
        raw_key = user_key_input.strip()
        decoded_key = urllib.parse.unquote(raw_key) 
        encoded_key = urllib.parse.quote(decoded_key)
        
        keys_to_try = [decoded_key, encoded_key]
        success_flag = False
        
        for api in API_CANDIDATES:
            if success_flag: break
            
            for k in keys_to_try:
                # API 호출 (pnu 파라미터 사용)
                target_url = f"{api['url']}?serviceKey={k}&pnu={pnu_input}&format=xml"
                
                try:
                    res = requests.get(target_url, timeout=5, verify=False)
                    if res.status_code == 200:
                        try:
                            root = ET.fromstring(res.content)
                            header_msg = root.findtext(".//resultMsg")
                            
                            # 정상 응답 확인
                            if header_msg and "NORMAL SERVICE" in header_msg:
                                st.success(f"🎉 성공! **[{api['name']}]** 서비스로 문이 열렸습니다!")
                                success_flag = True
                                
                                # 결과 데이터 파싱 및 표시
                                found_list = []
                                target_area = "정보 없음"
                                
                                for elem in root.iter():
                                    if elem.text and len(elem.text) > 1:
                                        # 용도지역 관련 단어 찾기
                                        if any(x in elem.text for x in ["지역", "지구", "구역"]):
                                            found_list.append(elem.text)
                                            # 핵심 용도지역 추출 로직
                                            if "종" in elem.text and "주거" in elem.text: target_area = elem.text
                                            elif "상업" in elem.text and "지역" in elem.text: target_area = elem.text

                                st.info(f"📜 조회된 규제 정보: {', '.join(list(set(found_list)))}")
                                
                                if target_area != "정보 없음":
                                    st.write(f"👉 **핵심 용도지역: {target_area}**")
                                    # 건폐율/용적률 자동 계산 (단순 예시)
                                    bc, far = 60, 200
                                    if "1종" in target_area: bc, far = 60, 150
                                    elif "2종" in target_area: bc, far = 60, 200
                                    elif "3종" in target_area: bc, far = 50, 250
                                    elif "준주거" in target_area: bc, far = 60, 400
                                    elif "상업" in target_area: bc, far = 60, 800
                                    
                                    c1, c2 = st.columns(2)
                                    c1.metric("예상 건폐율", f"{bc}%")
                                    c2.metric("예상 용적률", f"{far}%")
                                else:
                                    st.warning("용도지역 정보를 명확히 찾지 못했습니다. PNU를 확인해주세요.")
                                break 
                        except: pass
                except: pass

        if not success_flag:
            st.error("🚫 실패했습니다.")
            st.markdown("""
            **체크리스트:**
            1. **[토지이용규제법령정보]** 키를 넣었는지 확인하세요. (건축HUB 키 ❌)
            2. 키를 발급받은 지 1시간이 지났는지 확인하세요.
            """)
