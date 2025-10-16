# -*- coding: utf-8 -*-
"""
scripts/oto.py - OCR → Translate → Overlay Pipeline (New Architecture)

새 아키텍처 설계 원칙:
1. SRP 준수: 각 모듈은 단일 책임만 수행
2. Image 객체 전달: 불필요한 FSO 접근 제거
3. Pipeline scripts에서 변환 처리: OCRItem → Translation → OverlayItemPolicy
4. ENV 기반 설정: CASHOP_PATHS → ConfigLoader로 모든 정책 로드

Pipeline Flow:
1. ConfigLoader: ENV → paths.local.yaml → 각 모듈별 설정 로드
2. ImageLoader: 이미지 로드 및 전처리 → Image 반환
3. ImageOCR: OCR 실행 (Image 입력) → OCRItem[], Image 반환
4. Translation: OCRItem.text → 번역 (script 책임)
5. Conversion: OCRItem + translated_text → OverlayItemPolicy (script 책임)
6. ImageOverlay: OverlayItemPolicy 렌더링 (Image 입력) → Final Image 반환
"""

from __future__ import annotations
import os
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional

# PYTHONPATH: M:\CALife\CAShop - 구매대행\_code\modules
from cfg_utils import ConfigLoader
from logs_utils import LogManager
from path_utils import resolve
from script_utils import EnvBasedConfigInitializer

from image_utils.services.image_loader import ImageLoader
from image_utils.services.image_ocr import ImageOCR
from image_utils.services.image_overlay import ImageOverlay
from image_utils.core.models import OCRItem
from image_utils.core.policy import (
    ImageLoaderPolicy, 
    ImageOCRPolicy, 
    ImageOverlayPolicy,
    OverlayItemPolicy
)

from translate_utils.services.translator import Translator
# TranslatorPolicy는 아직 없을 수 있으므로 주석 처리
# from translate_utils.core.policy import TranslatorPolicy

class OTO:
    """OCR → Translate → Overlay Pipeline (New Architecture)
    
    환경변수(CASHOP_PATHS) 기반으로 ConfigLoader를 통해 모든 정책을 로드하고,
    Image 객체를 전달하며 각 단계를 실행하는 파이프라인.
    
    Architecture:
        1. ENV → paths.local.yaml → 각 모듈별 config YAML 경로
        2. ConfigLoader로 각 정책 (ImageLoaderPolicy, ImageOCRPolicy, etc.) 로드
        3. Image 객체를 단계 간 전달 (FSO 중복 제거)
        4. Script에서 OCRItem → Translation → OverlayItemPolicy 변환
    
    Example:
        >>> oto = OTO()  # ENV에서 자동 로드
        >>> result = oto.process_image("test.jpg")
        >>> # {'success': True, 'final_image': <PIL.Image>, ...}
    """
    
    PATHS_ENV_KEY = "CASHOP_PATHS"
    
    def __init__(
        self,
        paths_env_key: Optional[str] = None,
        log: Optional[LogManager] = None,
    ):
        """OTO Pipeline 초기화
        
        Args:
            paths_env_key: 환경변수 키 (기본: "CASHOP_PATHS")
            log: 외부 LogManager (없으면 생성)
        
        Raises:
            EnvironmentError: 환경변수가 설정되지 않은 경우
            FileNotFoundError: paths.local.yaml 또는 config 파일이 없는 경우
        """
        self.paths_env_key = paths_env_key or self.PATHS_ENV_KEY
        
        # LogManager 초기화 (공통 로거)
        if log is None:
            from logs_utils.core.policy import LogPolicy
            self.log = LogManager(LogPolicy()).logger
        else:
            self.log = log.logger if isinstance(log, LogManager) else log
        
        # 설정 로드 (간소화된 3줄)
        self.log.info(f"OTO Pipeline 초기화 중...")
        self.paths_dict = EnvBasedConfigInitializer.load_paths_from_env(self.paths_env_key)
        self.loader = EnvBasedConfigInitializer.create_config_loader(
            "configs_loader_file_oto", self.paths_dict
        )
        self._load_policies()
        self.log.success("OTO Pipeline 초기화 완료")
    
    # ==========================================================================
    # 설정 로드
    # ==========================================================================
    
    def _load_policies(self):
        """configs_loader_oto.yaml을 통해 모듈별 정책 로드

        """
        self.log.info(f"Config 정책 로드 중...")
        

        
        # 1. ImageLoader 정책
        try:
            self.image_loader_policy = self.loader._as_model_internal(
                ImageLoaderPolicy, 
                section="image"
            )
            self.log.info("  ✅ ImageLoader 정책 로드 완료")
        except Exception as e:
            self.log.warning(f"  ⚠️  ImageLoader 정책 로드 실패: {e}")
            self.image_loader_policy = None
        
        # 2. ImageOCR 정책
        try:
            self.image_ocr_policy = self.loader._as_model_internal(
                ImageOCRPolicy, 
                section="ocr"
            )
            self.log.info("  ✅ ImageOCR 정책 로드 완료")
        except Exception as e:
            self.log.warning(f"  ⚠️  ImageOCR 정책 로드 실패: {e}")
            self.image_ocr_policy = None
        
        # 3. Translator 정책
        try:
            self.translator_config = self.loader._as_dict_internal(section="translate")
            self.log.info("  ✅ Translator 정책 로드 완료")
        except Exception as e:
            self.log.warning(f"  ⚠️  Translator 정책 로드 실패: {e}")
            self.translator_config = None
        
        # 4. ImageOverlay 정책
        try:
            self.image_overlay_policy = self.loader._as_model_internal(
                ImageOverlayPolicy, 
                section="overlay"
            )
            self.log.info("  ✅ ImageOverlay 정책 로드 완료")
        except Exception as e:
            self.log.warning(f"  ⚠️  ImageOverlay 정책 로드 실패: {e}")
            self.image_overlay_policy = None
    
    # ==========================================================================
    # Pipeline 실행
    # ==========================================================================
    
    def process_image(
        self,
        image_path: str | Path,
        **overrides: Any
    ) -> Dict[str, Any]:
        """단일 이미지 OCR → 번역 → 오버레이 파이프라인
        
        New Architecture:
            1. ImageLoader.run() → Image 객체
            2. ImageOCR.run(image=...) → OCRItem[], preprocessed Image
            3. Script: OCRItem.text → Translator → translated_texts
            4. Script: OCRItem + translated_text → OverlayItemPolicy
            5. ImageOverlay.run(image=..., overlay_items=...) → Final Image
        
        Args:
            image_path: 이미지 경로
            **overrides: 정책 필드 오버라이드 (예: save__save_copy=True)
        
        Returns:
            {
                'success': bool,
                'image_path': Path,
                'loader_result': Dict,
                'ocr_result': Dict,
                'translate_result': Dict[str, str],
                'overlay_result': Dict,
                'final_image': Optional[PIL.Image],
                'error': Optional[str]
            }
        """
        image_path = resolve(image_path)  # 절대 경로로 변환
        result = {
            'success': False,
            'image_path': image_path,
            'loader_result': None,
            'ocr_result': None,
            'translate_result': None,
            'overlay_result': None,
            'final_image': None,
            'error': None,
        }
        
        try:
            if not image_path.exists():
                result['error'] = f"이미지 파일이 없습니다: {image_path}"
                self.log.error(result['error'])
                return result
            
            self.log.info(f"{'='*80}")
            self.log.info(f"🖼️  처리 시작: {image_path.name}")
            self.log.info(f"{'='*80}\n")
            
            # ====================================================================
            # Step 1: ImageLoader - 이미지 로드 및 전처리
            # ====================================================================
            if self.image_loader_policy:
                loader = ImageLoader(
                    cfg_like=self.image_loader_policy,
                    **overrides
                )
                loader_result = loader.run(source_override=str(image_path))
                
                if not loader_result.get('success'):
                    result['error'] = f"ImageLoader 실패: {loader_result.get('error')}"
                    self.log.error(result['error'])
                    return result
                
                image = loader_result['image']
                result['loader_result'] = loader_result
            else:
                # Policy 없으면 기본 로드
                from PIL import Image
                image = Image.open(image_path)
                self.log.info(f"ImageLoader 정책 없음 - 기본 로드: {image.size}")
            
            # ====================================================================
            # Step 2: ImageOCR - OCR 실행
            # ====================================================================
            if not self.image_ocr_policy:
                result['error'] = "ImageOCR 정책이 로드되지 않았습니다"
                self.log.error(result['error'])
                return result
            
            ocr = ImageOCR(
                cfg_like=self.image_ocr_policy,
                **overrides
            )
            ocr_result = ocr.run(
                source_override=str(image_path),
                image=image,  # Image 객체 전달 (FSO 중복 제거)
            )
            
            if not ocr_result.get('success'):
                result['error'] = f"ImageOCR 실패: {ocr_result.get('error')}"
                result['ocr_result'] = ocr_result
                self.log.error(result['error'])
                return result
            
            ocr_items: List[OCRItem] = ocr_result['ocr_items']
            preprocessed_image = ocr_result['image']
            result['ocr_result'] = ocr_result
            
            if not ocr_items:
                self.log.warning("OCR 결과 없음 - 번역/오버레이 스킵")
                result['success'] = True
                return result
            
            # ====================================================================
            # Step 3: Translation - OCR 텍스트 번역 (Script 책임)
            # ====================================================================
            original_texts = [item.text for item in ocr_items if item.text]
            
            if not original_texts:
                self.log.warning("번역할 텍스트 없음")
                result['success'] = True
                return result
            
            # Translator 사용
            if self.translator_config:
                # TODO: Translator 인터페이스 확인 후 구현
                self.log.info(f"번역 중... ({len(original_texts)}개 텍스트)")
                
                # 임시 번역 (역순으로 변환 - 테스트용)
                translated_texts = {text: f"[번역] {text[::-1]}" for text in original_texts}
                result['translate_result'] = translated_texts
            else:
                # 번역 스킵 (원본 사용)
                self.log.info("Translator 정책 없음 - 원본 텍스트 사용")
                translated_texts = {text: text for text in original_texts}
                result['translate_result'] = translated_texts
            
            # ====================================================================
            # Step 4: Conversion - OCRItem → OverlayItemPolicy (Script 책임)
            # ====================================================================
            overlay_items: List[OverlayItemPolicy] = []
            
            for item in ocr_items:
                if not item.text:
                    continue
                
                # 번역된 텍스트 가져오기
                translated_text = translated_texts.get(item.text, item.text)
                
                # OCRItem.to_overlay_item() 사용
                overlay_item = item.to_overlay_item(text_override=translated_text)
                overlay_items.append(overlay_item)
            
            # ====================================================================
            # Step 5: ImageOverlay - 오버레이 렌더링
            # ====================================================================
            if not self.image_overlay_policy:
                result['error'] = "ImageOverlay 정책이 로드되지 않았습니다"
                self.log.error(result['error'])
                return result
            
            overlay = ImageOverlay(
                cfg_like=self.image_overlay_policy,
                **overrides
            )
            overlay_result = overlay.run(
                source_path=str(image_path),
                image=preprocessed_image,  # OCR 전처리된 이미지 사용
                overlay_items=overlay_items,  # 변환된 아이템 전달
            )
            
            if not overlay_result.get('success'):
                result['error'] = f"ImageOverlay 실패: {overlay_result.get('error')}"
                result['overlay_result'] = overlay_result
                self.log.error(result['error'])
                return result
            
            result['overlay_result'] = overlay_result
            result['final_image'] = overlay_result.get('image')
            
            # ====================================================================
            # 완료
            # ====================================================================
            result['success'] = True
            
            self.log.info(f"{'='*80}")
            self.log.success(f"✅ 처리 완료: {image_path.name}")
            self.log.info(f"{'='*80}\n")
            
            return result
            
        except Exception as e:
            result['error'] = f"예외 발생: {type(e).__name__}: {e}"
            self.log.error(result['error'])
            
            import traceback
            self.log.error(traceback.format_exc())
            
            return result
    
    def process_images(
        self,
        image_paths: List[str | Path],
        **overrides: Any
    ) -> List[Dict[str, Any]]:
        """다중 이미지 일괄 처리
        
        Args:
            image_paths: 이미지 경로 리스트
            **overrides: 정책 필드 오버라이드
        
        Returns:
            각 이미지별 처리 결과 리스트
        """
        results = []
        
        self.log.info(f"{'='*80}")
        self.log.info(f"📸 다중 이미지 처리: {len(image_paths)}개")
        self.log.info(f"{'='*80}\n")
        
        for idx, image_path in enumerate(image_paths, 1):
            self.log.info(f"[{idx}/{len(image_paths)}] {Path(image_path).name}")
            
            result = self.process_image(image_path, **overrides)
            results.append(result)
        
        # 요약
        success_count = sum(1 for r in results if r.get('success'))
        
        self.log.info(f"\n{'='*80}")
        self.log.info(f"📊 처리 결과: 성공 {success_count}/{len(image_paths)}개")
        self.log.info(f"{'='*80}\n")
        
        return results


def main():
    """CLI 진입점"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="OTO Pipeline - OCR → Translate → Overlay",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # 단일 이미지 처리
  python oto.py image.jpg
  
  # 다중 이미지 처리
  python oto.py img1.jpg img2.jpg img3.jpg
  
  # 정책 오버라이드
  python oto.py --override save.save_copy=True image.jpg

Environment:
  CASHOP_PATHS: paths.local.yaml 경로 (필수)
    예: M:\\CALife\\CAShop - 구매대행\\_code\\configs\\paths.local.yaml
        """
    )
    
    parser.add_argument(
        "images",
        nargs="+",
        help="처리할 이미지 경로 (1개 이상)"
    )
    parser.add_argument(
        "--override", "-o",
        action="append",
        help="정책 필드 오버라이드 (예: save.save_copy=True)"
    )
    
    args = parser.parse_args()
    
    try:
        # Override 파싱
        overrides = {}
        if args.override:
            for override_str in args.override:
                if "=" not in override_str:
                    print(f"⚠️  잘못된 override 형식: {override_str} (형식: key=value)")
                    continue
                
                key, value = override_str.split("=", 1)
                
                # 타입 변환 시도
                if value.lower() in ("true", "yes", "1"):
                    value = True
                elif value.lower() in ("false", "no", "0"):
                    value = False
                elif value.isdigit():
                    value = int(value)
                elif value.replace(".", "", 1).isdigit():
                    value = float(value)
                
                # 중첩 키 처리 (예: save.save_copy → {'save': {'save_copy': ...}})
                keys = key.split(".")
                current = overrides
                for k in keys[:-1]:
                    if k not in current:
                        current[k] = {}
                    current = current[k]
                current[keys[-1]] = value
        
        # OTO Pipeline 생성
        print(f"🔧 OTO Pipeline 초기화 중...")
        oto = OTO()
        
        # 단일 또는 다중 이미지 처리
        if len(args.images) == 1:
            result = oto.process_image(args.images[0], **overrides)
            
            if result['success']:
                print("\n✅ 처리 성공!")
                sys.exit(0)
            else:
                print(f"\n❌ 처리 실패: {result.get('error')}")
                sys.exit(1)
        else:
            results = oto.process_images(args.images, **overrides)
            
            failed = [r for r in results if not r.get('success')]
            if failed:
                print(f"\n⚠️  {len(failed)}개 이미지 처리 실패")
                sys.exit(1)
            else:
                print("\n✅ 모든 이미지 처리 성공!")
                sys.exit(0)
    
    except (EnvironmentError, FileNotFoundError) as e:
        print(f"\n❌ 환경/파일 오류: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 예외 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
