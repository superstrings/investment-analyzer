"""
港股期权合约乘数配置

数据来源: 港交所 (HKEX) 官网
https://www.hkex.com.hk/Products/Listed-Derivatives/Single-Stock/Stock-Options?sc_lang=en

注意事项:
1. 港股期权合约乘数 ≠ 股票每手股数
2. 合约乘数由港交所规定，可能随时调整
3. 新增期权时需要查询 HKEX 官网确认合约乘数
4. 美股期权合约乘数统一为 100

更新日期: 2026-01-30
"""

# HKATS 代码 -> 合约乘数 (每张合约股数)
HK_OPTION_MULTIPLIERS = {
    # 半导体
    "HOS": 2000,    # 华虹半导体 (01347)
    "SMC": 2500,    # 中芯国际 (00981)

    # 互联网/科技
    "TCH": 100,     # 腾讯控股 (00700)
    "ALB": 500,     # 阿里巴巴 (09988)
    "MIU": 1000,    # 小米集团 (01810)
    "BIU": 150,     # 百度集团 (09888)
    "MET": 500,     # 美团 (03690)
    "KST": 500,     # 快手 (01024)
    "KDS": 500,     # 快手 (01024) - 备用代码
    "NCL": 100,     # 京东集团 (09618) - 需确认

    # 金融/保险
    "PAI": 500,     # 中国平安 (02318)
    "CLI": 1000,    # 中国人寿 (02628)
    "XCC": 1000,    # 建设银行 (00939)
    "ICB": 1000,    # 工商银行 (01398)

    # 能源/资源
    "CNC": 1000,    # 中海油 (00883)
    "ZJM": 2000,    # 紫金矿业 (02899)
    "JXC": 1000,    # 江西铜业 (00358) - 需确认

    # 汽车
    "BYD": 500,     # 比亚迪 (01211) - 注意: HKATS 代码是 BYD 不是 POP
    "POP": 500,     # 比亚迪 (备用代码，如有)

    # 消费/零售
    "CAT": 200,     # 安踏体育 (02020)

    # 医药
    "CIT": 2000,    # 阿里健康 (00241)
    "CTS": 1000,    # 中国生物制药 (01177)

    # 电信
    "CLI": 1000,    # 中兴通讯 (00763) - 代码冲突，需确认

    # 其他
    "HEX": 100,     # 港交所 (00388)
    "LAU": 100,     # 众安在线 (06060)
    "GHL": 1000,    # 海底捞 (06862)
    "SNO": 400,     # 国药控股 (01099)
    "ZAO": 1000,    # 颐海国际 (01579)
    "HNP": 2000,    # 华能国际 (00902)
}

# 美股期权标准合约乘数
US_OPTION_MULTIPLIER = 100


def get_hk_option_multiplier(hkats_code: str) -> int:
    """
    获取港股期权合约乘数

    Args:
        hkats_code: HKATS 期权代码前缀 (如 HOS, SMC, TCH)

    Returns:
        合约乘数，如果未找到则返回 None
    """
    return HK_OPTION_MULTIPLIERS.get(hkats_code.upper())


def get_option_multiplier(market: str, option_code: str) -> int:
    """
    获取期权合约乘数

    Args:
        market: 市场 (HK, US)
        option_code: 期权代码 (如 HOS260330C90000, NVDA250117C150000)

    Returns:
        合约乘数
    """
    if market == "US":
        return US_OPTION_MULTIPLIER

    if market == "HK":
        # 提取 HKATS 代码前缀 (前2-3个字母)
        prefix = ""
        for c in option_code:
            if c.isalpha():
                prefix += c
            else:
                break

        multiplier = get_hk_option_multiplier(prefix)
        if multiplier:
            return multiplier

        # 未找到配置，返回默认值并警告
        import logging
        logging.warning(f"未找到 {option_code} ({prefix}) 的合约乘数配置，使用默认值 100")
        return 100

    return 100  # 默认值
