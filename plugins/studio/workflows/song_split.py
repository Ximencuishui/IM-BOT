"""
歌曲分离工作流脚本
接收歌曲文件，调用分离工具（如 Demucs/Spleeter）进行人声与伴奏分离
"""
import os
import logging
import subprocess
import tempfile
from typing import Callable

logger = logging.getLogger(__name__)


class SongSplitWorkflow:
    """歌曲分离工作流"""

    SUPPORTED_FORMATS = ('.mp3', '.wav', '.flac', '.m4a', '.ogg', '.wma')

    def __init__(self, output_dir: str = None):
        self.output_dir = output_dir or os.path.join(os.getcwd(), 'data', 'studio_output')
        os.makedirs(self.output_dir, exist_ok=True)
        self._progress_callback = None

    def set_progress_callback(self, callback: Callable[[int, str], None]):
        """设置进度回调函数"""
        self._progress_callback = callback

    def _report_progress(self, progress: int, message: str):
        """报告进度"""
        if self._progress_callback:
            self._progress_callback(progress, message)
        logger.info(f"[{progress}%] {message}")

    def validate_file(self, file_path: str) -> bool:
        """验证输入文件"""
        if not os.path.exists(file_path):
            logger.error(f"文件不存在: {file_path}")
            return False

        ext = os.path.splitext(file_path)[1].lower()
        if ext not in self.SUPPORTED_FORMATS:
            logger.error(f"不支持的文件格式: {ext}，支持格式: {self.SUPPORTED_FORMATS}")
            return False

        file_size = os.path.getsize(file_path)
        max_size = 200 * 1024 * 1024  # 200MB
        if file_size > max_size:
            logger.error(f"文件过大: {file_size / 1024 / 1024:.1f}MB，最大支持 200MB")
            return False

        return True

    def run_demucs(self, input_file: str, model: str = 'htdemucs') -> str:
        """
        使用 Demucs 进行歌曲分离
        返回输出目录路径
        """
        self._report_progress(10, "准备分离环境...")

        output_dir = os.path.join(self.output_dir, os.path.splitext(os.path.basename(input_file))[0])
        os.makedirs(output_dir, exist_ok=True)

        self._report_progress(20, f"开始分离 (模型: {model})...")

        try:
            cmd = [
                'python', '-m', 'demucs',
                '--two-stems', 'vocals',  # 分离为人声和伴奏
                '-o', output_dir,
                '--mp3',  # 输出为MP3
                input_file,
            ]

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8'
            )

            for line in process.stdout:
                line = line.strip()
                if line:
                    logger.debug(f"Demucs: {line}")
                    # 尝试从输出中解析进度
                    if '%' in line:
                        try:
                            progress_str = line.split('%')[0].strip()
                            progress = int(progress_str.split()[-1])
                            mapped_progress = 20 + int(progress * 0.7)
                            self._report_progress(mapped_progress, f"分离中... {progress}%")
                        except (ValueError, IndexError):
                            pass

            process.wait()

            if process.returncode == 0:
                self._report_progress(95, "分离完成，正在整理文件...")
                return output_dir
            else:
                raise RuntimeError(f"Demucs 处理失败，返回码: {process.returncode}")

        except FileNotFoundError:
            logger.error("Demucs 未安装，请执行: pip install demucs")
            raise
        except Exception as e:
            logger.error(f"分离过程出错: {e}", exc_info=True)
            raise

    def run_spleeter(self, input_file: str) -> str:
        """
        使用 Spleeter 进行歌曲分离（备选方案）
        """
        self._report_progress(10, "准备 Spleeter 分离环境...")

        output_dir = os.path.join(self.output_dir, os.path.splitext(os.path.basename(input_file))[0])
        os.makedirs(output_dir, exist_ok=True)

        self._report_progress(20, "开始 Spleeter 分离...")

        try:
            from spleeter.separator import Separator

            separator = Separator('spleeter:2stems')
            self._report_progress(30, "模型加载完成，开始处理...")

            # Spleeter 不提供进度回调，发送固定进度
            self._report_progress(50, "正在分离人声和伴奏...")
            separator.separate_to_file(input_file, output_dir)

            self._report_progress(95, "分离完成，正在整理文件...")
            return output_dir

        except ImportError:
            logger.error("Spleeter 未安装，请执行: pip install spleeter")
            raise
        except Exception as e:
            logger.error(f"Spleeter 分离失败: {e}", exc_info=True)
            raise

    def process(self, input_file: str, use_demucs: bool = True) -> dict:
        """
        执行歌曲分离主流程

        Args:
            input_file: 输入音频文件路径
            use_demucs: 是否使用 Demucs（否则使用 Spleeter）

        Returns:
            dict: {"output_dir": str, "files": [{"name": str, "path": str}]}
        """
        self._report_progress(5, "正在验证文件...")
        if not self.validate_file(input_file):
            raise ValueError(f"文件验证失败: {input_file}")

        if use_demucs:
            output_dir = self.run_demucs(input_file)
        else:
            output_dir = self.run_spleeter(input_file)

        # 收集输出文件
        result_files = []
        for root, dirs, files in os.walk(output_dir):
            for f in files:
                if f.endswith('.mp3') or f.endswith('.wav'):
                    result_files.append({
                        'name': f,
                        'path': os.path.join(root, f),
                    })

        self._report_progress(100, "分离完成！")
        return {
            'output_dir': output_dir,
            'files': result_files,
        }


def run(input_file: str, progress_callback: Callable = None, **kwargs) -> dict:
    """
    工作流入口函数

    Args:
        input_file: 输入文件路径
        progress_callback: 进度回调函数
        **kwargs: 其他参数

    Returns:
        dict: 处理结果
    """
    workflow = SongSplitWorkflow()
    if progress_callback:
        workflow.set_progress_callback(progress_callback)
    return workflow.process(input_file, kwargs.get('use_demucs', True))