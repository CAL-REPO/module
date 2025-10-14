# -*- coding: utf-8 -*-
# data_utils/geometry_ops.py
"""Geometric calculation utilities for bounding boxes and spatial operations."""

from typing import Dict, Iterable, Tuple


class GeometryOps:
    """Utility functions for geometric calculations."""
    
    @staticmethod
    def polygon_bbox(points: Iterable[Tuple[float, float]]) -> Tuple[float, float, float, float]:
        """Calculate bounding box from polygon points.
        
        Args:
            points: Collection of (x, y) coordinates.
            
        Returns:
            Bounding box as (x_min, y_min, x_max, y_max).
            
        Examples:
            >>> points = [(0, 0), (10, 0), (10, 10), (0, 10)]
            >>> GeometryOps.polygon_bbox(points)
            (0, 0, 10, 10)
        """
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        return min(xs), min(ys), max(xs), max(ys)
    
    @staticmethod
    def bbox_center(bbox: Tuple[float, float, float, float]) -> Tuple[float, float]:
        """Calculate center point of a bounding box.
        
        Args:
            bbox: Bounding box as (x_min, y_min, x_max, y_max).
            
        Returns:
            Center point as (x, y).
            
        Examples:
            >>> GeometryOps.bbox_center((0, 0, 10, 10))
            (5.0, 5.0)
        """
        x0, y0, x1, y1 = bbox
        return (x0 + x1) / 2.0, (y0 + y1) / 2.0
    
    @staticmethod
    def bbox_dimensions(bbox: Tuple[float, float, float, float]) -> Tuple[float, float]:
        """Calculate width and height of a bounding box.
        
        Args:
            bbox: Bounding box as (x_min, y_min, x_max, y_max).
            
        Returns:
            Dimensions as (width, height).
            
        Examples:
            >>> GeometryOps.bbox_dimensions((0, 0, 10, 20))
            (10, 20)
        """
        x0, y0, x1, y1 = bbox
        return x1 - x0, y1 - y0
    
    @staticmethod
    def auto_font_size(
        text: str,
        bbox: Tuple[float, float, float, float],
        width_ratio: float = 0.95,
    ) -> int:
        """Automatically calculate font size to fit text within bbox.
        
        Args:
            text: Text content to fit.
            bbox: Target bounding box.
            width_ratio: Maximum ratio of bbox width to use (default 0.95).
            
        Returns:
            Calculated font size in pixels (minimum 12).
            
        Examples:
            >>> GeometryOps.auto_font_size("Hello", (0, 0, 100, 50))
            12
        """
        width, height = GeometryOps.bbox_dimensions(bbox)
        width = max(1, int(width))
        height = max(1, int(height))
        
        if not text:
            return max(12, int(height * width_ratio))
        
        approx_width = width * width_ratio
        approx_height = height * width_ratio
        size = min(approx_width / max(1, len(text)), approx_height)
        return max(12, int(size))
    
    @staticmethod
    def bbox_intersection_over_union(
        bbox_a: Dict[str, float],
        bbox_b: Dict[str, float]
    ) -> float:
        """Calculate Intersection over Union (IoU) between two bounding boxes.
        
        IoU measures the overlap between two bounding boxes as the ratio of their
        intersection area to their union area. Values range from 0 (no overlap) to
        1 (complete overlap).
        
        Args:
            bbox_a: First bounding box with keys 'x0', 'y0', 'x1', 'y1'.
            bbox_b: Second bounding box with keys 'x0', 'y0', 'x1', 'y1'.
            
        Returns:
            IoU score between 0.0 and 1.0.
            
        Examples:
            >>> bbox1 = {"x0": 0, "y0": 0, "x1": 10, "y1": 10}
            >>> bbox2 = {"x0": 5, "y0": 5, "x1": 15, "y1": 15}
            >>> GeometryOps.bbox_intersection_over_union(bbox1, bbox2)
            0.14285714285714285
            
            >>> # Identical boxes have IoU = 1.0
            >>> GeometryOps.bbox_intersection_over_union(bbox1, bbox1)
            1.0
            
            >>> # Non-overlapping boxes have IoU = 0.0
            >>> bbox3 = {"x0": 20, "y0": 20, "x1": 30, "y1": 30}
            >>> GeometryOps.bbox_intersection_over_union(bbox1, bbox3)
            0.0
        """
        x0_a, y0_a, x1_a, y1_a = bbox_a["x0"], bbox_a["y0"], bbox_a["x1"], bbox_a["y1"]
        x0_b, y0_b, x1_b, y1_b = bbox_b["x0"], bbox_b["y0"], bbox_b["x1"], bbox_b["y1"]
        
        # Calculate intersection coordinates
        x0_i = max(x0_a, x0_b)
        y0_i = max(y0_a, y0_b)
        x1_i = min(x1_a, x1_b)
        y1_i = min(y1_a, y1_b)
        
        # Calculate intersection area (if boxes overlap)
        if x1_i <= x0_i or y1_i <= y0_i:
            return 0.0
        
        intersection = (x1_i - x0_i) * (y1_i - y0_i)
        
        # Calculate individual areas
        area_a = (x1_a - x0_a) * (y1_a - y0_a)
        area_b = (x1_b - x0_b) * (y1_b - y0_b)
        
        # Calculate union area
        union = area_a + area_b - intersection
        
        # Avoid division by zero
        if union <= 0:
            return 0.0
        
        return intersection / union
