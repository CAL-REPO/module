# -*- coding: utf-8 -*-
# ImageLoader Integration Tests - Metadata & Save Copy 상세 검증

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'modules'))

import pytest
from PIL import Image
import tempfile
import shutil
import json

from image_utils.services.image_loader import ImageLoader


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
    
    # 테스트 이미지 생성
    test_image = Image.new('RGB', (200, 150), color='blue')
    test_image_path = input_dir / "sample_image.jpg"
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


def test_metadata_full_content(temp_dirs):
    """Test 1: Metadata 전체 내용 검증"""
    loader = ImageLoader(
        source__path=str(temp_dirs['test_image']),
        save__directory=str(temp_dirs['output']),
        save__save_copy=True,
        save__name__suffix="_processed",
        meta__save_meta=True,
        meta__directory=str(temp_dirs['meta']),
        log__name="test_integration",
        log__level="INFO",
        log__handlers=[]
    )
    result = loader.run()
    
    print(f"\n=== Test 1: Metadata Full Content ===")
    print(f"Success: {result['success']}")
    print(f"Saved Path: {result.get('saved_path')}")
    print(f"Meta Path: {result.get('meta_path')}")
    
    assert result['success'] is True
    assert 'saved_path' in result
    assert 'meta_path' in result
    
    # Metadata 파일 읽기
    meta_file = Path(result['meta_path'])
    assert meta_file.exists(), "Metadata 파일이 존재하지 않습니다"
    
    with open(meta_file, 'r', encoding='utf-8') as f:
        meta = json.load(f)
    
    print(f"\n=== Metadata Content ===")
    print(json.dumps(meta, indent=2, ensure_ascii=False))
    
    # 필수 필드 확인
    assert 'original_path' in meta, "original_path 필드가 없습니다"
    assert 'original_size' in meta, "original_size 필드가 없습니다"
    assert 'original_mode' in meta, "original_mode 필드가 없습니다"
    assert 'original_format' in meta, "original_format 필드가 없습니다"
    
    # 값 검증
    assert meta['original_size'] == [200, 150]
    assert meta['original_mode'] == 'RGB'
    assert Path(meta['original_path']).name == 'sample_image.jpg'


def test_save_copy_with_processing(temp_dirs):
    """Test 2: Save Copy + 이미지 처리 (resize, format 변경)"""
    loader = ImageLoader(
        source__path=str(temp_dirs['test_image']),
        save__directory=str(temp_dirs['output']),
        save__save_copy=True,
        save__format="PNG",
        save__name__suffix="_resized",
        process__resize_to=[100, 75],
        meta__save_meta=True,
        meta__directory=str(temp_dirs['meta']),
        log__name="test_integration",
        log__level="INFO",
        log__handlers=[]
    )
    result = loader.run()
    
    print(f"\n=== Test 2: Save Copy + Processing ===")
    print(f"Success: {result['success']}")
    print(f"Original Size: (200, 150)")
    print(f"Processed Size: {result['image'].size}")
    print(f"Saved Path: {result.get('saved_path')}")
    
    assert result['success'] is True
    
    # 처리된 이미지 크기 확인
    assert result['image'].size == (100, 75)
    
    # 저장된 파일 확인
    saved_path = Path(result['saved_path'])
    assert saved_path.exists()
    assert saved_path.suffix.lower() == '.png'
    assert '_resized' in saved_path.stem
    
    # 실제 저장된 이미지 읽어서 확인
    saved_image = Image.open(saved_path)
    assert saved_image.size == (100, 75)
    assert saved_image.format == 'PNG'
    
    # Metadata 확인
    meta_file = Path(result['meta_path'])
    with open(meta_file, 'r', encoding='utf-8') as f:
        meta = json.load(f)
    
    print(f"\n=== Processing Metadata ===")
    print(json.dumps(meta, indent=2, ensure_ascii=False))
    
    # Original vs Processed 정보 확인
    assert meta['original_size'] == [200, 150]
    if 'processed_size' in meta:
        assert meta['processed_size'] == [100, 75]


def test_multiple_save_with_counter(temp_dirs):
    """Test 3: 여러 번 저장 (suffix_counter 사용)"""
    saved_paths = []
    meta_paths = []
    
    for i in range(1, 4):  # 3번 저장
        loader = ImageLoader(
            source__path=str(temp_dirs['test_image']),
            save__directory=str(temp_dirs['output']),
            save__save_copy=True,
            save__name__suffix_counter=i,
            meta__save_meta=True,
            meta__directory=str(temp_dirs['meta']),
            log__name="test_integration",
            log__level="WARNING",
            log__handlers=[]
        )
        result = loader.run()
        
        assert result['success'] is True
        saved_paths.append(Path(result['saved_path']))
        meta_paths.append(Path(result['meta_path']))
    
    print(f"\n=== Test 3: Multiple Save with Counter ===")
    for i, (saved, meta) in enumerate(zip(saved_paths, meta_paths), 1):
        print(f"#{i} - Image: {saved.name}, Meta: {meta.name}")
        assert saved.exists()
        assert meta.exists()
    
    # 모든 파일이 다른지 확인
    assert len(set(saved_paths)) == 3, "이미지 파일명이 중복됩니다"
    assert len(set(meta_paths)) == 3, "메타 파일명이 중복됩니다"


def test_save_copy_false_no_file(temp_dirs):
    """Test 4: save_copy=False일 때 파일 생성되지 않음 확인"""
    loader = ImageLoader(
        source__path=str(temp_dirs['test_image']),
        save__directory=str(temp_dirs['output']),
        save__save_copy=False,  # 저장 안 함
        meta__save_meta=False,
        log__name="test_integration",
        log__level="WARNING",
        log__handlers=[]
    )
    result = loader.run()
    
    print(f"\n=== Test 4: Save Copy False ===")
    print(f"Success: {result['success']}")
    print(f"Has 'saved_path' key: {'saved_path' in result}")
    print(f"Output directory files: {list(temp_dirs['output'].iterdir())}")
    
    assert result['success'] is True
    assert 'saved_path' not in result or result['saved_path'] is None
    
    # output 디렉토리에 파일이 없어야 함
    output_files = list(temp_dirs['output'].iterdir())
    assert len(output_files) == 0, f"파일이 생성되었습니다: {output_files}"


def test_metadata_only_without_save(temp_dirs):
    """Test 5: Metadata만 저장 (이미지는 저장 안 함)"""
    loader = ImageLoader(
        source__path=str(temp_dirs['test_image']),
        save__directory=str(temp_dirs['output']),
        save__save_copy=False,  # 이미지 저장 안 함
        meta__save_meta=True,   # 메타만 저장
        meta__directory=str(temp_dirs['meta']),
        log__name="test_integration",
        log__level="INFO",
        log__handlers=[]
    )
    result = loader.run()
    
    print(f"\n=== Test 5: Metadata Only ===")
    print(f"Success: {result['success']}")
    print(f"Has 'saved_path': {'saved_path' in result}")
    print(f"Has 'meta_path': {'meta_path' in result}")
    
    assert result['success'] is True
    assert 'saved_path' not in result or result['saved_path'] is None
    assert 'meta_path' in result
    
    # Metadata 파일 확인
    meta_file = Path(result['meta_path'])
    assert meta_file.exists()
    
    with open(meta_file, 'r', encoding='utf-8') as f:
        meta = json.load(f)
    
    print(f"\n=== Metadata Content (No Image Save) ===")
    print(json.dumps(meta, indent=2, ensure_ascii=False))
    
    # 이미지는 없고 메타만 있어야 함
    output_files = list(temp_dirs['output'].iterdir())
    meta_files = list(temp_dirs['meta'].iterdir())
    
    assert len(output_files) == 0, "이미지 파일이 생성되었습니다"
    assert len(meta_files) == 1, "메타 파일이 생성되지 않았습니다"


def test_different_meta_directory(temp_dirs):
    """Test 6: 이미지와 메타 저장 위치 분리"""
    loader = ImageLoader(
        source__path=str(temp_dirs['test_image']),
        save__directory=str(temp_dirs['output']),  # 이미지는 output에
        save__save_copy=True,
        meta__save_meta=True,
        meta__directory=str(temp_dirs['meta']),    # 메타는 meta에
        log__name="test_integration",
        log__level="INFO",
        log__handlers=[]
    )
    result = loader.run()
    
    print(f"\n=== Test 6: Different Directories ===")
    print(f"Image Directory: {temp_dirs['output']}")
    print(f"Meta Directory: {temp_dirs['meta']}")
    
    assert result['success'] is True
    
    # 파일 위치 확인
    saved_path = Path(result['saved_path'])
    meta_path = Path(result['meta_path'])
    
    print(f"Saved Image: {saved_path}")
    print(f"Saved Meta: {meta_path}")
    
    assert saved_path.parent == temp_dirs['output']
    assert meta_path.parent == temp_dirs['meta']
    assert saved_path.exists()
    assert meta_path.exists()
    
    # 각 디렉토리에 파일이 하나씩 있는지 확인
    output_files = list(temp_dirs['output'].iterdir())
    meta_files = list(temp_dirs['meta'].iterdir())
    
    assert len(output_files) == 1, f"output 디렉토리에 {len(output_files)}개 파일"
    assert len(meta_files) == 1, f"meta 디렉토리에 {len(meta_files)}개 파일"
