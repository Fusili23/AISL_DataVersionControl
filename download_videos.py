import csv
import subprocess
import os
import sys
from pathlib import Path

# 설정
YT_DLP_DIR = r"C:\Users\seung\Desktop\yt-dlp"
OUTPUT_DIR = r"D:\raw"
CSV_FILE = r"OpenDV-YouTube - OpenDV-YouTube.csv"
# 여러 계정의 쿠키 파일들 (순환 사용)
COOKIES_FILES = [
    r"cookies.txt",
    r"cookies2.txt",
    r"cookies3.txt"
]
START_ID = 400  # 103번부터 시작

# 경로 설정
yt_dlp_exe = os.path.join(YT_DLP_DIR, "yt-dlp.exe")
ffmpeg_exe = os.path.join(YT_DLP_DIR, "ffmpeg.exe")
ffprobe_exe = os.path.join(YT_DLP_DIR, "ffprobe.exe")

# 출력 디렉토리 확인
os.makedirs(OUTPUT_DIR, exist_ok=True)

def download_and_trim_video(video_id, url, start_trim, end_trim, output_filename, cookie_file):
    """
    영상을 다운로드하고 트리밍합니다.
    """
    try:
        print(f"\n{'='*60}")
        print(f"다운로드 시작: ID {video_id} - {output_filename}")
        print(f"URL: {url}")
        print(f"트림 설정: 시작 {start_trim}초, 끝 {end_trim}초")
        print(f"쿠키 파일: {cookie_file}")
        print(f"{'='*60}\n")
        
        # 임시 파일명
        temp_file = os.path.join(OUTPUT_DIR, f"temp_{video_id}.mp4")
        final_file = os.path.join(OUTPUT_DIR, f"{output_filename}.mp4")
        
        # 이미 다운로드된 파일이 있는지 확인
        if os.path.exists(final_file):
            print(f"✓ 이미 존재함: {final_file}")
            return True
        
        # yt-dlp로 전체 영상 다운로드 (Node.js 런타임 활성화)
        download_cmd = [
            yt_dlp_exe,
            "--ffmpeg-location", YT_DLP_DIR,
            "--cookies", cookie_file,  # 쿠키 파일 사용
            "--js-runtimes", f"node:C:\\Program Files\\nodejs\\node.exe",  # Node.js 런타임 명시적으로 활성화
            "-f", "bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4] / bv*+ba/b",  # 더 관대한 포맷 선택
            "-N", "16",  # 16개의 fragment를 병렬로 다운로드
            "-o", temp_file,
            url
        ]
        
        print("다운로드 중...")
        result = subprocess.run(download_cmd)
        
        if result.returncode != 0:
            print(f"✗ 다운로드 실패")
            return False
        
        print("✓ 다운로드 완료")
        
        # ffprobe로 영상 길이 구하기
        print("영상 길이 확인 중...")
        probe_cmd = [
            ffprobe_exe,
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            temp_file
        ]
        
        probe_result = subprocess.run(probe_cmd, capture_output=True, text=True)
        if probe_result.returncode != 0:
            print(f"✗ 영상 길이 확인 실패")
            if os.path.exists(temp_file):
                os.remove(temp_file)
            return False
        
        try:
            total_duration = float(probe_result.stdout.strip())
            end_time = total_duration - end_trim
            
            # 유효성 검사
            if end_time <= start_trim:
                print(f"✗ 트리밍 오류: 영상 길이({total_duration:.1f}초)가 너무 짧습니다. (시작: {start_trim}초, 끝: {end_trim}초 제거)")
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                return False
            
            print(f"  영상 길이: {total_duration:.1f}초")
            print(f"  트리밍 범위: {start_trim}초 ~ {end_time:.1f}초 (총 {end_time - start_trim:.1f}초)")
        except ValueError:
            print(f"✗ 영상 길이 파싱 실패")
            if os.path.exists(temp_file):
                os.remove(temp_file)
            return False
        
        # ffmpeg로 트리밍
        print("트리밍 중...")
        trim_cmd = [
            ffmpeg_exe,
            "-ss", str(start_trim),  # 시작 지점
            "-i", temp_file,
            "-to", str(end_time),  # 종료 시간 (전체 길이 - end_trim)
            "-c:v", "copy",  # 비디오 코덱 복사 (재인코딩 없음)
            "-c:a", "copy",  # 오디오 코덱 복사 (재인코딩 없음)
            final_file,
            "-y"  # 덮어쓰기
        ]
        
        result = subprocess.run(trim_cmd)
        
        if result.returncode != 0:
            print(f"✗ 트리밍 실패")
            # 임시 파일 삭제
            if os.path.exists(temp_file):
                os.remove(temp_file)
            return False
        
        print("✓ 트리밍 완료")
        
        # 임시 파일 삭제
        if os.path.exists(temp_file):
            os.remove(temp_file)
            print("✓ 임시 파일 삭제 완료")
        
        print(f"✓ 완료: {final_file}\n")
        return True
        
    except Exception as e:
        print(f"✗ 오류 발생: {str(e)}")
        return False

def main():
    """
    메인 함수: CSV 파일을 읽고 순차적으로 다운로드
    """
    try:
        # CSV 파일 읽기
        with open(CSV_FILE, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        # 사용 가능한 쿠키 파일 필터링
        available_cookies = [c for c in COOKIES_FILES if os.path.exists(c)]
        if not available_cookies:
            print("❌ 오류: 사용 가능한 쿠키 파일이 없습니다.")
            print(f"다음 중 하나를 생성하세요: {', '.join(COOKIES_FILES)}")
            sys.exit(1)
        
        print(f"총 {len(rows)}개의 영상 정보가 있습니다.")
        print(f"사용 가능한 쿠키 파일: {len(available_cookies)}개")
        print(f"{START_ID}번부터 다운로드를 시작합니다.\n")
        
        success_count = 0
        fail_count = 0
        skip_count = 0
        cookie_index = 0  # 쿠키 파일 순환 인덱스
        
        for row in rows:
            video_id = int(row['ID'])
            
            # START_ID보다 작으면 건너뛰기
            if video_id < START_ID:
                skip_count += 1
                continue
            
            url = row['Link']
            start_trim = int(float(row['Discarded Length at the Begininning (second)']))
            end_trim = int(float(row['Discarded Length at the Ending (second)']))
            
            # 출력 파일명 (ID를 파일명으로 사용)
            output_filename = f"{video_id:05d}"
            
            # 쿠키 파일 순환 (각 영상마다 다음 쿠키 사용)
            current_cookie = available_cookies[cookie_index % len(available_cookies)]
            cookie_index += 1
            
            # 다운로드 및 트리밍
            success = download_and_trim_video(
                video_id,
                url,
                start_trim,
                end_trim,
                output_filename,
                current_cookie
            )
            
            if success:
                success_count += 1
            else:
                fail_count += 1
        
        # 최종 결과 출력
        print(f"\n{'='*60}")
        print("다운로드 완료!")
        print(f"건너뛴 영상: {skip_count}개")
        print(f"성공: {success_count}개")
        print(f"실패: {fail_count}개")
        print(f"{'='*60}\n")
        
    except KeyboardInterrupt:
        print("\n\n사용자에 의해 중단되었습니다.")
        sys.exit(0)
    except Exception as e:
        print(f"\n오류 발생: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
