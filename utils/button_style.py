# button_styles.py

BUTTON_STYLES = {
    'default': """
        QPushButton {
            background-color: #f8f9fa;
            border: 1px solid #dee2e6;
            border-radius: 4px;
            color: #212529;
            padding: 8px 16px;
            min-height: 38px;
            font-size: 14px;
            font-weight: 500;
        }
        QPushButton:hover {
            background-color: #e9ecef;
            border-color: #dee2e6;
            color: #0a58ca;
        }
        QPushButton:pressed {
            background-color: #dde0e3;
            border-color: #dee2e6;
            color: #0a53be;
        }
        QPushButton:disabled {
            background-color: #e9ecef;
            border-color: #dee2e6;
            color: #6c757d;
        }
    """
}

# 定义轮廓样式的颜色映射
OUTLINE_STYLES = {
    'default': """
        QPushButton {
            background-color: transparent;
            border: 1px solid #6c757d;
            color: #6c757d;
        }
        QPushButton:hover {
            background-color: #6c757d;
            color: #ffffff;
        }
    """
}

def get_button_style(style_type='default', size=None, outline=False):
    """
    获取按钮样式
    :param style_type: 按钮类型 (default, primary, success, danger, warning, info, none)
    :param size: 按钮大小 (None, 'small', 'large')
    :param outline: 是否使用轮廓样式
    :return: 样式字符串
    """
    # 获取基础样式或轮廓样式
    if outline:
        base_style = OUTLINE_STYLES.get(style_type, OUTLINE_STYLES['default'])
    else:
        base_style = BUTTON_STYLES.get(style_type, BUTTON_STYLES['default'])
    
    # 添加大小样式
    if size:
        size_style = BUTTON_STYLES.get(size, '')
        base_style = base_style.rstrip() + size_style
    
    return base_style