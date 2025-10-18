# -*- coding: utf-8 -*-
"""
OTO - OCR → Translate → Overlay Pipeline Entry Point.

책임:
1. 4개 서비스(ImageLoader, OCR, Translator, Overlay) 통합 실행
2. Image 객체 전달로 FSO 중복 제거
3. OCRItem → Translation → OverlayItem 변환 (Pipeline 책임)
4. BaseServiceLoader 상속으로 완전 대칭 구조
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from PIL import Image
from pydantic import BaseModel

from cfg_utils import ConfigPolicy, BaseServiceLoader
from logs_utils import LogManager
from path_utils import resolve

from script_utils.core.oto_policy import OTOPolicy

from image_utils.entry_point.loader import ImageLoader
from image_utils.entry_point.text_recognizer import ImageTextRecognizer
from image_utils.entry_point.overlayer import ImageOverlayer
from image_utils.core.models import OCRItem
from image_utils.core.policy import OverlayItemPolicy

from translate_utils.adapter import Translate


class OTO(BaseServiceLoader[OTOPolicy]):
    """OCR → Translate → Overlay Pipeline (ImageLoader/OCR/Translate/Overlay와 완전 대칭).
    
    BaseServiceLoader를 상속하여 ConfigLoader 통합 및 일관된 설정 로딩을 제공합니다.
    
    Attributes:
        policy: OTOPolicy 설정 (4개 서비스 정책 통합)
        log: loguru logger 인스턴스
        image_loader: ImageLoader 서비스 (lazy-loaded)
        image_ocr: ImageTextRecognizer 서비스 (lazy-loaded)
        translate: Translate 서비스 (lazy-loaded)
        image_overlay: ImageOverlayer 서비스 (lazy-loaded)
    """
    
    def __init__(
        self,
        cfg_like: Union[BaseModel, Path, str, dict, None] = None,
        *,
        policy: Optional[ConfigPolicy] = None,
        config_loader_path: Optional[Union[str, Path]] = None,
        log: Optional[LogManager] = None,
        **overrides: Any
    ):
        """ConfigLoader와 동일한 인자 패턴으로 초기화 (ImageLoader/OCR/Translator/Overlay와 완전 대칭).
        
        Args:
            cfg_like: BaseModel, YAML 경로, dict, 또는 None
                - BaseModel: OTOPolicy 인스턴스 직접 전달
                - str/Path: YAML 파일 경로
                - dict: 설정 딕셔너리
                - None: 기본 설정 파일 사용
            policy: ConfigPolicy 인스턴스
            config_loader_path: config_loader_oto.yaml 경로 override (선택)
            log: 외부 LogManager (없으면 policy.log로 생성)
            **overrides: 런타임 오버라이드 값 (image__source__path, ocr__provider__langs 등)
        
        Example:
            >>> # YAML 파일에서 로드
            >>> oto = OTO("configs/oto.yaml")
            
            >>> # dict로 직접 설정
            >>> oto = OTO({"image": {"source": {"path": "test.jpg"}}})
            
            >>> # config_loader_path override
            >>> oto = OTO(config_loader_path="./config_loader_oto.yaml")
            
            >>> # 런타임 오버라이드 (KeyPath 형식)
            >>> oto = OTO("config.yaml", image__source__path="test.jpg", ocr__provider__langs=["ch"])
        """
        # BaseServiceLoader 초기화 (self.policy 설정)
        super().__init__(cfg_like, policy=policy, config_loader_path=config_loader_path, **overrides)
        
        # LogManager 초기화
        if log is None:
            log_manager = LogManager(self.policy.log)
            self.log = log_manager.logger
        else:
            self.log = log.logger if isinstance(log, LogManager) else log
        
        # 각 서비스는 lazy-load (첫 run() 호출 시 초기화)
        self._image_loader: Optional[ImageLoader] = None
        self._image_ocr: Optional[ImageTextRecognizer] = None
        self._translate: Optional[Translate] = None
        self._image_overlay: Optional[ImageOverlayer] = None
        
        self.log.info("OTO Pipeline initialized")
    
    # ==========================================================================
    # BaseServiceLoader Abstract Methods Implementation
    # ==========================================================================
    
    def _get_policy_model(self) -> type[OTOPolicy]:
        """Policy 모델 클래스 반환."""
        return OTOPolicy
    
    def _get_config_loader_path(self) -> Path:
        """config_loader_oto.yaml 경로 반환."""
        # scripts/oto.py 기준 경로
        return Path(__file__).parent.parent / "configs" / "loader" / "config_loader_oto.yaml"
    
    def _get_default_section(self) -> str:
        """기본 section 이름: None (OTO는 다중 섹션 통합)."""
        return ""  # OTO는 image, ocr, translate, overlay 섹션 모두 로드
    
    def _get_config_path(self) -> Path:
        """마지막 안전 장치용 기본 설정 파일: oto.yaml."""
        # 현재는 config_loader_oto.yaml이 각 서비스별 YAML을 지정하므로 사용 안 함
        return Path(__file__).parent.parent / "configs" / "oto" / "image.yaml"  # Placeholder
    
    def _get_reference_context(self) -> dict[str, Any]:
        """paths.local.yaml을 reference_context로 제공."""
        from modules.cfg_utils.services.paths_loader import PathsLoader
        try:
            return PathsLoader.load()
        except FileNotFoundError:
            # paths.local.yaml이 없어도 동작 계속 (선택 사항)
            self.log.warning("paths.local.yaml not found (CASHOP_PATHS not set)")
            return {}
    
    # ==========================================================================
    # Service Lazy Loading
    # ==========================================================================
    
    @property
    def image_loader(self) -> ImageLoader:
        """ImageLoader lazy-loading."""
        if self._image_loader is None:
            self._image_loader = ImageLoader(
                cfg_like=self.policy.image,
                log=None,  # 각 서비스가 자체 LogManager 생성
            )
        return self._image_loader
    
    @property
    def image_ocr(self) -> ImageTextRecognizer:
        """ImageTextRecognizer lazy-loading."""
        if self._image_ocr is None:
            self._image_ocr = ImageTextRecognizer(
                cfg_like=self.policy.ocr,
                log=None,  # 각 서비스가 자체 LogManager 생성
            )
        return self._image_ocr
    
    @property
    def translate(self) -> Translate:
        """Translate lazy-loading (인스턴스 재사용).
        
        run() 메서드를 사용하므로 매번 새 인스턴스를 생성할 필요 없음.
        이미지 여러 개 처리 시 동일 인스턴스를 재사용하여 Provider 연결 유지.
        """
        if self._translate is None:
            self._translate = Translate(
                policy=self.policy.translate,
                log_manager=None,  # Translate가 자체 LogManager 생성
            )
        return self._translate
    
    @property
    def image_overlay(self) -> ImageOverlayer:
        """ImageOverlayer lazy-loading."""
        if self._image_overlay is None:
            self._image_overlay = ImageOverlayer(
                cfg_like=self.policy.overlay,
                log=None,  # 각 서비스가 자체 LogManager 생성
            )
        return self._image_overlay
    
    # ==========================================================================
    # Core Methods
    # ==========================================================================
    
    def run(
        self,
        source_override: Optional[Union[str, Path]] = None,
        **overrides: Any
    ) -> Dict[str, Any]:
        """OCR → Translate → Overlay 파이프라인 실행 (ImageLoader/OCR와 완전 대칭).
        
        Pipeline Flow:
            1. ImageLoader.run() → Image 객체
            2. ImageTextRecognizer.run(image=...) → OCRItem[], preprocessed Image
            3. Translator.run() → Dict[str, str] (original → translated)
            4. Script: OCRItem + translated_text → OverlayItemPolicy
            5. ImageOverlayer.run(image=..., overlay_items=...) → Final Image
        
        Args:
            source_override: 소스 경로 오버라이드 (policy.image.source.path 대신 사용)
            **overrides: 정책 필드 오버라이드 (예: save__save_copy=True)
        
        Returns:
            결과 딕셔너리 (ImageLoader와 일관성 유지):
            {
                "success": bool,
                "image": PIL.Image.Image,  # 최종 오버레이된 이미지
                "metadata": Dict[str, Any],  # 통합 메타데이터
                "original_path": Path,
                "loader_result": Dict,
                "ocr_result": Dict,
                "translate_result": Dict[str, str],
                "overlay_result": Dict,
                "error": Optional[str]
            }
        """
        result = {
            "success": False,
            "image": None,  # 최종 이미지 (ImageLoader/OCR과 일관성)
            "metadata": None,  # 통합 메타데이터
            "original_path": None,
            "loader_result": None,
            "ocr_result": None,
            "translate_result": None,
            "overlay_result": None,
            "error": None,
        }
        
        try:
            # 1. 소스 경로 결정
            source_path = source_override or self.policy.image.source.path
            source_path = resolve(source_path)
            result["original_path"] = source_path
            
            if not source_path.exists():
                raise FileNotFoundError(f"Image not found: {source_path}")
            
            self.log.info(f"{'='*80}")
            self.log.info(f"🖼️  OTO Pipeline: {source_path.name}")
            self.log.info(f"{'='*80}\n")
            
            # ====================================================================
            # Step 1: ImageLoader - 이미지 로드 및 전처리
            # ====================================================================
            self.log.info("[1/5] ImageLoader: Loading image...")
            loader_result = self.image_loader.run(source_override=source_path)
            
            if not loader_result.get('success'):
                raise RuntimeError(f"ImageLoader failed: {loader_result.get('error')}")
            
            image = loader_result['image']
            result['loader_result'] = loader_result
            self.log.success(f"✅ Image loaded: {image.size} {image.mode}")
            
            # ====================================================================
            # Step 2: ImageTextRecognizer - OCR 실행
            # ====================================================================
            self.log.info("\n[2/5] ImageTextRecognizer: Running OCR...")
            ocr_result = self.image_ocr.run(
                source_override=source_path,
                image=image,  # Image 객체 전달
            )
            
            if not ocr_result.get('success'):
                raise RuntimeError(f"ImageTextRecognizer failed: {ocr_result.get('error')}")
            
            ocr_items: List[OCRItem] = ocr_result['ocr_items']
            preprocessed_image = ocr_result['image']
            result['ocr_result'] = ocr_result
            self.log.success(f"✅ OCR completed: {len(ocr_items)} items")
            
            if not ocr_items:
                self.log.warning("No OCR items found - skipping translation/overlay")
                result['success'] = True
                result['image'] = preprocessed_image
                return result
            
            # ====================================================================
            # Step 3: Translator - 번역 실행
            # ====================================================================
            self.log.info("\n[3/5] Translator: Translating texts...")
            
            # OCRItem에서 텍스트 추출
            original_texts = [item.text for item in ocr_items if item.text]
            
            if not original_texts:
                self.log.warning("No texts to translate")
                result['success'] = True
                result['image'] = preprocessed_image
                return result
            
            self.log.info(f"  Original texts: {len(original_texts)}")
            
            # ✅ Translate 실행 (run 메서드 사용)
            # run()은 배치 번역 + 세그먼트 단위 캐싱 지원
            # DB 캐싱은 pipeline.run()에서 자동 동작:
            # - 캐시 히트: DeepL API 호출 생략
            # - 캐시 미스: 모든 세그먼트를 한 번에 bulk 번역
            try:
                # Translate 인스턴스 재사용 (lazy-loading)
                translated_dict = self.translate.run(original_texts)
                
                # 결과 검증
                if not isinstance(translated_dict, dict):
                    self.log.warning(f"Translation returned non-dict: {type(translated_dict)} - using original texts")
                    translated_dict = {text: text for text in original_texts}
                elif not translated_dict:
                    self.log.warning("Translation returned empty dict - using original texts")
                    translated_dict = {text: text for text in original_texts}
                
                # 누락된 텍스트는 원본 사용
                for text in original_texts:
                    if text not in translated_dict:
                        translated_dict[text] = text
                    
            except Exception as e:
                self.log.error(f"Translation error: {e} - using original texts")
                import traceback
                self.log.debug(traceback.format_exc())
                translated_dict = {text: text for text in original_texts}
            
            result['translate_result'] = translated_dict
            self.log.success(f"✅ Translation completed: {len(translated_dict)} texts")
            
            # ====================================================================
            # Step 4: Conversion - OCRItem → OverlayItemPolicy (Pipeline 책임)
            # ====================================================================
            self.log.info("\n[4/5] Conversion: OCRItem → OverlayItem...")
            
            overlay_items: List[OverlayItemPolicy] = []
            
            for item in ocr_items:
                if not item.text:
                    continue
                
                # 번역된 텍스트 가져오기
                translated_text = translated_dict.get(item.text, item.text)
                
                # OCRItem.to_overlay_item() 사용
                overlay_item = item.to_overlay_item(text_override=translated_text)
                overlay_items.append(overlay_item)
            
            self.log.success(f"✅ Converted: {len(overlay_items)} overlay items")
            
            # ====================================================================
            # Step 5: ImageOverlayer - 오버레이 렌더링
            # ====================================================================
            self.log.info("\n[5/5] ImageOverlayer: Rendering overlay...")
            
            overlay_result = self.image_overlay.run(
                source_override=source_path,
                image=preprocessed_image,  # OCR 전처리된 이미지 사용
                overlay_items=overlay_items,  # 변환된 아이템 전달
            )
            
            if not overlay_result.get('success'):
                raise RuntimeError(f"ImageOverlayer failed: {overlay_result.get('error')}")
            
            result['overlay_result'] = overlay_result
            result['image'] = overlay_result['image']
            self.log.success(f"✅ Overlay completed")
            
            # ====================================================================
            # 통합 메타데이터
            # ====================================================================
            result['metadata'] = {
                "original_path": str(source_path),
                "loader": loader_result.get('metadata'),
                "ocr": {
                    "items_count": len(ocr_items),
                    "items": [item.model_dump() for item in ocr_items],
                },
                "translate": {
                    "count": len(translated_dict),
                    "translations": translated_dict,
                },
                "overlay": overlay_result.get('metadata'),
            }
            
            result['success'] = True
            
            self.log.info(f"\n{'='*80}")
            self.log.success(f"✅ OTO Pipeline Completed: {source_path.name}")
            self.log.info(f"{'='*80}\n")
            
        except FileNotFoundError as e:
            result['error'] = f"File not found: {e}"
            self.log.error(result['error'])
        except RuntimeError as e:
            result['error'] = str(e)
            self.log.error(result['error'])
        except Exception as e:
            result['error'] = f"Unexpected error: {type(e).__name__}: {e}"
            self.log.error(result['error'])
            
            import traceback
            self.log.error(traceback.format_exc())
        
        return result
    
    def __repr__(self) -> str:
        return f"OTO(source={self.policy.image.source.path})"


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
            # 단일 이미지
            result = oto.run(source_override=args.images[0], **overrides)
            
            if result['success']:
                print("\n✅ 처리 성공!")
                print(f"   최종 이미지: {result['image'].size if result['image'] else 'N/A'}")
                sys.exit(0)
            else:
                print(f"\n❌ 처리 실패: {result.get('error')}")
                sys.exit(1)
        else:
            # 다중 이미지 (반복 호출)
            print(f"📸 다중 이미지 처리: {len(args.images)}개\n")
            results = []
            
            for idx, image_path in enumerate(args.images, 1):
                print(f"[{idx}/{len(args.images)}] {Path(image_path).name}")
                result = oto.run(source_override=image_path, **overrides)
                results.append(result)
            
            # 요약
            success_count = sum(1 for r in results if r.get('success'))
            failed = [r for r in results if not r.get('success')]
            
            print(f"\n📊 처리 결과: 성공 {success_count}/{len(args.images)}개")
            
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


