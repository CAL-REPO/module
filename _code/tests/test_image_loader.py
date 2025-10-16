# -*- coding: utf-8 -*-
# Tests for ImageLoader

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'modules'))

import pytest
from PIL import Image
import tempfile
import shutil

from image_utils.services.image_loader import ImageLoader


@pytest.fixture
def temp_dirs():
    """임시 디렉토리 생성"""
    temp_base = Path(tempfile.mkdtemp())
    input_dir = temp_base / "input"
    output_dir = temp_base / "output"
    
    input_dir.mkdir(parents=True)
    output_dir.mkdir(parents=True)
    
    # 테스트 이미지 생성
    test_image = Image.new('RGB', (100, 100), color='red')
    test_image_path = input_dir / "test.jpg"
    test_image.save(test_image_path)
    
    yield {
        'base': temp_base,
        'input': input_dir,
        'output': output_dir,
        'test_image': test_image_path
    }
    
    # 정리
    shutil.rmtree(temp_base)


@pytest.fixture
def image_config_base():
    """ImageLoader 기본 config 경로"""
    return Path(__file__).parent.parent / 'modules' / 'image_utils' / 'configs' / 'image.yaml'


def test_image_loader_basic_load(temp_dirs, image_config_base):
    """Test 1: 기본 이미지 로드"""
    loader = ImageLoader(
        source__path=str(temp_dirs['test_image']),
        save__directory=str(temp_dirs['output']),
        save__save_copy=False,
        meta__save_meta=False,
        log__name="test_loader",
        log__level="WARNING",
        log__handlers=[]
    )
    result = loader.run()
    
    assert result['success'] is True
    assert 'image' in result
    assert result['image'].size == (100, 100)


def test_image_loader_save_enabled(temp_dirs):
    """Test 2: 이미지 저장 (save_copy=True)"""
    loader = ImageLoader(
        source__path=str(temp_dirs['test_image']),
        save__directory=str(temp_dirs['output']),
        save__save_copy=True,
        save__name__suffix="_copy",
        save__name__ensure_unique=False,
        meta__save_meta=False,
        log__name="test_loader",
        log__level="WARNING",
        log__handlers=[]
    )
    result = loader.run()
    
    assert result['success'] is True
    assert 'saved_path' in result
    
    # 저장된 파일 확인
    saved_file = Path(result['saved_path'])
    assert saved_file.exists()
    assert saved_file.parent == temp_dirs['output']
    assert '_copy' in saved_file.stem


def test_image_loader_with_meta(temp_dirs):
    """Test 3: 메타데이터 저장"""
    loader = ImageLoader(
        source__path=str(temp_dirs['test_image']),
        save__directory=str(temp_dirs['output']),
        save__save_copy=True,
        meta__save_meta=True,
        meta__directory=str(temp_dirs['output']),
        log__name="test_loader",
        log__level="WARNING",
        log__handlers=[]
    )
    result = loader.run()
    
    assert result['success'] is True
    assert 'meta_path' in result
    
    # 메타 파일 확인
    meta_file = Path(result['meta_path'])
    assert meta_file.exists()
    assert meta_file.suffix == '.json'
    
    # 메타 내용 확인
    import json
    with open(meta_file, 'r', encoding='utf-8') as f:
        meta = json.load(f)
    
    assert 'original_path' in meta  # 실제 필드명
    assert 'original_size' in meta
    assert meta['original_size'] == [100, 100]


def test_image_loader_resize(temp_dirs):
    """Test 4: 이미지 리사이즈"""
    loader = ImageLoader(
        source__path=str(temp_dirs['test_image']),
        save__directory=str(temp_dirs['output']),
        save__save_copy=True,
        process__resize_to=[50, 50],
        meta__save_meta=False,
        log__name="test_loader",
        log__level="WARNING",
        log__handlers=[]
    )
    result = loader.run()
    
    assert result['success'] is True
    assert result['image'].size == (50, 50)
    
    # 저장된 이미지 크기 확인
    saved_image = Image.open(result['saved_path'])
    assert saved_image.size == (50, 50)


def test_image_loader_format_conversion(temp_dirs):
    """Test 5: 포맷 변환 (JPG → PNG)"""
    loader = ImageLoader(
        source__path=str(temp_dirs['test_image']),
        save__directory=str(temp_dirs['output']),
        save__save_copy=True,
        save__format="PNG",
        meta__save_meta=False,
        log__name="test_loader",
        log__level="WARNING",
        log__handlers=[]
    )
    result = loader.run()
    
    assert result['success'] is True
    
    # 저장된 파일 확인
    saved_file = Path(result['saved_path'])
    assert saved_file.suffix.lower() == '.png'
    
    # 파일 포맷 확인
    saved_image = Image.open(saved_file)
    assert saved_image.format == 'PNG'


def test_image_loader_with_suffix_counter(temp_dirs):
    """Test 6: suffix_counter 사용 (실제 동작 확인)"""
    # 첫 번째 저장
    loader1 = ImageLoader(
        source__path=str(temp_dirs['test_image']),
        save__directory=str(temp_dirs['output']),
        save__save_copy=True,
        save__name__suffix_counter=1,
        meta__save_meta=False,
        log__name="test_loader",
        log__level="WARNING",
        log__handlers=[]
    )
    result1 = loader1.run()
    
    assert result1['success'] is True
    saved_path1 = Path(result1['saved_path'])
    assert saved_path1.exists()
    
    # 두 번째 저장 (다른 카운터)
    loader2 = ImageLoader(
        source__path=str(temp_dirs['test_image']),
        save__directory=str(temp_dirs['output']),
        save__save_copy=True,
        save__name__suffix_counter=2,
        meta__save_meta=False,
        log__name="test_loader",
        log__level="WARNING",
        log__handlers=[]
    )
    result2 = loader2.run()
    
    assert result2['success'] is True
    saved_path2 = Path(result2['saved_path'])
    assert saved_path2.exists()
    
    # 두 파일이 다른지 확인
    assert saved_path1 != saved_path2


def test_image_loader_quality_setting(temp_dirs):
    """Test 7: JPEG 품질 설정"""
    loader = ImageLoader(
        source__path=str(temp_dirs['test_image']),
        save__directory=str(temp_dirs['output']),
        save__save_copy=True,
        save__quality=50,  # 낮은 품질
        meta__save_meta=False,
        log__name="test_loader",
        log__level="WARNING",
        log__handlers=[]
    )
    result = loader.run()
    
    assert result['success'] is True
    
    # 저장된 파일 크기 확인 (낮은 품질 = 작은 파일)
    saved_file = Path(result['saved_path'])
    assert saved_file.exists()
    file_size = saved_file.stat().st_size
    assert file_size < 10000  # 10KB 이하


def test_image_loader_mode_conversion(temp_dirs):
    """Test 8: 이미지 모드 변환 (RGB → L)"""
    loader = ImageLoader(
        source__path=str(temp_dirs['test_image']),
        save__directory=str(temp_dirs['output']),
        save__save_copy=True,
        process__convert_mode="L",  # 올바른 필드명
        meta__save_meta=False,
        log__name="test_loader",
        log__level="WARNING",
        log__handlers=[]
    )
    result = loader.run()
    
    assert result['success'] is True
    
    # 저장된 이미지 모드 확인
    saved_image = Image.open(result['saved_path'])
    assert saved_image.mode == 'L'
