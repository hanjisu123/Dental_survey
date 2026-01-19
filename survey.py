import streamlit as st
import pandas as pd
import os
from datetime import datetime
from PIL import Image
import re

# --- 1. 기본 설정 및 CSS 스타일링 ---
st.set_page_config(page_title="임상 유용성 평가 설문", layout="wide")

# [CSS] 스타일링 정의
st.markdown("""
<style>
    /* 1. 라디오 버튼 선택지 텍스트 (Original, Method A 등) 스타일 */
    div[class*="stRadio"] label p {
        font-size: 20px !important;
        font-weight: bold !important;
    }
    
    /* 2. 라디오 버튼 컨테이너 강제 중앙 정렬 */
    div[role="radiogroup"] {
        display: flex !important;
        justify-content: center !important; /* 내부 아이템 가운데 정렬 */
        width: 100% !important;
        gap: 60px !important; /* 선택지 사이 간격 */
    }

    /* 3. 라디오 버튼 위젯 자체의 마진 조정 */
    div[data-testid="stRadio"] {
        width: 100% !important;
        display: flex;
        justify-content: center !important;
        align-items: center !important;
        margin-top: 10px;
        margin-bottom: 20px;
    }
    
    /* 4. 이미지 캡션 크기 및 정렬 */
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
    .question-text {
        font-size: 18px;
        font-weight: 600;
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
    
    # 1. 정확한 매칭
    exact_path = os.path.join(folder_path, filename)
    if os.path.exists(exact_path):
        return Image.open(exact_path)
    
    # 2. 숫자 기반 매칭
    target_num = extract_number(filename)
    if os.path.exists(folder_path):
        for f in os.listdir(folder_path):
            if extract_number(f) == target_num and f.lower().endswith(('.png', '.jpg', '.jpeg')):
                return Image.open(os.path.join(folder_path, f))
    
    # 3. 실패 시 회색 박스
    return Image.new('RGB', (300, 300), color=(220, 220, 220))

def save_data():
    """데이터 CSV 저장"""
    df = pd.DataFrame([st.session_state.responses])
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    name = st.session_state.responses.get('Evaluator_Name', 'Unknown')
    filename = f"survey_result_{name}_{timestamp}.csv"
    df.to_csv(filename, index=False, encoding='utf-8-sig')
    return filename

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
        specialty = st.text_input("전문 과목")
        
        if st.form_submit_button("설문 시작하기"):
            if name and affiliation:
                st.session_state.responses['Evaluator_Name'] = name
                st.session_state.responses['Affiliation'] = affiliation
                st.session_state.responses['Experience'] = experience
                st.session_state.responses['Specialty'] = specialty
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

# [PAGE 3] PART 2. 종합 평가 (디자인 수정됨)
elif st.session_state.page == 'part2':
    st.header("PART 2. 종합 평가")
    st.info("모든 케이스를 검토하신 후, 기술적/임상적 측면에서 Method A와 B를 평가해 주십시오.")
    
    with st.form("part2_form"):
        # --- Method A ---
        st.subheader("1. [Method A] 평가")
        st.markdown("**1-1. 시각적 품질 및 재현성**")
        q1_a_1 = st.slider("1. 치아 표면의 반사광이 인위적이지 않고 자연스럽게 제거되었습니까?", 1, 5, 3)
        q1_a_2 = st.slider("2. 제거 후에도 치아의 구조 및 주변 잇몸 조직이 왜곡 없이 잘 보존되었습니까?", 1, 5, 3)
        q1_a_3 = st.slider("3. 치아 본연의 색상과 명도가 왜곡 없이 유지되었습니까?", 1, 5, 3)
        
        st.markdown("**1-2. 임상적 진단 유용성**")
        q1_a_4 = st.slider("4. 반사광에 가려졌던 충치나 미세 균열 등의 병변 식별이 용이해졌습니까?", 1, 5, 3)
        q1_a_5 = st.slider("5. 반사광으로 인한 오진 가능성을 줄이고 진단 정확도에 기여합니까?", 1, 5, 3)
        q1_a_6 = st.slider("6. 임상 적용 시 고품질 이미지 확보 시간을 단축할 것 같습니까?", 1, 5, 3)

        st.write("---")

        # --- Method B ---
        st.subheader("2. [Method B] 평가")
        st.markdown("**2-1. 시각적 품질 및 재현성**")
        q1_b_1 = st.slider("1. 치아 표면의 반사광이 인위적이지 않고 자연스럽게 제거되었습니까? (Method B)", 1, 5, 3)
        q1_b_2 = st.slider("2. 제거 후에도 치아의 구조 및 주변 잇몸 조직이 왜곡 없이 잘 보존되었습니까? (Method B)", 1, 5, 3)
        q1_b_3 = st.slider("3. 치아 본연의 색상과 명도가 왜곡 없이 유지되었습니까? (Method B)", 1, 5, 3)
        
        st.markdown("**2-2. 임상적 진단 유용성**")
        q1_b_4 = st.slider("4. 반사광에 가려졌던 충치나 미세 균열 등의 병변 식별이 용이해졌습니까? (Method B)", 1, 5, 3)
        q1_b_5 = st.slider("5. 반사광으로 인한 오진 가능성을 줄이고 진단 정확도에 기여합니까? (Method B)", 1, 5, 3)
        q1_b_6 = st.slider("6. 임상 적용 시 고품질 이미지 확보 시간을 단축할 것 같습니까? (Method B)", 1, 5, 3)

        st.write("---")

        # --- 종합 (수정된 디자인) ---
        st.subheader("3. 종합적 선호도 및 실무 도입 의사")
        
        # 3.1 질문 (텍스트 분리)
        st.markdown("""<p class="question-text">3.1 시각적 품질과 진단 유용성을 모두 고려했을 때, 가장 반사광이 잘 제거된 결과물은 무엇입니까?</p>""", unsafe_allow_html=True)
        final_pref = st.radio(
            "3.1_hidden_label",
            options=["Original", "Method A", "Method B"],
            horizontal=True,
            label_visibility="collapsed"
        )
        
        st.write("") # 간격

        # 3.2 이유
        st.markdown("""<p class="question-text">3.2 위 선택을 하신 결정적인 이유는 무엇입니까?</p>""", unsafe_allow_html=True)
        reason = st.text_area("3.2_hidden_label", label_visibility="collapsed", placeholder="예: 디테일 보존 우수, 이질감 없음 등")

        st.write("")

        # 3.3 도입 의향
        st.markdown("""<p class="question-text">3.3 해당 기술을 실제 진료에 도입하실 의향이 있습니까?</p>""", unsafe_allow_html=True)
        adoption = st.select_slider(
            "3.3_hidden_label",
            options=["매우 낮음", "낮음", "보통", "높음", "매우 높음"],
            value="보통",
            label_visibility="collapsed"
        )
        
        st.write("")

        # 4. 전문가 의견
        st.markdown("""<p class="question-text">4. 전문가 추가 의견</p>""", unsafe_allow_html=True)
        expert_opinion = st.text_area("4_hidden_label", label_visibility="collapsed", placeholder="자유롭게 의견을 남겨주세요.")
        
        st.write("")
        st.write("")
        
        # 제출 버튼
        if st.form_submit_button("설문 제출하기"):
            st.session_state.responses.update({
                "Method_A_Naturalness": q1_a_1, "Method_A_Structure": q1_a_2, "Method_A_Color": q1_a_3,
                "Method_A_Identify": q1_a_4, "Method_A_Accuracy": q1_a_5, "Method_A_Time": q1_a_6,
                "Method_B_Naturalness": q1_b_1, "Method_B_Structure": q1_b_2, "Method_B_Color": q1_b_3,
                "Method_B_Identify": q1_b_4, "Method_B_Accuracy": q1_b_5, "Method_B_Time": q1_b_6,
                "Final_Preference": final_pref, "Preference_Reason": reason,
                "Adoption_Intent": adoption, "Expert_Opinion": expert_opinion
            })
            st.session_state.page = 'finish'
            st.rerun()

# [PAGE 4] 종료
elif st.session_state.page == 'finish':
    st.balloons()
    st.title("설문에 참여해 주셔서 감사합니다.")
    try:
        filename = save_data()
        st.success(f"평가 결과가 성공적으로 저장되었습니다.\n파일명: {filename}")
        st.markdown("창을 닫으셔도 좋습니다.")
    except Exception as e:
        st.error(f"데이터 저장 중 오류가 발생했습니다: {e}")