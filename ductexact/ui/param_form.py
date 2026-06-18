"""형상별 입력칸 자동 생성. 길이칸마다 단위 콤보박스를 둔다."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QFormLayout, QDoubleSpinBox, QSpinBox, QComboBox, QHBoxLayout,
    QLabel,
)

from ..core.shapes.base import Shape, ParamSpec
from ..core.units import LENGTH_UNITS


class ParamForm(QWidget):
    """선택된 형상의 입력 위젯 묶음."""

    def __init__(self, shape: Shape, default_unit: str = "mm"):
        super().__init__()
        self.shape = shape
        self.default_unit = default_unit
        self._widgets: dict[str, tuple[ParamSpec, QWidget, QComboBox | None]] = {}
        self._labels: dict[str, QLabel] = {}

        layout = QFormLayout(self)
        # 라벨이 길면 입력칸 위로 줄바꿈(좁은 패널에서 라벨 잘림 방지)
        layout.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        layout.setFieldGrowthPolicy(
            QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        for spec in shape.params:
            row, value_w, unit_w = self._build_row(spec)
            label = QLabel(spec.label)
            label.setWordWrap(True)            # 긴 라벨 줄바꿈
            if spec.help:
                label.setToolTip(spec.help)
            layout.addRow(label, row)
            self._widgets[spec.key] = (spec, value_w, unit_w)
            self._labels[spec.key] = label

        self._wire_dependencies()

    def _set_enabled(self, key: str, on: bool) -> None:
        """입력칸(+단위, 라벨)을 활성/비활성(회색)으로."""
        entry = self._widgets.get(key)
        if entry is None:
            return
        _, value_w, unit_w = entry
        value_w.setEnabled(on)
        if unit_w is not None:
            unit_w.setEnabled(on)
        if key in self._labels:
            self._labels[key].setEnabled(on)

    def _wire_dependencies(self) -> None:
        """형상별 조건부 입력칸 활성화 규칙 연결."""
        if self.shape.key == "reducer" and "kind" in self._widgets:
            combo = self._widgets["kind"][1]
            combo.currentTextChanged.connect(self._update_reducer_fields)
            self._update_reducer_fields(combo.currentText())

    def _update_reducer_fields(self, kind: str) -> None:
        """리듀서: 원형 단면이면 해당 세로(H) 입력 비활성화(사각만 사용)."""
        self._set_enabled("H1", kind.startswith("사각"))   # 입구가 사각일 때만
        self._set_enabled("H2", kind.endswith("사각"))     # 출구가 사각일 때만

    def _build_row(self, spec: ParamSpec):
        container = QWidget()
        h = QHBoxLayout(container)
        h.setContentsMargins(0, 0, 0, 0)
        unit_w = None

        if spec.kind == "length":
            value_w = QDoubleSpinBox()
            value_w.setRange(spec.minimum, spec.maximum)
            value_w.setDecimals(2)
            value_w.setValue(spec.default)
            unit_w = QComboBox()
            unit_w.addItems(list(LENGTH_UNITS.keys()))
            unit_w.setCurrentText(spec.default_unit or self.default_unit)
            unit_w.setMaximumWidth(64)
            value_w.setMinimumWidth(70)
            h.addWidget(value_w, 1)
            h.addWidget(unit_w, 0)
        elif spec.kind == "angle":
            value_w = QDoubleSpinBox()
            value_w.setRange(spec.minimum, spec.maximum)
            value_w.setDecimals(1)
            value_w.setValue(spec.default)
            value_w.setSuffix(" deg")
            h.addWidget(value_w, 1)
        elif spec.kind == "int":
            value_w = QSpinBox()
            value_w.setRange(int(spec.minimum), int(spec.maximum))
            value_w.setValue(int(spec.default))
            h.addWidget(value_w, 1)
        elif spec.kind == "choice":
            value_w = QComboBox()
            value_w.addItems(spec.choices)
            h.addWidget(value_w, 1)
        else:
            value_w = QDoubleSpinBox()
            h.addWidget(value_w, 1)

        if spec.help:
            container.setToolTip(spec.help)
        return container, value_w, unit_w

    def raw_values(self) -> dict:
        """{key: (value, unit)} 형식. length 외에는 unit='-'."""
        out = {}
        for key, (spec, w, unit_w) in self._widgets.items():
            if spec.kind == "length":
                out[key] = (w.value(), unit_w.currentText())
            elif spec.kind == "angle":
                out[key] = (w.value(), "deg")
            elif spec.kind == "int":
                out[key] = (w.value(), "-")
            elif spec.kind == "choice":
                out[key] = (w.currentText(), "-")
        return out
