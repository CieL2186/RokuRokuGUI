from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


class MatchSettingDialog(QDialog):
    """将棋所風の対局設定ダイアログ。"""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        self.setWindowTitle("対局")
        self.resize(850, 520)

        self._setup_ui()
        self._connect_signals()
        self._refresh_enabled_state()

    def _setup_ui(self) -> None:
        root_layout = QVBoxLayout()
        self.setLayout(root_layout)

        main_layout = QHBoxLayout()
        root_layout.addLayout(main_layout)

        left_layout = QVBoxLayout()
        right_layout = QVBoxLayout()

        main_layout.addLayout(left_layout, stretch=1)
        main_layout.addLayout(right_layout, stretch=1)

        left_layout.addWidget(self._create_black_group())
        left_layout.addWidget(self._create_white_group())
        left_layout.addWidget(self._create_start_position_group())
        left_layout.addStretch()

        right_layout.addWidget(self._create_time_group())
        right_layout.addWidget(self._create_match_option_group())
        right_layout.addWidget(self._create_continuous_group())
        right_layout.addWidget(self._create_kifu_save_group())
        right_layout.addStretch()

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )

        start_button = button_box.button(QDialogButtonBox.StandardButton.Ok)
        cancel_button = button_box.button(QDialogButtonBox.StandardButton.Cancel)

        if start_button is not None:
            start_button.setText("Start")

        if cancel_button is not None:
            cancel_button.setText("Cancel")

        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        root_layout.addWidget(button_box)

    # =========================
    # 左側
    # =========================

    def _create_black_group(self) -> QGroupBox:
        group = QGroupBox("先手／下手")
        layout = QGridLayout()
        group.setLayout(layout)

        self.black_human_radio = QRadioButton("人間")
        self.black_engine_radio = QRadioButton("エンジン")
        self.black_engine_radio.setChecked(True)

        self.black_name_label = QLabel("名前")
        self.black_name_edit = QLineEdit()

        self.black_engine_combo = QComboBox()
        self.black_engine_combo.setEditable(True)
        self.black_engine_combo.addItem("")

        self.black_engine_button = QPushButton("エンジン設定...")

        layout.addWidget(self.black_human_radio, 0, 0)
        layout.addWidget(self.black_name_label, 0, 1)
        layout.addWidget(self.black_name_edit, 0, 2, 1, 2)

        layout.addWidget(self.black_engine_radio, 1, 0)
        layout.addWidget(self.black_engine_combo, 1, 1, 1, 2)
        layout.addWidget(self.black_engine_button, 1, 3)

        return group

    def _create_white_group(self) -> QGroupBox:
        group = QGroupBox("後手／上手")
        layout = QGridLayout()
        group.setLayout(layout)

        self.white_human_radio = QRadioButton("人間")
        self.white_engine_radio = QRadioButton("エンジン")
        self.white_engine_radio.setChecked(True)

        self.white_name_label = QLabel("名前")
        self.white_name_edit = QLineEdit()

        self.white_engine_combo = QComboBox()
        self.white_engine_combo.setEditable(True)
        self.white_engine_combo.addItem("")

        self.white_engine_button = QPushButton("エンジン設定...")

        layout.addWidget(self.white_human_radio, 0, 0)
        layout.addWidget(self.white_name_label, 0, 1)
        layout.addWidget(self.white_name_edit, 0, 2, 1, 2)

        layout.addWidget(self.white_engine_radio, 1, 0)
        layout.addWidget(self.white_engine_combo, 1, 1, 1, 2)
        layout.addWidget(self.white_engine_button, 1, 3)

        return group

    def _create_start_position_group(self) -> QGroupBox:
        group = QGroupBox("開始局面")
        layout = QGridLayout()
        group.setLayout(layout)

        self.start_initial_radio = QRadioButton("初期局面")
        self.start_initial_radio.setChecked(True)

        self.initial_position_combo = QComboBox()
        self.initial_position_combo.addItem("平手")

        self.start_current_radio = QRadioButton("現在の局面")
        self.start_file_radio = QRadioButton("局面集から選ぶ")

        self.position_file_label = QLabel("使用ファイル")
        self.position_file_edit = QLineEdit()
        self.position_file_button = QPushButton("ファイル選択...")

        self.order_group = QGroupBox("順番")
        order_layout = QVBoxLayout()
        self.order_group.setLayout(order_layout)

        self.order_first_radio = QRadioButton("最初から")
        self.order_random_radio = QRadioButton("ランダム")
        self.order_random_radio.setChecked(True)

        order_layout.addWidget(self.order_first_radio)
        order_layout.addWidget(self.order_random_radio)

        self.swap_side_each_position_check = QCheckBox("各局面で手番を入れ替え")

        layout.addWidget(self.start_initial_radio, 0, 0)
        layout.addWidget(self.initial_position_combo, 0, 1)

        layout.addWidget(self.start_current_radio, 1, 0, 1, 2)
        layout.addWidget(self.start_file_radio, 2, 0, 1, 2)

        layout.addWidget(self.position_file_label, 3, 0)
        layout.addWidget(self.position_file_edit, 3, 1)
        layout.addWidget(self.position_file_button, 4, 1)

        layout.addWidget(self.order_group, 5, 0, 1, 2)
        layout.addWidget(self.swap_side_each_position_check, 6, 0, 1, 2)

        return group

    # =========================
    # 右側
    # =========================

    def _create_time_group(self) -> QGroupBox:
        group = QGroupBox("時間設定")
        layout = QGridLayout()
        group.setLayout(layout)

        def make_hour_spin(value: int = 0) -> QSpinBox:
            spin = QSpinBox()
            spin.setRange(0, 99)
            spin.setValue(value)
            return spin

        def make_min_spin(value: int = 10) -> QSpinBox:
            spin = QSpinBox()
            spin.setRange(0, 59)
            spin.setValue(value)
            return spin

        def make_sec_spin(value: int = 1) -> QSpinBox:
            spin = QSpinBox()
            spin.setRange(1, 999)
            spin.setValue(value)
            return spin

        # =========================
        # 持ち時間
        # =========================
        self.time_main_radio = QRadioButton("持ち時間")
        self.time_main_radio.setChecked(True)

        self.time_common_check = QCheckBox("先手後手共通")
        self.time_common_check.setChecked(True)

        self.main_hour_spin = make_hour_spin(0)
        self.main_min_spin = make_min_spin(10)

        self.black_main_hour_spin = make_hour_spin(0)
        self.black_main_min_spin = make_min_spin(10)
        self.white_main_hour_spin = make_hour_spin(0)
        self.white_main_min_spin = make_min_spin(10)

        # =========================
        # 秒読み
        # =========================
        self.byoyomi_radio = QRadioButton("秒読み")

        self.byoyomi_common_check = QCheckBox("先手後手共通")
        self.byoyomi_common_check.setChecked(True)

        self.byoyomi_sec_spin = make_sec_spin(1)

        self.black_byoyomi_sec_spin = make_sec_spin(1)
        self.white_byoyomi_sec_spin = make_sec_spin(1)

        # =========================
        # 1手ごとの加算
        # =========================
        self.increment_radio = QRadioButton("1手ごとの加算")

        self.increment_common_check = QCheckBox("先手後手共通")
        self.increment_common_check.setChecked(True)

        self.increment_sec_spin = make_sec_spin(1)

        self.black_increment_sec_spin = make_sec_spin(1)
        self.white_increment_sec_spin = make_sec_spin(1)

        # =========================
        # なし
        # =========================
        self.no_time_radio = QRadioButton("秒読みも加算もなし")

        self.time_button_group = QButtonGroup(self)
        self.time_button_group.addButton(self.time_main_radio)
        self.time_button_group.addButton(self.byoyomi_radio)
        self.time_button_group.addButton(self.increment_radio)
        self.time_button_group.addButton(self.no_time_radio)

        row = 0

        # 持ち時間
        layout.addWidget(self.time_main_radio, row, 0)
        layout.addWidget(self.time_common_check, row, 1, 1, 4)
        row += 1

        layout.addWidget(QLabel("共通"), row, 1)
        layout.addWidget(self.main_hour_spin, row, 2)
        layout.addWidget(QLabel("時間"), row, 3)
        layout.addWidget(self.main_min_spin, row, 4)
        layout.addWidget(QLabel("分"), row, 5)
        row += 1

        layout.addWidget(QLabel("先手"), row, 1)
        layout.addWidget(self.black_main_hour_spin, row, 2)
        layout.addWidget(QLabel("時間"), row, 3)
        layout.addWidget(self.black_main_min_spin, row, 4)
        layout.addWidget(QLabel("分"), row, 5)
        row += 1

        layout.addWidget(QLabel("後手"), row, 1)
        layout.addWidget(self.white_main_hour_spin, row, 2)
        layout.addWidget(QLabel("時間"), row, 3)
        layout.addWidget(self.white_main_min_spin, row, 4)
        layout.addWidget(QLabel("分"), row, 5)
        row += 1

        # 秒読み
        layout.addWidget(self.byoyomi_radio, row, 0)
        layout.addWidget(self.byoyomi_common_check, row, 1, 1, 4)
        row += 1

        layout.addWidget(QLabel("共通"), row, 1)
        layout.addWidget(self.byoyomi_sec_spin, row, 2)
        layout.addWidget(QLabel("秒"), row, 3)
        row += 1

        layout.addWidget(QLabel("先手"), row, 1)
        layout.addWidget(self.black_byoyomi_sec_spin, row, 2)
        layout.addWidget(QLabel("秒"), row, 3)
        row += 1

        layout.addWidget(QLabel("後手"), row, 1)
        layout.addWidget(self.white_byoyomi_sec_spin, row, 2)
        layout.addWidget(QLabel("秒"), row, 3)
        row += 1

        # 1手ごとの加算
        layout.addWidget(self.increment_radio, row, 0)
        layout.addWidget(self.increment_common_check, row, 1, 1, 4)
        row += 1

        layout.addWidget(QLabel("共通"), row, 1)
        layout.addWidget(self.increment_sec_spin, row, 2)
        layout.addWidget(QLabel("秒"), row, 3)
        row += 1

        layout.addWidget(QLabel("先手"), row, 1)
        layout.addWidget(self.black_increment_sec_spin, row, 2)
        layout.addWidget(QLabel("秒"), row, 3)
        row += 1

        layout.addWidget(QLabel("後手"), row, 1)
        layout.addWidget(self.white_increment_sec_spin, row, 2)
        layout.addWidget(QLabel("秒"), row, 3)
        row += 1

        # なし
        layout.addWidget(self.no_time_radio, row, 0, 1, 4)

        return group

    def _create_match_option_group(self) -> QGroupBox:
        group = QGroupBox("対局オプション")
        layout = QGridLayout()
        group.setLayout(layout)

        self.max_moves_check = QCheckBox("手数が")
        self.max_moves_spin = QSpinBox()
        self.max_moves_spin.setRange(1, 10000)
        self.max_moves_spin.setValue(1000)
        self.max_moves_label = QLabel("手に達したら引き分けにする")

        self.lose_on_time_check = QCheckBox("時間切れを負けにする")

        layout.addWidget(self.max_moves_check, 0, 0)
        layout.addWidget(self.max_moves_spin, 0, 1)
        layout.addWidget(self.max_moves_label, 0, 2)

        layout.addWidget(self.lose_on_time_check, 1, 0, 1, 3)

        return group

    def _create_continuous_group(self) -> QGroupBox:
        group = QGroupBox("連続対局")
        layout = QGridLayout()
        group.setLayout(layout)

        self.continuous_check = QCheckBox("連続対局")
        self.continuous_games_label = QLabel("連続対局数")
        self.continuous_games_spin = QSpinBox()
        self.continuous_games_spin.setRange(1, 10000)
        self.continuous_games_spin.setValue(2)

        self.swap_side_each_game_check = QCheckBox("対局ごとに手番を入れ替え")
        self.swap_side_each_game_check.setChecked(True)

        layout.addWidget(self.continuous_check, 0, 0, 1, 3)
        layout.addWidget(self.continuous_games_label, 1, 0)
        layout.addWidget(self.continuous_games_spin, 1, 1)
        layout.addWidget(self.swap_side_each_game_check, 2, 0, 1, 3)

        return group

    def _create_kifu_save_group(self) -> QGroupBox:
        group = QGroupBox("棋譜自動保存")
        layout = QGridLayout()
        group.setLayout(layout)

        self.auto_save_check = QCheckBox("棋譜自動保存")
        self.save_dir_label = QLabel("保存場所")
        self.save_dir_edit = QLineEdit()
        self.save_dir_button = QPushButton("保存場所指定...")

        self.kifu_format_label = QLabel("棋譜形式")
        self.kifu_format_combo = QComboBox()
        self.kifu_format_combo.addItems(["KIF", "USI"])

        layout.addWidget(self.auto_save_check, 0, 0, 1, 3)
        layout.addWidget(self.save_dir_label, 1, 0)
        layout.addWidget(self.save_dir_edit, 1, 1)
        layout.addWidget(self.save_dir_button, 2, 2)

        layout.addWidget(self.kifu_format_label, 3, 0)
        layout.addWidget(self.kifu_format_combo, 3, 1)

        return group

    # =========================
    # signals
    # =========================

    def _connect_signals(self) -> None:
        for widget in [
            self.black_human_radio,
            self.black_engine_radio,
            self.white_human_radio,
            self.white_engine_radio,
            self.start_initial_radio,
            self.start_current_radio,
            self.start_file_radio,
            self.time_main_radio,
            self.byoyomi_radio,
            self.increment_radio,
            self.no_time_radio,
            self.max_moves_check,
            self.continuous_check,
            self.auto_save_check,
        ]:
            widget.toggled.connect(self._refresh_enabled_state)

        self.black_engine_button.clicked.connect(
            lambda: self._select_engine_file(self.black_engine_combo)
        )
        self.white_engine_button.clicked.connect(
            lambda: self._select_engine_file(self.white_engine_combo)
        )

        self.position_file_button.clicked.connect(self._select_position_file)
        self.save_dir_button.clicked.connect(self._select_save_dir)
        self.time_common_check.toggled.connect(self._refresh_enabled_state)
        self.byoyomi_common_check.toggled.connect(self._refresh_enabled_state)
        self.increment_common_check.toggled.connect(self._refresh_enabled_state)

    def _refresh_enabled_state(self) -> None:
        main_time = self.time_main_radio.isChecked()
        byoyomi = self.byoyomi_radio.isChecked()
        increment = self.increment_radio.isChecked()

        # =========================
        # 持ち時間
        # =========================
        self.time_common_check.setEnabled(main_time)

        main_common = main_time and self.time_common_check.isChecked()
        main_individual = main_time and not self.time_common_check.isChecked()

        self.main_hour_spin.setEnabled(main_common)
        self.main_min_spin.setEnabled(main_common)

        self.black_main_hour_spin.setEnabled(main_individual)
        self.black_main_min_spin.setEnabled(main_individual)
        self.white_main_hour_spin.setEnabled(main_individual)
        self.white_main_min_spin.setEnabled(main_individual)

        # =========================
        # 秒読み
        # =========================
        self.byoyomi_common_check.setEnabled(byoyomi)

        byoyomi_common = byoyomi and self.byoyomi_common_check.isChecked()
        byoyomi_individual = byoyomi and not self.byoyomi_common_check.isChecked()

        self.byoyomi_sec_spin.setEnabled(byoyomi_common)

        self.black_byoyomi_sec_spin.setEnabled(byoyomi_individual)
        self.white_byoyomi_sec_spin.setEnabled(byoyomi_individual)

        # =========================
        # 1手ごとの加算
        # =========================
        self.increment_common_check.setEnabled(increment)

        increment_common = increment and self.increment_common_check.isChecked()
        increment_individual = increment and not self.increment_common_check.isChecked()

        self.increment_sec_spin.setEnabled(increment_common)

        self.black_increment_sec_spin.setEnabled(increment_individual)
        self.white_increment_sec_spin.setEnabled(increment_individual)

    def _select_engine_file(self, combo: QComboBox) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "エンジンを選択",
            "",
            "Executable Files (*.exe);;All Files (*)",
        )

        if not path:
            return

        if combo.findText(path) == -1:
            combo.addItem(path)

        combo.setCurrentText(path)

    def _select_position_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "局面集を選択",
            "",
            "Position Files (*.txt *.sfen *.kif);;All Files (*)",
        )

        if path:
            self.position_file_edit.setText(path)

    def _select_save_dir(self) -> None:
        path = QFileDialog.getExistingDirectory(
            self,
            "棋譜保存場所を選択",
            "",
        )

        if path:
            self.save_dir_edit.setText(path)

    # =========================
    # settings
    # =========================

    def get_settings(self) -> dict[str, object]:
        if self.time_main_radio.isChecked():
            time_mode = "main_time"
        elif self.byoyomi_radio.isChecked():
            time_mode = "byoyomi"
        elif self.increment_radio.isChecked():
            time_mode = "increment"
        else:
            time_mode = "none"

        # =========================
        # 持ち時間
        # =========================
        main_time_common = self.time_common_check.isChecked()

        if main_time_common:
            black_main_hour = self.main_hour_spin.value()
            black_main_min = self.main_min_spin.value()
            white_main_hour = self.main_hour_spin.value()
            white_main_min = self.main_min_spin.value()
        else:
            black_main_hour = self.black_main_hour_spin.value()
            black_main_min = self.black_main_min_spin.value()
            white_main_hour = self.white_main_hour_spin.value()
            white_main_min = self.white_main_min_spin.value()

        # =========================
        # 秒読み
        # =========================
        byoyomi_common = self.byoyomi_common_check.isChecked()

        if byoyomi_common:
            black_byoyomi_sec = self.byoyomi_sec_spin.value()
            white_byoyomi_sec = self.byoyomi_sec_spin.value()
        else:
            black_byoyomi_sec = self.black_byoyomi_sec_spin.value()
            white_byoyomi_sec = self.white_byoyomi_sec_spin.value()

        # =========================
        # 1手ごとの加算
        # =========================
        increment_common = self.increment_common_check.isChecked()

        if increment_common:
            black_increment_sec = self.increment_sec_spin.value()
            white_increment_sec = self.increment_sec_spin.value()
        else:
            black_increment_sec = self.black_increment_sec_spin.value()
            white_increment_sec = self.white_increment_sec_spin.value()

        return {
            "black_player": "AI" if self.black_engine_radio.isChecked() else "Human",
            "black_name": self.black_name_edit.text().strip(),
            "black_engine_path": self.black_engine_combo.currentText().strip(),

            "white_player": "AI" if self.white_engine_radio.isChecked() else "Human",
            "white_name": self.white_name_edit.text().strip(),
            "white_engine_path": self.white_engine_combo.currentText().strip(),

            "start_position_mode": self._start_position_mode(),
            "initial_position_type": self.initial_position_combo.currentText(),
            "position_file_path": self.position_file_edit.text().strip(),
            "position_order": "random" if self.order_random_radio.isChecked() else "first",
            "swap_side_each_position": self.swap_side_each_position_check.isChecked(),

            # 時間設定
            "time_mode": time_mode,

            "main_time_common": main_time_common,
            "black_main_time_hour": black_main_hour,
            "black_main_time_min": black_main_min,
            "white_main_time_hour": white_main_hour,
            "white_main_time_min": white_main_min,

            "byoyomi_common": byoyomi_common,
            "black_byoyomi_sec": black_byoyomi_sec,
            "white_byoyomi_sec": white_byoyomi_sec,

            "increment_common": increment_common,
            "black_increment_sec": black_increment_sec,
            "white_increment_sec": white_increment_sec,

            "max_moves_enabled": self.max_moves_check.isChecked(),
            "max_moves": self.max_moves_spin.value(),
            "lose_on_time": self.lose_on_time_check.isChecked(),

            "continuous_enabled": self.continuous_check.isChecked(),
            "continuous_games": self.continuous_games_spin.value(),
            "swap_side_each_game": self.swap_side_each_game_check.isChecked(),

            "auto_save_kifu": self.auto_save_check.isChecked(),
            "kifu_save_dir": self.save_dir_edit.text().strip(),
            "kifu_format": self.kifu_format_combo.currentText(),
        }

    def _start_position_mode(self) -> str:
        if self.start_current_radio.isChecked():
            return "current"
        if self.start_file_radio.isChecked():
            return "position_file"
        return "initial"

    def _time_mode(self) -> str:
        if self.byoyomi_radio.isChecked():
            return "byoyomi"
        if self.increment_radio.isChecked():
            return "increment"
        if self.no_time_radio.isChecked():
            return "none"
        return "main_time"