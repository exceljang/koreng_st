import streamlit as st
import pandas as pd
import os
import asyncio
import edge_tts
import time
import base64
import subprocess

async def get_voices():
    voices = await edge_tts.list_voices()
    return voices

async def speak_text(text, voice, rate):
    # WAV 형식으로 직접 저장
    communicate = edge_tts.Communicate(text, voice, rate=rate)
    temp_file = "temp.wav"
    
    # Edge TTS 명령어로 직접 WAV 생성
    cmd = f'edge-tts --voice "{voice}" --rate "{rate}" --text "{text}" --write-media {temp_file}'
    subprocess.run(cmd, shell=True)
    
    # WAV 파일 읽기
    with open(temp_file, "rb") as audio_file:
        audio_bytes = audio_file.read()
    
    # 임시 파일 삭제
    os.remove(temp_file)
    
    return audio_bytes

def autoplay_audio(audio_bytes):
    b64 = base64.b64encode(audio_bytes).decode()
    md = f"""
        <audio autoplay="true" onended="this.remove();">
            <source src="data:audio/wav;base64,{b64}" type="audio/wav">
        </audio>
    """
    st.markdown(md, unsafe_allow_html=True)

def calculate_duration(text, speed_option):
    # 한글은 글자당 약 0.25초, 영어는 글자당 약 0.12초로 조정
    korean_chars = sum(1 for c in text if ord('가') <= ord(c) <= ord('힣'))
    other_chars = len(text) - korean_chars
    duration = (korean_chars * 0.25) + (other_chars * 0.12) + 0.5
    return duration / 2 if speed_option == "2x" else duration

def main():
    st.set_page_config(page_title="Language Learning App")
    st.subheader("Language Learning App")

    # 상태 초기화
    if 'current_index' not in st.session_state:
        st.session_state.current_index = 0
    if 'current_subject' not in st.session_state:
        st.session_state.current_subject = None
    if 'speed' not in st.session_state:
        st.session_state.speed = "+0%"
    if 'is_playing' not in st.session_state:
        st.session_state.is_playing = False

    # 음성 목록
    voices = asyncio.run(get_voices())
    korean_voices = [voice for voice in voices if voice["Locale"] == "ko-KR"]
    english_voices = [voice for voice in voices if voice["Locale"] == "en-US"]

    # 사이드바
    with st.sidebar:
        st.header("Settings")
        korean_voice = st.selectbox(
            "Korean Voice",
            options=[voice["ShortName"] for voice in korean_voices],
            format_func=lambda x: f"{x} ({[v for v in korean_voices if v['ShortName'] == x][0]['FriendlyName']})"
        )
        english_voice = st.selectbox(
            "English Voice",
            options=[voice["ShortName"] for voice in english_voices],
            format_func=lambda x: f"{x} ({[v for v in english_voices if v['ShortName'] == x][0]['FriendlyName']})"
        )
        speed_option = st.radio("Speed", ["1x", "2x"], horizontal=True)
        st.session_state.speed = "+0%" if speed_option == "1x" else "+100%"
        repeat = st.checkbox("Repeat")

    # 엑셀 파일 로드
    if os.path.exists('KorengPro.xlsx'):
        excel_file = pd.ExcelFile('KorengPro.xlsx')
        sheets = {}
        for sheet_name in excel_file.sheet_names:
            df = pd.read_excel(excel_file, sheet_name=sheet_name)
            df = df.iloc[:, [1, 2]]
            df.columns = ['Korean', 'English']
            sheets[sheet_name] = df
    else:
        st.error("KorengPro.xlsx 파일을 찾을 수 없습니다.")
        return

    # 주제 선택
    st.subheader("Subject")
    subjects = [
        ["Sleep", "Morning", "Cooking", "Cleaning", "Go out"],
        ["Clinic", "Meeting", "Shopping", "Daily1", "Daily2"]
    ]

    for row in subjects:
        cols = st.columns(5)
        for col, subject in zip(cols, row):
            with col:
                if st.button(subject, key=f"btn_{subject}", use_container_width=True):
                    st.session_state.current_subject = subject
                    st.session_state.current_index = 0
                    st.session_state.is_playing = False  # 자동 재생 방지

    # 현재 선택된 주제 표시
    if st.session_state.current_subject and st.session_state.current_subject in sheets:
        current_data = sheets[st.session_state.current_subject]
        total_sentences = len(current_data)
        current_row = current_data.iloc[st.session_state.current_index]

        # 고정된 텍스트 영역
        st.markdown("#### Korean")
        korean_text = st.empty()
        korean_text.markdown(f"""
            <div style='text-align: center; font-size: 18px; padding: 10px; 
            background-color: #f0f2f6; border-radius: 5px; margin: 5px 0; min-height: 60px;'>
                {current_row['Korean'] if st.session_state.is_playing else ''}
            </div>
        """, unsafe_allow_html=True)

        st.markdown("#### English")
        english_text = st.empty()
        english_text.markdown(f"""
            <div style='text-align: center; font-size: 18px; padding: 10px; 
            background-color: #f0f2f6; border-radius: 5px; margin: 5px 0; min-height: 60px;'>
                {''}
            </div>
        """, unsafe_allow_html=True)

        # 컨트롤 버튼
        col1, col2, col3 = st.columns([1,1,1])
        with col1:
            if st.button("START", key="start_btn"):
                st.session_state.is_playing = True
                # START 버튼 클릭 시 한국어 텍스트 표시
                korean_text.markdown(f"""
                    <div style='text-align: center; font-size: 18px; padding: 10px; 
                    background-color: #f0f2f6; border-radius: 5px; margin: 5px 0; min-height: 60px;'>
                        {current_row['Korean']}
                    </div>
                """, unsafe_allow_html=True)
        with col2:
            if st.button("STOP", key="stop_btn"):
                st.session_state.is_playing = False
                # STOP 버튼 클릭 시 텍스트 영역 비우기
                korean_text.markdown(f"""
                    <div style='text-align: center; font-size: 18px; padding: 10px; 
                    background-color: #f0f2f6; border-radius: 5px; margin: 5px 0; min-height: 60px;'>
                        {''}
                    </div>
                """, unsafe_allow_html=True)
                english_text.markdown(f"""
                    <div style='text-align: center; font-size: 18px; padding: 10px; 
                    background-color: #f0f2f6; border-radius: 5px; margin: 5px 0; min-height: 60px;'>
                        {''}
                    </div>
                """, unsafe_allow_html=True)
        with col3:
            if st.button("RESET", key="reset_btn"):
                st.session_state.current_index = 0
                st.session_state.is_playing = False
                # RESET 버튼 클릭 시 텍스트 영역 비우기
                korean_text.markdown(f"""
                    <div style='text-align: center; font-size: 18px; padding: 10px; 
                    background-color: #f0f2f6; border-radius: 5px; margin: 5px 0; min-height: 60px;'>
                        {''}
                    </div>
                """, unsafe_allow_html=True)
                english_text.markdown(f"""
                    <div style='text-align: center; font-size: 18px; padding: 10px; 
                    background-color: #f0f2f6; border-radius: 5px; margin: 5px 0; min-height: 60px;'>
                        {''}
                    </div>
                """, unsafe_allow_html=True)

        # 진행 상황
        st.progress(st.session_state.current_index / (total_sentences - 1))
        st.text(f"{st.session_state.current_index + 1} / {total_sentences}")

        # 오디오 플레이어를 위한 컨테이너
        audio_placeholder = st.empty()

        # 자동 재생
        if st.session_state.is_playing:
            try:
                with audio_placeholder.container():
                    # 한국어 재생
                    korean_audio = asyncio.run(speak_text(current_row['Korean'], korean_voice, st.session_state.speed))
                    autoplay_audio(korean_audio)
                    time.sleep(calculate_duration(current_row['Korean'], speed_option))
                    
                    # 영어 텍스트 표시 및 재생
                    english_text.markdown(f"""
                        <div style='text-align: center; font-size: 18px; padding: 10px; 
                        background-color: #f0f2f6; border-radius: 5px; margin: 5px 0; min-height: 60px;'>
                            {current_row['English']}
                        </div>
                    """, unsafe_allow_html=True)
                    
                    english_audio = asyncio.run(speak_text(current_row['English'], english_voice, st.session_state.speed))
                    autoplay_audio(english_audio)
                    time.sleep(calculate_duration(current_row['English'], speed_option))

                # 다음 문장으로 이동
                if st.session_state.current_index < total_sentences - 1:
                    st.session_state.current_index += 1
                elif repeat:
                    st.session_state.current_index = 0
                else:
                    st.session_state.is_playing = False

                audio_placeholder.empty()
                time.sleep(0.005)
                st.rerun()

            except Exception as e:
                st.error(f"음성 재생 오류: {str(e)}")
                st.session_state.is_playing = False

if __name__ == "__main__":
    main() 