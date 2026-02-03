import streamlit as st
import pandas as pd
import os
from datetime import datetime
from PIL import Image
import re
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- 1. 기본 설정 및 CSS 스타일링 ---
st.set_page_config(page_title="임상 유용성 평가 설문", layout="wide")

# [CSS] 스타일링 정의
st.markdown("""
<style>
    /* 1. 라디오 버튼 선택지 텍스트 스타일 */
    div[class*="stRadio"] label p {
        font-size: 18px !important;
        font-weight: bold !important;
    }
    
    /* 2. 라디오 버튼 컨테이너 (가로 정렬) */
    div[role="radiogroup"] {
        display: flex !important;
        justify-content: center !important;
        width: 100% !important;
        gap: 40px !important;
    }

    /* 3. 라디오 버튼 위젯 여백 */
    div[data-testid="stRadio"] {
        width: 100% !important;
        margin-top: 10px;
        margin-bottom: 20px;
    }
    
    /* 4. 캡션 스타일 */
    div[data-testid="caption"] {
        font-size: 16px !important;
        text-align: center !important;
    }
    
    /* 5. 버튼 스타일 */
    div.stButton > button {
        width: 100%;
        height: 50px; 
        font-size: 16px !important;
    }
    
    /* 6. PART 2 질문 텍스트 스타일 */
    .question-title {
        font-size: 18px;
        font-weight: 700;
        margin-top: 20px;
        margin-bottom: 5px;
        color: #ffffff;
    }
    .question-desc {
        font-size: 14px;
        color: #ffffff;
        margin-bottom: 10px;
    }
</style>
""", unsafe_allow_html=True)

# [설정] 최상위 이미지 폴더 경로
IMAGE_ROOT = "."

# 폴더 이름 매핑
FOLDER_NAMES = {
    "Original": "Original",
    "Method A": "Method A", 
    "Method B": "Method B"
}

# --- 2. 헬퍼 함수 ---

def extract_number(filename):
    """파일명에서 숫자만 추출"""
    numbers = re.findall(r'\d+', filename)
    return int(numbers[0]) if numbers else 0

def get_image_files():
    """Original 폴더 스캔 및 정렬"""
    original_path = os.path.join(IMAGE_ROOT, FOLDER_NAMES["Original"])
    
    if not os.path.exists(original_path):
        st.error(f"❌ 오류: '{original_path}' 폴더를 찾을 수 없습니다.")
        return []
    
    files = [f for f in os.listdir(original_path) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.tiff'))]
    files.sort(key=extract_number)
    return files

def load_image(filename, type_key):
    """이미지 로드 함수"""
    folder_name = FOLDER_NAMES[type_key]
    folder_path = os.path.join(IMAGE_ROOT, folder_name)
    exact_path = os.path.join(folder_path, filename)
    if os.path.exists(exact_path):
        return Image.open(exact_path)
    
    target_num = extract_number(filename)
    if os.path.exists(folder_path):
        for f in os.listdir(folder_path):
            if extract_number(f) == target_num and f.lower().endswith(('.png', '.jpg', '.jpeg')):
                return Image.open(os.path.join(folder_path, f))
    
    return Image.new('RGB', (300, 300), color=(220, 220, 220))

def save_data_to_google_sheet(response_dict):
    """구글 시트에 데이터 저장 (타임스탬프 맨 앞, 헤더 생성 제거)"""
    try:
        # 1. 구글 인증 및 시트 열기
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
        client = gspread.authorize(creds)
        sheet = client.open("Dental_Survey_Results").sheet1 

        # 2. 값(Value) 리스트 만들기
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        row_data = [
            timestamp,                                   # 1. 타임스탬프 (A열)
            response_dict.get('Evaluator_Name', ''),     # 2. 이름 (B열)
            response_dict.get('Affiliation', ''),        # 3. 소속 (C열)
            response_dict.get('Experience', ''),         # 4. 경력 (D열)
            response_dict.get('Specialty', '')           # 5. 전문 과목 (E열)
        ]

        # Case 1~50 선택값 (Method A/B)
        for i in range(1, 51):
            choice = response_dict.get(f'Case_{i}_Choice', '')
            row_data.append(choice)
            
        # Part 2 답변 값
        part2_keys = [
            "1-1_Anatomical_Detail", "1-2_Overmasking_Prevention",
            "2-1_Diagnostic_Efficiency", "2-2_Workflow_Predictability",
            "3-1_Bias_Elimination", "3-2_Scalability",
            "4-1_Final_Preference", "4-2_Adoption_Intent", "4-3_Expert_Opinion"
        ]
        for key in part2_keys:
            row_data.append(response_dict.get(key, ''))
            
        # [삭제됨] 마지막에 타임스탬프 추가하던 코드 삭제

        # 3. 데이터 추가 (헤더 확인 없이 바로 추가)
        sheet.append_row(row_data)
        return True, sheet.spreadsheet.url

    except Exception as e:
        return False, str(e)

# --- 3. 세션 상태 초기화 ---
if 'page' not in st.session_state: st.session_state.page = 'intro'
if 'responses' not in st.session_state: st.session_state.responses = {}
if 'current_index' not in st.session_state: st.session_state.current_index = 0
if 'file_list' not in st.session_state:
    st.session_state.file_list = get_image_files()

if not st.session_state.file_list:
    st.warning("⚠️ 이미지 파일이 발견되지 않았습니다.")
    st.stop()

TOTAL_CASES = len(st.session_state.file_list)

# --- 4. 페이지 구성 ---

# [PAGE 0] 인트로
if st.session_state.page == 'intro':
    st.title("구강카메라 치근단 이미지 내 반사광 제거 알고리즘의 임상적 유용성 평가")
    st.markdown("### 주관: 삼육대학교 (Sahmyook University)")
    
    st.info("""
    **[설문 목적]**
    본 설문은 치과 임상 진단의 정확도를 높이기 위해 개발된 알고리즘의 성능을 평가하기 위해 마련되었습니다.
    구강카메라 치근단 이미지의 반사광은 병변 식별을 방해하는 주요 요인입니다.
    본 연구는 이를 효과적으로 제거하여 임상 진단의 정확도를 개선하는 데 기여하고자 합니다.
    """)
    
    st.write("---")
    st.subheader("평가자 정보 입력")
    
    with st.form("info_form"):
        col1, col2 = st.columns(2)
        name = col1.text_input("성함")
        affiliation = col2.text_input("소속 병원/기관")
        experience = st.number_input("임상 경력 (년)", min_value=0, step=1)
        
        if st.form_submit_button("설문 시작하기"):
            if name and affiliation:
                st.session_state.responses['Evaluator_Name'] = name
                st.session_state.responses['Affiliation'] = affiliation
                st.session_state.responses['Experience'] = experience
                st.session_state.page = 'instruction'
                st.rerun()
            else:
                st.error("성함과 소속을 입력해주세요.")

# [PAGE 1] 안내사항
elif st.session_state.page == 'instruction':
    st.title("⚠️ 평가 전 안내사항")
    st.markdown("""
    ### 정확한 평가를 위해 디스플레이 설정을 확인해 주세요.
    1. **모니터 밝기**를 **최대**로 설정해 주시기 바랍니다.
    2. 주변 조명을 너무 밝지 않게 조절해 주시면 더욱 정확한 식별이 가능합니다.
    3. 설문은 **총 2개의 파트**로 진행됩니다.
       - **PART 1:** 케이스별 이미지 비교 평가
       - **PART 2:** 알고리즘 전반에 대한 종합 평가
    """)
    st.write("---")
    if st.button("준비 완료 (PART 1 시작)"):
        st.session_state.page = 'part1'
        st.rerun()

# [PAGE 2] PART 1. 케이스별 비교 평가
elif st.session_state.page == 'part1':
    idx = st.session_state.current_index
    current_case_num = idx + 1
    current_filename = st.session_state.file_list[idx]
    
    st.header(f"PART 1. 이미지 케이스 비교 평가 ({current_case_num}/{TOTAL_CASES})")
    st.markdown("""
    ##### 이미지를 확대하여 관찰하신 후, **Original과 비교하였을 때** 가장 반사광이 잘 제거된(자연스러운) 이미지를 선택해주세요.
    """)
    
    img_orig = load_image(current_filename, "Original")
    img_method_a = load_image(current_filename, "Method A")
    img_method_b = load_image(current_filename, "Method B")
    
    _, col1, _, col2, col3, _ = st.columns([0.5, 1.2, 0.1, 1.2, 1.2, 0.5])
    
    with col1: st.image(img_orig, caption="Original (기준)", use_container_width=True)
    with col2: st.image(img_method_a, caption="Method A", use_container_width=True)
    with col3: st.image(img_method_b, caption="Method B", use_container_width=True)
    
    st.write("---")
    
    choice = st.radio(
        label="결과 선택", 
        options=["Method A", "Method B", "크게 차이 없음"],
        key=f"q_{current_filename}",
        horizontal=True,
        label_visibility="collapsed"
    )
    
    st.write(""); st.write("")
    
    b_col1, b_space, b_col2 = st.columns([1, 8, 1])
    
    with b_col1:
        if idx > 0:
            if st.button("⬅️ 이전"):
                st.session_state.current_index -= 1
                st.rerun()

    with b_col2:
        is_last = (current_case_num == TOTAL_CASES)
        btn_text = "종합 평가로 ➡️" if is_last else "다음 ➡️"
        
        if st.button(btn_text):
            st.session_state.responses[f"Case_{current_case_num}_File"] = current_filename
            st.session_state.responses[f"Case_{current_case_num}_Choice"] = choice
            
            if not is_last:
                st.session_state.current_index += 1
                st.rerun()
            else:
                st.session_state.page = 'part2'
                st.rerun()

# [PAGE 3] PART 2. 종합 평가 (새로운 질문 적용)
elif st.session_state.page == 'part2':
    st.header("PART 2. 알고리즘 성능 및 임상적 가치 종합 평가")
    st.info("50개의 케이스를 모두 검토하신 결과를 바탕으로, 각 알고리즘이 지닌 치의학적 가치와 고충실도(High-fidelity) 데이터 확보 가능성에 대해 평가해 주십시오.")
    
    with st.form("part2_form"):
        # --- Section 1 ---
        st.subheader("1. 해부학적 무결성 및 재현성 (Anatomical Integrity & Fidelity)")
        
        st.markdown('<p class="question-title">1.1. 해부학적 세부 구조 보존</p>', unsafe_allow_html=True)
        st.markdown('<p class="question-desc">Method B는 반사광 제거 시 법랑질 특유의 질감이나 미세한 굴곡 등 해부학적 세부 사항을 왜곡 없이 유지합니까?</p>', unsafe_allow_html=True)
        q1_1 = st.select_slider(
            "1.1_label", 
            options=[1, 2, 3, 4, 5], 
            value=3, 
            label_visibility="collapsed",
            format_func=lambda x: f"{x}" if x in [2,3,4] else f"{x} ({'전혀 보존되지 않음' if x==1 else '매우 잘 보존됨'})"
        )
        
        st.markdown('<p class="question-title">1.2. 과도한 마스킹 방지</p>', unsafe_allow_html=True)
        st.markdown('<p class="question-desc">Method B는 정상적인 치아 조직 정보까지 손실시키는 과도한 마스킹(Over-masking) 문제를 효과적으로 해결했다고 판단하십니까?</p>', unsafe_allow_html=True)
        q1_2 = st.select_slider(
            "1.2_label", 
            options=[1, 2, 3, 4, 5], 
            value=3, 
            label_visibility="collapsed",
            format_func=lambda x: f"{x}" if x in [2,3,4] else f"{x} ({'전혀 그렇지 않음' if x==1 else '매우 그러함'})"
        )
        
        st.write("---")

        # --- Section 2 ---
        st.subheader("2. 임상적 예측 가능성 및 유용성 (Clinical Predictability & Utility)")
        
        st.markdown('<p class="question-title">2.1. 진단 및 판독 효율성</p>', unsafe_allow_html=True)
        st.markdown('<p class="question-desc">반사광에 의해 왜곡되지 않은 선명한 데이터가 임상가의 정확한 판독과 시계열적 추적 관찰(Longitudinal monitoring)에 실질적인 근거를 제공합니까?</p>', unsafe_allow_html=True)
        q2_1 = st.select_slider(
            "2.1_label", 
            options=[1, 2, 3, 4, 5], 
            value=3, 
            label_visibility="collapsed",
            format_func=lambda x: f"{x}" if x in [2,3,4] else f"{x} ({'전혀 기여하지 않음' if x==1 else '매우 크게 기여함'})"
        )

        st.markdown('<p class="question-title">2.2. 워크플로우 예측 가능성</p>', unsafe_allow_html=True)
        st.markdown('<p class="question-desc">정밀한 표면 데이터 복원이 CAD/CAM 기반 수복물 설계 시 오차를 최소화하고 예측 가능성(Predictability)을 높이는 데 유용합니까?</p>', unsafe_allow_html=True)
        q2_2 = st.select_slider(
            "2.2_label", 
            options=[1, 2, 3, 4, 5], 
            value=3, 
            label_visibility="collapsed",
            format_func=lambda x: f"{x}" if x in [2,3,4] else f"{x} ({'전혀 유용하지 않음' if x==1 else '매우 유용함'})"
        )

        st.write("---")

        # --- Section 3 ---
        st.subheader("3. 데이터 표준화 및 확장성 (Standardization & Scalability)")
        
        st.markdown('<p class="question-title">3.1. 사용자 편향(Observer Bias) 제거</p>', unsafe_allow_html=True)
        st.markdown('<p class="question-desc">Method B의 자동화 파이프라인이 수작업 마스킹 시 발생하는 사용자 편향을 제거하고 데이터의 객관적 신뢰성을 보장한다고 보십니까?</p>', unsafe_allow_html=True)
        q3_1 = st.select_slider(
            "3.1_label", 
            options=[1, 2, 3, 4, 5], 
            value=3, 
            label_visibility="collapsed",
            format_func=lambda x: f"{x}" if x in [2,3,4] else f"{x} ({'전혀 보장하지 않음' if x==1 else '매우 확실히 보장함'})"
        )

        st.markdown('<p class="question-title">3.2. 대규모 데이터 확장성</p>', unsafe_allow_html=True)
        st.markdown('<p class="question-desc">자동 전처리 공정이 향후 고도화된 진단 AI 학습을 위한 대규모 High-fidelity 데이터셋 확보에 도움이 될 것이라 판단하십니까?</p>', unsafe_allow_html=True)
        q3_2 = st.select_slider(
            "3.2_label", 
            options=[1, 2, 3, 4, 5], 
            value=3, 
            label_visibility="collapsed",
            format_func=lambda x: f"{x}" if x in [2,3,4] else f"{x} ({'전혀 필요하지 않음' if x==1 else '매우 필수적임'})"
        )

        st.write("---")

        # --- Section 4 ---
        st.subheader("4. 종합 결론")
        
        st.markdown('<p class="question-title">4.1. 최종 선호 알고리즘</p>', unsafe_allow_html=True)
        st.markdown('<p class="question-desc">모든 임상적/기술적 요소를 고려할 때 가장 우수하다고 판단되는 알고리즘은 무엇입니까?</p>', unsafe_allow_html=True)
        q4_1 = st.radio(
            "4.1_label",
            options=["Method A", "Method B"],
            horizontal=True,
            label_visibility="collapsed"
        )

        st.markdown('<p class="question-title">4.2. 실무 도입 의향</p>', unsafe_allow_html=True)
        st.markdown('<p class="question-desc">Method B를 실제 임상 현장이나 연구 데이터 정제 공정에 도입하실 의향이 있습니까?</p>', unsafe_allow_html=True)
        q4_2 = st.select_slider(
            "4.2_label",
            options=[1, 2, 3, 4, 5],
            value=3,
            label_visibility="collapsed",
            format_func=lambda x: f"{x}" if x in [2,3,4] else f"{x} ({'의사 전혀 없음' if x==1 else '매우 강한 의사 있음'})"
        )

        st.markdown('<p class="question-title">4.3. 전문가 정성 의견</p>', unsafe_allow_html=True)
        st.markdown('<p class="question-desc">Method B가 디지털 진단 및 맞춤형 수복물 제작에 기여할 것으로 기대되는 측면이나 보완점을 자유롭게 서술해 주십시오.</p>', unsafe_allow_html=True)
        expert_opinion = st.text_area("4.3_label", label_visibility="collapsed")
        
        st.write("")
        st.write("")
        
        # 제출 버튼
        if st.form_submit_button("설문 제출하기"):
            st.session_state.responses.update({
                "1-1_Anatomical_Detail": q1_1,
                "1-2_Overmasking_Prevention": q1_2,
                "2-1_Diagnostic_Efficiency": q2_1,
                "2-2_Workflow_Predictability": q2_2,
                "3-1_Bias_Elimination": q3_1,
                "3-2_Scalability": q3_2,
                "4-1_Final_Preference": q4_1,
                "4-2_Adoption_Intent": q4_2,
                "4-3_Expert_Opinion": expert_opinion
            })
            st.session_state.page = 'finish'
            st.rerun()

# [PAGE 4] 종료
elif st.session_state.page == 'finish':
    st.balloons()
    st.title("설문에 참여해 주셔서 감사합니다.")

    # 1. 저장 로직 실행
    if 'data_saved' not in st.session_state:
        with st.spinner("결과를 서버(구글 시트)에 저장 중입니다..."):
            # [수정 포인트] 함수가 값 2개를 반환하므로 변수 2개로 받아야 함 (Unpacking)
            is_success, result_msg = save_data_to_google_sheet(st.session_state.responses)
            
            if is_success:
                st.session_state.data_saved = True
                st.session_state.sheet_url = result_msg
            else:
                st.error(f"⚠️ 저장 중 문제가 발생했습니다: {result_msg}")

    # 2. 결과 화면 표시
    if st.session_state.get('data_saved'):
        st.success("✅ 설문 결과가 성공적으로 제출되었습니다!")
        # sheet_url이 있는지 확인 후 표시
        if 'sheet_url' in st.session_state:
            st.markdown(f"👉 **[저장된 구글 시트 바로가기]({st.session_state.sheet_url})**")
    
    st.markdown("창을 닫으셔도 좋습니다.")



