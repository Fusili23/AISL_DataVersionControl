import subprocess
import os
import re

# --- CONFIGURATION (설정) ---
# 유튜브 링크 리스트 (여러 개일 경우 쉼표로 구분하여 나열)
URLS = [
    "https://www.youtube.com/watch?v=7WUmHuDQ4vI",
]

# 원하는 프레임레이트 (FPS)
TARGET_FPS = 30

# 원하는 해상도 (가로x세로)
TARGET_RES = "1920x1080"

# 앞부분 자를 시간 (초)
TRIM_START = 0

# 뒷부분 자를 시간 (초)
TRIM_END_OFFSET = 0

# 저장할 디렉토리 (기본값: 현재 디렉토리 ".")
OUTPUT_DIR = "."
# -----------------------------

def get_video_duration(input_file):
    """영상의 전체 길이를 초 단위로 반환"""
    cmd = [
        'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1', input_file
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    return float(result.stdout)

def sanitize_filename(filename):
    """파일명으로 사용할 수 없는 문자 제거"""
    return re.sub(r'[\\/*?:"<>|]', "", filename)




def check_dependencies():
    """필수 프로그램 설치 여부 확인 및 경고"""
    missing = []
    for tool in ['yt-dlp', 'ffmpeg', 'ffprobe']:
        try:
            subprocess.run([tool, '--version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        except FileNotFoundError:
            missing.append(tool)
    
    if missing:
        print("!" * 50)
        print("Warning: The following required tools are missing or not in PATH:")
        for tool in missing:
            print(f" - {tool}")
        print("\nPlease ensure yt-dlp, ffmpeg, and ffprobe are installed and configured correctly.")
        print("!" * 50)
        print("Continuing anyway, but errors are likely...")
        print("!" * 50)

def process_videos():
    check_dependencies()
    
    # 1. 설정값 사용
    print("--- 설정 확인 ---")
    print(f"URLs: {URLS}")
    print(f"Target FPS: {TARGET_FPS}")
    print(f"Target Resolution: {TARGET_RES}")
    print(f"Trim Start: {TRIM_START}s")
    print(f"Trim End Offset: {TRIM_END_OFFSET}s")
    print(f"Output Directory: {OUTPUT_DIR}")
    
    urls = URLS
    target_fps = TARGET_FPS
    target_res = TARGET_RES
    trim_start = float(TRIM_START)
    trim_end_offset = float(TRIM_END_OFFSET)
    output_dir = OUTPUT_DIR

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    for url in urls:
        url = url.strip()
        if not url: continue

        print(f"\n[작업 시작] {url}")

        # 2. yt-dlp를 이용한 원본 화질 다운로드
        # -f "bestvideo+bestaudio/best"는 원본 최고 화질을 가져옵니다.
        download_cmd = [
            'yt-dlp',
            '-f', 'bestvideo+bestaudio/best',
            '--merge-output-format', 'mp4',
            '-o', 'temp_video.%(ext)s',
            url
        ]
        
        try:
            subprocess.run(download_cmd, check=True)
            
            # 다운로드된 파일명 확인 (확장자가 다를 수 있음)
            temp_file = "temp_video.mp4"
            if not os.path.exists(temp_file):
                # mp4 외의 확장자로 받아졌을 경우 탐색
                for f in os.listdir('.'):
                    if f.startswith("temp_video"):
                        temp_file = f
                        break

            # 영상 제목 가져오기 (파일명용)
            title_cmd = ['yt-dlp', '--get-title', url]
            video_title = subprocess.run(title_cmd, stdout=subprocess.PIPE, text=True).stdout.strip()
            safe_title = sanitize_filename(video_title)
            output_file = os.path.join(output_dir, f"{safe_title}_processed.mp4")

            # 3. FFmpeg를 이용한 전처리 (FPS, 해상도, 트리밍)
            print(f"[전처리 중] {video_title}...")
            
            total_duration = get_video_duration(temp_file)
            duration_to_keep = total_duration - trim_start - trim_end_offset

            if duration_to_keep <= 0:
                print(f"오류: 자를 시간이 영상 길이보다 깁니다. {video_title} 건너뜀.")
                continue

            # 해상도 형식을 W:H 형태로 변환 (예: 1920x1080 -> 1920:1080)
            ffmpeg_res = target_res.replace('x', ':')

            ffmpeg_cmd = [
                'ffmpeg', '-y',
                '-ss', str(trim_start),               # 앞부분 자르기
                '-i', temp_file,                      # 입력 파일
                '-t', str(duration_to_keep),          # 유지할 길이
                '-vf', f"scale={ffmpeg_res},fps={target_fps}", # 해상도 및 FPS 조절
                '-c:v', 'libx264', '-crf', '18',      # 고화질 인코딩 설정
                '-c:a', 'aac', '-b:a', '192k',        # 오디오 설정
                output_file
            ]

            subprocess.run(ffmpeg_cmd, check=True)
            print(f"[완료] 저장됨: {output_file}")

            # 임시 파일 삭제
            os.remove(temp_file)

        except Exception as e:
            print(f"오류 발생 ({url}): {e}")

if __name__ == "__main__":
    process_videos()