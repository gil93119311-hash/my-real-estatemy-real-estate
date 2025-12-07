import streamlit as st
import requests
import xml.etree.ElementTree as ET
import urllib3

# SSL 경고 무시
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(page_title="부동산 신축 분석기 v7.0 (만능진단)", layout="wide")

st.title("🏗️ 부동산 신축 사업성 분석기 v7.0")
st.markdown("---")
st.info("🔎 선생님의 키가 어떤 서비스용인지 자동으로 찾아내는 '진단 모드'입니다.")

# --- 사이드바 ---
st.sidebar.header("🔑 키 입력")
user_key = st.sidebar.text_input("공공데이터포털 키 (Decoding)", type="password")

# --- 메인 기능: PNU 수동 입력 ---
st.subheader("🔢 분석할 땅의 PNU 코드를 입력하세요")
pnu_input = st.text_input("PNU 코드 (19자리)", "1159010700100840008")

# --- [핵심] 테스트할 주소 목록 ---
# 선생님이 가입했을 가능성이 높은 서비스 주소 4개를 모두 모았습니다.
API_CANDIDATES = [
    {
        "name": "1. 토지이용'계획' (NSLandUseInfoService) - 정석",
        "url": "http://apis.data.go.kr/1613000/NSLandUseInfoService/getLandUsePlanInfo"
    },
    {
        "name": "2. 토지이용'규제' (arLandUseInfoService) - 유력 후보",
        "url": "http://apis.data.go.kr/1613000/arLandUseInfoService/getLandUseAttr"
    },
    {
        "name": "3. 규제'법령' (LandUseRegulationInfoService)",
        "url": "http://apis.data.go.kr/1613000/LandUseRegulationInfoService/getLandUseRegulationInfo"
    },
    {
        "name": "4. 도시계획정보 (UrbanPlanningStatisticsService)",
        "url": "http://apis.data.go.kr/1613000/UrbanPlanningStatisticsService/getUrbanPlanningStatistics"
    }
]

if st.button("🚀 만능 진단 시작 (모든 주소 테스트)"):
    if not user_key:
        st.error("왼쪽 사이드바에 키를 입력해주세요!")
    else:
        clean_key = user_key.strip()
        st.write("🔍 진단을 시작합니다... (하나씩 접속 시도 중)")
        
        success_flag = False
        
        # 반복문으로 4개 주소 모두 테스트
        for api in API_CANDIDATES:
            target_url = f"{api['url']}?serviceKey={clean_key}&pnu={pnu_input}&format=xml"
            
            try:
                # 접속 시도
                res = requests.get(target_url, timeout=5, verify=False)
                
                # 결과 확인
                if res.status_code == 200:
                    # 200 OK가 떴다면, 내용물(XML) 확인
                    try:
                        root = ET.fromstring(res.content)
                        header_msg = root.findtext(".//resultMsg")
                        
                        # 에러 메시지가 없는지 확인 (NORMAL SERVICE 여부)
                        if header_msg and "NORMAL SERVICE" in header_msg:
                            st.success(f"🎉 찾았다! 선생님의 키는 **[{api['name']}]** 용입니다!")
                            success_flag = True
                            
                            # --- 데이터 파싱 및 결과 보여주기 ---
                            found_list = []
                            target_area = "정보 없음"
                            
                            # 모든 텍스트 긁어오기
                            for elem in root.iter():
                                if elem.text and len(elem.text) > 1:
                                    if any(x in elem.text for x in ["지역", "지구", "구역"]):
                                        found_list.append(elem.text)
                                        # 핵심 용도지역 추출
                                        if "종" in elem.text and "주거" in elem.text:
                                            target_area = elem.text
                                        elif "상업" in elem.text and "지역" in elem.text:
                                            target_area = elem.text

                            st.info(f"📜 조회된 정보: {', '.join(list(set(found_list)))}")
                            
                            if target_area != "정보 없음":
                                st.write(f"👉 **핵심 용도지역: {target_area}**")
                                # 자동 계산
                                bc, far = 60, 200
                                if "1종" in target_area: bc, far = 60, 150
                                elif "2종" in target_area: bc, far = 60, 200
                                elif "3종" in target_area: bc, far = 50, 250
                                elif "준주거" in target_area: bc, far = 60, 400
                                elif "상업" in target_area: bc, far = 60, 800
                                
                                c1, c2 = st.columns(2)
                                c1.metric("건폐율", f"{bc}%")
                                c2.metric("용적률", f"{far}%")
                            
                            break # 성공했으니 반복 중단
                        
                        else:
                            # 200은 떴지만 에러 메시지인 경우 (SERVICE KEY ERROR 등)
                            st.warning(f"⚠️ {api['name']} 접속은 됐으나 거부됨: {header_msg}")
                            
                    except:
                        st.warning(f"⚠️ {api['name']} : 데이터 해석 실패")
                        
                elif res.status_code == 404:
                    st.caption(f"❌ {api['name']} : 주소 없음 (404)")
                elif res.status_code == 500:
                    st.caption(f"❌ {api['name']} : 서버 내부 에러 (500) - 키 불일치 가능성")
            
            except Exception as e:
                st.caption(f"❌ {api['name']} : 접속 오류 ({e})")
        
        if not success_flag:
            st.error("🚫 모든 주소 테스트 실패.")
            st.markdown("""
            **가능한 원인:**
            1. 키가 아직 정부 서버에 등록되지 않음 (1시간 대기 필요)
            2. 키를 복사할 때 공백이 포함됨
            3. 아예 다른 서비스(예: 도로명주소, 건축물대장 등)를 신청하셨음
            """)
