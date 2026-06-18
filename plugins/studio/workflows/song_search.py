"""
歌曲代找工作流脚本
根据歌曲名称在曲库中搜索匹配歌曲资源
"""
import logging
from typing import Callable

logger = logging.getLogger(__name__)


class SongSearchWorkflow:
    """歌曲代找工作流"""

    def __init__(self):
        self._progress_callback = None

    def set_progress_callback(self, callback: Callable[[int, str], None]):
        self._progress_callback = callback

    def _report_progress(self, progress: int, message: str):
        if self._progress_callback:
            self._progress_callback(progress, message)
        logger.info(f"[{progress}%] {message}")

    def search_local(self, song_name: str, artist: str = '') -> list:
        """
        在本地曲库搜索（TODO: 实现本地曲库索引）
        返回匹配歌曲列表
        """
        self._report_progress(30, f"正在搜索: {song_name} {artist}")
        # TODO: 实现本地曲库搜索
        return []

    def search_online(self, song_name: str, artist: str = '') -> list:
        """
        在线搜索歌曲（TODO: 接入音乐API）
        返回匹配歌曲列表
        """
        self._report_progress(50, f"正在在线搜索: {song_name} {artist}")
        # TODO: 实现在线音乐API搜索
        return []

    def process(self, song_name: str, artist: str = '') -> dict:
        """
        执行歌曲代找流程

        Args:
            song_name: 歌曲名称
            artist: 歌手名称（可选）

        Returns:
            dict: {"found": bool, "songs": list, "message": str}
        """
        self._report_progress(10, f"开始搜索歌曲: {song_name}")

        # 先搜索本地曲库
        local_results = self.search_local(song_name, artist)
        if local_results:
            self._report_progress(100, f"在本地曲库找到 {len(local_results)} 首匹配歌曲")
            return {'found': True, 'source': 'local', 'songs': local_results}

        # 再搜索在线资源
        online_results = self.search_online(song_name, artist)
        if online_results:
            self._report_progress(100, f"在线找到 {len(online_results)} 首匹配歌曲")
            return {'found': True, 'source': 'online', 'songs': online_results}

        self._report_progress(100, "未找到匹配歌曲")
        return {
            'found': False,
            'songs': [],
            'message': f'未找到歌曲 "{song_name}"{" - " + artist if artist else ""}，请通知老板人工处理',
        }


def run(song_name: str, artist: str = '', progress_callback: Callable = None, **kwargs) -> dict:
    """
    工作流入口函数
    """
    workflow = SongSearchWorkflow()
    if progress_callback:
        workflow.set_progress_callback(progress_callback)
    return workflow.process(song_name, artist)