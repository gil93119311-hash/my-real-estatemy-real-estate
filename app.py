import streamlit as st
import requests
import xml.etree.ElementTree as ET
import urllib3
import urllib.parse

# SSL 경고 무시 (접속 성공률 높임)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(page_title="부동산 신축 분석기 v7.7 (진짜 에러 확인)", layout="wide")

st.title("🏗️ 부동산 신축 사업성 분석기 v7.7")
st.markdown("---")
st.info("✅ 선생님의 마이페이지에 적힌 **[arLandUseInfoService]** (토지이용정보)로 접속합니다.")

# --- 사이드바 ---
st.sidebar.header("🔑 키 입력")
user_key_input = st.sidebar.text_input("공공데이터포털 키", type="password")

# --- 메인 기능 ---
st.subheader("🔢 PNU 코드 입력")
pnu_input = st.text_input("PNU 코드 (19자리)", "1159010700100840008")

# --- [핵심] 선생님 마이페이지 이미지와 똑같은 HTTPS 주소 ---
TARGET_URL = "https://apis.data.go.kr/1613000/arLandUseInfoService/getLandUseAttr"

if st.button("🚀 부동산 분석 시작"):
    if not user_key_input:
        st.error("👈 왼쪽 사이드바에 키를 입력해주세요!")
    else:
        st.write("데이터 조회 중...")
        
        # 1. 키 전처리
        raw_key = user_key_input.strip()
        decoded_key = urllib.parse.unquote(raw_key) 
        encoded_key = urllib.parse.quote(decoded_key)
        
        # 2. 시도할 키 조합 (디코딩, 인코딩)
        keys_to_try = [decoded_key, encoded_key]
        
        success = False
        last_error_msg = "" # 마지막 에러 메시지 저장용
        
        for k in keys_to_try:
            params = {
                "serviceKey": k,
                "pnu": pnu_input,
                "format": "xml",
                "numOfRows": "100"
            }
            
            try:
                # HTTPS 접속 시도 (verify=False로 인증서 에러 방지)
                response = requests.get(TARGET_URL, params=params, timeout=10, verify=False)
                
                if response.status_code == 200:
                    try:
                        root = ET.fromstring(response.content)
                        header_msg = root.findtext(".//resultMsg")
                        
                        if header_msg and "NORMAL SERVICE" in header_msg:
                            st.success("🎉 **성공!** 데이터 문이 열렸습니다.")
                            success = True
                            
                            # 데이터 파싱
                            items = []
                            target_area = "정보 없음"
                            
                            for item in root.iter("item"):
                                unm = item.findtext("landUseNm")
                                if unm:
                                    items.append(unm)
                                    if any(x in unm for x in ["주거", "상업", "공업"]):
                                        target_area = unm

                            if items:
                                st.info(f"📜 **조회 결과:** {', '.join(list(set(items)))}")
                                if target_area != "정보 없음":
                                    st.write(f"👉 **핵심 용도:** **{target_area}**")
                                    # 용적률 단순 예시
                                    far = 200
                                    if "3종" in target_area: far = 250
                                    elif "상업" in target_area: far = 800
                                    st.metric("예상 용적률", f"{far}%")
                            else:
                                st.warning("접속은 성공했으나, 해당 PNU에 대한 데이터가 비어있습니다.")
                            
                            break # 성공 시 반복 종료
                        else:
                            # 200 OK지만 거절된 경우 (에러 메시지 저장)
                            last_error_msg = header_msg
                            
                    except Exception as parse_err:
                        last_error_msg = f"데이터 해석 오류: {parse_err}"
                else:
                    last_error_msg = f"서버 접속 오류 (코드: {response.status_code})"
                    
            except Exception as e:
                last_error_msg = f"통신 오류: {e}"

        if not success:
            st.error("🚫 실패했습니다.")
            # 엉터리 추측 대신 실제 에러 메시지를 보여줍니다.
            st.code(f"서버 응답 메시지: {last_error_msg}")
            
            if "SERVICE_KEY_IS_NOT_REGISTERED" in str(last_error_msg):
                st.write("👉 진단: 키가 서버에 등록되지 않았습니다. (키값 자체의 문제일 수 있음)")
            elif "SERVICE_ACCESS_DENIED" in str(last_error_msg):
                st.write("👉 진단: 주소는 맞는데 권한이 없습니다. (활용신청 재확인 필요)")
            elif "LIMITED" in str(last_error_msg):
                st.write("👉 진단: 일일 트래픽 초과입니다.")
