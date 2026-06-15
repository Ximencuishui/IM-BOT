"""
插件系统初始化
"""
import importlib
import os


def load_plugins(app):
    """加载所有插件"""
    plugin_dir = os.path.dirname(__file__)
    for item in os.listdir(plugin_dir):
        item_path = os.path.join(plugin_dir, item)
        if os.path.isdir(item_path) and item != 'base':
            init_file = os.path.join(item_path, '__init__.py')
            if os.path.exists(init_file):
                try:
                    module = importlib.import_module(f'plugins.{item}')
                    if hasattr(module, 'register_plugin'):
                        module.register_plugin(app)
                except Exception as e:
                    print(f"加载插件 {item} 失败: {e}")