# scripts/utils.py
from vnpy.trader.constant import Exchange

def get_exchange_by_code(code: str) -> Exchange:
    """
    根据股票代码前缀判断交易所
    规则：
        - 6 开头：上海证券交易所 (SSE)
        - 0、2、3 开头：深圳证券交易所 (SZSE)
        - 4、8 开头：北京证券交易所 (BSE) 或老三板，按需调整
    """
    if code.startswith(('6', '5')):   # 5开头是基金/债券，但股票主要是6
        return Exchange.SSE
    elif code.startswith(('0', '2', '3')):
        return Exchange.SZSE
    elif code.startswith(('4', '8')):
        return Exchange.BSE   # 北京证券交易所
    else:
        # 默认返回 SSE，或抛出异常
        raise ValueError(f"无法确定股票 {code} 的交易所")