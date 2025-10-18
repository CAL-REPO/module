# -*- coding: utf-8 -*-
"""Configuration 소스 구현체."""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Union

from pydantic import BaseModel

from modules.keypath_utils import KeyPathDict

from ..core.interface import ConfigSource
from ..core.policy import SourcePolicy


class BaseModelSource(ConfigSource):
    """Pydantic BaseModel 소스.
    
    BaseModel은 이미 Python 객체이므로 yaml_parser 불필요.
    SourcePolicy의 normalizer로 키 정규화, 빈 값 제거 등 가능.
    
    Examples:
        >>> from image_utils import ImageLoaderPolicy
        >>> from cfg_utils_v2.core.policy import SourcePolicy, NormalizePolicy
        >>> 
        >>> image_policy = ImageLoaderPolicy()
        >>> source_policy = SourcePolicy(normalizer=NormalizePolicy(drop_blanks=True))
        >>> source = BaseModelSource(
        ...     image_policy,
        ...     section="image",
        ...     policy=source_policy
        ... )
        >>> kpd = source.extract()
    """

    def __init__(
        self,
        data: BaseModel,
        section: Optional[str] = None,
        policy: Optional[SourcePolicy] = None,
    ):
        """초기화.
        
        Args:
            data: BaseModel 인스턴스
            section: Section 이름
            policy: SourcePolicy (normalizer, merge 포함)
        """
        super().__init__(
            data=data,
            section=section,
            policy=policy
        )

    def extract(self) -> KeyPathDict:
        """BaseModel → dict → 정규화.
        
        Returns:
            정규화된 KeyPathDict
        
        Raises:
            TypeError: data가 BaseModel이 아닌 경우
        """
        if not isinstance(self.raw_data, BaseModel):
            raise TypeError(f"Expected BaseModel, got {type(self.raw_data)}")
        
        # 1. BaseModel → dict
        data = self.raw_data.model_dump()
        
        # 2. Section 적용
        data = self._apply_section(data)
        
        # 3. 정규화
        kpd = KeyPathDict(data=data)
        kpd = self._normalize(kpd, stage="extract")
        
        return kpd


class DictSource(ConfigSource):
    """딕셔너리 소스.
    
    dict는 이미 Python 객체이므로 yaml_parser 불필요.
    SourcePolicy의 normalizer로 키 정규화, 빈 값 제거 등 가능.
    
    Examples:
        >>> from cfg_utils_v2.core.policy import SourcePolicy, NormalizePolicy
        >>> 
        >>> policy = SourcePolicy(normalizer=NormalizePolicy(drop_blanks=True))
        >>> source = DictSource(
        ...     {"max_width": 1024, "empty": ""},
        ...     section="image",
        ...     policy=policy
        ... )
        >>> kpd = source.extract()
        >>> kpd.data
        {"image": {"max_width": 1024}}  # empty 제거됨
    """

    def __init__(
        self,
        data: dict,
        section: Optional[str] = None,
        policy: Optional[SourcePolicy] = None,
    ):
        """초기화.
        
        Args:
            data: dict 데이터
            section: Section 이름
            policy: SourcePolicy (normalizer, merge 포함)
        """
        super().__init__(
            data=data,
            section=section,
            policy=policy
        )

    def extract(self) -> KeyPathDict:
        """dict → 정규화.
        
        Returns:
            정규화된 KeyPathDict
        
        Raises:
            TypeError: data가 dict가 아닌 경우
        """
        if not isinstance(self.raw_data, dict):
            raise TypeError(f"Expected dict, got {type(self.raw_data)}")
        
        # 1. dict 복사
        data = self.raw_data.copy()
        
        # 2. Section 적용
        data = self._apply_section(data)
        
        # 3. 정규화
        kpd = KeyPathDict(data=data)
        kpd = self._normalize(kpd, stage="extract")
        
        return kpd


class YamlFileSource(ConfigSource):
    """YAML 파일 소스.
    
    YAML 파일은 SourcePolicy의 yaml_parser와 normalizer 사용.
    
    Examples:
        >>> from cfg_utils_v2.core.policy import SourcePolicy, YamlParserPolicy, NormalizePolicy
        >>> 
        >>> policy = SourcePolicy(
        ...     yaml_parser=YamlParserPolicy(enable_env=True),
        ...     normalizer=NormalizePolicy(drop_blanks=True)
        ... )
        >>> source = YamlFileSource(
        ...     "config.yaml",
        ...     section="image",
        ...     policy=policy
        ... )
        >>> kpd = source.extract()
    """
    
    def __init__(
        self,
        path: Union[str, Path],
        section: Optional[str] = None,
        policy: Optional[SourcePolicy] = None,
    ):
        """초기화.
        
        Args:
            path: YAML 파일 경로
            section: Section 이름
            policy: SourcePolicy (yaml_parser, normalizer, merge 포함)
        """
        super().__init__(
            data=path,
            section=section,
            policy=policy
        )
    
    def extract(self) -> KeyPathDict:
        """YAML 파일 → 파싱 → 정규화.
        
        Returns:
            정규화된 KeyPathDict
        
        Raises:
            FileNotFoundError: YAML 파일이 없는 경우
        """
        from modules.structured_io.formats.yaml_io import YamlParser
        from ..core.policy import YamlParserPolicy
        
        path = Path(self.raw_data)
        if not path.exists():
            raise FileNotFoundError(f"YAML file not found: {path}")
        
        # 1. yaml_parser 정책 가져오기 (policy.yaml_parser 또는 기본값)
        yaml_parser_policy = None
        if self.policy is not None and self.policy.yaml_parser is not None:
            yaml_parser_policy = self.policy.yaml_parser
        else:
            # 기본 parser 정책
            yaml_parser_policy = YamlParserPolicy(
                encoding="utf-8",
                safe_mode=True
            )
        
        # 2. YAML 파싱
        parser = YamlParser(policy=yaml_parser_policy)
        text = path.read_text(encoding=yaml_parser_policy.encoding)
        data = parser.parse(text, base_path=path.parent)
        
        # 3. Section 적용
        data = self._apply_section(data)
        
        # 4. 정규화 (policy.normalizer 적용)
        kpd = KeyPathDict(data=data)
        kpd = self._normalize(kpd, stage="extract")
        
        return kpd
