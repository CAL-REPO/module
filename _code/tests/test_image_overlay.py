# -*- coding: utf-8 -*-
# Tests for ImageOverlay

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'modules'))

import pytest
from PIL import Image, ImageDraw
import tempfile
import shutil
import json

from image_utils.services.image_overlay import ImageOverlay
from image_utils.core.policy import OverlayItemPolicy, FontPolicy


@pytest.fixture
def temp_dirs():
    """임시 디렉토리 생성"""
    temp_base = Path(tempfile.mkdtemp())
    input_dir = temp_base / "input"
    output_dir = temp_base / "output"
    meta_dir = temp_base / "meta"
    
    input_dir.mkdir(parents=True)
    output_dir.mkdir(parents=True)
    meta_dir.mkdir(parents=True)
    
    # 테스트 이미지 생성 (단색 배경)
    test_image = Image.new('RGB', (400, 300), color='white')
    test_image_path = input_dir / "base_image.jpg"
    test_image.save(test_image_path, quality=95)
    
    yield {
        'base': temp_base,
        'input': input_dir,
        'output': output_dir,
        'meta': meta_dir,
        'test_image': test_image_path
    }
    
    # 정리
    shutil.rmtree(temp_base)


def test_image_overlay_basic_initialization(temp_dirs):
    """Test 1: ImageOverlay 기본 초기화"""
    overlay = ImageOverlay(
        source__path=str(temp_dirs['test_image']),
        items=[],
        save__save_copy=False,
        meta__save_meta=False,
        log__name="test_overlay",
        log__level="WARNING",
        log__handlers=[]
    )
    
    print(f"\n=== Test 1: Basic Initialization ===")
    print(f"Overlay: {overlay}")
    print(f"Source: {overlay.policy.source.path}")
    print(f"Items: {len(overlay.policy.items)}")
    
    assert str(overlay.policy.source.path) == str(temp_dirs['test_image'])
    assert len(overlay.policy.items) == 0


def test_image_overlay_single_text(temp_dirs):
    """Test 2: 단일 텍스트 오버레이"""
    # PIL Image 생성
    base_image = Image.new('RGB', (400, 300), color='lightblue')
    
    # 오버레이 아이템 생성
    items = [
        OverlayItemPolicy(
            text="HELLO WORLD",
            polygon=[(50, 100), (350, 100), (350, 200), (50, 200)],
            font=FontPolicy(
                size=40,
                fill="#FFFFFF",
                stroke_fill="#000000",
                stroke_width=2
            ),
            anchor="mm"
        )
    ]
    
    overlay = ImageOverlay(
        source__path=str(temp_dirs['test_image']),
        items=items,
        save__save_copy=True,
        save__directory=str(temp_dirs['output']),
        meta__save_meta=False,
        log__name="test_overlay",
        log__level="INFO",
        log__handlers=[]
    )
    
    result = overlay.run(
        source_path=temp_dirs['test_image'],
        image=base_image
    )
    
    print(f"\n=== Test 2: Single Text Overlay ===")
    print(f"Success: {result['success']}")
    print(f"Overlaid Items: {result['overlaid_items']}")
    print(f"Saved Path: {result.get('saved_path')}")
    
    assert result['success'] is True
    assert result['overlaid_items'] == 1
    assert result['image'] is not None
    assert result['image'].size == (400, 300)
    
    if result.get('saved_path'):
        saved_file = Path(result['saved_path'])
        assert saved_file.exists()


def test_image_overlay_multiple_texts(temp_dirs):
    """Test 3: 다중 텍스트 오버레이"""
    base_image = Image.new('RGB', (600, 400), color='white')
    
    # 여러 텍스트 아이템
    items = [
        OverlayItemPolicy(
            text="Title Text",
            polygon=[(50, 50), (550, 50), (550, 100), (50, 100)],
            font=FontPolicy(size=36, fill="#FF0000", stroke_width=0),
            anchor="mm"
        ),
        OverlayItemPolicy(
            text="Subtitle Text",
            polygon=[(50, 120), (550, 120), (550, 170), (50, 170)],
            font=FontPolicy(size=24, fill="#0000FF", stroke_width=0),
            anchor="mm"
        ),
        OverlayItemPolicy(
            text="Body Text",
            polygon=[(50, 200), (550, 200), (550, 350), (50, 350)],
            font=FontPolicy(size=18, fill="#000000", stroke_width=0),
            anchor="lt",
            offset=[10.0, 10.0]
        )
    ]
    
    overlay = ImageOverlay(
        source__path=str(temp_dirs['test_image']),
        items=items,
        save__save_copy=False,
        meta__save_meta=False,
        log__name="test_overlay",
        log__level="INFO",
        log__handlers=[]
    )
    
    result = overlay.run(
        source_path=temp_dirs['test_image'],
        image=base_image
    )
    
    print(f"\n=== Test 3: Multiple Texts ===")
    print(f"Success: {result['success']}")
    print(f"Overlaid Items: {result['overlaid_items']}")
    
    assert result['success'] is True
    assert result['overlaid_items'] == 3


def test_image_overlay_with_metadata(temp_dirs):
    """Test 4: Metadata 저장"""
    base_image = Image.new('RGB', (400, 300), color='lightgray')
    
    items = [
        OverlayItemPolicy(
            text="Test Text",
            polygon=[(100, 100), (300, 100), (300, 200), (100, 200)],
            font=FontPolicy(size=30, fill="#00FF00"),
            conf=0.95,
            lang="en"
        )
    ]
    
    overlay = ImageOverlay(
        source__path=str(temp_dirs['test_image']),
        items=items,
        save__save_copy=True,
        save__directory=str(temp_dirs['output']),
        meta__save_meta=True,
        meta__directory=str(temp_dirs['meta']),
        log__name="test_overlay",
        log__level="INFO",
        log__handlers=[]
    )
    
    result = overlay.run(
        source_path=temp_dirs['test_image'],
        image=base_image
    )
    
    print(f"\n=== Test 4: With Metadata ===")
    print(f"Success: {result['success']}")
    print(f"Meta Path: {result.get('meta_path')}")
    
    assert result['success'] is True
    assert result.get('meta_path') is not None
    
    # Metadata 파일 확인
    meta_file = Path(result['meta_path'])
    assert meta_file.exists()
    
    with open(meta_file, 'r', encoding='utf-8') as f:
        meta = json.load(f)
    
    print(f"\n=== Metadata Content ===")
    print(json.dumps(meta, indent=2, ensure_ascii=False))
    
    assert 'overlaid_items' in meta
    assert meta['overlaid_items'] == 1
    assert 'items' in meta
    assert len(meta['items']) == 1
    assert meta['items'][0]['text'] == "Test Text"
    assert meta['items'][0]['conf'] == 0.95
    assert meta['items'][0]['lang'] == "en"


def test_image_overlay_background_opacity(temp_dirs):
    """Test 5: 배경 투명도 설정"""
    base_image = Image.new('RGB', (400, 300), color='red')
    
    items = [
        OverlayItemPolicy(
            text="Semi-Transparent",
            polygon=[(50, 100), (350, 100), (350, 200), (50, 200)],
            font=FontPolicy(size=32, fill="#FFFFFF")
        )
    ]
    
    overlay = ImageOverlay(
        source__path=str(temp_dirs['test_image']),
        items=items,
        background_opacity=0.5,  # 50% 투명도
        save__save_copy=False,
        meta__save_meta=False,
        log__name="test_overlay",
        log__level="INFO",
        log__handlers=[]
    )
    
    result = overlay.run(
        source_path=temp_dirs['test_image'],
        image=base_image
    )
    
    print(f"\n=== Test 5: Background Opacity ===")
    print(f"Success: {result['success']}")
    print(f"Background Opacity: {overlay.policy.background_opacity}")
    
    assert result['success'] is True
    assert overlay.policy.background_opacity == 0.5


def test_image_overlay_no_items(temp_dirs):
    """Test 6: 아이템 없을 때 (빈 오버레이)"""
    base_image = Image.new('RGB', (400, 300), color='yellow')
    
    overlay = ImageOverlay(
        source__path=str(temp_dirs['test_image']),
        items=[],  # 빈 리스트
        save__save_copy=False,
        meta__save_meta=False,
        log__name="test_overlay",
        log__level="WARNING",
        log__handlers=[]
    )
    
    result = overlay.run(
        source_path=temp_dirs['test_image'],
        image=base_image
    )
    
    print(f"\n=== Test 6: No Items ===")
    print(f"Success: {result['success']}")
    print(f"Overlaid Items: {result['overlaid_items']}")
    
    assert result['success'] is True
    assert result['overlaid_items'] == 0
    assert result['image'] == base_image  # 원본 그대로


def test_image_overlay_load_from_file(temp_dirs):
    """Test 7: 파일에서 이미지 로드"""
    items = [
        OverlayItemPolicy(
            text="Loaded from File",
            polygon=[(50, 100), (350, 100), (350, 200), (50, 200)],
            font=FontPolicy(size=28, fill="#FF00FF")
        )
    ]
    
    overlay = ImageOverlay(
        source__path=str(temp_dirs['test_image']),
        items=items,
        save__save_copy=False,
        meta__save_meta=False,
        log__name="test_overlay",
        log__level="INFO",
        log__handlers=[]
    )
    
    # image=None으로 파일에서 로드
    result = overlay.run(
        source_path=temp_dirs['test_image'],
        image=None
    )
    
    print(f"\n=== Test 7: Load from File ===")
    print(f"Success: {result['success']}")
    print(f"Image Size: {result['image_size']}")
    print(f"Overlaid Items: {result['overlaid_items']}")
    
    assert result['success'] is True
    assert result['image_size'] == (400, 300)
    assert result['overlaid_items'] == 1


def test_image_overlay_with_stroke(temp_dirs):
    """Test 8: 텍스트 외곽선"""
    base_image = Image.new('RGB', (400, 300), color='navy')
    
    items = [
        OverlayItemPolicy(
            text="OUTLINED TEXT",
            polygon=[(50, 100), (350, 100), (350, 200), (50, 200)],
            font=FontPolicy(
                size=36,
                fill="#FFFF00",        # 노란색 텍스트
                stroke_fill="#000000",  # 검은색 외곽선
                stroke_width=3
            ),
            anchor="mm"
        )
    ]
    
    overlay = ImageOverlay(
        source__path=str(temp_dirs['test_image']),
        items=items,
        save__save_copy=True,
        save__directory=str(temp_dirs['output']),
        meta__save_meta=False,
        log__name="test_overlay",
        log__level="INFO",
        log__handlers=[]
    )
    
    result = overlay.run(
        source_path=temp_dirs['test_image'],
        image=base_image
    )
    
    print(f"\n=== Test 8: With Stroke ===")
    print(f"Success: {result['success']}")
    print(f"Saved Path: {result.get('saved_path')}")
    
    assert result['success'] is True
    assert result['overlaid_items'] == 1
    
    # 저장된 파일 확인
    if result.get('saved_path'):
        saved_image = Image.open(result['saved_path'])
        assert saved_image.size == (400, 300)


def test_image_overlay_error_handling(temp_dirs):
    """Test 9: 에러 핸들링 (존재하지 않는 파일)"""
    overlay = ImageOverlay(
        source__path="nonexistent.jpg",
        source__must_exist=False,
        items=[],
        save__save_copy=False,
        meta__save_meta=False,
        log__name="test_overlay_error",
        log__level="WARNING",
        log__handlers=[]
    )
    
    result = overlay.run(
        source_path="nonexistent.jpg",
        image=None
    )
    
    print(f"\n=== Test 9: Error Handling ===")
    print(f"Success: {result['success']}")
    print(f"Error: {result.get('error')}")
    
    assert result['success'] is False
    assert result['error'] is not None
