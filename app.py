import streamlit as st
import requests
import xml.etree.ElementTree as ET
import urllib3
import urllib.parse

# SSL 경고 무시 (접속 성공률 높임)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(page_title="부동산 신축 분석기 v7.3 (정밀진단)", layout="wide")

st.title("🏗️ 부동산 신축 사업성 분석기 v7.3")
st.markdown("---")
st.info("🔎 선생님의 마이페이지에 적힌 **[arLandUseInfoService]** 주소로 **[HTTPS]** 접속을 시도합니다.")

# --- 사이드바 ---
st.sidebar.header("🔑 키 입력")
# 선생님이 가진 키(056031f...)를 그대로 넣으세요.
user_key_input = st.sidebar.text_input("공공데이터포털 키", type="password")

# --- 메인 기능 ---
st.subheader("🔢 PNU 코드 입력")
pnu_input = st.text_input("PNU 코드 (19자리)", "1159010700100840008")

# --- [핵심 수정] 선생님 권한에 딱 맞춘 HTTPS 주소 ---
# 선생님 마이페이지에 적힌 End Point가 'arLandUseInfoService'입니다.
TARGET_API = {
    "name": "토지이용규제 (arLandUseInfo) - HTTPS 적용",
    "url": "https://apis.data.go.kr/1613000/arLandUseInfoService/getLandUseAttr"
}

if st.button("🚀 정밀 진단 시작"):
    if not user_key_input:
        st.error("👈 왼쪽 사이드바에 키를 입력해주세요!")
    else:
        st.write("CONNECTING... 서버와 통신을 시도합니다.")
        
        # 1. 키 처리 (공백 제거)
        raw_key = user_key_input.strip()
        
        # 2. 인코딩/디코딩 버전 모두 준비
        decoded_key = urllib.parse.unquote(raw_key) 
        encoded_key = urllib.parse.quote(decoded_key)
        
        keys_to_try = [decoded_key, encoded_key]
        success = False
        
        # 키 2가지 버전으로 시도
        for k in keys_to_try:
            # HTTPS 강제 적용 URL
            final_url = f"{TARGET_API['url']}?serviceKey={k}&pnu={pnu_input}&format=xml"
            
            try:
                # verify=False로 인증서 문제 우회
                res = requests.get(final_url, timeout=10, verify=False)
                
                # 결과 화면에 출력 (디버깅용)
                st.code(f"응답 코드: {res.status_code}\n응답 내용: {res.text[:300]}...", language="xml")

                if res.status_code == 200:
                    root = ET.fromstring(res.content)
                    header_msg = root.findtext(".//resultMsg")
                    
                    if header_msg and "NORMAL SERVICE" in header_msg:
                        st.success(f"🎉 **성공했습니다!** (HTTPS 접속 해결)")
                        
                        # 데이터 파싱
                        items = []
                        for elem in root.iter():
                            if elem.text and any(x in elem.text for x in ["지역", "지구", "구역"]):
                                items.append(elem.text)
                        
                        if items:
                            st.success(f"📜 조회 결과: {', '.join(list(set(items)))}")
                        else:
                            st.warning("접속은 성공했으나, 해당 PNU에 대한 규제 정보가 없습니다.")
                        success = True
                        break
                    else:
                        # 200 OK지만 에러 메시지가 온 경우
                        st.error(f"❌ 접속은 됐지만 거절당했습니다: {header_msg}")
                        if "SERVICE_KEY_IS_NOT_REGISTERED" in str(res.content):
                            st.warning("진단: 키는 맞는데 '등록되지 않음'으로 뜹니다. (서버 동기화 문제 가능성)")
                        elif "SERVICE_ACCESS_DENIED" in str(res.content):
                            st.warning("진단: 키는 맞는데 '접근 권한'이 없습니다. (활용신청 문제)")
            except Exception as e:
                st.error(f"⚠️ 통신 오류 발생: {e}")

        if not success:
            st.error("🚫 모든 시도가 실패했습니다. 위의 '응답 내용'을 확인해주세요.")

