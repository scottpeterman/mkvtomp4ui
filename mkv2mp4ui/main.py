import sys
import os
import threading
from pathlib import Path
from PyQt6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout,
                             QWidget, QPushButton, QLabel, QListWidget, QListWidgetItem,
                             QProgressBar, QTextEdit, QFileDialog, QCheckBox, QGroupBox,
                             QSpinBox, QComboBox, QMessageBox, QSplitter, QDialog)
from PyQt6.QtCore import QThread, pyqtSignal, Qt, QTimer, QSettings
from PyQt6.QtGui import QFont, QIcon
import ffmpeg
import subprocess

# Import our FFmpeg downloader utility
try:
    from ffmpeg_downloader import check_ffmpeg, FFmpegPromptDialog
    import shutil
except ImportError:
    # Fallback if the module isn't available
    def check_ffmpeg():
        import shutil
        return shutil.which('ffmpeg') is not None


    FFmpegPromptDialog = None


class ConversionWorker(QThread):
    progress_updated = pyqtSignal(int, str)  # file_index, status_message
    conversion_complete = pyqtSignal(int, bool, str)  # file_index, success, message
    ffmpeg_output = pyqtSignal(str)  # FFmpeg output line
    all_complete = pyqtSignal()

    def __init__(self, files_to_convert, output_folder, codec_settings, ffmpeg_path):
        super().__init__()
        self.files_to_convert = files_to_convert
        self.output_folder = output_folder
        self.codec_settings = codec_settings
        self.ffmpeg_path = ffmpeg_path
        self.should_stop = False
        self.current_process = None

    def run(self):
        for i, (input_file, output_file) in enumerate(self.files_to_convert):
            if self.should_stop:
                break

            self.progress_updated.emit(i, f"Converting: {Path(input_file).name}")

            try:
                # Build ffmpeg command manually for better control
                cmd = [self.ffmpeg_path, '-i', input_file]

                # Add codec options
                if self.codec_settings['video_codec'] != 'copy':
                    cmd.extend(['-c:v', self.codec_settings['video_codec']])
                    if self.codec_settings['crf']:
                        cmd.extend(['-crf', str(self.codec_settings['crf'])])
                    if self.codec_settings['preset']:
                        cmd.extend(['-preset', self.codec_settings['preset']])
                else:
                    cmd.extend(['-c:v', 'copy'])

                if self.codec_settings['audio_codec'] != 'copy':
                    cmd.extend(['-c:a', self.codec_settings['audio_codec']])
                else:
                    cmd.extend(['-c:a', 'copy'])

                # Add output file and overwrite option
                cmd.extend(['-y', output_file])

                # Log the command being executed
                self.ffmpeg_output.emit(f"Command: {' '.join(cmd)}")

                # Run FFmpeg with real-time output capture
                self.current_process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,  # Redirect stderr to stdout
                    universal_newlines=True,
                    bufsize=1
                )

                # Stream output in real-time
                while True:
                    if self.should_stop:
                        if self.current_process:
                            self.current_process.terminate()
                        break

                    output = self.current_process.stdout.readline()
                    if output == '' and self.current_process.poll() is not None:
                        break
                    if output:
                        # Clean up the output line and emit it
                        clean_output = output.strip()
                        if clean_output:
                            self.ffmpeg_output.emit(clean_output)

                # Wait for process to complete
                return_code = self.current_process.wait()

                if return_code == 0 and not self.should_stop:
                    self.conversion_complete.emit(i, True, f"✓ Converted: {Path(input_file).name}")
                else:
                    self.conversion_complete.emit(i, False,
                                                  f"✗ Failed: {Path(input_file).name} (Exit code: {return_code})")

            except Exception as e:
                self.conversion_complete.emit(i, False, f"✗ Error: {Path(input_file).name} - {str(e)}")

        self.all_complete.emit()

    def stop(self):
        self.should_stop = True
        if self.current_process:
            try:
                self.current_process.terminate()
                self.current_process.wait(timeout=5)  # Wait up to 5 seconds
            except subprocess.TimeoutExpired:
                self.current_process.kill()  # Force kill if it doesn't terminate gracefully
            except Exception:
                pass


class MKVConverterGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.mkv_files = []
        self.conversion_worker = None
        self.ffmpeg_path = None
        self.output_folder = None
        self.total_duration_seconds = None  # Store total duration for ETA calculation

        # Initialize QSettings for persistent configuration
        self.settings = QSettings("MKVConverter", "MKVtoMP4")

        # Initialize UI first
        self.initUI()

        # Load saved settings
        self.load_settings()

        # Then check for FFmpeg and offer to download if needed
        self.check_and_setup_ffmpeg()

    def find_ffmpeg(self):
        """Find FFmpeg executable, prioritizing local installation"""
        # First check if ffmpeg.exe is in the same directory as the script
        script_dir = Path(__file__).parent if hasattr(Path(__file__), 'parent') else Path.cwd()
        local_ffmpeg = script_dir / "ffmpeg.exe"

        if local_ffmpeg.exists():
            return str(local_ffmpeg)

        # Check project root (parent directory)
        project_root = script_dir.parent if script_dir.parent != script_dir else script_dir
        root_ffmpeg = project_root / "ffmpeg.exe"

        if root_ffmpeg.exists():
            return str(root_ffmpeg)

        # Check current working directory
        cwd_ffmpeg = Path.cwd() / "ffmpeg.exe"
        if cwd_ffmpeg.exists():
            return str(cwd_ffmpeg)

        # Fall back to system PATH
        try:
            result = subprocess.run(['where', 'ffmpeg'], capture_output=True, text=True, check=True)
            return result.stdout.strip().split('\n')[0]
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass

        # Try 'which' on Unix-like systems
        try:
            result = subprocess.run(['which', 'ffmpeg'], capture_output=True, text=True, check=True)
            return result.stdout.strip()
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass

        return None

    def check_and_setup_ffmpeg(self):
        """Check for FFmpeg and handle download if needed"""
        # Use the check_ffmpeg function from ffmpeg_downloader module
        if check_ffmpeg():
            # FFmpeg is available, find the path
            self.ffmpeg_path = self.find_ffmpeg()
            if self.ffmpeg_path:
                self.log(f"FFmpeg found: {self.ffmpeg_path}")
                self.log("MKV to MP4 Converter ready. Select a folder to begin.")
                return True
            else:
                # This shouldn't happen if check_ffmpeg returned True, but just in case
                self.log("FFmpeg reported as available but path not found. Trying system PATH...")
                import shutil
                system_ffmpeg = shutil.which('ffmpeg')
                if system_ffmpeg:
                    self.ffmpeg_path = system_ffmpeg
                    self.log(f"FFmpeg found in system PATH: {self.ffmpeg_path}")
                    self.log("MKV to MP4 Converter ready. Select a folder to begin.")
                    return True

        # If we get here, check_ffmpeg either showed the dialog or FFmpeg is still not available
        self.ffmpeg_path = self.find_ffmpeg()
        if self.ffmpeg_path:
            self.log(f"FFmpeg successfully installed: {self.ffmpeg_path}")
            self.log("MKV to MP4 Converter ready. Select a folder to begin.")
            return True
        else:
            import mkv2mp4ui.ffmpeg_downloader as downloader
            dialog = QDialog()
            downloader.FFmpegPromptDialog.exec(dialog)
            self.log("WARNING: FFmpeg not found! Conversion will not work until FFmpeg is installed.")
            self.log("Please install FFmpeg manually or restart the application to try the download again.")
            return False

    def load_settings(self):
        """Load saved settings from QSettings"""
        # Load conversion settings
        video_codec = self.settings.value("video_codec", "libx264")
        audio_codec = self.settings.value("audio_codec", "aac")
        crf_value = self.settings.value("crf", 23, type=int)
        preset = self.settings.value("preset", "medium")

        # Apply saved settings to UI components
        video_index = self.video_codec_combo.findText(video_codec)
        if video_index >= 0:
            self.video_codec_combo.setCurrentIndex(video_index)

        audio_index = self.audio_codec_combo.findText(audio_codec)
        if audio_index >= 0:
            self.audio_codec_combo.setCurrentIndex(audio_index)

        self.crf_spinbox.setValue(crf_value)

        preset_index = self.preset_combo.findText(preset)
        if preset_index >= 0:
            self.preset_combo.setCurrentIndex(preset_index)

        # Load window geometry and state
        geometry = self.settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)

        window_state = self.settings.value("windowState")
        if window_state:
            self.restoreState(window_state)

        # Load last used folders
        last_source_folder = self.settings.value("last_source_folder", "")
        if last_source_folder and os.path.exists(last_source_folder):
            self.selected_folder_label.setText(last_source_folder)
            self.selected_folder_label.setStyleSheet("color: #d9a109; background-color: transparent; padding: 2px;")
            # Actually scan for MKV files in the saved folder
            self.scan_for_mkv_files(last_source_folder)

        last_output_folder = self.settings.value("last_output_folder", "")
        if last_output_folder and os.path.exists(last_output_folder):
            self.output_folder = last_output_folder
            self.output_folder_label.setText(last_output_folder)
            self.output_folder_label.setStyleSheet("color: #d9a109; background-color: transparent; padding: 2px;")

        self.log("Settings loaded from previous session")

    def save_settings(self):
        """Save current settings to QSettings"""
        # Save conversion settings
        self.settings.setValue("video_codec", self.video_codec_combo.currentText())
        self.settings.setValue("audio_codec", self.audio_codec_combo.currentText())
        self.settings.setValue("crf", self.crf_spinbox.value())
        self.settings.setValue("preset", self.preset_combo.currentText())

        # Save window geometry and state
        self.settings.setValue("geometry", self.saveGeometry())
        self.settings.setValue("windowState", self.saveState())

        # Save last used folders
        if self.selected_folder_label.text() != "No folder selected":
            self.settings.setValue("last_source_folder", self.selected_folder_label.text())

        if self.output_folder:
            self.settings.setValue("last_output_folder", self.output_folder)

        # Ensure settings are written to disk
        self.settings.sync()

    def closeEvent(self, event):
        """Override closeEvent to save settings before closing"""
        # Stop any running conversion
        if self.conversion_worker and self.conversion_worker.isRunning():
            reply = QMessageBox.question(
                self, "Conversion in Progress",
                "A conversion is currently running. Do you want to stop it and exit?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.stop_conversion()
                # Wait a moment for the worker to stop
                if self.conversion_worker:
                    self.conversion_worker.wait(3000)  # Wait up to 3 seconds
            else:
                event.ignore()
                return

        # Save settings before closing
        self.save_settings()
        self.log("Settings saved")

        # Accept the close event
        event.accept()

    def initUI(self):
        self.setWindowTitle("MKV to MP4 Batch Converter")
        self.setGeometry(100, 100, 900, 700)

        # Central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Create splitter for resizable sections
        splitter = QSplitter(Qt.Orientation.Vertical)
        main_layout.addWidget(splitter)

        # Top section - File selection and settings
        top_widget = QWidget()
        top_layout = QVBoxLayout(top_widget)

        # Folder selection
        folder_group = QGroupBox("Source Folder")
        folder_layout = QVBoxLayout(folder_group)

        folder_button_layout = QHBoxLayout()
        self.select_folder_btn = QPushButton("Select Folder with MKV Files")
        self.select_folder_btn.clicked.connect(self.select_folder)
        self.selected_folder_label = QLabel("No folder selected")
        self.selected_folder_label.setStyleSheet("color: #888; background-color: transparent; padding: 2px;")

        folder_button_layout.addWidget(self.select_folder_btn)
        folder_button_layout.addWidget(self.selected_folder_label, 1)
        folder_layout.addLayout(folder_button_layout)

        # Output folder selection
        output_layout = QHBoxLayout()
        self.select_output_btn = QPushButton("Select Output Folder")
        self.select_output_btn.clicked.connect(self.select_output_folder)
        self.output_folder_label = QLabel("Same as source folder")
        self.output_folder_label.setStyleSheet("color: #888; background-color: transparent; padding: 2px;")

        output_layout.addWidget(self.select_output_btn)
        output_layout.addWidget(self.output_folder_label, 1)
        folder_layout.addLayout(output_layout)

        top_layout.addWidget(folder_group)

        # Conversion settings
        settings_group = QGroupBox("Conversion Settings")
        settings_layout = QHBoxLayout(settings_group)

        # Video codec
        settings_layout.addWidget(QLabel("Video Codec:"))
        self.video_codec_combo = QComboBox()
        self.video_codec_combo.addItems(["libx264", "libx265", "copy"])
        # Connect to save settings when changed
        self.video_codec_combo.currentTextChanged.connect(self.on_settings_changed)
        settings_layout.addWidget(self.video_codec_combo)

        # Audio codec
        settings_layout.addWidget(QLabel("Audio Codec:"))
        self.audio_codec_combo = QComboBox()
        self.audio_codec_combo.addItems(["aac", "mp3", "copy"])
        # Connect to save settings when changed
        self.audio_codec_combo.currentTextChanged.connect(self.on_settings_changed)
        settings_layout.addWidget(self.audio_codec_combo)

        # Quality (CRF)
        settings_layout.addWidget(QLabel("Quality (CRF):"))
        self.crf_spinbox = QSpinBox()
        self.crf_spinbox.setRange(0, 51)
        self.crf_spinbox.setValue(23)
        self.crf_spinbox.setToolTip("Lower values = better quality, larger files (18-28 recommended)")
        # Connect to save settings when changed
        self.crf_spinbox.valueChanged.connect(self.on_settings_changed)
        settings_layout.addWidget(self.crf_spinbox)

        # Preset
        settings_layout.addWidget(QLabel("Preset:"))
        self.preset_combo = QComboBox()
        self.preset_combo.addItems(["medium", "fast", "faster", "veryfast", "slow", "slower"])
        # Connect to save settings when changed
        self.preset_combo.currentTextChanged.connect(self.on_settings_changed)
        settings_layout.addWidget(self.preset_combo)

        settings_layout.addStretch()
        top_layout.addWidget(settings_group)

        # File list
        files_group = QGroupBox("MKV Files Found")
        files_layout = QVBoxLayout(files_group)

        file_controls_layout = QHBoxLayout()
        self.select_all_cb = QCheckBox("Select All")
        self.select_all_cb.clicked.connect(self.toggle_select_all)
        self.file_count_label = QLabel("0 files found")

        file_controls_layout.addWidget(self.select_all_cb)
        file_controls_layout.addWidget(self.file_count_label)
        file_controls_layout.addStretch()

        files_layout.addLayout(file_controls_layout)

        self.file_list = QListWidget()
        self.file_list.setMinimumHeight(150)
        # Connect itemChanged signal to update button state when checkboxes change
        self.file_list.itemChanged.connect(self.update_file_count)
        files_layout.addWidget(self.file_list)

        top_layout.addWidget(files_group)
        splitter.addWidget(top_widget)

        # Bottom section - Conversion controls and progress
        bottom_widget = QWidget()
        bottom_layout = QVBoxLayout(bottom_widget)

        # Conversion controls
        controls_layout = QHBoxLayout()
        self.convert_btn = QPushButton("Start Conversion")
        self.convert_btn.clicked.connect(self.start_conversion)
        self.convert_btn.setEnabled(False)

        self.stop_btn = QPushButton("Stop Conversion")
        self.stop_btn.clicked.connect(self.stop_conversion)
        self.stop_btn.setEnabled(False)

        self.progress_bar = QProgressBar()
        self.progress_label = QLabel("Initializing...")

        controls_layout.addWidget(self.convert_btn)
        controls_layout.addWidget(self.stop_btn)
        controls_layout.addStretch()
        controls_layout.addWidget(self.progress_label)

        bottom_layout.addLayout(controls_layout)
        bottom_layout.addWidget(self.progress_bar)

        # Log output
        log_group = QGroupBox("Conversion Log")
        log_layout = QVBoxLayout(log_group)

        self.log_text = QTextEdit()
        self.log_text.setMaximumHeight(200)
        self.log_text.setFont(QFont("Consolas", 9))
        log_layout.addWidget(self.log_text)

        bottom_layout.addWidget(log_group)
        splitter.addWidget(bottom_widget)

        # Set splitter proportions
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 1)

    def on_settings_changed(self):
        """Called when any setting is changed - saves settings immediately"""
        # Use a timer to debounce rapid changes (like spinning through CRF values)
        if not hasattr(self, 'settings_timer'):
            self.settings_timer = QTimer()
            self.settings_timer.setSingleShot(True)
            self.settings_timer.timeout.connect(self.save_settings)

        # Reset the timer - this debounces rapid changes
        self.settings_timer.start(500)  # Save after 500ms of no changes

    def select_folder(self):
        # Start from the last used folder if available
        start_dir = self.settings.value("last_source_folder", "")

        folder = QFileDialog.getExistingDirectory(
            self,
            "Select folder containing MKV files",
            start_dir
        )
        if folder:
            self.selected_folder_label.setText(folder)
            self.selected_folder_label.setStyleSheet("color: #d9a109; background-color: transparent; padding: 2px;")
            self.scan_for_mkv_files(folder)
            # Save the folder selection immediately
            self.settings.setValue("last_source_folder", folder)

    def select_output_folder(self):
        # Start from the last used output folder if available
        start_dir = self.settings.value("last_output_folder", "")
        if not start_dir:
            # Fall back to the source folder if no output folder was previously set
            start_dir = self.settings.value("last_source_folder", "")

        folder = QFileDialog.getExistingDirectory(
            self,
            "Select output folder for MP4 files",
            start_dir
        )
        if folder:
            self.output_folder = folder
            self.output_folder_label.setText(folder)
            self.output_folder_label.setStyleSheet("color: #d9a109; background-color: transparent; padding: 2px;")
            # Save the output folder selection immediately
            self.settings.setValue("last_output_folder", folder)
        else:
            self.output_folder = None
            self.output_folder_label.setText("Same as source folder")
            self.output_folder_label.setStyleSheet("color: #888; background-color: transparent; padding: 2px;")

    def scan_for_mkv_files(self, folder):
        self.mkv_files = []
        self.file_list.clear()

        # Find all MKV files
        for file_path in Path(folder).rglob("*.mkv"):
            self.mkv_files.append(str(file_path))

        # Add to list widget with checkboxes
        for mkv_file in self.mkv_files:
            item = QListWidgetItem(Path(mkv_file).name)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked)
            item.setData(Qt.ItemDataRole.UserRole, mkv_file)  # Store full path
            self.file_list.addItem(item)

        self.update_file_count()
        self.log(f"Found {len(self.mkv_files)} MKV files in {folder}")

    def update_file_count(self):
        total = len(self.mkv_files)
        selected = sum(1 for i in range(self.file_list.count())
                       if self.file_list.item(i).checkState() == Qt.CheckState.Checked)

        self.file_count_label.setText(f"{selected}/{total} files selected")
        self.convert_btn.setEnabled(selected > 0 and self.ffmpeg_path is not None)

    def toggle_select_all(self):
        check_state = Qt.CheckState.Checked if self.select_all_cb.isChecked() else Qt.CheckState.Unchecked

        for i in range(self.file_list.count()):
            self.file_list.item(i).setCheckState(check_state)

        self.update_file_count()

    def get_selected_files(self):
        selected = []
        for i in range(self.file_list.count()):
            item = self.file_list.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                input_file = item.data(Qt.ItemDataRole.UserRole)

                # Determine output file path
                if self.output_folder:
                    output_file = os.path.join(self.output_folder,
                                               Path(input_file).stem + ".mp4")
                else:
                    output_file = str(Path(input_file).with_suffix(".mp4"))

                selected.append((input_file, output_file))
        return selected

    def start_conversion(self):
        selected_files = self.get_selected_files()
        if not selected_files:
            QMessageBox.warning(self, "Warning", "No files selected for conversion!")
            return

        # Check if FFmpeg is available
        if not self.ffmpeg_path:
            # Try to find FFmpeg again in case it was installed
            self.ffmpeg_path = self.find_ffmpeg()

            if not self.ffmpeg_path:
                reply = QMessageBox.question(
                    self, "FFmpeg Still Not Found",
                    "FFmpeg is still not found!\n\n"
                    "Would you like to try the FFmpeg downloader again?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.Yes
                )

                if reply == QMessageBox.StandardButton.Yes:
                    if check_ffmpeg():
                        # Check_ffmpeg handles the download dialog
                        new_ffmpeg_path = self.find_ffmpeg()
                        if new_ffmpeg_path:
                            self.ffmpeg_path = new_ffmpeg_path
                            # Continue with conversion since FFmpeg is now available
                        else:
                            return  # Still no FFmpeg, abort
                    else:
                        return  # User cancelled or failed
                else:
                    return  # User doesn't want to download

        # Test FFmpeg
        try:
            subprocess.run([self.ffmpeg_path, '-version'], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            QMessageBox.critical(self, "Error",
                                 f"FFmpeg executable found but not working: {self.ffmpeg_path}\n\n"
                                 "Please check your FFmpeg installation.")
            return

        # Get codec settings
        codec_settings = {
            'video_codec': self.video_codec_combo.currentText(),
            'audio_codec': self.audio_codec_combo.currentText(),
            'crf': self.crf_spinbox.value() if self.video_codec_combo.currentText() != 'copy' else None,
            'preset': self.preset_combo.currentText() if self.video_codec_combo.currentText() != 'copy' else None
        }

        # Setup progress
        self.progress_bar.setMaximum(len(selected_files))
        self.progress_bar.setValue(0)

        # Start conversion worker
        self.conversion_worker = ConversionWorker(selected_files, self.output_folder, codec_settings, self.ffmpeg_path)
        self.conversion_worker.progress_updated.connect(self.update_progress)
        self.conversion_worker.conversion_complete.connect(self.file_conversion_complete)
        self.conversion_worker.ffmpeg_output.connect(self.log_ffmpeg_output)
        self.conversion_worker.all_complete.connect(self.all_conversions_complete)

        self.conversion_worker.start()

        # Update UI
        self.convert_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.log(f"Starting conversion of {len(selected_files)} files...")

    def stop_conversion(self):
        if self.conversion_worker:
            self.conversion_worker.stop()
            self.log("Stopping conversion...")

    def update_progress(self, file_index, status_message):
        self.progress_bar.setValue(file_index)
        self.progress_label.setText(status_message)

    def file_conversion_complete(self, file_index, success, message):
        self.progress_bar.setValue(file_index + 1)
        self.log(message)

    def all_conversions_complete(self):
        self.progress_label.setText("Conversion complete!")
        self.convert_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.log("All conversions completed!")

        # Show completion message
        QMessageBox.information(self, "Complete", "Batch conversion completed!")

    def log_ffmpeg_output(self, output_line):
        """Log FFmpeg output with timestamp and parse progress"""
        from datetime import datetime
        import re

        timestamp = datetime.now().strftime("%H:%M:%S")

        # Parse progress information and calculate ETA
        if "frame=" in output_line and "time=" in output_line:
            self.parse_progress_and_update_eta(output_line)
            # Progress-related output in blue with enhanced formatting
            self.log_text.append(f'<span style="color: #42a5f5;">[{timestamp}] {output_line}</span>')
        elif "error" in output_line.lower() or "failed" in output_line.lower():
            self.log_text.append(f'<span style="color: #ff6b6b;">[{timestamp}] {output_line}</span>')
        elif "warning" in output_line.lower():
            self.log_text.append(f'<span style="color: #ffa726;">[{timestamp}] {output_line}</span>')
        elif "Duration:" in output_line:
            # Store duration for ETA calculation
            self.parse_duration(output_line)
            self.log_text.append(f"[{timestamp}] {output_line}")
        else:
            self.log_text.append(f"[{timestamp}] {output_line}")

        # Auto-scroll to bottom
        self.log_text.verticalScrollBar().setValue(
            self.log_text.verticalScrollBar().maximum()
        )

    def parse_duration(self, duration_line):
        """Parse total duration from FFmpeg output"""
        import re
        # Look for Duration: HH:MM:SS.ss
        match = re.search(r'Duration: (\d{2}):(\d{2}):(\d{2}\.\d{2})', duration_line)
        if match:
            hours, minutes, seconds = match.groups()
            self.total_duration_seconds = int(hours) * 3600 + int(minutes) * 60 + float(seconds)
        else:
            self.total_duration_seconds = None

    def parse_progress_and_update_eta(self, progress_line):
        """Parse FFmpeg progress line and update ETA"""
        import re
        from datetime import datetime, timedelta

        # Parse current time processed: time=00:01:06.69
        time_match = re.search(r'time=(\d{2}):(\d{2}):(\d{2}\.\d{2})', progress_line)
        speed_match = re.search(r'speed=(\d+\.?\d*)x', progress_line)

        if time_match and hasattr(self, 'total_duration_seconds') and self.total_duration_seconds:
            hours, minutes, seconds = time_match.groups()
            current_seconds = int(hours) * 3600 + int(minutes) * 60 + float(seconds)

            # Calculate progress percentage
            progress_percent = (current_seconds / self.total_duration_seconds) * 100

            # Calculate ETA using speed if available
            if speed_match:
                speed = float(speed_match.group(1))
                remaining_seconds = self.total_duration_seconds - current_seconds
                eta_seconds = remaining_seconds / speed if speed > 0 else 0

                eta_time = datetime.now() + timedelta(seconds=eta_seconds)
                eta_str = eta_time.strftime("%H:%M:%S")

                # Update progress label with detailed info
                self.progress_label.setText(
                    f"Progress: {progress_percent:.1f}% | Speed: {speed:.1f}x | ETA: {eta_str}"
                )
            else:
                # Fallback without speed info
                self.progress_label.setText(f"Progress: {progress_percent:.1f}%")

    def log(self, message):
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")
        self.log_text.verticalScrollBar().setValue(
            self.log_text.verticalScrollBar().maximum()
        )


def main():
    app = QApplication(sys.argv)

    # Set application properties for QSettings
    app.setOrganizationName("MKVConverter")
    app.setApplicationName("MKVtoMP4")

    # Check if ffmpeg-python is installed
    try:
        import ffmpeg
    except ImportError:
        QMessageBox.critical(None, "Missing Dependency",
                             "ffmpeg-python is required but not installed.\n\n"
                             "Please install it with:\npip install ffmpeg-python")
        sys.exit(1)

    # Create and show the main window
    # FFmpeg checking is now handled within the main window initialization
    window = MKVConverterGUI()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()