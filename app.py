import streamlit as st
import requests
import xml.etree.ElementTree as ET
import urllib3
import urllib.parse

# SSL 경고 무시
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(page_title="부동산 신축 분석기 v7.1 (키 자동변환)", layout="wide")

st.title("🏗️ 부동산 신축 사업성 분석기 v7.1")
st.markdown("---")
st.info("🤖 선생님이 가진 키를 자동으로 변환해서 맞는 열쇠를 찾아냅니다.")

# --- 사이드바 ---
st.sidebar.header("🔑 키 입력")
# 아무 키나 넣으세요. 코드가 알아서 처리합니다.
user_key_input = st.sidebar.text_input("공공데이터포털 키 (아무거나)", type="password")

# --- 메인 기능 ---
st.subheader("🔢 PNU 코드 입력")
pnu_input = st.text_input("PNU 코드 (19자리)", "1159010700100840008")

# --- 테스트할 주소 목록 (4곳) ---
API_CANDIDATES = [
    {"name": "1. 토지이용'규제' (arLandUseInfo) - 선생님 키 유력", "url": "http://apis.data.go.kr/1613000/arLandUseInfoService/getLandUseAttr"},
    {"name": "2. 토지이용'계획' (NSLandUseInfo) - 정석", "url": "http://apis.data.go.kr/1613000/NSLandUseInfoService/getLandUsePlanInfo"},
    {"name": "3. 규제'법령' (RegulationInfo)", "url": "http://apis.data.go.kr/1613000/LandUseRegulationInfoService/getLandUseRegulationInfo"},
    {"name": "4. 도시계획 (UrbanPlanning)", "url": "http://apis.data.go.kr/1613000/UrbanPlanningStatisticsService/getUrbanPlanningStatistics"}
]

if st.button("🚀 만능 분석 시작 (키 자동 변환)"):
    if not user_key_input:
        st.error("왼쪽 사이드바에 키를 입력해주세요!")
    else:
        st.write("🔍 맞는 열쇠를 찾는 중입니다...")
        
        # [핵심] 키 자동 변환 로직 (Encoding <-> Decoding)
        # 사용자가 뭘 넣었든, 두 가지 버전을 다 만듭니다.
        raw_key = user_key_input.strip()
        decoded_key = urllib.parse.unquote(raw_key) # 디코딩 된 버전
        encoded_key = urllib.parse.quote(decoded_key) # 인코딩 된 버전
        
        # 시도할 키 목록
        keys_to_try = [decoded_key, encoded_key]
        
        success_flag = False
        
        # 1. 모든 서비스 주소에 대해
        for api in API_CANDIDATES:
            if success_flag: break # 찾았으면 중단
            
            # 2. 모든 키 버전에 대해 (변환해가며 시도)
            for k in keys_to_try:
                # URL 직접 조립
                target_url = f"{api['url']}?serviceKey={k}&pnu={pnu_input}&format=xml"
                
                try:
                    res = requests.get(target_url, timeout=5, verify=False)
                    
                    if res.status_code == 200:
                        try:
                            root = ET.fromstring(res.content)
                            header_msg = root.findtext(".//resultMsg")
                            
                            if header_msg and "NORMAL SERVICE" in header_msg:
                                st.success(f"🎉 성공! **[{api['name']}]** 문이 열렸습니다!")
                                success_flag = True
                                
                                # 결과 파싱
                                found_list = []
                                target_area = "정보 없음"
                                for elem in root.iter():
                                    if elem.text and len(elem.text) > 1:
                                        if any(x in elem.text for x in ["지역", "지구", "구역"]):
                                            found_list.append(elem.text)
                                            if "종" in elem.text and "주거" in elem.text: target_area = elem.text
                                            elif "상업" in elem.text and "지역" in elem.text: target_area = elem.text

                                st.info(f"📜 조회 내용: {', '.join(list(set(found_list)))}")
                                
                                if target_area != "정보 없음":
                                    st.write(f"👉 **핵심 용도지역: {target_area}**")
                                    # 계산 로직
                                    bc, far = 60, 200
                                    if "1종" in target_area: bc, far = 60, 150
                                    elif "2종" in target_area: bc, far = 60, 200
                                    elif "3종" in target_area: bc, far = 50, 250
                                    elif "준주거" in target_area: bc, far = 60, 400
                                    elif "상업" in target_area: bc, far = 60, 800
                                    
                                    c1, c2 = st.columns(2)
                                    c1.metric("건폐율", f"{bc}%")
                                    c2.metric("용적률", f"{far}%")
                                break # 키 찾음 반복 종료
                                
                        except:
                            pass # XML 파싱 에러는 무시하고 다음 키 시도
                            
                except:
                    pass # 접속 에러는 무시하고 다음 키 시도

        if not success_flag:
            st.error("🚫 모든 열쇠(Encoding/Decoding)와 모든 문(주소)을 다 시도했으나 실패했습니다.")
            st.warning("가능성 1: 키가 발급된 지 1시간이 안 지났습니다. (가장 유력)")
            st.warning("가능성 2: 복사한 키에 공백이 있거나 완전히 다른 키입니다.")
