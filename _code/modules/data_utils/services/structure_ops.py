"""
data_utils.services.structure_ops
---------------------------------
Data structure transformation utilities for nested lists, dicts, and key-paths.
"""

from __future__ import annotations
from typing import Any, Dict, List, Tuple
from boltons.iterutils import remap


class StructureOps:
    """Static utility class for transforming data structures.

    The core methods provided include:

    1. :meth:`value_to_list` – Normalize a value into a list.
    2. :meth:`list_to_grouped_pairs` – Convert a flat list into a grouped pair structure.
    3. :meth:`group_pairs_to_multivalue` – Merge grouped pairs into a multi‑valued dictionary.
    4. :meth:`dict_to_keypath` – Flatten nested dictionaries into keypath dictionaries.
    5. :meth:`keypath_to_dict` – Restore nested dictionaries from keypath dictionaries.

    The standard return types are defined in :mod:`data_utils.types` as
    ``GroupedPairDict`` and ``MultiValueGroupDict``.
    """

    @staticmethod
    def value_to_list(x: Any) -> List[Any]:
        """Normalize the input into a list.

        If ``x`` is ``None``, an empty list is returned. If ``x`` is already a
        list or tuple, it is converted to a list. Otherwise, ``x`` is wrapped
        in a single‑element list.

        Examples::

            >>> StructureOps.value_to_list(5)
            [5]
            >>> StructureOps.value_to_list([5, 6])
            [5, 6]
            >>> StructureOps.value_to_list(None)
            []
        """
        if x is None:
            return []
        if isinstance(x, list):
            return x
        if isinstance(x, tuple):
            return list(x)
        return [x]

    @staticmethod
    def list_to_grouped_pairs(
        seq: List[Any],
        group_size: int = 3,
        *,
        section_index: int = 0,
        key_index: int = 1,
        value_index: int = 2,
        skip_missing: bool = False,
    ) -> Dict[str | None, List[Tuple[str | None, Any]]]:
        """Convert a flat list into a grouped pair dictionary.

        The input sequence is interpreted in groups of ``group_size`` elements,
        where each group represents ``(section, key, value)``.  Elements are
        coerced to strings if not ``None``.  Optionally, entries with missing
        keys or values can be skipped.

        Args:
            seq: The flat list to transform.
            group_size: Number of elements per group. Defaults to ``3``.
            section_index: Index of the section element within each group.
            key_index: Index of the key element within each group.
            value_index: Index of the value element within each group.
            skip_missing: If ``True``, skip groups where ``key`` or ``value`` is ``None``.

        Returns:
            A dictionary mapping section names to lists of ``(key, value)`` pairs.
        """
        out: Dict[str | None, List[Tuple[str | None, Any]]] = {}
        if not isinstance(seq, list) or len(seq) % group_size != 0:
            return out
        for i in range(0, len(seq), group_size):
            group = seq[i:i + group_size]
            if len(group) < group_size:
                continue
            section, key, value = group[section_index], group[key_index], group[value_index]
            if skip_missing and (key is None or value is None):
                continue
            section = str(section) if section is not None else None
            key = str(key) if key is not None else None
            out.setdefault(section, []).append((key, value))
        return out

    @staticmethod
    def group_pairs_to_multivalue(
        grouped_pairs: Dict[str | None, List[Tuple[str | None, Any]]]
    ) -> Dict[str | None, Dict[str | None, List[Any]]]:
        """Merge grouped pairs into a multi‑value dictionary.

        Given a ``GroupedPairDict`` mapping sections to lists of ``(key, value)``
        tuples, produce a new mapping where each section maps to a dictionary of
        keys to lists of values.  Duplicate keys accumulate their values in a
        list.

        Args:
            grouped_pairs: A mapping of section names to lists of ``(key, value)`` pairs.

        Returns:
            A dictionary mapping section names to dictionaries that map keys to lists of values.

        Examples::

            >>> pairs = {"section": [("key1", "value1"), ("key1", "value2"), ("key2", "value3")]}
            >>> StructureOps.group_pairs_to_multivalue(pairs)
            {'section': {'key1': ['value1', 'value2'], 'key2': ['value3']}}
        """
        out: Dict[str | None, Dict[str | None, List[Any]]] = {}
        for section, items in grouped_pairs.items():
            section_key = section if section is not None else None
            out.setdefault(section_key, {})
            for key, value in items:
                key_norm = key if key is not None else None
                out[section_key].setdefault(key_norm, []).append(value)
        return out

    @staticmethod
    def dict_to_keypath(data: Dict[str, Any], sep: str = ".") -> Dict[str, Any]:
        """Flatten a nested dictionary into a keypath‑based dictionary.

        The resulting dictionary uses the ``sep`` character to join nested keys
        into a single string.

        Args:
            data: The nested dictionary to flatten.
            sep: The separator used to join nested keys. Defaults to ``'.'``.

        Returns:
            A flat dictionary where nested keys are joined by ``sep``.
        """
        flat: Dict[str, Any] = {}
        def visit(path, key, value):
            if isinstance(value, dict):
                return key, value
            joined_key = sep.join([*path, key]) if path else key
            flat[joined_key] = value
            return key, value
        remap(data, visit=visit)
        return flat

    @staticmethod
    def keypath_to_dict(data: Dict[str, Any], sep: str = ".") -> Dict[str, Any]:
        """Restore a nested dictionary from a keypath‑based dictionary.

        Args:
            data: The flat dictionary to unflatten, where keys may contain ``sep``.
            sep: The separator used in the flat keys. Defaults to ``'.'``.

        Returns:
            A nested dictionary corresponding to the flattened structure.
        """
        result: Dict[str, Any] = {}
        for key, value in data.items():
            parts: List[str] = key.split(sep)
            cur = result
            for part in parts[:-1]:
                cur = cur.setdefault(part, {})
            cur[parts[-1]] = value
        return result
