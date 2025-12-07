import streamlit as st
import requests
import xml.etree.ElementTree as ET
import urllib3

# SSL 경고 무시
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(page_title="부동산 신축 분석기 v6.1 (규제우회)", layout="wide")

st.title("🏗️ 부동산 신축 사업성 분석기 v6.1")
st.markdown("---")
st.info("💡 팁: 이 버전은 선생님이 이미 가지고 계신 **'토지이용규제정보서비스'** 키를 사용합니다.")

# --- 사이드바 ---
st.sidebar.header("🔑 핵심 열쇠")
# 규제 서비스 키를 입력받습니다
reg_key = st.sidebar.text_input("토지이용'규제'정보 키 (Decoding)", type="password")

# --- 메인 기능: PNU 수동 입력 ---
st.subheader("🔢 분석할 땅의 PNU 코드를 입력하세요")
st.markdown("예시(사당동 84-8): **1159010700100840008**")

pnu_input = st.text_input("PNU 코드 (19자리)", "1159010700100840008")

if st.button("🚀 분석 시작"):
    if not reg_key:
        st.error("왼쪽 사이드바에 키를 입력해주세요!")
    elif len(pnu_input) != 19:
        st.error("PNU 코드는 정확히 19자리 숫자여야 합니다.")
    else:
        # --- [규제] 서비스 주소 사용 (arLandUseInfoService) ---
        # 이 서비스는 '행위제한' 정보를 주지만, 그 안에 '용도지역'도 포함되어 있습니다.
        url = "http://apis.data.go.kr/1613000/arLandUseInfoService/getLandUseAttr"
        
        clean_key = reg_key.strip()
        final_url = f"{url}?serviceKey={clean_key}&pnu={pnu_input}&format=xml"
        
        try:
            res = requests.get(final_url, timeout=10, verify=False)
            
            if res.status_code == 200:
                try:
                    root = ET.fromstring(res.content)
                    header_msg = root.findtext(".//resultMsg")
                    
                    if header_msg and "NORMAL SERVICE" not in header_msg:
                        st.error(f"🏛️ 정부 서버 거부: {header_msg}")
                        if "SERVICE KEY" in header_msg:
                            st.warning("💡 키가 잘못되었거나 아직 등록 중입니다.")
                    else:
                        # --- 데이터 찾기 (규제 서비스 태그: lnduseAttrNm) ---
                        target_area = "정보 없음"
                        found_list = []
                        
                        items = root.findall(".//lnduseAttrNm")
                        for item in items:
                            if item.text:
                                text = item.text
                                found_list.append(text)
                                # 핵심 용도지역 찾기 로직
                                if "종" in text and "주거" in text: # 예: 제2종일반주거지역
                                    target_area = text
                                elif "상업" in text and "지역" in text: # 예: 일반상업지역
                                    target_area = text
                                elif "준주거" in text:
                                    target_area = text
                        
                        if target_area != "정보 없음":
                            st.success(f"✅ 조회 성공! 핵심 용도지역: **[{target_area}]**")
                            
                            # 자동 계산 로직
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
                            
                        else:
                            st.warning("데이터는 가져왔으나, 명확한 '용도지역(주거/상업)' 글자가 안 보입니다.")
                            # 혹시 모르니 전체 목록 보여주기
                            st.info(f"📜 발견된 규제 목록: {', '.join(found_list)}")
                            
                except ET.ParseError:
                    st.error("데이터 해석 실패 (XML 오류)")
                    st.code(res.text)
            else:
                st.error(f"접속 오류 코드: {res.status_code}")
                
        except Exception as e:
            st.error(f"시스템 오류: {e}")
