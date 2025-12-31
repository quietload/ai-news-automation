#!/usr/bin/env python3
"""
구독/좋아요 엔딩 이미지 생성 (1회용)
- Shorts용 (세로)
- Video용 (가로)
- gpt-image-1.5 사용
"""

import os
import requests
from pathlib import Path

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
OPENAI_API_BASE = "https://api.openai.com/v1"

output_dir = Path("assets")
output_dir.mkdir(exist_ok=True)

def generate_image(prompt: str, output_path: Path, size: str):
    """GPT Image 1.5로 이미지 생성"""
    response = requests.post(
        f"{OPENAI_API_BASE}/images/generations",
        headers={"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"},
        json={"model": "gpt-image-1.5", "prompt": prompt, "n": 1, "size": size, "quality": "high"},
        timeout=120
    )
    
    if response.status_code != 200:
        raise Exception(f"Image Error: {response.text}")
    
    data = response.json()["data"][0]
    
    # url 또는 b64_json 형식 처리
    if "url" in data:
        img_response = requests.get(data["url"], timeout=60)
        with open(output_path, 'wb') as f:
            f.write(img_response.content)
    elif "b64_json" in data:
        import base64
        img_data = base64.b64decode(data["b64_json"])
        with open(output_path, 'wb') as f:
            f.write(img_data)
    else:
        print(f"Response: {data}")
        raise Exception("Unknown response format")
    
    print(f"[OK] Saved: {output_path}")
    return output_path


# Shorts용 엔딩 (세로)
print("\n[1/2] Generating Shorts ending image (vertical)...")
shorts_prompt = """
Professional photograph of a YouTube engagement scene, vertical portrait format.
- Clean white marble desk with soft natural lighting from window
- Rose gold smartphone showing a blurred YouTube video
- Hand with thumb up gesture beside the phone (no face visible)
- Small golden notification bell icon decoration on desk
- Soft bokeh background, warm and inviting atmosphere
- Photorealistic, high-end product photography style
- NO text, NO words, NO logos
"""
generate_image(shorts_prompt, output_dir / "ending_shorts.png", "1024x1536")


# Video용 엔딩 (가로)
print("\n[2/2] Generating Video ending image (horizontal)...")
video_prompt = """
Professional photograph of a YouTube engagement scene, horizontal landscape format.
- Modern minimalist desk setup with soft studio lighting
- Large monitor displaying blurred video content
- Wooden desk with a decorative thumbs up sculpture on left side
- Golden bell notification icon decoration on right side
- Shallow depth of field, professional product photography
- Warm, welcoming color tones
- Photorealistic, cinematic quality
- NO text, NO words, NO logos
"""
generate_image(video_prompt, output_dir / "ending_video.png", "1536x1024")

print("\n" + "="*50)
print("[OK] Ending images created with gpt-image-1.5!")
print("  - assets/ending_shorts.png (1024x1536)")
print("  - assets/ending_video.png (1536x1024)")
print("="*50)
