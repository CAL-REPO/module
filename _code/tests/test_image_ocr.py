# -*- coding: utf-8 -*-
# Tests for ImageOCR

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'modules'))

import pytest
from PIL import Image, ImageDraw, ImageFont
import tempfile
import shutil
import json

from image_utils.services.image_ocr import ImageOCR


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
    
    # 테스트 이미지 생성 (텍스트 포함)
    test_image = Image.new('RGB', (400, 200), color='white')
    draw = ImageDraw.Draw(test_image)
    
    # 간단한 텍스트 추가 (OCR 테스트용)
    try:
        # 시스템 폰트 사용 시도
        font = ImageFont.truetype("arial.ttf", 40)
    except:
        # 기본 폰트 사용
        font = ImageFont.load_default()
    
    draw.text((50, 80), "HELLO WORLD 123", fill='black', font=font)
    
    test_image_path = input_dir / "test_text.jpg"
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


def test_image_ocr_basic_initialization(temp_dirs):
    """Test 1: ImageOCR 기본 초기화"""
    ocr = ImageOCR(
        source__path=str(temp_dirs['test_image']),
        provider__provider="paddle",
        provider__langs=["en"],
        provider__min_conf=0.5,
        save__save_copy=False,
        meta__save_meta=False,
        log__name="test_ocr",
        log__level="WARNING",
        log__handlers=[]
    )
    
    print(f"\n=== Test 1: Basic Initialization ===")
    print(f"OCR: {ocr}")
    print(f"Provider: {ocr.policy.provider.provider}")
    print(f"Languages: {ocr.policy.provider.langs}")
    
    assert ocr.policy.provider.provider == "paddle"
    assert ocr.policy.provider.langs == ["en"]
    assert ocr.policy.provider.min_conf == 0.5


@pytest.mark.skipif(True, reason="PaddleOCR 설치 필요 - 실제 테스트 시 주석 해제")
def test_image_ocr_run_basic(temp_dirs):
    """Test 2: OCR 실행 (기본)"""
    ocr = ImageOCR(
        source__path=str(temp_dirs['test_image']),
        provider__provider="paddle",
        provider__langs=["en"],
        provider__min_conf=0.3,
        save__save_copy=False,
        meta__save_meta=False,
        log__name="test_ocr",
        log__level="INFO",
        log__handlers=[]
    )
    
    result = ocr.run()
    
    print(f"\n=== Test 2: OCR Run Basic ===")
    print(f"Success: {result['success']}")
    print(f"OCR Items: {len(result['ocr_items'])}")
    
    if result['success']:
        for item in result['ocr_items']:
            print(f"  - Text: '{item.text}', Conf: {item.conf:.2f}")
    
    assert result['success'] is True
    assert 'ocr_items' in result
    assert isinstance(result['ocr_items'], list)


@pytest.mark.skipif(True, reason="PaddleOCR 설치 필요 - 실제 테스트 시 주석 해제")
def test_image_ocr_with_metadata(temp_dirs):
    """Test 3: OCR + Metadata 저장"""
    ocr = ImageOCR(
        source__path=str(temp_dirs['test_image']),
        provider__provider="paddle",
        provider__langs=["en"],
        save__save_copy=False,
        meta__save_meta=True,
        meta__directory=str(temp_dirs['meta']),
        log__name="test_ocr",
        log__level="INFO",
        log__handlers=[]
    )
    
    result = ocr.run()
    
    print(f"\n=== Test 3: OCR with Metadata ===")
    print(f"Success: {result['success']}")
    print(f"Meta Path: {result.get('meta_path')}")
    
    if result['success'] and result.get('meta_path'):
        meta_file = Path(result['meta_path'])
        assert meta_file.exists()
        
        with open(meta_file, 'r', encoding='utf-8') as f:
            meta = json.load(f)
        
        print(f"\n=== Metadata Content ===")
        print(json.dumps(meta, indent=2, ensure_ascii=False))
        
        assert 'ocr_items' in meta
        assert 'provider' in meta
        assert meta['provider']['name'] == 'paddle'


@pytest.mark.skipif(True, reason="PaddleOCR 설치 필요 - 실제 테스트 시 주석 해제")
def test_image_ocr_with_preprocessing(temp_dirs):
    """Test 4: OCR + 전처리 (리사이즈)"""
    # 큰 이미지 생성
    large_image = Image.new('RGB', (2000, 1000), color='white')
    draw = ImageDraw.Draw(large_image)
    
    try:
        font = ImageFont.truetype("arial.ttf", 80)
    except:
        font = ImageFont.load_default()
    
    draw.text((100, 400), "LARGE IMAGE TEXT", fill='black', font=font)
    
    large_image_path = temp_dirs['input'] / "large_text.jpg"
    large_image.save(large_image_path, quality=95)
    
    ocr = ImageOCR(
        source__path=str(large_image_path),
        provider__provider="paddle",
        provider__langs=["en"],
        preprocess__max_width=800,  # 리사이즈
        save__save_copy=False,
        meta__save_meta=False,
        log__name="test_ocr",
        log__level="INFO",
        log__handlers=[]
    )
    
    result = ocr.run()
    
    print(f"\n=== Test 4: OCR with Preprocessing ===")
    print(f"Original Size: {result['original_size']}")
    print(f"Preprocessed Size: {result['preprocessed_size']}")
    print(f"OCR Items: {len(result['ocr_items'])}")
    
    assert result['success'] is True
    assert result['original_size'][0] == 2000
    assert result['preprocessed_size'][0] == 800  # 리사이즈됨


@pytest.mark.skipif(True, reason="PaddleOCR 설치 필요 - 실제 테스트 시 주석 해제")
def test_image_ocr_with_postprocessing(temp_dirs):
    """Test 5: OCR + 후처리 (신뢰도 필터링, 특수문자 제거)"""
    ocr = ImageOCR(
        source__path=str(temp_dirs['test_image']),
        provider__provider="paddle",
        provider__langs=["en"],
        provider__min_conf=0.7,  # 높은 신뢰도만
        postprocess__strip_special_chars=True,
        postprocess__filter_alphanumeric=True,
        save__save_copy=False,
        meta__save_meta=False,
        log__name="test_ocr",
        log__level="INFO",
        log__handlers=[]
    )
    
    result = ocr.run()
    
    print(f"\n=== Test 5: OCR with Postprocessing ===")
    print(f"Success: {result['success']}")
    print(f"OCR Items (after filtering): {len(result['ocr_items'])}")
    
    for item in result['ocr_items']:
        print(f"  - Text: '{item.text}', Conf: {item.conf:.2f}")
        # 특수문자가 제거되었는지 확인
        assert not any(c in item.text for c in ['!', '@', '#', '$', '%', '^', '&', '*'])
    
    assert result['success'] is True


def test_image_ocr_with_pil_image(temp_dirs):
    """Test 6: PIL Image 객체로 직접 OCR (파일 없이)"""
    # PIL Image 생성
    test_image = Image.new('RGB', (300, 100), color='white')
    draw = ImageDraw.Draw(test_image)
    
    try:
        font = ImageFont.truetype("arial.ttf", 30)
    except:
        font = ImageFont.load_default()
    
    draw.text((50, 35), "DIRECT IMAGE", fill='black', font=font)
    
    ocr = ImageOCR(
        provider__provider="paddle",
        provider__langs=["en"],
        save__save_copy=False,
        meta__save_meta=False,
        log__name="test_ocr",
        log__level="WARNING",
        log__handlers=[]
    )
    
    # 주의: PaddleOCR가 설치되지 않았으면 실패
    # result = ocr.run(image=test_image)
    
    print(f"\n=== Test 6: OCR with PIL Image ===")
    print("OCR 초기화 완료 (PaddleOCR 필요 시 skipif로 테스트)")
    
    # 초기화만 확인
    assert ocr.policy.provider.provider == "paddle"


def test_image_ocr_config_override(temp_dirs):
    """Test 7: Config 오버라이드"""
    # 기본 config 파일 사용 + 오버라이드
    ocr = ImageOCR(
        source__path=str(temp_dirs['test_image']),
        provider__provider="paddle",
        provider__langs=["ch", "en"],  # 다국어
        provider__min_conf=0.6,
        preprocess__max_width=1000,
        postprocess__deduplicate_iou_threshold=0.8,
        save__save_copy=False,
        meta__save_meta=False,
        log__name="test_ocr_override",
        log__level="WARNING",
        log__handlers=[]
    )
    
    print(f"\n=== Test 7: Config Override ===")
    print(f"Provider: {ocr.policy.provider.provider}")
    print(f"Languages: {ocr.policy.provider.langs}")
    print(f"Min Conf: {ocr.policy.provider.min_conf}")
    print(f"Max Width: {ocr.policy.preprocess.max_width}")
    print(f"IoU Threshold: {ocr.policy.postprocess.deduplicate_iou_threshold}")
    
    assert ocr.policy.provider.langs == ["ch", "en"]
    assert ocr.policy.provider.min_conf == 0.6
    assert ocr.policy.preprocess.max_width == 1000
    assert ocr.policy.postprocess.deduplicate_iou_threshold == 0.8


def test_image_ocr_error_handling(temp_dirs):
    """Test 8: 에러 핸들링 (존재하지 않는 파일)"""
    ocr = ImageOCR(
        source__path="nonexistent_file.jpg",
        source__must_exist=False,  # 에러 발생하지 않도록
        provider__provider="paddle",
        save__save_copy=False,
        meta__save_meta=False,
        log__name="test_ocr_error",
        log__level="WARNING",
        log__handlers=[]
    )
    
    result = ocr.run()
    
    print(f"\n=== Test 8: Error Handling ===")
    print(f"Success: {result['success']}")
    print(f"Error: {result.get('error')}")
    
    assert result['success'] is False
    assert result['error'] is not None
    assert 'error' in result
