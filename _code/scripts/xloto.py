# -*- coding: utf-8 -*-
"""
scripts/xloto.py
Excel 기반 이미지 OCR/번역/오버레이 자동화 스크립트

업무 흐름:
1. 환경변수(CASHOP_PATHS)에서 paths.local.yaml 로드
2. excel.yaml, xloto.yaml 설정 로드
3. XlController로 Excel 데이터 읽기 (DataFrame)
4. download=날짜, translation≠날짜인 행 필터링 → CAS No 리스트 + 셀 주소 추출
5. original 폴더에 있고 translated 폴더에 없는 이미지 OCR/번역/오버레이 처리
6. 처리 완료 후 translation 셀에 현재 날짜 기록

성능 최적화:
- OCR 인스턴스 재사용 (GPU 메모리 절약)
- Translator 인스턴스 재사용 (캐시 공유)
- Batch Translation (API 호출 횟수 최소화)
"""

from __future__ import annotations
import os
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
import pandas as pd

# ===== 환경변수 자동 설정 =====
# CASHOP_PATHS가 설정되지 않은 경우 setup_env.py 실행
if "CASHOP_PATHS" not in os.environ:
    setup_script = Path(__file__).parent / "setup_env.py"
    if setup_script.exists():
        print("⚠️  CASHOP_PATHS 환경변수 미설정. 자동 설정 시도...")
        try:
            # setup_env.py 실행
            exec(setup_script.read_text(encoding='utf-8'))
            from setup_env import setup_cashop_env
            if not setup_cashop_env(verbose=True):
                print("❌ 환경변수 자동 설정 실패. 수동 설정 필요.")
                sys.exit(1)
        except Exception as e:
            print(f"❌ setup_env.py 실행 실패: {e}")
            print("   수동으로 환경변수를 설정하세요:")
            print('   $env:CASHOP_PATHS = "M:\\CALife\\CAShop - 구매대행\\_code\\configs\\paths.local.yaml"')
            sys.exit(1)

# PYTHONPATH: M:\CALife\CAShop - 구매대행\_code\modules
from cfg_utils import ConfigLoader
from xl_utils import XlController
from image_utils import ImageTextRecognizer, ImageOverlayer
from translate_utils import Translator


class XlOtoConfig:
    """환경변수 기반 설정 로더"""
    
    PATHS_ENV_KEY = "CASHOP_PATHS"
    
    def __init__(self):
        self.paths_yaml = self._get_paths_yaml()
        self.paths = ConfigLoader(self.paths_yaml).as_dict()
        
        # Excel/XLOTO 설정 경로
        self.excel_cfg_path = str(self.paths.get("configs_excel", ""))
        self.xloto_cfg_path = str(self.paths.get("configs_xloto", ""))
        
        # 이미지 디렉토리
        self.public_img_dir = Path(str(self.paths.get("public_img_dir", "")))
        self.origin_dirname = str(self.paths.get("public_img_origin_dirname", "original"))
        self.translated_dirname = str(self.paths.get("public_img_tr_dirname", "translated"))
    
    def _get_paths_yaml(self) -> str:
        """환경변수에서 paths.local.yaml 경로 가져오기"""
        paths_env = os.getenv(self.PATHS_ENV_KEY)
        
        if not paths_env:
            raise EnvironmentError(
                f"환경변수 '{self.PATHS_ENV_KEY}'가 설정되지 않았습니다.\n"
                f"다음 명령으로 설정하세요:\n"
                f'  Windows (PowerShell): $env:{self.PATHS_ENV_KEY}="M:\\CALife\\CAShop - 구매대행\\_code\\configs\\paths.local.yaml"\n'
                f'  Windows (CMD): set {self.PATHS_ENV_KEY}=M:\\CALife\\CAShop - 구매대행\\_code\\configs\\paths.local.yaml'
            )
        
        if not Path(paths_env).exists():
            raise FileNotFoundError(
                f"환경변수 '{self.PATHS_ENV_KEY}'가 가리키는 파일이 존재하지 않습니다: {paths_env}"
            )
        
        return paths_env


class CASNoExtractor:
    """DataFrame에서 처리 대상 CAS No 및 셀 주소 추출"""
    
    def __init__(self, df: pd.DataFrame, column_aliases: Dict[str, List[str]]):
        self.df = df
        self.aliases = column_aliases
    
    def _resolve_column(self, key: str) -> Optional[str]:
        """컬럼 별칭 → 실제 컬럼명 매핑"""
        aliases = self.aliases.get(key, [])
        for col in self.df.columns:
            col_lower = str(col).lower().strip()
            if col_lower in [a.lower().strip() for a in aliases]:
                return col
        return None
    
    def extract_target_rows(self) -> pd.DataFrame:
        """download=날짜, translation≠날짜인 행 필터링"""
        cas_col = self._resolve_column("cas")
        download_col = self._resolve_column("download")
        translation_col = self._resolve_column("translation")
        
        if not all([cas_col, download_col, translation_col]):
            raise ValueError(
                f"필수 컬럼을 찾을 수 없습니다: "
                f"cas={cas_col}, download={download_col}, translation={translation_col}"
            )
        
        # download 컬럼이 날짜이고, translation 컬럼이 날짜가 아닌 행
        target_df = self.df[
            (pd.to_datetime(self.df[download_col], errors='coerce').notna()) &
            (pd.to_datetime(self.df[translation_col], errors='coerce').isna())
        ].copy()
        
        # CAS No, 셀 주소 저장
        target_df['_cas_no'] = target_df[cas_col].astype(str)
        target_df['_translation_row'] = target_df.index + 2  # Excel은 1-based, header 고려
        target_df['_translation_col'] = translation_col
        
        return target_df[[cas_col, download_col, translation_col, '_cas_no', '_translation_row', '_translation_col']]
    
    def get_cas_list_with_cell_info(self) -> List[Dict[str, Any]]:
        """CAS No 리스트 + 셀 정보 반환"""
        target_df = self.extract_target_rows()
        
        return [
            {
                'cas_no': str(row['_cas_no']),
                'translation_row': int(row['_translation_row']),
                'translation_col': str(row['_translation_col']),
            }
            for _, row in target_df.iterrows()
        ]


class ImageOTOProcessor:
    """이미지 OCR/번역/오버레이 처리
    
    성능 최적화:
    - OCR 인스턴스 재사용 (GPU 메모리 절약)
    - Translator 인스턴스 재사용
    - Batch Translation (API 호출 횟수 최소화)
    """
    
    def __init__(
        self,
        xloto_cfg_path: str,
        public_img_dir: Path,
        origin_dirname: str,
        translated_dirname: str,
    ):
        self.xloto_cfg_path = xloto_cfg_path
        self.public_img_dir = public_img_dir
        self.origin_dirname = origin_dirname
        self.translated_dirname = translated_dirname
        
        # ===== 성능 최적화: 인스턴스 재사용 =====
        # OCR 인스턴스 (한 번만 생성, GPU 메모리 절약)
        self.ocr = ImageTextRecognizer(
            self.xloto_cfg_path,
            section="ocr",
        )
        
        # Translator: Config만 로드 (provider, cache 설정)
        # 실제 번역 시 매번 새 인스턴스 생성하지만, Cache는 공유됨
        self.xloto_cfg_path_for_translate = xloto_cfg_path
    
    def get_missing_images(self, cas_no: str) -> List[Path]:
        """translated 폴더에 없는 original 이미지 파일 반환"""
        origin_dir = self.public_img_dir / cas_no / self.origin_dirname
        translated_dir = self.public_img_dir / cas_no / self.translated_dirname
        
        if not origin_dir.exists():
            return []
        
        # Original 폴더의 모든 이미지 파일
        origin_images = []
        for ext in ['*.jpg', '*.jpeg', '*.png', '*.JPG', '*.JPEG', '*.PNG']:
            origin_images.extend(list(origin_dir.glob(ext)))
        
        # Translated 폴더에 없는 파일만 필터링
        missing_images = []
        for img_path in origin_images:
            # 확장자를 제외한 이름으로 비교
            base_name = img_path.stem
            
            # translated 폴더에 같은 이름의 파일이 있는지 확인 (확장자 무관)
            found = False
            if translated_dir.exists():
                for ext in ['.jpg', '.jpeg', '.png', '.JPG', '.JPEG', '.PNG']:
                    if (translated_dir / f"{base_name}{ext}").exists():
                        found = True
                        break
            
            if not found:
                missing_images.append(img_path)
        
        return missing_images
    
    def process_image(self, image_path: Path, output_dir: Path) -> bool:
        """단일 이미지 OCR/번역/오버레이 처리
        
        성능 최적화:
        - OCR 인스턴스 재사용 (source_override만 사용)
        - Batch Translation (모든 OCR 결과를 한 번에 번역)
        - Translator 인스턴스 재사용 (캐시 공유)
        """
        try:
            print(f"     🔍 OCR 실행: {image_path.name}")
            
            # ===== 1. ImageTextRecognizer: OCR 실행 (인스턴스 재사용) =====
            ocr_result = self.ocr.run(source_override=str(image_path))
            
            # OCR 결과 확인
            if not ocr_result or not ocr_result.get('success'):
                error_msg = ocr_result.get('error', 'Unknown error') if ocr_result else 'No result'
                print(f"        ⚠️  OCR 실패: {error_msg}")
                return False
            
            ocr_items = ocr_result.get('ocr_items', [])
            if not ocr_items:
                print(f"        ⚠️  OCR 결과 없음")
                return False
            
            print(f"        ✅ OCR 완료: {len(ocr_items)}개 텍스트")
            
            # ===== 2. 번역 (Override 패턴으로 최적화) =====
            print(f"        🔤 번역 중...")
            
            # 모든 OCR 텍스트 추출
            original_texts = []
            bboxes = []
            
            for ocr_item in ocr_items:
                original_text = ocr_item.text if hasattr(ocr_item, 'text') else ocr_item.get('text', '')
                bbox = ocr_item.bbox if hasattr(ocr_item, 'bbox') else ocr_item.get('bbox', [0, 0, 100, 100])
                
                if not original_text:
                    continue
                
                original_texts.append(original_text)
                bboxes.append(bbox)
            
            if not original_texts:
                print(f"        ⚠️  번역할 텍스트 없음")
                return False
            
            # Translator.run() with source__text override (Batch Translation)
            # 인스턴스는 재사용하되, source 텍스트만 동적으로 주입
            try:
                # Config에서 provider 설정만 가져오고, source는 runtime override
                temp_translator = Translator(
                    self.xloto_cfg_path,
                    source__text=original_texts,  # 동적 텍스트 주입
                    provider__source_lang="ZH",
                    provider__target_lang="KO"
                )
                translation_result = temp_translator.run()
                
                # Dict[str, str] → List[str] 변환
                translated_texts = [translation_result.get(text, text) for text in original_texts]
                print(f"        ✅ 번역 완료: {len(translated_texts)}개")
            except Exception as e:
                print(f"        ⚠️  번역 실패: {e}")
                # 번역 실패 시 원본 텍스트 사용
                translated_texts = original_texts
            
            # 오버레이용 데이터 생성
            overlay_texts = [
                {
                    'bbox': bboxes[i],
                    'text': translated_texts[i],
                }
                for i in range(len(translated_texts))
            ]
            
            # ===== 3. ImageOverlayer: 오버레이 적용 =====
            print(f"        🎨 오버레이 적용 중...")
            
            overlay = ImageOverlayer(
                self.xloto_cfg_path,
                section="overlay",
                source__path=str(image_path),
                save__directory=str(output_dir),
                texts=overlay_texts,
            )
            
            overlay_result = overlay.run(source_override=str(image_path))
            
            if not overlay_result or not overlay_result.get('success'):
                error_msg = overlay_result.get('error', 'Unknown error') if overlay_result else 'No result'
                print(f"        ⚠️  오버레이 실패: {error_msg}")
                return False
            
            saved_path = overlay_result.get('saved_path')
            print(f"        ✅ 저장 완료: {saved_path.name if saved_path else 'Unknown'}")
            
            return True
            
        except Exception as e:
            print(f"        ❌ 처리 실패: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def process_cas_no(self, cas_no: str) -> int:
        """CAS No의 모든 미처리 이미지 처리"""
        missing_images = self.get_missing_images(cas_no)
        
        if not missing_images:
            print(f"  ℹ️  {cas_no}: 처리할 이미지 없음")
            return 0
        
        print(f"\n  📸 {cas_no}: {len(missing_images)}개 이미지 처리 시작")
        
        translated_dir = self.public_img_dir / cas_no / self.translated_dirname
        translated_dir.mkdir(parents=True, exist_ok=True)
        
        success_count = 0
        for idx, img_path in enumerate(missing_images, 1):
            print(f"\n     [{idx}/{len(missing_images)}] {img_path.name}")
            if self.process_image(img_path, translated_dir):
                success_count += 1
        
        print(f"\n  ✅ {cas_no}: {success_count}/{len(missing_images)}개 성공")
        return success_count


class XlOtoRunner:
    """메인 실행 로직"""
    
    def __init__(self, config: XlOtoConfig):
        self.config = config
    
    def run(self):
        """전체 워크플로우 실행"""
        print("=" * 80)
        print("XLOTO - Excel 기반 이미지 OCR/번역/오버레이 자동화")
        print("=" * 80)
        
        # 1. Excel 데이터 로드
        print("\n[1/5] Excel 데이터 로드 중...")
        print(f"  📁 파일: {self.config.excel_cfg_path}")
        
        with XlController(self.config.excel_cfg_path) as xl:
            ws = xl.get_worksheet()
            df = ws.to_dataframe(anchor="A1", header=True, index=False)
        
        print(f"  ✅ {len(df)}개 행 로드 완료")
        
        # 2. Column aliases 로드 및 CAS No 추출
        print("\n[2/5] 처리 대상 CAS No 추출 중...")
        excel_config = ConfigLoader(self.config.excel_cfg_path).as_dict()
        column_aliases = excel_config.get("excel", {}).get("aliases", {})
        
        extractor = CASNoExtractor(df, column_aliases)
        target_list = extractor.get_cas_list_with_cell_info()
        
        print(f"  ✅ {len(target_list)}개 CAS No 추출 완료")
        if target_list:
            for item in target_list[:5]:  # 최대 5개만 출력
                print(f"     - {item['cas_no']} (Row {item['translation_row']})")
            if len(target_list) > 5:
                print(f"     ... 외 {len(target_list) - 5}개")
        
        if not target_list:
            print("\n⚠️  처리할 항목이 없습니다.")
            return
        
        # 3. 이미지 OCR/번역/오버레이 처리
        print("\n[3/5] 이미지 처리 시작...")
        print(f"  📁 원본 폴더: {self.config.origin_dirname}")
        print(f"  📁 번역 폴더: {self.config.translated_dirname}")
        
        processor = ImageOTOProcessor(
            self.config.xloto_cfg_path,
            self.config.public_img_dir,
            self.config.origin_dirname,
            self.config.translated_dirname,
        )
        
        processed_cas_list = []
        for idx, item in enumerate(target_list, 1):
            print(f"\n{'='*80}")
            print(f"[{idx}/{len(target_list)}] {item['cas_no']}")
            print(f"{'='*80}")
            
            cas_no = item['cas_no']
            success_count = processor.process_cas_no(cas_no)
            
            if success_count > 0:
                processed_cas_list.append(item)
        
        print(f"\n{'='*80}")
        print(f"[3/5] ✅ {len(processed_cas_list)}/{len(target_list)}개 CAS No 처리 완료")
        print(f"{'='*80}")
        
        # 4. Excel translation 셀에 날짜 기록
        if processed_cas_list:
            print("\n[4/5] Excel translation 셀 업데이트 중...")
            current_date = datetime.now().strftime("%Y-%m-%d")
            
            with XlController(self.config.excel_cfg_path) as xl:
                ws = xl.get_worksheet()
                
                # translation 컬럼 인덱스 찾기
                translation_col_name = processed_cas_list[0]['translation_col']
                col_idx_result = df.columns.get_loc(translation_col_name)
                
                # get_loc이 int가 아닌 경우 처리
                if isinstance(col_idx_result, int):
                    translation_col_idx = col_idx_result + 1  # 1-based
                else:
                    # slice나 array인 경우 첫 번째 요소 사용
                    translation_col_idx = 1  # fallback
                
                for item in processed_cas_list:
                    row = int(item['translation_row'])
                    ws.write_cell(row, translation_col_idx, current_date)
                    print(f"     ✅ {item['cas_no']}: ({row}, {translation_col_idx}) = {current_date}")
            
            print(f"  ✅ {len(processed_cas_list)}개 셀 업데이트 완료")
        else:
            print("\n[4/5] 처리된 항목이 없어 Excel 업데이트를 건너뜁니다.")
        
        # 5. 완료
        print("\n[5/5] 작업 완료!")
        print("=" * 80)
        print(f"📊 총 {len(target_list)}개 CAS No 중 {len(processed_cas_list)}개 처리 완료")
        print("=" * 80)


def main():
    """메인 엔트리포인트"""
    try:
        # 설정 로드
        config = XlOtoConfig()
        
        # 실행
        runner = XlOtoRunner(config)
        runner.run()
        
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
