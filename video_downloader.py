import subprocess
import os
import re
import csv
import sys
import time

# --- CONFIGURATION (설정) ---
# CSV 파일 경로
CSV_FILE = "OpenDV-YouTube - OpenDV-YouTube.csv"

# 외부 도구 경로 (yt-dlp, ffmpeg, ffprobe가 있는 폴더)
TOOLS_DIR = r"C:\Users\seung\Desktop\yt-dlp"

# 저장할 디렉토리
OUTPUT_DIR = r"D:\raw"

# 다운로드 사이의 대기 시간 (초) - YouTube 속도 제한 방지
# 0 = 대기 없음, 30-60 = 권장 (YouTube 스로틀링 방지)
DELAY_BETWEEN_DOWNLOADS = 30

# === 다운로드 속도 최적화 설정 ===
# 동시 다운로드 fragment 수 (높을수록 빠름, 권장: 16)
CONCURRENT_FRAGMENTS = 16

# HTTP 청크 크기 (네트워크 최적화, 권장: 10M)
HTTP_CHUNK_SIZE = "10M"

# aria2c 외부 다운로더 사용 (설치 필요, 가장 빠름)
# aria2c 설치: https://github.com/aria2/aria2/releases
# True로 설정하면 aria2c 사용, False면 내장 다운로더 사용
USE_ARIA2C = True  # aria2c 설치 후 True로 변경
ARIA2C_PATH = r"C:\Users\seung\Desktop\yt-dlp\aria2-1.37.0-win-64bit-build1\aria2c.exe"
# ========================

# === YouTube 인증 설정 ===
# 대부분의 공개 YouTube 동영상은 쿠키 없이 다운로드 가능합니다.
# 비공개 또는 연령 제한 동영상의 경우에만 인증이 필요합니다.

# 옵션 1: 여러 쿠키 파일 사용 (권장 - 계정 간 로테이션으로 Rate Limit 방지)
# Chrome 확장 프로그램 "Get cookies.txt LOCALLY"로 여러 계정의 쿠키를 추출
# 각 계정마다 다른 파일명으로 저장 (예: youtube_cookies_account1.txt, youtube_cookies_account2.txt)
COOKIE_FILES = [
    "youtube_cookies.txt",
    # "youtube_cookies_account2.txt",  # 두 번째 계정 추가
    # "youtube_cookies_account3.txt",  # 세 번째 계정 추가
]
# None으로 설정하면 쿠키 사용 안 함: COOKIE_FILES = None

# 옵션 2: 브라우저에서 직접 쿠키 가져오기 (브라우저가 닫혀있어야 함)
# COOKIE_FILES를 None으로 설정하고 아래 브라우저 이름 사용
# 주의: Chrome의 쿠키 암호화 변경으로 인해 DPAPI 오류가 발생할 수 있습니다.
BROWSER_FOR_COOKIES = None  # chrome, firefox, edge 등 (None으로 설정하면 사용 안 함)
# ========================

# -----------------------------

def get_tool_path(tool_name):
    """도구의 전체 경로를 반환"""
    tool_path = os.path.join(TOOLS_DIR, f"{tool_name}.exe")
    if os.path.exists(tool_path):
        return tool_path
    
    # 설정된 경로에 없으면 시스템 PATH에서 찾기 시도
    return tool_name

def get_video_duration(input_file):
    """영상의 전체 길이를 초 단위로 반환"""
    ffprobe_cmd = get_tool_path('ffprobe')
    cmd = [
        ffprobe_cmd, '-v', 'error', '-show_entries', 'format=duration',
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
        tool_path = get_tool_path(tool)
        try:
            subprocess.run([tool_path, '--version'] if tool != 'ffmpeg' else [tool_path, '-version'], 
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        except FileNotFoundError:
            missing.append(tool)
    
    if missing:
        print("!" * 50)
        print("Warning: The following required tools are missing or not found in:")
        print(f" - {TOOLS_DIR}")
        for tool in missing:
            print(f" - {tool}")
        print("\nPlease ensure yt-dlp, ffmpeg, and ffprobe are installed and configured correctly.")
        print("!" * 50)
        print("Continuing anyway, but errors are likely...")
        print("!" * 50)

def process_single_video(video_id, url, trim_start, trim_end_offset, output_dir, cookie_index=0):
    """
    프로세스 단일 비디오
    Args:
        cookie_index: 사용할 쿠키 파일 인덱스 (여러 계정 로테이션용)
    Returns: True if video was downloaded, False if skipped
    """
    url = url.strip()
    if not url: return False

    output_file = os.path.join(output_dir, f"{video_id}.mp4")
    
    # 이미 다운로드된 파일 건너뛰기
    if os.path.exists(output_file):
        print(f"\n[건너뜀] ID: {video_id} - 이미 존재합니다: {output_file}")
        return False  # 다운로드 안 함

    print(f"\n[작업 시작] ID: {video_id}, URL: {url}")
    print(f" - Trim Start: {trim_start}s")
    print(f" - Trim End Offset: {trim_end_offset}s")

    # 1. yt-dlp를 이용한 원본 화질 다운로드
    temp_filename = f"temp_video_{video_id}"
    yt_dlp_cmd = get_tool_path('yt-dlp')
    
    download_cmd = [
        yt_dlp_cmd,
        '-f', 'bestvideo[height<=1080]+bestaudio/best[height<=1080]',  # 최대 1080p로 제한
        '--merge-output-format', 'mp4',
        '--ffmpeg-location', TOOLS_DIR, # yt-dlp가 ffmpeg를 찾을 수 있도록 설정
        '-N', str(CONCURRENT_FRAGMENTS),  # 동시 다운로드 fragment 수
        '--http-chunk-size', HTTP_CHUNK_SIZE,  # HTTP 청크 크기 최적화
        '--newline',  # 진행률을 새 줄로 표시 (총 속도와 % 표시)
        '--console-title',  # 터미널 창 제목에 진행률 표시 (% 및 속도)
    ]
    
    # aria2c 외부 다운로더 사용 (최고 속도)
    if USE_ARIA2C:
        aria2c_cmd = ARIA2C_PATH if ARIA2C_PATH else 'aria2c'
        download_cmd.extend([
            '--external-downloader', aria2c_cmd,
            '--external-downloader-args', 'aria2c:-x 16 -k 1M'
        ])
        print(f" - Using aria2c external downloader for maximum speed")
    
    
    # 쿠키 설정 추가 (계정 로테이션 지원)
    if COOKIE_FILES and len(COOKIE_FILES) > 0:
        # 여러 쿠키 파일 중 하나 선택 (로테이션)
        current_cookie = COOKIE_FILES[cookie_index % len(COOKIE_FILES)]
        if os.path.exists(current_cookie):
            download_cmd.extend(['--cookies', current_cookie])
            print(f" - Using cookie file [{cookie_index % len(COOKIE_FILES) + 1}/{len(COOKIE_FILES)}]: {current_cookie}")
        else:
            print(f" - WARNING: Cookie file not found: {current_cookie}")
    elif BROWSER_FOR_COOKIES:
        # 브라우저에서 직접 쿠키 가져오기 (브라우저 종료 필요)
        download_cmd.extend(['--cookies-from-browser', BROWSER_FOR_COOKIES])
        print(f" - Using cookies from browser: {BROWSER_FOR_COOKIES}")
    else:
        print(" - WARNING: No authentication method configured. Download may fail.")
    
    download_cmd.extend([
        '-o', f'{temp_filename}.%(ext)s',
        url
    ])
    
    # 다운로드 시도 (rate limit 감지 시 다음 계정으로 자동 전환)
    max_retries = len(COOKIE_FILES) if COOKIE_FILES else 1
    for retry_attempt in range(max_retries):
        try:
            current_cookie_index = (cookie_index + retry_attempt) % len(COOKIE_FILES) if COOKIE_FILES else 0
            
            # 재시도 시 쿠키 파일 업데이트
            if retry_attempt > 0 and COOKIE_FILES:
                # 이전 쿠키 제거
                for i in range(len(download_cmd)):
                    if download_cmd[i] == '--cookies':
                        download_cmd[i+1] = COOKIE_FILES[current_cookie_index]
                        print(f"\n[계정 전환] Rate limit 감지 - 다음 계정 시도 [{current_cookie_index + 1}/{len(COOKIE_FILES)}]: {COOKIE_FILES[current_cookie_index]}")
                        break
            
            subprocess.run(download_cmd, check=True, capture_output=True, text=True)
            break  # 성공 시 루프 종료
            
        except subprocess.CalledProcessError as e:
            # Rate limit 오류 확인
            error_output = e.stderr + e.stdout if e.stderr and e.stdout else ""
            if "rate-limited" in error_output.lower() or "try again later" in error_output.lower():
                if retry_attempt < max_retries - 1:
                    print(f"\n[경고] 계정 rate limit 감지 - 다음 계정으로 전환 중...")
                    continue  # 다음 계정으로 재시도
                else:
                    print(f"\n[오류] 모든 계정이 rate limit 상태입니다. 나중에 다시 시도하세요.")
                    return False
            else:
                # 다른 오류이면 바로 실패 처리
                print(f"다운로드 또는 처리 중 오류 발생 ({url}): {e}")
                if error_output:
                    print(f"오류 상세: {error_output[:500]}")  # 처음 500자만 출력
                return False
    
        
        # 다운로드된 파일명 확인
        temp_file = f"{temp_filename}.mp4"
        if not os.path.exists(temp_file):
             # 혹시나 다른 확장자로 받아졌을 경우를 대비해 확인 (yt-dlp가 병합 실패시 등)
             for f in os.listdir('.'):
                 if f.startswith(temp_filename):
                     temp_file = f
                     break

        if not os.path.exists(temp_file):
            print(f"오류: 다운로드된 파일을 찾을 수 없습니다. ({url})")
            return False

        # 2. FFmpeg를 이용한 전처리 (FPS, 해상도, 트리밍)
        print(f"[전처리 중] {output_file}...")
        
        try:
            total_duration = get_video_duration(temp_file)
            duration_to_keep = total_duration - trim_start - trim_end_offset
    
            if duration_to_keep <= 0:
                print(f"오류: 자를 시간이 영상 길이보다 깁니다. {video_id} 건너뜀.")
                # 임시 파일 삭제
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                return False
    
            ffmpeg_bin = get_tool_path('ffmpeg')
    
            # 트리밍만 수행 (재인코딩 없이 스트림 복사 - 매우 빠름)
            ffmpeg_cmd = [
                ffmpeg_bin, '-y',
                '-ss', str(trim_start),               # 앞부분 자르기
                '-i', temp_file,                      # 입력 파일
                '-t', str(duration_to_keep),          # 유지할 길이
                '-c', 'copy',                         # 스트림 복사 (재인코딩 안함)
                output_file
            ]
    
            subprocess.run(ffmpeg_cmd, check=True)
            print(f"[완료] 저장됨: {output_file}")
            
            # 임시 파일 삭제
            if os.path.exists(temp_file):
                os.remove(temp_file)
            
            return True  # 성공적으로 다운로드 및 처리 완료
        
        except Exception as e:
             print(f"FFmpeg 처리 중 오류 발생 ({video_id}): {e}")
             # 임시 파일 삭제
             if os.path.exists(temp_file):
                 os.remove(temp_file)
             return False


def process_videos():
    check_dependencies()
    
    if not os.path.exists(OUTPUT_DIR):
        print(f"생성: 출력 디렉토리 {OUTPUT_DIR}")
        os.makedirs(OUTPUT_DIR)

    if not os.path.exists(CSV_FILE):
        print(f"오류: CSV 파일을 찾을 수 없습니다: {CSV_FILE}")
        return

    print(f"--- 설정 확인 ---")
    print(f"CSV File: {CSV_FILE}")
    print(f"Output Directory: {OUTPUT_DIR}")
    print(f"Tools Directory: {TOOLS_DIR}")

    with open(CSV_FILE, mode='r', encoding='utf-8') as csvfile:
        reader = csv.reader(csvfile)
        header = next(reader) # 헤더 건너뛰기
        
        # 헤더 인덱스 확인 (혹시 모를 순서 변경 대비, 혹은 하드코딩)
        # ID: 0, Link: 4, StartTrim: 10, EndTrim: 11
        
        video_count = 0
        for row in reader:
            success = run_video_processing(row, cookie_index=video_count)
            if not success:
                continue
            
            video_count += 1
            
            # YouTube 스로틀링 방지를 위한 대기 (실제 다운로드 후에만)
            if DELAY_BETWEEN_DOWNLOADS > 0:
                print(f"\n[대기 중] YouTube 속도 제한 방지를 위해 {DELAY_BETWEEN_DOWNLOADS}초 대기...")
                for remaining in range(DELAY_BETWEEN_DOWNLOADS, 0, -1):
                    print(f"  남은 시간: {remaining}초", end='\r')
                    time.sleep(1)
                print()  # 새 줄

def run_video_processing(row, cookie_index=0):
    try:
        # CSV 컬럼 인덱스에 맞춰 데이터 추출
        video_id = row[0]
        # url = row[4]
        # User defined structure: 
        # ID,VideoID,Title,YouTuber,Link,Duration,Train / Val,Mini / Full Set,Nation or Area (Inferred by GPT),"State, Province, or City (Inferred by GPT and refined by human)",Discarded Length at the Begininning (second),Discarded Length at the Ending (second)
        
        url = row[4]
        trim_start = float(row[10])
        trim_end_offset = float(row[11])
        
        return process_single_video(video_id, url, trim_start, trim_end_offset, OUTPUT_DIR, cookie_index)
    except (ValueError, IndexError) as e:
        print(f"CSV 행 파싱 오류: {row} - {e}")
        return False

if __name__ == "__main__":
    process_videos()