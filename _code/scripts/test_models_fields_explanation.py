# -*- coding: utf-8 -*-
"""Core Models 필드 설명 및 사용 예시

NormalizedItem, SavedArtifact, SaveSummary의
각 필드 역할과 실제 사용 패턴을 보여줍니다.
"""

from pathlib import Path

print("=" * 70)
print("Core Models 필드 설명")
print("=" * 70)

# ========================================
# 1. NormalizedItem
# ========================================
print("\n[1] NormalizedItem - Extract와 Save를 연결하는 중간 데이터 모델")
print("-" * 70)

from crawl_utils.core.models import NormalizedItem

# 예시 1: Rule 모드 (이미지)
item1 = NormalizedItem(
    kind="image",
    value="https://example.com/product.jpg",
    section="default",  # 현재 미사용
    name_hint=None,  # 현재 미사용
    extension=None,  # PostProcessor에서 추론
    metadata={
        "directory": "m:/output/images/{{runtime.cas_no}}",
        "name": "{{runtime.cas_no}}_{{item.index:03d}}",
        "ops": {
            "overwrite": True,
            "create_parents": True,
            "ensure_unique": False
        },
        "mode": "rule",
        "source_key": "images"
    },
    record_index=1,  # 1번째 record
    item_index=1     # 1번째 item
)

print(f"\n✅ Rule 모드 (이미지):")
print(f"  kind: {item1.kind}")
print(f"  value: {item1.value}")
print(f"  extension: {item1.extension} (None이면 PostProcessor가 추론)")
print(f"  metadata:")
print(f"    - directory: {item1.metadata['directory']}")
print(f"    - name: {item1.metadata['name']}")
print(f"    - ops: {item1.metadata['ops']}")
print(f"  index: record[{item1.record_index}], item[{item1.item_index}]")

# 예시 2: Auto 모드 (TypeInferencer 사용)
item2 = NormalizedItem(
    kind="image",
    value="https://example.com/photo.png",
    extension="png",  # TypeInferencer가 자동 추론
    metadata={
        "directory": "m:/output/auto",
        "name": "auto_{{item.index:03d}}",
        "ops": {"overwrite": True, "create_parents": True},
        "mode": "auto"
    },
    record_index=1,
    item_index=2
)

print(f"\n✅ Auto 모드 (이미지):")
print(f"  kind: {item2.kind}")
print(f"  extension: {item2.extension} (TypeInferencer가 추론)")
print(f"  metadata.mode: {item2.metadata['mode']}")

# 예시 3: 텍스트
item3 = NormalizedItem(
    kind="text",
    value="상품명: 사과",
    metadata={
        "directory": "m:/output/texts",
        "name": "title",
        "ops": {"overwrite": True, "create_parents": True}
    },
    record_index=1,
    item_index=1
)

print(f"\n✅ 텍스트:")
print(f"  kind: {item3.kind}")
print(f"  value: {item3.value}")

# ========================================
# 필드별 역할 정리
# ========================================
print("\n[필드별 역할]")
print("-" * 70)
print("""
📋 kind (ItemKind):
  - "image": 이미지 (URL 다운로드 또는 bytes 저장)
  - "text": 텍스트 (str 저장)
  - "file": 파일 (URL 다운로드 또는 bytes 저장)

📦 value (Any):
  - kind="image": URL (str) 또는 bytes
  - kind="text": 텍스트 내용 (str)
  - kind="file": URL (str) 또는 bytes

📁 section (str): 그룹화 용도 (현재 미사용)
  - 기본값: "default"
  - 향후: "main_images", "detail_images" 등

💡 name_hint (Optional[str]): 파일명 힌트 (현재 미사용)
  - Normalizer가 추출한 파일명 힌트
  - PostProcessor는 metadata["name"] 우선 사용

🔤 extension (Optional[str]): 파일 확장자
  - Auto 모드: TypeInferencer가 자동 추론 (.jpg, .png, .txt)
  - Rule 모드: None (PostProcessor에서 추론)
  - 우선순위: extension > _infer_extension(value) > kind 기본값

📊 metadata (Dict[str, Any]): 저장 정책 (PostProcessor용)
  - directory: 저장 디렉토리 (Jinja2 템플릿)
  - name: 파일명 (Jinja2 템플릿, 확장자 제외)
  - ops: FSO 작업 정책
    • overwrite: 덮어쓰기 (기본값: False)
    • create_parents: 부모 디렉토리 생성 (기본값: True)
    • ensure_unique: 중복 시 자동 번호 (기본값: True)
  - mode: "rule" 또는 "auto" (디버깅용)
  - source_key: 원본 KeyPath (Rule 모드만)

🔢 record_index (int): 몇 번째 record인지 (1-based)
  - Jinja2: {{item.record}}

🔢 item_index (int): record 내 몇 번째 item인지 (1-based)
  - Jinja2: {{item.index}}
  - explode=True로 리스트 분리 시 자동 증가
""")

# ========================================
# 2. SavedArtifact
# ========================================
print("\n[2] SavedArtifact - 파일 저장 결과")
print("-" * 70)

from crawl_utils.core.models import SavedArtifact

# 예시 1: 저장 성공
artifact1 = SavedArtifact(
    path=Path("m:/output/images/CAPEA-001_001.jpg"),
    item=item1,
    status="saved",
    detail=None
)

print(f"\n✅ 저장 성공:")
print(f"  path: {artifact1.path}")
print(f"  status: {artifact1.status}")
print(f"  detail: {artifact1.detail}")

# 예시 2: 건너뜀
artifact2 = SavedArtifact(
    path=Path(),  # 빈 경로
    item=item1,
    status="skipped",
    detail="No metadata"
)

print(f"\n⚠️ 건너뜀:")
print(f"  path: {artifact2.path} (빈 경로)")
print(f"  status: {artifact2.status}")
print(f"  detail: {artifact2.detail}")

# 예시 3: 실패
artifact3 = SavedArtifact(
    path=Path(),  # 빈 경로
    item=item1,
    status="failed",
    detail="HTTPError: 404 Not Found"
)

print(f"\n❌ 실패:")
print(f"  path: {artifact3.path} (빈 경로)")
print(f"  status: {artifact3.status}")
print(f"  detail: {artifact3.detail}")

print("\n[필드별 역할]")
print("-" * 70)
print("""
📂 path (Path):
  - status="saved": 실제 저장된 경로
  - status="skipped": Path() (빈 경로)
  - status="failed": Path() (빈 경로)

📦 item (NormalizedItem):
  - 원본 NormalizedItem (참조)
  - 실패 시 디버깅용

✅ status (Literal):
  - "saved": 성공적으로 저장됨
  - "skipped": 건너뜀 (metadata 없음, 조건 미충족)
  - "failed": 실패 (네트워크, 권한 오류 등)

💬 detail (Optional[str]):
  - status="saved": None 또는 "Downloaded 1.2MB"
  - status="skipped": "No metadata", "Empty value"
  - status="failed": 예외 메시지 (str(exc))
""")

# ========================================
# 3. SaveSummary
# ========================================
print("\n[3] SaveSummary - 파일 저장 결과 요약")
print("-" * 70)

from crawl_utils.core.models import SaveSummary

# 예시: 여러 kind 저장
summary = SaveSummary(
    artifacts={
        "image": [
            SavedArtifact(Path("m:/output/images/img1.jpg"), item1, "saved"),
            SavedArtifact(Path("m:/output/images/img2.jpg"), item2, "saved"),
            SavedArtifact(Path(), item1, "failed", "HTTPError: 404"),
        ],
        "text": [
            SavedArtifact(Path("m:/output/texts/title.txt"), item3, "saved"),
        ],
        "file": []
    }
)

print(f"\n✅ SaveSummary:")
print(f"  image: {len(summary['image'])} artifacts")
print(f"  text: {len(summary['text'])} artifacts")
print(f"  file: {len(summary['file'])} artifacts")

# flatten() 사용
all_artifacts = summary.flatten()
print(f"\n  flatten(): {len(all_artifacts)} total artifacts")

# 저장 성공한 파일만 추출
saved_paths = [a.path for a in summary.flatten() if a.status == "saved"]
print(f"\n  Saved files:")
for path in saved_paths:
    print(f"    • {path}")

# 실패한 항목 분석
failed = [(a.item.value, a.detail) for a in summary.flatten() if a.status == "failed"]
if failed:
    print(f"\n  Failed items:")
    for value, detail in failed:
        print(f"    • {value}: {detail}")

print("\n[필드별 역할]")
print("-" * 70)
print("""
📊 artifacts (Dict[str, List[SavedArtifact]]):
  - 구조: {"image": [...], "text": [...], "file": [...]}
  - kind별로 저장 결과 그룹화

🔧 flatten() -> List[SavedArtifact]:
  - 모든 artifact를 단일 리스트로 평탄화
  - 순서: image → text → file

🔍 __getitem__(kind) -> List[SavedArtifact]:
  - 특정 kind의 artifact만 조회
  - 예: summary["image"]
""")

# ========================================
# 4. 전체 흐름 예시
# ========================================
print("\n[4] 전체 흐름 예시")
print("-" * 70)
print("""
1️⃣ Extract (Dict):
   extracted_data = [
       {
           "title": "사과",
           "images": ["url1.jpg", "url2.jpg"],
           "price": 1000
       }
   ]

2️⃣ Normalize (NormalizedItem):
   normalizer = Normalizer(rules=[...])
   normalized_items = normalizer.normalize(extracted_data)
   
   # 결과: 3개 NormalizedItem
   [
       NormalizedItem(kind="text", value="사과", record_index=1, item_index=1),
       NormalizedItem(kind="image", value="url1.jpg", record_index=1, item_index=1),
       NormalizedItem(kind="image", value="url2.jpg", record_index=1, item_index=2)
   ]

3️⃣ Save (SavedArtifact):
   post_processor = SyncPostProcessor(runtime_context={...})
   save_summary = post_processor.save_many(normalized_items)
   
   # 결과: SaveSummary
   SaveSummary(
       artifacts={
           "text": [SavedArtifact(Path("title.txt"), ..., "saved")],
           "image": [
               SavedArtifact(Path("img_001.jpg"), ..., "saved"),
               SavedArtifact(Path("img_002.jpg"), ..., "saved")
           ]
       }
   )

4️⃣ 결과 분석:
   # 모든 저장 파일
   saved_paths = [a.path for a in save_summary.flatten() if a.status == "saved"]
   
   # 통계
   total = len(save_summary.flatten())
   saved = sum(1 for a in save_summary.flatten() if a.status == "saved")
   failed = sum(1 for a in save_summary.flatten() if a.status == "failed")
""")

print("\n" + "=" * 70)
print("✅ 모든 필드 설명 완료")
print("=" * 70)
