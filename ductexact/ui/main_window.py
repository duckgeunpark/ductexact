"""메인 윈도우: 형상선택 → 입력폼 → 공통설정 → 생성 → 미리보기/내보내기."""
from __future__ import annotations

import os

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QListWidget, QGroupBox,
    QComboBox, QPushButton, QLabel, QTableWidget, QTableWidgetItem, QFormLayout,
    QFileDialog, QMessageBox, QPlainTextEdit, QCheckBox, QDoubleSpinBox, QTabWidget,
)
from PySide6.QtCore import Qt

from ..core.shapes import SHAPES
from ..core.shapes.base import CommonSettings
from ..core import allowances as al
from ..core.nesting import nest
from ..core.assembly import build_drawing
from ..config import load_config
from ..io.dxf_export import export_pattern
from ..io.nesting_dxf import export_nesting
from ..io.drawing_dxf import export_drawing
from ..io.table_export import (
    export_csv, export_draw_csv, draw_table, as_text, DRAW_HEADERS,
)
from .param_form import ParamForm
from .preview import PreviewCanvas
from .resources import app_icon


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DuctExact")
        self.setWindowIcon(app_icon())
        self.resize(1180, 720)
        self.cfg_data = load_config()
        self.current_pattern = None
        self.current_drawing = None
        self.param_form: ParamForm | None = None

        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)

        # ---- 좌: 형상 목록 ----
        self.shape_list = QListWidget()
        for s in SHAPES:
            self.shape_list.addItem(s.name)
        self.shape_list.setMaximumWidth(170)
        self.shape_list.currentRowChanged.connect(self._on_shape_changed)
        root.addWidget(self.shape_list)

        # ---- 중: 입력 + 공통설정 ----
        mid = QVBoxLayout()
        self.param_box = QGroupBox("형상 치수")
        self.param_box_layout = QVBoxLayout(self.param_box)
        mid.addWidget(self.param_box)
        mid.addWidget(self._build_common_box())
        mid.addWidget(self._build_nesting_box())

        self.gen_btn = QPushButton("전개도 생성")
        self.gen_btn.clicked.connect(self.generate)
        mid.addWidget(self.gen_btn)
        btn_row = QHBoxLayout()
        self.dxf_btn = QPushButton("DXF 내보내기")
        self.dxf_btn.clicked.connect(self.export_dxf)
        self.csv_btn = QPushButton("CSV 내보내기")
        self.csv_btn.clicked.connect(self.export_csv_file)
        btn_row.addWidget(self.dxf_btn)
        btn_row.addWidget(self.csv_btn)
        mid.addLayout(btn_row)
        self.draw_dxf_btn = QPushButton("완성도 DXF 내보내기")
        self.draw_dxf_btn.clicked.connect(self.export_drawing_file)
        mid.addWidget(self.draw_dxf_btn)
        mid.addStretch(1)
        midw = QWidget()
        midw.setLayout(mid)
        midw.setMaximumWidth(360)
        root.addWidget(midw)

        # ---- 우: 미리보기(전개도/완성도 탭) + 표 ----
        right = QVBoxLayout()
        self.tabs = QTabWidget()
        self.preview = PreviewCanvas()          # 전개도
        self.draw_preview = PreviewCanvas()      # 완성도
        self.tabs.addTab(self.preview, "전개도")
        self.tabs.addTab(self.draw_preview, "완성도")
        right.addWidget(self.tabs, 3)
        self.table = QTableWidget(0, len(DRAW_HEADERS))
        self.table.setHorizontalHeaderLabels(DRAW_HEADERS)
        right.addWidget(self.table, 2)
        self.notes = QPlainTextEdit()
        self.notes.setReadOnly(True)
        self.notes.setMaximumHeight(90)
        right.addWidget(self.notes)
        root.addLayout(right, 1)

        self.shape_list.setCurrentRow(0)

    # ---------- 공통설정 박스 ----------
    def _build_common_box(self) -> QGroupBox:
        box = QGroupBox("공통 설정 (제작 여유)")
        form = QFormLayout(box)
        d = self.cfg_data["defaults"]

        self.seam_cb = QComboBox()
        self.seam_cb.addItems(list(self.cfg_data["seam_allowance_mm"].keys()))
        self.seam_cb.setCurrentText(d["seam"])
        self.joint_cb = QComboBox()
        self.joint_cb.addItems(list(self.cfg_data["end_allowance_mm"].keys()))
        self.joint_cb.setCurrentText(d["joint"])
        self.gauge_cb = QComboBox()
        self.gauge_cb.addItems(list(self.cfg_data["gauge_thickness_mm"].keys()))
        self.gauge_cb.setCurrentText(d["gauge"])
        self.outunit_cb = QComboBox()
        self.outunit_cb.addItems(["mm", "cm", "m", "in", "ft"])
        self.outunit_cb.setCurrentText(d["output_unit"])
        self.basis_cb = QComboBox()
        self.basis_cb.addItems(["ID", "OD"])
        self.basis_cb.setCurrentText(d["dim_basis"])

        self.ba_chk = QCheckBox("굽힘여유(중립선) 보정 사용")
        self.kf_spin = QDoubleSpinBox()
        self.kf_spin.setRange(0.0, 1.0)
        self.kf_spin.setSingleStep(0.05)
        self.kf_spin.setValue(0.5)

        form.addRow("심 방식", self.seam_cb)
        form.addRow("단부 연결", self.joint_cb)
        form.addRow("게이지(GA)", self.gauge_cb)
        form.addRow("출력 단위", self.outunit_cb)
        form.addRow("치수 기준", self.basis_cb)
        form.addRow(self.ba_chk)
        form.addRow("K-factor", self.kf_spin)

        # 굽힘여유 보정 체크 시에만 K-factor 입력 활성화(미체크 시 회색)
        kf_label = form.labelForField(self.kf_spin)

        def _toggle_kf(on):
            self.kf_spin.setEnabled(on)
            if kf_label is not None:
                kf_label.setEnabled(on)

        self.ba_chk.toggled.connect(_toggle_kf)
        _toggle_kf(self.ba_chk.isChecked())   # 초기 상태 반영(기본 미체크→비활성)
        return box

    def _build_nesting_box(self) -> QGroupBox:
        box = QGroupBox("네스팅 (판재 배치)")
        form = QFormLayout(box)
        self.sheet_w = QDoubleSpinBox()
        self.sheet_w.setRange(100, 100000)
        self.sheet_w.setValue(1219)      # 4ft
        self.sheet_h = QDoubleSpinBox()
        self.sheet_h.setRange(100, 100000)
        self.sheet_h.setValue(2438)      # 8ft
        self.nest_gap = QDoubleSpinBox()
        self.nest_gap.setRange(0, 1000)
        self.nest_gap.setValue(10)
        self.rotate_chk = QCheckBox("90° 회전 허용")
        self.rotate_chk.setChecked(True)
        nb = QHBoxLayout()
        self.nest_prev_btn = QPushButton("네스팅 미리보기")
        self.nest_prev_btn.clicked.connect(self.nest_preview)
        self.nest_dxf_btn = QPushButton("네스팅 DXF")
        self.nest_dxf_btn.clicked.connect(self.nest_dxf)
        form.addRow("시트 폭(mm)", self.sheet_w)
        form.addRow("시트 높이(mm)", self.sheet_h)
        form.addRow("간격(mm)", self.nest_gap)
        form.addRow(self.rotate_chk)
        wrap = QWidget()
        wrap.setLayout(nb)
        nb.addWidget(self.nest_prev_btn)
        nb.addWidget(self.nest_dxf_btn)
        form.addRow(wrap)
        return box

    def _settings(self) -> CommonSettings:
        return CommonSettings(
            seam=self.seam_cb.currentText(),
            joint=self.joint_cb.currentText(),
            gauge=self.gauge_cb.currentText(),
            output_unit=self.outunit_cb.currentText(),
            dim_basis=self.basis_cb.currentText(),
            use_bend_allowance=self.ba_chk.isChecked(),
            k_factor=self.kf_spin.value(),
            seam_table=self.cfg_data["seam_allowance_mm"],
            end_table=self.cfg_data["end_allowance_mm"],
            gauge_table=self.cfg_data["gauge_thickness_mm"],
        )

    # ---------- 이벤트 ----------
    def _on_shape_changed(self, row: int):
        if row < 0:
            return
        shape_cls = SHAPES[row]
        if self.param_form is not None:
            self.param_box_layout.removeWidget(self.param_form)
            self.param_form.deleteLater()
        self.param_form = ParamForm(shape_cls(), self.outunit_cb.currentText()
                                    if hasattr(self, "outunit_cb") else "mm")
        self.param_box_layout.addWidget(self.param_form)
        self.param_box.setTitle(f"형상 치수 — {shape_cls.name}")

    def generate(self):
        row = self.shape_list.currentRow()
        shape = SHAPES[row]()
        try:
            raw = self.param_form.raw_values()
            p = shape.param_values_to_mm(raw)
            pat = shape.develop(p, self._settings())
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "오류", f"전개 실패:\n{exc}")
            return
        self.current_pattern = pat
        self.preview.show_pattern(pat)
        self._fill_table(pat)
        # 표는 도해(좌표)용이므로 요약값·비고는 아래 비고창에 표시
        unit = self.outunit_cb.currentText()
        summary = [f"{r.get('항목', '')}: {r.get('값', '')} {r.get('단위', '')}".strip()
                   for r in pat.table]
        lines = [f"[검산용 요약 — 단위 {unit}]"] + summary
        if pat.notes:
            lines += ["", "[비고]"] + pat.notes
        self.notes.setPlainText("\n".join(lines))
        # 완성도(조립도)도 함께 생성
        try:
            self.current_drawing = build_drawing(shape.key, p, self._settings())
            self.draw_preview.show_drawing(self.current_drawing)
        except Exception as exc:  # noqa: BLE001
            self.current_drawing = None
            self.draw_preview.clear()

    def _fill_table(self, pat):
        """우측 표에 '따라그리기 도해표'(좌표/접기선/경계선)를 채운다."""
        headers, rows = draw_table(pat, self.outunit_cb.currentText())
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        self.table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            for j, val in enumerate(row):
                self.table.setItem(i, j, QTableWidgetItem(str(val)))
        self.table.resizeColumnsToContents()

    def export_dxf(self):
        if not self.current_pattern:
            QMessageBox.information(self, "안내", "먼저 전개도를 생성하세요.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "DXF 저장", "pattern.dxf",
                                              "DXF (*.dxf)")
        if not path:
            return
        export_pattern(self.current_pattern, path, self.outunit_cb.currentText())
        QMessageBox.information(self, "완료", f"저장됨:\n{path}")

    def export_drawing_file(self):
        if not self.current_drawing:
            QMessageBox.information(self, "안내", "먼저 전개도를 생성하세요.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "완성도 DXF 저장",
                                              "assembly.dxf", "DXF (*.dxf)")
        if not path:
            return
        export_drawing(self.current_drawing, path, self.outunit_cb.currentText())
        QMessageBox.information(self, "완료", f"저장됨:\n{path}")

    def _run_nest(self):
        if not self.current_pattern:
            QMessageBox.information(self, "안내", "먼저 전개도를 생성하세요.")
            return None
        return nest([self.current_pattern], self.sheet_w.value(),
                    self.sheet_h.value(), self.nest_gap.value(),
                    self.rotate_chk.isChecked())

    def nest_preview(self):
        res = self._run_nest()
        if res is None:
            return
        self.preview.show_nesting(res)
        s = res.summary()
        self.notes.setPlainText(
            f"네스팅: 시트 {s['sheets']}장, 활용률 {s['utilization']*100:.1f}%, "
            f"미배치 {s['unplaced']}개")

    def nest_dxf(self):
        res = self._run_nest()
        if res is None:
            return
        path, _ = QFileDialog.getSaveFileName(self, "네스팅 DXF 저장",
                                              "nesting.dxf", "DXF (*.dxf)")
        if not path:
            return
        export_nesting(res, path, self.outunit_cb.currentText())
        QMessageBox.information(self, "완료", f"저장됨:\n{path}")

    def export_csv_file(self):
        if not self.current_pattern:
            QMessageBox.information(self, "안내", "먼저 전개도를 생성하세요.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "CSV 저장", "pattern.csv",
                                              "CSV (*.csv)")
        if not path:
            return
        # 좌표 도해표(따라그리기) + 검산용 요약을 함께 저장
        export_draw_csv(self.current_pattern, path, self.outunit_cb.currentText())
        QMessageBox.information(self, "완료", f"저장됨:\n{path}")
