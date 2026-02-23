# RRFAdaptivePurgeMesh.py
from ..Script import Script
import re

class RRFAdaptivePurgeMesh(Script):
    def getSettingDataString(self):
        return """{
            "name": "RRF Adaptive Purge & Mesh",
            "key": "RRFAdaptivePurgeMesh",
            "metadata": {},
            "version": 2,
            "settings": {}
        }"""

    def execute(self, data):
        min_x, max_x = 9999.0, -9999.0
        min_y, max_y = 9999.0, -9999.0
        bed_x, bed_y = 300.0, 300.0
        
        p_move = re.compile(r'[Gg][01].*[Xx]([-\d\.]+).*[Yy]([-\d\.]+)')
        p_limit = re.compile(r';BED_LIMITS.*X([\d\.]+).*Y([\d\.]+)')
        
        found_model = False
        parsing_layer_0 = False
        
        for layer in data:
            if ";LAYER:0" in layer: parsing_layer_0 = True
            
            for line in layer.split("\n"):
                if ";BED_LIMITS" in line:
                    m = p_limit.search(line)
                    if m: bed_x, bed_y = float(m.group(1)), float(m.group(2))
                        
                if parsing_layer_0 and "E" in line and (line.startswith("G1") or line.startswith("G0")):
                    m = p_move.search(line)
                    if m:
                        found_model = True
                        x, y = float(m.group(1)), float(m.group(2))
                        min_x, max_x = min(min_x, x), max(max_x, x)
                        min_y, max_y = min(min_y, y), max(max_y, y)

        if not found_model:
            return data

        # Calculate purge: 10mm left of model. Clamp to 0.5 to stay on bed.
        purge_x = max(0.5, min_x - 10.0)
        purge_y = min_y
        
        # Mesh with 10mm padding, clamped to bed size
        m_min_x, m_max_x = max(10.0, min_x - 10), min(bed_x - 10, max_x + 10)
        m_min_y, m_max_y = max(10.0, min_y - 10), min(bed_y - 10, max_y + 10)
        
        # Spacing logic (same as your original adaptive mesh)
        spacing = 50
        x_span, y_span = m_max_x - m_min_x, m_max_y - m_min_y
        if x_span < spacing: spacing = x_span / 2
        if y_span < spacing: spacing = min(spacing, y_span / 2)
        spacing = max(15, int(spacing))

        injection = (
            f"; --- RRF ADAPTIVE DATA ---\n"
            f"set global.purge_x = {purge_x:.3f}\n"
            f"set global.purge_y = {purge_y:.3f}\n"
            f"M557 X{m_min_x:.1f}:{m_max_x:.1f} Y{m_min_y:.1f}:{m_max_y:.1f} S{spacing}\n"
            f"; -------------------------\n"
        )

        new_data = []
        injected = False
        for layer in data:
            if not injected and ";FLAVOR:" in layer:
                layer = layer + "\n" + injection
                injected = True
            new_data.append(layer)
            
        return new_data