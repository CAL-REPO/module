# -*- coding: utf-8 -*-
"""
scripts/oto.py
이미지 OCR → 번역 → 오버레이 자동화 파이프라인

설계 원칙:
1. cfg_utils의 override 패턴 활용
2. 환경변수(CASHOP_PATHS) → paths.local.yaml → config paths 추출
3. 각 섹션 정책(image, ocr, translate, overlay)에 따라 파이프라인 실행
4. source만 동적 override (나머지는 yaml 정책 준수)

파이프라인:
1. ImageLoader: 이미지 로드 (image section 정책)
2. ImageOCR: OCR 실행 (ocr section 정책)
3. Translator: 번역 (translate section 정책, source=ocr 결과)
4. ImageOverlay: 오버레이 (overlay section 정책, texts=번역 결과)
"""

from __future__ import annotations
import os
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional

# PYTHONPATH: M:\CALife\CAShop - 구매대행\_code\modules
from cfg_utils import ConfigLoader
from image_utils import ImageLoader, ImageOCR, ImageOverlay
from translate_utils import Translator


class OTO:
    """OCR → Translate → Overlay 파이프라인
    
    환경변수 기반 설정 로드 후 단일 이미지 또는 다중 이미지 처리
    
    Example:
        >>> # 단일 이미지 처리
        >>> oto = OTO()
        >>> result = oto.process_image("path/to/image.jpg")
        
        >>> # 다중 이미지 처리
        >>> results = oto.process_images(["img1.jpg", "img2.jpg"])
    """
    
    PATHS_ENV_KEY = "CASHOP_PATHS"
    
    def __init__(
        self,
        config_names: Optional[str | List[str]] = None,
        paths_env_key: Optional[str] = None
    ):
        """OTO 파이프라인 초기화
        
        Args:
            config_names: 설정 파일명 또는 리스트
                - str: 단일 파일 (예: "xloto" → configs_xloto 경로 사용)
                - List[str]: 다중 파일 (예: ["image", "ocr", "translate", "overlay"])
                - None: 기본값 "xloto" 사용
            paths_env_key: 환경변수 키 (기본: CASHOP_PATHS)
        
        Examples:
            >>> # 단일 통합 파일 사용
            >>> oto = OTO(config_names="xloto")
            
            >>> # 개별 모듈 파일 사용
            >>> oto = OTO(config_names=["image", "ocr", "translate", "overlay"])
            
            >>> # 기본값 사용
            >>> oto = OTO()
        """
        self.config_names = config_names or "xloto"
        self.paths_env_key = paths_env_key or self.PATHS_ENV_KEY
        
        # 설정 로드
        self._load_paths()
        self._load_config()
    
    # ==========================================================================
    # 설정 로드
    # ==========================================================================
    
    def _load_paths(self):
        """환경변수 → paths.local.yaml → config paths 추출"""
        # 1. 환경변수에서 paths.local.yaml 경로 가져오기
        paths_yaml = os.getenv(self.paths_env_key)
        if not paths_yaml:
            raise EnvironmentError(
                f"환경변수 '{self.paths_env_key}'가 설정되지 않았습니다.\n"
                f"설정 방법:\n"
                f'  $env:{self.paths_env_key} = "M:\\CALife\\CAShop - 구매대행\\_code\\configs\\paths.local.yaml"'
            )
        
        if not Path(paths_yaml).exists():
            raise FileNotFoundError(f"paths.yaml 파일이 없습니다: {paths_yaml}")
        
        # 2. paths.local.yaml 로드
        self.paths = ConfigLoader(paths_yaml).as_dict()
        
        # 3. config 경로 추출 (단일 또는 다중)
        if isinstance(self.config_names, str):
            # 단일 파일: configs_xloto
            config_key = f"configs_{self.config_names}"
            config_path = str(self.paths.get(config_key, ""))
            
            if not config_path or not Path(config_path).exists():
                raise FileNotFoundError(
                    f"설정 파일 경로를 찾을 수 없습니다: {config_key}\n"
                    f"paths.local.yaml에 '{config_key}' 키가 정의되어 있는지 확인하세요."
                )
            
            self.config_paths = [config_path]
        
        elif isinstance(self.config_names, list):
            # 다중 파일: [configs_image, configs_ocr, ...]
            self.config_paths = []
            for name in self.config_names:
                config_key = f"configs_{name}"
                config_path = str(self.paths.get(config_key, ""))
                
                if not config_path or not Path(config_path).exists():
                    raise FileNotFoundError(
                        f"설정 파일 경로를 찾을 수 없습니다: {config_key}\n"
                        f"paths.local.yaml에 '{config_key}' 키가 정의되어 있는지 확인하세요."
                    )
                
                self.config_paths.append(config_path)
        
        else:
            raise TypeError(f"config_names는 str 또는 List[str]이어야 합니다: {type(self.config_names)}")
    
    def _load_config(self):
        """config.yaml 로드 (섹션별 정책 준비)"""
        # ConfigLoader 생성 (한 번만 로드)
        self.config_loader = ConfigLoader(self.config_path)
        
        # 각 섹션의 정책을 미리 확인 (optional)
        # 실제로는 각 서비스에서 section 파라미터로 로드
        self.has_image = self._has_section("image")
        self.has_ocr = self._has_section("ocr")
        self.has_translate = self._has_section("translate")
        self.has_overlay = self._has_section("overlay")
    
    def _has_section(self, section: str) -> bool:
        """섹션 존재 여부 확인"""
        try:
            data = self.config_loader.as_dict(section=section)
            return bool(data)
        except Exception:
            return False
    
    # ==========================================================================
    # 파이프라인 실행
    # ==========================================================================
    
    def process_image(
        self,
        image_path: str | Path,
        output_dir: Optional[str | Path] = None,
        **overrides: Any
    ) -> Dict[str, Any]:
        """단일 이미지 OCR → 번역 → 오버레이
        
        Args:
            image_path: 이미지 경로
            output_dir: 출력 디렉토리 (None이면 config 정책 따름)
            **overrides: 추가 override (예: provider__target_lang="EN")
        
        Returns:
            {
                'success': bool,
                'ocr_result': Dict,
                'translate_result': Dict,
                'overlay_result': Dict,
                'error': Optional[str]
            }
        """
        try:
            image_path = Path(image_path)
            if not image_path.exists():
                return {
                    'success': False,
                    'error': f"이미지 파일이 없습니다: {image_path}"
                }
            
            print(f"\n{'='*80}")
            print(f"🖼️  이미지 처리: {image_path.name}")
            print(f"{'='*80}")
            
            # 1. ImageLoader: 이미지 로드 (image section 정책)
            print("\n[1/4] 이미지 로드 중...")
            if self.has_image:
                loader = ImageLoader(
                    self.config_path,
                    section="image",
                    source__path=str(image_path),  # source만 override
                    **overrides
                )
                load_result = loader.run()
                if not load_result.get('success'):
                    return {
                        'success': False,
                        'error': f"이미지 로드 실패: {load_result.get('error')}"
                    }
                print(f"  ✅ 로드 완료: {image_path.name}")
            else:
                print(f"  ℹ️  image section 없음 - 스킵")
                load_result = None
            
            # 2. ImageOCR: OCR 실행 (ocr section 정책)
            print("\n[2/4] OCR 실행 중...")
            ocr = ImageOCR(
                self.config_path,
                section="ocr",
                source__path=str(image_path),  # source만 override
                **overrides
            )
            ocr_result = ocr.run()
            
            if not ocr_result.get('success'):
                return {
                    'success': False,
                    'ocr_result': ocr_result,
                    'error': f"OCR 실패: {ocr_result.get('error')}"
                }
            
            ocr_items = ocr_result.get('ocr_items', [])
            print(f"  ✅ OCR 완료: {len(ocr_items)}개 텍스트 추출")
            
            if not ocr_items:
                print(f"  ⚠️  OCR 결과 없음 - 번역/오버레이 스킵")
                return {
                    'success': True,
                    'ocr_result': ocr_result,
                    'translate_result': None,
                    'overlay_result': None
                }
            
            # 3. Translator: 번역 (translate section 정책, source=ocr 결과)
            print("\n[3/4] 번역 중...")
            
            # OCR 결과에서 텍스트 추출
            original_texts = []
            for item in ocr_items:
                text = item.text if hasattr(item, 'text') else item.get('text', '')
                if text:
                    original_texts.append(text)
            
            if not original_texts:
                print(f"  ⚠️  번역할 텍스트 없음 - 스킵")
                return {
                    'success': True,
                    'ocr_result': ocr_result,
                    'translate_result': None,
                    'overlay_result': None
                }
            
            # Translator: source__text override
            translator = Translator(
                self.config_path,
                section="translate",
                source__text=original_texts,  # OCR 결과를 source로 주입
                **overrides
            )
            translate_result = translator.run()  # Dict[str, str]
            
            print(f"  ✅ 번역 완료: {len(translate_result)}개")
            
            # 4. OCR items에 번역 결과 매핑
            print("\n[4/4] 오버레이 적용 중...")
            
            overlay_texts = []
            for item in ocr_items:
                original_text = item.text if hasattr(item, 'text') else item.get('text', '')
                bbox = item.bbox if hasattr(item, 'bbox') else item.get('bbox', [0, 0, 100, 100])
                
                if not original_text:
                    continue
                
                # 번역 결과 매핑
                translated_text = translate_result.get(original_text, original_text)
                
                overlay_texts.append({
                    'bbox': bbox,
                    'text': translated_text
                })
            
            # 5. ImageOverlay: 오버레이 (overlay section 정책, texts=번역 결과)
            overlay_overrides = overrides.copy()
            if output_dir:
                overlay_overrides['save__directory'] = str(output_dir)
            
            overlay = ImageOverlay(
                self.config_path,
                section="overlay",
                source__path=str(image_path),  # source만 override
                texts=overlay_texts,  # 번역 결과 주입
                **overlay_overrides
            )
            overlay_result = overlay.run()
            
            if not overlay_result.get('success'):
                return {
                    'success': False,
                    'ocr_result': ocr_result,
                    'translate_result': translate_result,
                    'overlay_result': overlay_result,
                    'error': f"오버레이 실패: {overlay_result.get('error')}"
                }
            
            saved_path = overlay_result.get('saved_path')
            print(f"  ✅ 저장 완료: {saved_path}")
            
            print(f"\n{'='*80}")
            print(f"✅ 처리 완료: {image_path.name}")
            print(f"{'='*80}")
            
            return {
                'success': True,
                'ocr_result': ocr_result,
                'translate_result': translate_result,
                'overlay_result': overlay_result
            }
            
        except Exception as e:
            print(f"\n❌ 처리 실패: {e}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e)
            }
    
    def process_images(
        self,
        image_paths: List[str | Path],
        output_dir: Optional[str | Path] = None,
        **overrides: Any
    ) -> List[Dict[str, Any]]:
        """다중 이미지 일괄 처리
        
        Args:
            image_paths: 이미지 경로 리스트
            output_dir: 출력 디렉토리
            **overrides: 추가 override
        
        Returns:
            각 이미지별 처리 결과 리스트
        """
        results = []
        
        print(f"\n{'='*80}")
        print(f"📸 다중 이미지 처리: {len(image_paths)}개")
        print(f"{'='*80}")
        
        for idx, image_path in enumerate(image_paths, 1):
            print(f"\n[{idx}/{len(image_paths)}] {Path(image_path).name}")
            
            result = self.process_image(
                image_path,
                output_dir=output_dir,
                **overrides
            )
            results.append(result)
        
        # 요약
        success_count = sum(1 for r in results if r.get('success'))
        print(f"\n{'='*80}")
        print(f"📊 처리 완료: {success_count}/{len(image_paths)}개 성공")
        print(f"{'='*80}")
        
        return results


def main():
    """테스트 실행"""
    import argparse
    
    parser = argparse.ArgumentParser(description="OTO 파이프라인 실행")
    parser.add_argument("image", nargs="+", help="처리할 이미지 경로")
    parser.add_argument("--output", "-o", help="출력 디렉토리")
    parser.add_argument("--config", "-c", default="xloto", help="설정 파일명 (기본: xloto)")
    args = parser.parse_args()
    
    try:
        # OTO 파이프라인 생성
        oto = OTO(config_name=args.config)
        
        # 단일 또는 다중 이미지 처리
        if len(args.image) == 1:
            result = oto.process_image(args.image[0], output_dir=args.output)
            if result['success']:
                print("\n✅ 성공!")
            else:
                print(f"\n❌ 실패: {result.get('error')}")
                sys.exit(1)
        else:
            results = oto.process_images(args.image, output_dir=args.output)
            failed = [r for r in results if not r.get('success')]
            if failed:
                print(f"\n⚠️  {len(failed)}개 이미지 처리 실패")
                sys.exit(1)
            else:
                print("\n✅ 모든 이미지 처리 성공!")
    
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
