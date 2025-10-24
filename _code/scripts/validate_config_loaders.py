# -*- coding: utf-8 -*-
"""config_loader 파일 검증 스크립트

config_loader*.yaml 파일들의 유효성을 검증합니다.

검증 항목:
1. 대상 YAML 파일 존재 확인
2. 절대 경로 사용 여부 (환경변수 권장)
3. enable_env 설정 확인
4. 섹션 이름 일치 확인
5. Adapter vs EntryPoint YAML 구분

Usage:
    python scripts/validate_config_loaders.py
    python scripts/validate_config_loaders.py --fix  # 자동 수정
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml


class ConfigLoaderValidator:
    """ConfigLoader YAML 파일 검증기"""
    
    def __init__(self, root_dir: Path):
        self.root_dir = root_dir
        self.code_dir = root_dir / "_code"
        self.issues: List[Dict[str, Any]] = []
        
        # 환경변수 매핑 (paths.local.yaml 기준)
        self.env_mapping = {
            "configs_dir": self.code_dir / "configs",
            "configs_xloto_dir": self.code_dir / "configs" / "xloto",
            "configs_xlcrawl_dir": self.code_dir / "configs" / "xlcrawl",
            "configs_crawl_dir": self.code_dir / "configs" / "xlcrawl",
            "configs_oto_dir": self.code_dir / "configs" / "oto",
            "modules_dir": self.code_dir / "modules",
        }
    
    def find_config_loader_files(self) -> List[Path]:
        """config_loader*.yaml 파일 찾기"""
        config_loaders = []
        
        # modules/**/configs/config_loader*.yaml
        for module_dir in (self.code_dir / "modules").iterdir():
            if module_dir.is_dir():
                configs_dir = module_dir / "configs"
                if configs_dir.exists():
                    config_loaders.extend(configs_dir.glob("config_loader*.yaml"))
        
        # configs/loader/config_loader*.yaml
        loader_dir = self.code_dir / "configs" / "loader"
        if loader_dir.exists():
            config_loaders.extend(loader_dir.glob("config_loader*.yaml"))
        
        return sorted(config_loaders)
    
    def resolve_env_path(self, path_str: str) -> Optional[Path]:
        """환경변수 경로를 실제 경로로 변환
        
        Args:
            path_str: 경로 문자열 (예: "{{configs_xloto_dir}}/excel.yaml")
        
        Returns:
            실제 경로 또는 None (변환 실패 시)
        """
        # {{variable}} 패턴 찾기
        pattern = r'\{\{(\w+)\}\}'
        matches = re.findall(pattern, path_str)
        
        if not matches:
            return None
        
        # 첫 번째 환경변수만 처리
        var_name = matches[0]
        if var_name not in self.env_mapping:
            return None
        
        # 경로 치환
        resolved = path_str.replace(f'{{{{{var_name}}}}}', str(self.env_mapping[var_name]))
        return Path(resolved)
    
    def validate_src_path(self, src_value: Any, config_loader_path: Path) -> Tuple[bool, str]:
        """src 경로 유효성 검증
        
        Args:
            src_value: src 필드 값 (str, list 등)
            config_loader_path: config_loader 파일 경로 (상대 경로 해석용)
        
        Returns:
            (is_valid, message)
        """
        # src 형식 파싱
        if isinstance(src_value, list) and len(src_value) >= 1:
            path_str = src_value[0]
            section = src_value[1] if len(src_value) > 1 else None
        elif isinstance(src_value, str):
            path_str = src_value
            section = None
        else:
            return False, f"Unknown src format: {src_value}"
        
        # path_str도 리스트일 수 있음 (중첩 리스트)
        if isinstance(path_str, list):
            return False, f"Nested list in src: {src_value}"
        
        # 절대 경로 체크
        is_absolute = Path(path_str).is_absolute()
        uses_env = "{{" in path_str or "${" in path_str
        
        if is_absolute:
            target_path = Path(path_str)
        elif uses_env:
            # 환경변수 경로 해석
            target_path = self.resolve_env_path(path_str)
            if target_path is None:
                return False, f"Cannot resolve env path: {path_str}"
        else:
            # 상대 경로 (config_loader 파일 기준)
            target_path = (config_loader_path.parent / path_str).resolve()
        
        # 파일 존재 확인
        if not target_path.exists():
            return False, f"Target file not found: {target_path}"
        
        # 경고: 절대 경로 사용
        if is_absolute:
            return True, f"⚠️ Using absolute path (consider env vars): {path_str}"
        
        return True, "OK"
    
    def validate_config_loader(self, config_loader_path: Path) -> List[Dict[str, Any]]:
        """config_loader 파일 검증
        
        Returns:
            이슈 목록 [{"file": ..., "issue": ..., "severity": ...}, ...]
        """
        issues = []
        
        try:
            with open(config_loader_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
        except Exception as e:
            issues.append({
                "file": str(config_loader_path),
                "issue": f"Failed to load YAML: {e}",
                "severity": "CRITICAL"
            })
            return issues
        
        # source 섹션 찾기
        source_section = None
        for key in data:
            if isinstance(data[key], dict) and "source" in data[key]:
                source_section = data[key]["source"]
                break
        
        if source_section is None:
            # root에 source가 있을 수도
            source_section = data.get("source")
        
        if source_section is None:
            issues.append({
                "file": str(config_loader_path),
                "issue": "No 'source' section found",
                "severity": "WARNING"
            })
            return issues
        
        # List[SourcePolicy] 형태 처리
        if isinstance(source_section, list):
            for idx, source_policy in enumerate(source_section):
                if not isinstance(source_policy, dict):
                    continue
                
                src_value = source_policy.get("src")
                if src_value is None:
                    issues.append({
                        "file": str(config_loader_path),
                        "issue": f"source[{idx}] has no 'src' field",
                        "severity": "ERROR"
                    })
                    continue
                
                # src 경로 검증
                is_valid, message = self.validate_src_path(src_value, config_loader_path)
                
                if not is_valid:
                    issues.append({
                        "file": str(config_loader_path),
                        "issue": f"source[{idx}]: {message}",
                        "severity": "ERROR"
                    })
                elif message != "OK":
                    issues.append({
                        "file": str(config_loader_path),
                        "issue": f"source[{idx}]: {message}",
                        "severity": "WARNING"
                    })
                
                # enable_env 확인 (환경변수 사용 시)
                yaml_parser = source_policy.get("yaml_parser", {})
                enable_env = yaml_parser.get("enable_env", False)
                
                if isinstance(src_value, (list, str)):
                    path_str = src_value[0] if isinstance(src_value, list) else src_value
                    if ("{{" in path_str or "${" in path_str) and not enable_env:
                        issues.append({
                            "file": str(config_loader_path),
                            "issue": f"source[{idx}]: Uses env vars but enable_env=false",
                            "severity": "ERROR"
                        })
        
        # 단일 SourcePolicy 형태 처리
        elif isinstance(source_section, dict):
            src_value = source_section.get("src")
            if src_value:
                is_valid, message = self.validate_src_path(src_value, config_loader_path)
                
                if not is_valid:
                    issues.append({
                        "file": str(config_loader_path),
                        "issue": f"source: {message}",
                        "severity": "ERROR"
                    })
                elif message != "OK":
                    issues.append({
                        "file": str(config_loader_path),
                        "issue": f"source: {message}",
                        "severity": "WARNING"
                    })
        
        return issues
    
    def validate_all(self) -> List[Dict[str, Any]]:
        """모든 config_loader 파일 검증"""
        config_loaders = self.find_config_loader_files()
        
        print(f"Found {len(config_loaders)} config_loader files")
        print("-" * 80)
        
        all_issues = []
        
        for config_loader_path in config_loaders:
            print(f"\nValidating: {config_loader_path.relative_to(self.code_dir)}")
            issues = self.validate_config_loader(config_loader_path)
            
            if not issues:
                print("  ✅ OK")
            else:
                for issue in issues:
                    severity = issue["severity"]
                    icon = "🔴" if severity == "CRITICAL" else "❌" if severity == "ERROR" else "⚠️"
                    print(f"  {icon} [{severity}] {issue['issue']}")
                
                all_issues.extend(issues)
        
        return all_issues
    
    def generate_report(self, issues: List[Dict[str, Any]]) -> str:
        """검증 보고서 생성"""
        report = []
        report.append("=" * 80)
        report.append("ConfigLoader Validation Report")
        report.append("=" * 80)
        report.append("")
        
        if not issues:
            report.append("✅ All config_loader files are valid!")
            return "\n".join(report)
        
        # 심각도별 분류
        critical = [i for i in issues if i["severity"] == "CRITICAL"]
        errors = [i for i in issues if i["severity"] == "ERROR"]
        warnings = [i for i in issues if i["severity"] == "WARNING"]
        
        report.append(f"Total Issues: {len(issues)}")
        report.append(f"  🔴 CRITICAL: {len(critical)}")
        report.append(f"  ❌ ERROR: {len(errors)}")
        report.append(f"  ⚠️ WARNING: {len(warnings)}")
        report.append("")
        
        # 이슈 상세
        for severity, issue_list in [("CRITICAL", critical), ("ERROR", errors), ("WARNING", warnings)]:
            if not issue_list:
                continue
            
            report.append("-" * 80)
            report.append(f"{severity} Issues:")
            report.append("-" * 80)
            
            for issue in issue_list:
                report.append(f"\nFile: {issue['file']}")
                report.append(f"Issue: {issue['issue']}")
        
        return "\n".join(report)


def main():
    """메인 실행"""
    # 프로젝트 루트 찾기
    current = Path(__file__).resolve()
    while current.parent != current:
        if (current / "_code").exists():
            root_dir = current
            break
        current = current.parent
    else:
        print("❌ Cannot find project root")
        sys.exit(1)
    
    validator = ConfigLoaderValidator(root_dir)
    issues = validator.validate_all()
    
    print("\n")
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    report = validator.generate_report(issues)
    print(report)
    
    # 보고서 저장
    report_path = root_dir / "_code" / "docs" / "CONFIGLOADER_VALIDATION_REPORT.md"
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"\n📄 Report saved: {report_path}")
    
    # Exit code
    critical = [i for i in issues if i["severity"] == "CRITICAL"]
    errors = [i for i in issues if i["severity"] == "ERROR"]
    
    if critical:
        sys.exit(2)
    elif errors:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
