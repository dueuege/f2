# path: f2/utils/utils.py

import f2
import re
import sys
import httpx
import random
import asyncio
import secrets
import datetime
import traceback
import browser_cookie3
import importlib_resources

from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from typing import Any, Dict, List, Union, Optional
from cryptography.exceptions import InvalidTag, InvalidKey
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives import padding as aes_padding
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.asymmetric import padding as rsa_padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from f2.log.logger import logger
from f2.i18n.translator import _
from f2.exceptions.api_exceptions import APIFilterError

# 生成一个 16 字节的随机字节串 (Generate a random byte string of 16 bytes)
seed_bytes = secrets.token_bytes(16)

# 将字节字符串转换为整数 (Convert the byte string to an integer)
seed_int = int.from_bytes(seed_bytes, "big")

# 设置随机种子 (Seed the random module)
random.seed(seed_int)


def gen_random_str(randomlength: int) -> str:
    """
    根据传入长度产生随机字符串 (Generate a random string based on the given length)

    Args:
        randomlength (int): 需要生成的随机字符串的长度 (The length of the random string to be generated)

    Returns:
        str: 生成的随机字符串 (The generated random string)
    """

    base_str = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+-"
    return "".join(random.choice(base_str) for _ in range(randomlength))


def get_timestamp(unit: str = "milli") -> int:
    """
    根据给定的单位获取当前时区的时间戳 (Get the current time based on the given unit)

    Args:
        unit (str): 时间单位，可以是 "milli"、"sec"、"min" 等
            (The time unit, which can be "milli", "sec", "min", etc.)

    Returns:
        int: 根据给定单位的当前时间 (The current time based on the given unit)
    """

    now = datetime.datetime.now(datetime.timezone.utc) - datetime.datetime(
        1970, 1, 1, tzinfo=datetime.timezone.utc
    )
    if unit == "milli":
        return int(now.total_seconds() * 1000)
    elif unit == "sec":
        return int(now.total_seconds())
    elif unit == "min":
        return int(now.total_seconds() / 60)
    else:
        raise ValueError(_("不支持的时间单位：{0}").format(unit))


def timestamp_2_str(
    timestamp: Union[str, int, float, list],
    format: str = "%Y-%m-%d %H-%M-%S",
    tz: datetime.timezone = datetime.timezone(datetime.timedelta(hours=8)),
) -> Union[str, int, float, list]:
    """
    将 UNIX 时间戳转换为东八区北京时间格式化字符串使用

    Args:
        timestamp (Union[str, int, float, list]): 要转换的 UNIX 时间戳
        format (str, optional): 返回的日期时间字符串的格式，默认为 '%Y-%m-%d %H-%M-%S'。
        tz (datetime.timezone, optional): 时区，默认为东八区北京时间

    Returns:
        Union[str, int, float, list]: 格式化的日期时间字符串
    """

    # 处理空或无效时间戳
    if timestamp in [None, "None"]:
        return _("Invalid timestamp")

    if timestamp in [0, "0"]:
        return datetime.datetime.now(tz=tz).strftime(format)

    # 递归处理列表中的时间戳
    def convert(ts):
        if isinstance(ts, str):
            # 处理类似 "Wed Jun 01 10:23:01 +0800 2022" 的格式
            if len(ts) == 30:
                return datetime.datetime.strptime(ts, "%a %b %d %H:%M:%S %z %Y")
            else:
                try:
                    timestamp_value = float(ts)
                    if timestamp_value > 1e10:
                        timestamp_value /= 1000
                    return datetime.datetime.fromtimestamp(timestamp_value, tz=tz)
                except ValueError:
                    raise TypeError(_("无效的时间戳字符串: {0}").format(ts))
        elif isinstance(ts, (int, float)):
            timestamp_value = float(ts)
            if timestamp_value > 1e10:
                timestamp_value /= 1000
            return datetime.datetime.fromtimestamp(timestamp_value, tz=tz)
        else:
            raise TypeError(_("不支持的时间戳类型: {0}").format(type(ts)))

    # 如果是列表，则递归处理每个时间戳
    if isinstance(timestamp, list):
        return [
            (
                convert(ts).strftime(format)
                if not isinstance(ts, list)
                else [convert(t).strftime(format) for t in ts]
            )
            for ts in timestamp
        ]

    # 处理单个时间戳
    return convert(timestamp).strftime(format)


def str_2_timestamp(
    date_str: str,
    format: str = "%Y-%m-%d %H-%M-%S",
    unit: str = "milli",
    tz: datetime.timezone = datetime.timezone(datetime.timedelta(hours=8)),
) -> int:
    """
    将日期时间字符串转换为 UNIX 时间戳

    Args:
        date_str (str): 要转换的日期时间字符串 (The date-time string to be converted)
        format (str, optional): 日期时间字符串的格式，默认为 '%Y-%m-%d %H-%M-%S'。
                                (The format for the date-time string, defaults to '%Y-%m-%d %H-%M-%S')
        unit (str, optional): 时间单位，默认为 'milli'。 (The time unit, defaults to 'milli')
        tz (datetime.timezone, optional): 时区，默认为东八区北京时间 (The timezone, defaults to UTC+8)

    Returns:
        int: UNIX 时间戳 (The UNIX timestamp)
    """

    date_obj = datetime.datetime.strptime(date_str, format)
    if unit == "milli":
        return int(date_obj.replace(tzinfo=tz).timestamp() * 1000)
    elif unit == "sec":
        return int(date_obj.replace(tzinfo=tz).timestamp())
    elif unit == "min":
        return int(date_obj.replace(tzinfo=tz).timestamp() / 60)
    else:
        raise ValueError(_("不支持的时间单位：{0}").format(unit))


def interval_2_timestamp(
    interval: str,
    date_type: str = "start",
    format: str = "%Y-%m-%d %H-%M-%S",
    unit: str = "milli",
    tz: datetime.timezone = datetime.timezone(datetime.timedelta(hours=8)),
) -> int:
    """
    将日期区间字符串转换为 UNIX 时间戳区间

    Args:
        interval (str): 日期区间字符串，格式为 '2022-01-01|2023-01-01' (The date range string, formatted as '2022-01-01|2023-01-01')
        date_type (str, optional): 'start' 表示使用开始日期，'end' 表示使用结束日期 (Whether to use the start or end date, defaults to 'start')
        format (str, optional): 日期字符串的格式，默认为 '%Y-%m-%d' (The date string format, defaults to '%Y-%m-%d')
        unit (str, optional): 时间单位，默认为 'milli' (The time unit, defaults to 'milli')
        tz (datetime.timezone, optional): 时区，默认为东八区北京时间 (The timezone, defaults to UTC+8)

    Returns:
        int: UNIX 时间戳 (The UNIX timestamp)
    """

    if not interval:
        logger.warning(_("日期区间为空，无法转换为时间戳"))
        return 0

    try:
        start_date, end_date = interval.split("|")
        if date_type == "start":
            date_str = f"{start_date} 00-00-00"
        elif date_type == "end":
            date_str = f"{end_date} 23-59-59"
        else:
            logger.warning(_("不支持的日期类型：{0}").format(date_type))
            return 0

        return str_2_timestamp(date_str, format, unit, tz)
    except ValueError:
        logger.error(_("日期区间参数格式错误，请查阅文档后重试"))
        logger.error(traceback.format_exc())
    return 0


def split_set_cookie(cookie_str: str) -> str:
    """
    拆分Set-Cookie字符串并拼接 (Split the Set-Cookie string and concatenate)

    Args:
        cookie_str (str): 待拆分的Set-Cookie字符串 (The Set-Cookie string to be split)

    Returns:
        str: 拼接后的Cookie字符串 (Concatenated cookie string)
    """

    if not isinstance(cookie_str, str):
        raise TypeError(_("cookie_str 参数应为字符串"))

    # 拆分Set-Cookie字符串,避免错误地在expires字段的值中分割字符串 (Split the Set-Cookie string, avoiding incorrect splitting on the value of the 'expires' field)
    # 拆分每个Cookie字符串，只获取第一个分段（即key=value部分） / Split each Cookie string, only getting the first segment (i.e., key=value part)
    # 拼接所有的Cookie (Concatenate all cookies)
    return ";".join(
        cookie.split(";")[0] for cookie in re.split(", (?=[a-zA-Z])", cookie_str)
    )


def split_dict_cookie(cookie_dict: Dict) -> str:
    """
    拆分Cookie字典并拼接 (Split the Cookie dictionary and concatenate)

    Args:
        cookie_dict (dict): 待拆分的Cookie字典 (The Cookie dictionary to be split)

    Returns:
        str: 拼接后的Cookie字符串 (Concatenated cookie string)
    """
    return "; ".join(f"{key}={value}" for key, value in cookie_dict.items())


def extract_valid_urls(inputs: Union[str, List[str]]) -> Union[str, List[str], None]:
    """
    从输入中提取有效的URL (Extract valid URLs from input)

    Args:
        inputs (Union[str, list[str]]): 输入的字符串或字符串列表 (Input string or list of strings)

    Returns:
        Union[str, list[str]]: 提取出的有效URL或URL列表 (Extracted valid URL or list of URLs)
    """
    url_pattern = re.compile(r"https?://\S+")

    # 如果输入是单个字符串
    if isinstance(inputs, str):
        match = url_pattern.search(inputs)
        return match.group(0) if match else None

    # 如果输入是字符串列表
    elif isinstance(inputs, list):
        valid_urls = []

        for input_str in inputs:
            matches = url_pattern.findall(input_str)
            if matches:
                valid_urls.extend(matches)

        return valid_urls


def _get_first_item_from_list(_list: List) -> List:
    """
    从列表中提取第一个项目 (Extract the first item from a list)

    .. deprecated:: 0.0.1.6
        `_get_first_item_from_list` 在 0.0.1.7 版本及之后将被移除。
        本方法不再有替代方案。 (This function will be removed in version 0.0.1.7 or later.
        No replacement will be provided.)

    Args:
        _list (List): 输入的列表 (Input list)

    Returns:
        List: 提取出的第一个项目 (The extracted first item)
    """
    import warnings

    warnings.warn(
        _(
            "_get_first_item_from_list is deprecated and will be removed in version 0.0.1.7. "
        ),
        _("No replacement will be provided."),
        DeprecationWarning,
        stacklevel=2,
    )
    # 检查是否是列表 (Check if it's a list)
    if _list and isinstance(_list, list):
        # 如果列表里第一个还是列表则提起每一个列表的第一个值
        # (If the first one in the list is still a list then bring up the first value of each list)
        if isinstance(_list[0], list):
            return [inner[0] for inner in _list if inner]
        # 如果只是普通列表，则返回这个列表包含的第一个项目作为新列表
        # (If it's just a regular list, return the first item wrapped in a list)
        else:
            return [_list[0]]
    return []


def get_resource_path(filepath: str) -> Path:
    """
    获取资源文件的路径 (Get the path of the resource file)

    Args:
        filepath: str: 文件路径 (file path)
    """

    return importlib_resources.files("f2") / filepath


def replaceT(obj: Union[str, Any]) -> Union[str, Any]:
    """
    替换文案非法字符 (Replace illegal characters in the text)

    Args:
        obj (str): 传入对象 (Input object)

    Returns:
        new: 处理后的内容 (Processed content)
    """

    reSub = r"[^\u4e00-\u9fa5a-zA-Z0-9#]"

    if isinstance(obj, list):
        return [re.sub(reSub, "_", i) if isinstance(i, str) else i or "" for i in obj]

    if isinstance(obj, str):
        return re.sub(reSub, "_", obj)

    return obj


def split_filename(text: str, os_limit: Dict[str, int]) -> str:
    """
    根据操作系统的字符限制分割文件名，并用 '......' 代替。
    前半部分是后半部分的两倍。

    Args:
        text (str): 要计算的文本
        os_limit (Dict[str, int]): 操作系统的字符限制

    Returns:
        str: 分割后的文本
    """
    # 获取操作系统名称和文件名长度限制
    os_name = sys.platform
    filename_length_limit = os_limit.get(os_name, 200)

    # 清理转义字符
    text = re.sub(r"\s+", " ", text).strip()

    # 计算文本的字节长度
    text_bytes = text.encode("utf-8")
    text_length = len(text_bytes)

    # 如果长度未超过限制，直接返回
    if text_length <= filename_length_limit:
        return text

    # 计算截断比例（2:1）
    split_index_first = (filename_length_limit - 6) * 2 // 3
    split_index_second = (filename_length_limit - 6) // 3

    # 截取前后部分
    first_part = text_bytes[:split_index_first].decode("utf-8", errors="ignore")
    second_part = text_bytes[-split_index_second:].decode("utf-8", errors="ignore")

    return f"{first_part}......{second_part}"


def ensure_path(path: Union[str, Path]) -> Path:
    """确保路径是一个Path对象 (Ensure the path is a Path object)"""
    return Path(path) if isinstance(path, str) else path


def get_cookie_from_browser(browser_choice: str, domain: str = "") -> dict:
    """
    根据用户选择的浏览器获取domain的cookie。

    Args:
        browser_choice (str): 用户选择的浏览器名称

    Returns:
        str: *.domain的cookie值
    """

    if not browser_choice or not domain:
        return ""

    BROWSER_FUNCTIONS = {
        "chrome": browser_cookie3.chrome,
        "firefox": browser_cookie3.firefox,
        "edge": browser_cookie3.edge,
        "opera": browser_cookie3.opera,
        "opera_gx": browser_cookie3.opera_gx,
        "safari": browser_cookie3.safari,
        "chromium": browser_cookie3.chromium,
        "brave": browser_cookie3.brave,
        "vivaldi": browser_cookie3.vivaldi,
        "librewolf": browser_cookie3.librewolf,
    }
    cj_function = BROWSER_FUNCTIONS.get(browser_choice)
    cj = cj_function(domain_name=domain)
    cookie_value = {c.name: c.value for c in cj if c.domain.endswith(domain)}
    return cookie_value


def check_invalid_naming(
    naming: str, allowed_patterns: list, allowed_separators: list
) -> list:
    """
    检查命名是否符合命名模板 (Check if the naming conforms to the naming template)

    Args:
        naming (str): 命名字符串 (Naming string)
        allowed_patterns (list): 允许的模式列表 (List of allowed patterns)
        allowed_separators (list): 允许的分隔符列表 (List of allowed separators)
    Returns:
        list: 无效的模式列表 (List of invalid patterns)
    """
    if not naming or not allowed_patterns or not allowed_separators:
        return []

    temp_naming = naming
    invalid_patterns = []

    # 检查提供的模式是否有效
    for pattern in allowed_patterns:
        if pattern in temp_naming:
            temp_naming = temp_naming.replace(pattern, "")

    # 此时，temp_naming应只包含分隔符
    for char in temp_naming:
        if char not in allowed_separators:
            invalid_patterns.append(char)

    # 检查连续的无效模式或分隔符
    for pattern in allowed_patterns:
        # 检查像"{xxx}{xxx}"这样的模式
        if pattern + pattern in naming:
            invalid_patterns.append(pattern + pattern)
        for sep in allowed_patterns:
            # 检查像"{xxx}-{xxx}"这样的模式
            if pattern + sep + pattern in naming:
                invalid_patterns.append(pattern + sep + pattern)

    return invalid_patterns


# ---- 作者侧车文件 (Author sidecar files) ----

# 通用字段词表。各应用在自己的 utils.py 中把这些名字映射到平台字段。
# (Canonical vocabulary. Each app maps these names onto its own fields.)
SIDECAR_CANONICAL_FIELDS = [
    "nickname",
    "nickname_raw",
    "author_id",
    "author_handle",
    "work_id",
    "work_type",
    "create_time",
    "desc",
    "author_url",
    "work_url",
    "seen_at",
]

# `authors_naming` 未配置时使用的默认模板
# (Default template when `authors_naming` is not configured)
SIDECAR_DEFAULT_NAMING = "Authors-{nickname}"

# `authors_fields` 未配置时使用的默认字段
# (Default field list when `authors_fields` is not configured)
SIDECAR_DEFAULT_FIELDS = [
    "nickname",
    "nickname_raw",
    "author_id",
    "author_handle",
    "work_id",
    "create_time",
    "author_url",
    "work_url",
    "seen_at",
]

# 侧车文件名中单个字段的字节上限。
# 目录名本身最长约 220 字节，而单个路径组件上限为 255 字节，
# 因此这里保守取 80，兼顾可读性与 SMB 兼容性。
# (Per-field byte cap for the sidecar filename.)
SIDECAR_NAME_LIMIT = {"win32": 80, "cygwin": 80, "darwin": 80, "linux": 80}

# 文件名中允许出现的字面量字符 (Literal characters allowed in the filename)
_SIDECAR_ILLEGAL_LITERAL_RE = re.compile(r"[^一-龥a-zA-Z0-9#\-_. ]")
_SIDECAR_PLACEHOLDER_RE = re.compile(r"\{([^{}]*)\}")


def inline_text(value: Any) -> str:
    """
    把任意值压成单行安全文本 (Flatten any value into safe single-line text)

    换行与制表符会破坏侧车文件的 `key: value` 结构，这里统一折叠成单个空格。
    (Newlines and tabs would break the sidecar's `key: value` structure.)

    Args:
        value (Any): 任意值 (Any value)

    Returns:
        str: 单行文本 (Single-line text)
    """

    if value is None:
        return ""

    return re.sub(r"\s+", " ", str(value)).strip()


def check_invalid_sidecar_naming(naming: str, allowed_fields: list) -> list:
    """
    检查侧车文件名模板是否合法 (Check if the sidecar naming template is valid)

    与 `check_invalid_naming` 不同，这里允许字面量文本（如 `Authors-`），
    因此不能复用那个函数：它会把 `Authors` 逐字符判为非法。
    (Unlike `check_invalid_naming`, literal text such as `Authors-` is allowed here,
    which is why that function cannot be reused.)

    Args:
        naming (str): 命名模板 (Naming template)
        allowed_fields (list): 允许的字段名列表 (List of allowed field names)

    Returns:
        list: 无效的模式列表 (List of invalid patterns)
    """

    if not naming:
        return []

    invalid_patterns = []

    # 占位符必须属于通用词表 (Placeholders must belong to the canonical vocabulary)
    for field in _SIDECAR_PLACEHOLDER_RE.findall(naming):
        if field not in allowed_fields:
            invalid_patterns.append("{" + field + "}")

    # 去掉占位符后剩下的字面量必须是文件名安全字符
    # (Literal text left after stripping placeholders must be filename-safe)
    literal = _SIDECAR_PLACEHOLDER_RE.sub("", naming)
    invalid_patterns.extend(sorted(set(_SIDECAR_ILLEGAL_LITERAL_RE.findall(literal))))

    # 目录穿越与隐藏文件 (Path traversal and hidden files)
    if ".." in naming or naming.startswith("."):
        invalid_patterns.append(naming)

    return invalid_patterns


def resolve_sidecar_fields(
    data: dict,
    field_map: dict,
    url_templates: dict,
    fields: list,
) -> list:
    """
    把通用字段名解析为 (字段名, 值) 列表 (Resolve canonical names to (name, value) pairs)

    某应用不存在的字段、或取值为空的字段，都会被跳过而不是写成空行。
    (Fields an app does not have, or that resolve to empty, are skipped rather than
    written as empty lines.)

    Args:
        data (dict): 作品数据字典 (Work data dict)
        field_map (dict): 通用字段名 -> 平台字段名 (Canonical name -> platform field)
        url_templates (dict): 通用字段名 -> URL 模板 (Canonical name -> URL template)
        fields (list): 需要输出的通用字段名 (Canonical names to emit)

    Returns:
        list: (字段名, 值) 元组列表 (List of (name, value) tuples)
    """

    # 先解析出全部可用的基础字段，URL 模板需要引用它们
    # (Resolve every available base field first; URL templates reference them)
    resolved = {}
    for canonical, platform_field in field_map.items():
        value = inline_text(data.get(platform_field))
        if value:
            resolved[canonical] = value

    pairs = []
    for canonical in fields:
        if canonical == "seen_at":
            pairs.append((canonical, timestamp_2_str(get_timestamp("sec"))))
            continue

        if canonical in url_templates:
            template = url_templates[canonical]
            required = _SIDECAR_PLACEHOLDER_RE.findall(template)
            if any(name not in resolved for name in required):
                logger.debug(
                    _("侧车字段 {0} 缺少依赖字段，已跳过").format(canonical)
                )
                continue
            pairs.append((canonical, template.format(**resolved)))
            continue

        if canonical not in resolved:
            logger.debug(_("侧车字段 {0} 不可用，已跳过").format(canonical))
            continue

        pairs.append((canonical, resolved[canonical]))

    return pairs


def format_sidecar_name(
    naming_template: str,
    data: dict,
    field_map: dict,
    fallback_fields: list = None,
) -> str:
    """
    生成侧车文件名（不含后缀）(Format the sidecar file name, without suffix)

    昵称可能为空、为 None，或经 `replaceT` 后只剩下划线（纯 emoji / 纯符号昵称），
    这些情况下逐级回退到备用字段，最后回退到 "unknown"。
    (A nickname may be empty, None, or reduce to underscores after `replaceT`;
    fall back through the alternatives, then to "unknown".)

    Args:
        naming_template (str): 命名模板 (Naming template)
        data (dict): 作品数据字典 (Work data dict)
        field_map (dict): 通用字段名 -> 平台字段名 (Canonical name -> platform field)
        fallback_fields (list, optional): 回退字段顺序 (Fallback order)

    Returns:
        str: 文件名 (File name)
    """

    fallback_fields = fallback_fields or ["author_id", "work_id"]

    def _value(canonical: str) -> str:
        platform_field = field_map.get(canonical)
        if platform_field is None:
            return ""
        value = inline_text(data.get(platform_field))
        # replaceT 会把 emoji 等字符全部替换成下划线，此时视为无效
        # (replaceT turns emoji into underscores; treat that as empty)
        return "" if not value.strip("_") else value

    fields = {}
    for canonical in _SIDECAR_PLACEHOLDER_RE.findall(naming_template):
        # 配置文件中的模板不会经过 click 回调校验，因此这里必须再查一次，
        # 否则一个拼写错误会静默地把每个目录都命名成同一个回退值。
        # (A template set in the config file never passes through the click callback,
        # so re-check here: a typo would otherwise silently name every folder the same.)
        if canonical not in SIDECAR_CANONICAL_FIELDS:
            raise KeyError(_("文件名模板字段 {0} 不存在，请检查").format(canonical))

        value = _value(canonical)

        if not value:
            for fallback in fallback_fields:
                value = _value(fallback)
                if value:
                    break

        fields[canonical] = split_filename(value or "unknown", SIDECAR_NAME_LIMIT)

    try:
        return naming_template.format(**fields)
    except KeyError as e:
        raise KeyError(_("文件名模板字段 {0} 不存在，请检查").format(e))


def format_sidecar_content(pairs: list) -> str:
    """
    生成侧车文件内容 (Format the sidecar file content)

    Args:
        pairs (list): (字段名, 值) 元组列表 (List of (name, value) tuples)

    Returns:
        str: 文件内容 (File content)
    """

    return "".join(f"{name}: {value}\n" for name, value in pairs)


def merge_config(
    main_conf: dict,
    custom_conf: dict,
    **kwargs,
):
    """
    合并配置参数，使 CLI 参数优先级高于自定义配置，自定义配置优先级高于主配置，最终生成完整配置参数字典。

    Args:
        main_conf (dict): 主配置参数字典
        custom_conf (dict): 自定义配置参数字典
        **kwargs: CLI 参数和其他额外的配置参数

    Returns:
        dict: 合并后的配置参数字典

    Raises:
        ValueError: 当主配置或自定义配置为空时抛出错误。
    """

    if not main_conf:
        raise ValueError("主配置参数不能为空，请检查配置文件是否正确加载")

    if not custom_conf:
        raise ValueError("自定义配置参数不能为空或空字典，请提供有效的自定义配置")

    # 合并主配置和自定义配置
    merged_conf = {}
    for key, value in main_conf.items():
        merged_conf[key] = value  # 将主配置复制到合并后的配置中

    for key, value in custom_conf.items():
        if value not in [None, ""]:  # 只有值不为 None 和 空字符串，才进行合并
            merged_conf[key] = value  # 自定义配置参数会覆盖主配置中的同名参数

    # 合并 CLI 参数与合并后的配置，确保 CLI 参数的优先级最高
    for key, value in kwargs.items():
        if value not in [None, ""]:  # 如果值不为 None 和 空字符串，则进行合并
            merged_conf[key] = value  # CLI 参数会覆盖自定义配置和主配置中的同名参数

    return merged_conf


def unescape_json(json_text: str) -> dict:
    """
    反转义 JSON 文本

    Args:
        json_text (str): 带有转义字符的 JSON 文本

    Returns:
        json_obj (dict): 反转义后的 JSON 对象
    """

    # 反转义 JSON 文本
    json_text = re.sub(r"\\{2}", r"\\", json_text)
    json_text = re.sub(r"\\\"", r"\"", json_text)
    json_text = re.sub(r"\\", r"", json_text)
    json_text = re.sub(r"\"{", r"{", json_text)
    json_text = re.sub(r"}\"", r"}", json_text)
    json_text = re.sub(r"\&", r"&", json_text)
    json_text = re.sub(r"\\n", r"", json_text)
    json_text = re.sub(r"\\t", r"", json_text)
    json_text = re.sub(r"\\r", r"", json_text)

    try:
        # 尝试解析 JSON 文本
        import json

        json_obj = json.loads(json_text)
    except Exception as e:
        print(f"`unescape_json` error: {e}, raw_json: {json_text}")
        json_obj = {}

    return json_obj


def check_python_version(min_version: tuple = (3, 10)) -> None:
    """
    检查当前 Python 版本是否满足最低要求

    Args:
        min_version (tuple, optional): 最低 Python 版本要求，默认为 (3, 10)

    Raises:
        SystemExit: 当 Python 版本不满足最低要求时，退出程序
    """

    console = Console()
    if sys.version_info < min_version:
        message = _("当前 Python 版本：{0} 不满足最低要求：{1}").format(
            sys.version.split()[0], ".".join(map(str, min_version))
        )
        panel = Panel(
            f"[bold red]{message}[/bold red]",
            title=_("[bold red]Python 版本错误[/bold red]"),
            border_style="red",
        )
        console.print(panel)
        sys.exit(1)


async def check_f2_version():
    """用于检查F2的版本是否最新"""

    latest_version = await get_latest_version("f2")

    if latest_version:
        if f2.__version__ < latest_version:
            message = _(
                "您当前使用的版本 {0} 可能已过时，请考虑及时升级到最新版本 {1}，"
                "使用 pip install -U f2 更新"
            ).format(f2.__version__, latest_version)
            Console().print(
                Panel(
                    message,
                    title=_("F2 低版本警告"),
                    subtitle=_("请及时更新"),
                    style="bold red",
                    border_style="red",
                )
            )
        elif f2.__version__ >= latest_version:
            message = _("您当前使用的是最新版本：{0}").format(f2.__version__)
            Console().print(
                Panel(
                    message,
                    title=_("F2 版本检查"),
                    style="bold green",
                    border_style="green",
                )
            )
    else:
        message = _("无法获取最新版本信息")
        Console().print(
            Panel(
                message,
                title=_("F2 版本检查网络超时"),
                style="bold yellow",
                border_style="yellow",
            )
        )


async def get_latest_version(package_name: str) -> str:
    """
    获取 Python 包的最新版本号

    Args:
        package_name (str): Python 包名

    Returns:
        str: Python 包的最新版本号
    """
    async with httpx.AsyncClient(
        timeout=5.0,
        transport=httpx.AsyncHTTPTransport(retries=5),
        verify=False,
    ) as aclient:
        try:
            response = await aclient.get(f"{f2.PYPI_URL}/{package_name}/json")
            response.raise_for_status()
            package_data = response.json()
            latest_version = package_data["info"]["version"]
            return latest_version
        except asyncio.CancelledError:
            logger.warning(_("取消检查更新"))
        except (httpx.HTTPStatusError, httpx.RequestError, KeyError) as e:
            logger.debug(traceback.format_exc())
            return None


class BaseEndpointManager:
    @classmethod
    def model_2_endpoint(cls, base_endpoint: str, params: dict) -> str:
        param_str = "&".join([f"{k}={v}" for k, v in params.items()])
        separator = "&" if "?" in base_endpoint else "?"
        return f"{base_endpoint}{separator}{param_str}"


async def filter_by_date_interval(
    data: Union[List[Dict], Dict],
    interval: str,
    fied_name: str = "create_time",
) -> Union[List[Dict], Dict, None]:
    """
    筛选指定日期区间内的作品

    Args:
        data (Union[List[Dict], Dict]): 作品列表或单个作品
        interval (str): 日期区间，格式：2022-01-01|2023-01-01

    Returns:
        filtered_data (Union[List[Dict], Dict, None]): 筛选后的作品列表或单个作品
    """

    def is_within_interval(item: Dict) -> bool:
        date_str = item.get(fied_name)
        if not date_str:
            logger.warning(_("作品缺少创建时间：{0}").format(item))
            return False
        try:
            date = datetime.datetime.strptime(date_str, "%Y-%m-%d %H-%M-%S")
        except ValueError:
            logger.warning(_("无法解析作品的创建时间：{0}").format(date_str))
            return False

        if date < start_date or date > end_date:
            return False

        return True

    if not data or not interval:
        logger.error(_("作品或日期区间为空"))
        return None

    try:
        start_str, end_str = interval.split("|")
        start_date = datetime.datetime.strptime(start_str, "%Y-%m-%d")
        end_date = datetime.datetime.strptime(end_str, "%Y-%m-%d") + datetime.timedelta(
            days=1, seconds=-1
        )

        if end_date < start_date:
            logger.error(_("结束日期早于开始日期，请检查日期区间"))
            return None

        # logger.info(_("筛选日期区间：{0} 至 {1}").format(start_date, end_date))
    except ValueError:
        logger.error(_("日期区间参数格式错误，请查阅文档后重试"))
        return None

    if isinstance(data, dict):
        if is_within_interval(data):
            return data
        else:
            logger.warning(
                _("作品创作时间不在筛选日期区间内：{0}").format(data.get("create_time"))
            )
            return None

    elif isinstance(data, list):
        filtered_list = [item for item in data if is_within_interval(item)]
        if filtered_list:
            logger.info(
                _("在 {0} 条作品中有 {1} 条作品符合筛选日期条件：{2}").format(
                    len(data), len(filtered_list), interval
                )
            )
        else:
            logger.warning(_("没有找到符合条件的作品"))
        return filtered_list


def check_proxy_avail(
    http_proxy: str,
    https_proxy: str,
    test_url: str = "https://www.google.com",
    expected_content: str = None,
    timeout: int = 5,
    method: str = "GET",
    **kwargs,
) -> bool:
    """
    检查 HTTP 和 HTTPS 代理是否可用

    Args:
        http_proxy (str): HTTP 代理地址 (例如 "http://proxy_ip:proxy_port")
        https_proxy (str): HTTPS 代理地址 (例如 "http://proxy_ip:proxy_port")
        test_url (str): 测试地址，默认 https://www.google.com
        expected_content (str): 预期的内容关键字，用于验证页面加载正确
        timeout (int): 请求超时时间，默认 5 秒
        method (str): 请求方法，如 "GET", "POST", "PUT", "DELETE", "OPTIONS"
        **kwargs: 其他请求参数，如 data, json, headers 等

    Returns:
        bool: 如果代理可用返回 True，否则返回 False
    """

    if not http_proxy or not https_proxy:
        logger.error(_("代理地址为空"))
        return False

    proxy_mounts = {
        "http://": httpx.HTTPTransport(proxy=http_proxy),
        "https://": httpx.HTTPTransport(proxy=https_proxy),
    }

    try:
        logger.info(_("正在测试代理服务器是否可用🚀"))
        # 创建 HTTP 和 HTTPS 的代理挂载
        with httpx.Client(timeout=timeout, mounts=proxy_mounts) as client:
            # 根据方法选择请求
            response = client.request(
                method.upper(),
                test_url,
                follow_redirects=True,
                **kwargs,
            )
            response.raise_for_status()

            # 验证响应内容是否包含预期关键字
            if expected_content and expected_content not in response.text:
                logger.warning(_("代理请求成功，但内容不符合预期"))
                return False

            logger.info("[green]代理请求成功，测试地址：{0}[/green]".format(test_url))
            return True

    except httpx.ProxyError as e:
        logger.error(_("代理错误：{0}").format(e))
    except httpx.TimeoutException as e:
        logger.error(_("代理请求超时，错误: {0}").format(e))
    except httpx.TooManyRedirects as e:
        logger.error(_("重定向次数过多：{0}").format(e))
    except httpx.HTTPStatusError as e:
        logger.error(
            _("代理请求 {0} 状态码错误：{1}").format(test_url, e.response.status_code)
        )
    except httpx.RequestError as e:
        logger.error(_("代理请求错误：{0}").format(e))
    except Exception as e:
        logger.error(_("代理请求失败：{0}").format(e))

    return False


def filter_to_list(
    filter_instance: Any,
    entries_path: str,
    exclude_fields: List[str],
    extra_fields: List[str] = None,
) -> list:
    """
    通用的 `_to_list` 方法实现。

    Args:
        filter_instance (Any): Filter 实例
        entries_path (str): entries 的路径
        exclude_fields (List[str]): 排除的字段列表
        extra_fields (List[str], optional): 额外的字段列表

    Returns:
        list: entries 列表
    """

    # 生成属性名称列表，然后过滤掉排除的属性
    keys = [
        prop_name
        for prop_name in dir(filter_instance)
        if not prop_name.startswith("__")
        and not prop_name.startswith("_")
        and prop_name not in exclude_fields
    ]

    entries = filter_instance._get_attr_value(entries_path) or []
    list_dicts = []
    # 使用集合避免重复记录相同的错误
    errors = set()
    extra_fields = extra_fields or {}

    # 遍历每个条目并创建一个字典
    for entry in entries:
        d = {key: getattr(filter_instance, key, None) for key in extra_fields}
        for key in keys:
            try:
                attr_values = getattr(filter_instance, key)
                # 当前entry在属性列表中的索引
                index = entries.index(entry)
                # 如果属性值的长度足够则赋值，否则赋None
                d[key] = attr_values[index] if index < len(attr_values) else None
            except TypeError as e:
                # 如果字段已出错，跳过重复记录
                error_message = _("字段 {0} 出错: {1}").format(key, str(e))
                if error_message not in errors:
                    errors.add(error_message)
                d[key] = None
            except Exception as e:
                # 捕获其他未预料的异常
                error_message = _("字段 {0} 出现未预料的错误: {1}").format(key, str(e))
                if error_message not in errors:
                    errors.add(error_message)
                d[key] = None

        list_dicts.append(d)

    # 如果有错误，统一抛出异常
    if errors:
        raise APIFilterError(_("由于接口更新，部分字段处理失败:\n") + "\n".join(errors))

    return list_dicts


class AESEncryptionUtils:
    # 支持的加密算法和密钥长度
    SUPPORTED_ALGORITHMS = {
        "AES128": 16,
        "AES192": 24,
        "AES256": 32,
    }

    SUPPORTED_MODES = ["GCM", "CBC", "ECB"]

    def __init__(
        self,
        key: bytes,
        algorithm: str = "AES256",
        mode: str = "GCM",
        padding_scheme: str = "pkcs7",
        iv: Optional[bytes] = None,
    ):
        """
        初始化AES加密工具类实例

        Args:
            key (bytes): 密钥
            algorithm (str, optional): 加密算法
            mode (str, optional): 加密模式 ('GCM', 'CBC', 'ECB')
            padding_scheme (str, optional): 填充方案 ('pkcs7')
            iv (Optional[bytes], optional): IV (初始化向量)

        Raises:
            ValueError: 当算法或模式不可用时抛出错误

        Returns:
            EncryptionUtils: 加密工具类实例
        """
        # 检查算法是否支持
        if algorithm not in self.SUPPORTED_ALGORITHMS:
            raise ValueError(_("算法必须为 'AES128', 'AES192' 或 'AES256'。"))

        # 检查模式是否支持
        if mode not in self.SUPPORTED_MODES:
            raise ValueError(_("模式必须为 'GCM', 'CBC' 或 'ECB'。"))

        self.key = key
        self.algorithm = algorithm
        self.mode = mode
        self.padding_scheme = padding_scheme
        self.iv = iv

        # 检查密钥长度是否正确
        expected_key_length = self.SUPPORTED_ALGORITHMS[algorithm]
        if len(self.key) != expected_key_length:
            raise ValueError(
                _("{0} 算法密钥长度不正确：{1} 字节，期望长度为 {2} 字节。").format(
                    algorithm, len(self.key), expected_key_length
                )
            )

    def aes_encrypt(self, plaintext: bytes) -> bytes:
        """
        AES 加密

        Args:
            plaintext (bytes): 明文数据

        Returns:
            bytes: 密文数据
        """
        if self.mode == "GCM":
            return self._aes_encrypt_gcm(plaintext)
        elif self.mode == "CBC":
            return self._aes_encrypt_cbc(plaintext)
        elif self.mode == "ECB":
            return self._aes_encrypt_ecb(plaintext)

    def aes_decrypt(self, ciphertext: bytes, iv: Optional[bytes] = None) -> bytes:
        """
        AES 解密

        Args:
            ciphertext (bytes): 密文数据

        Returns:
            bytes: 明文数据
        """
        if self.mode == "GCM":
            return self._aes_decrypt_gcm(ciphertext)
        elif self.mode == "CBC":
            return self._aes_decrypt_cbc(ciphertext, iv)
        elif self.mode == "ECB":
            return self._aes_decrypt_ecb(ciphertext)

    def _aes_encrypt_gcm(self, plaintext: bytes, nonce: bytes = None) -> bytes:
        """GCM模式加密"""
        if nonce is None:
            nonce = self.iv or secrets.token_bytes(12)
        # 为了安全，GCM每次加密都应该生成一个新的随机 12位 nonce
        # 但 Bark 应用不支持随机 nonce 的解密
        # 所以其他开发者在GCM模式的下不需要传入 iv 参数，就会使用随机 nonce
        cipher = Cipher(
            algorithms.AES(self.key), modes.GCM(nonce), backend=default_backend()
        )
        encryptor = cipher.encryptor()

        ciphertext = encryptor.update(plaintext) + encryptor.finalize()
        return nonce + encryptor.tag + ciphertext  # 返回 nonce、tag 和密文

    def _aes_decrypt_gcm(self, ciphertext: bytes) -> bytes:
        """GCM模式解密"""
        nonce = ciphertext[:12]  # 获取 nonce（12 字节）
        tag = ciphertext[12:28]  # 获取认证标签（16 字节）
        ciphertext_data = ciphertext[28:]  # 获取密文

        try:
            cipher = Cipher(
                algorithms.AES(self.key),
                modes.GCM(nonce, tag),
                backend=default_backend(),
            )
            decryptor = cipher.decryptor()
            return decryptor.update(ciphertext_data) + decryptor.finalize()
        except InvalidTag:
            raise ValueError(_("GCM 模式解密失败：认证标签无效"))

    def _aes_encrypt_cbc(self, plaintext: bytes) -> bytes:
        """CBC模式加密"""
        # 使用 PKCS7 填充
        padder = aes_padding.PKCS7(128).padder()
        padded_data = padder.update(plaintext) + padder.finalize()

        cipher = Cipher(
            algorithms.AES(self.key), modes.CBC(self.iv), backend=default_backend()
        )
        encryptor = cipher.encryptor()

        ciphertext = encryptor.update(padded_data) + encryptor.finalize()
        return ciphertext  # 返回密文

    def _aes_decrypt_cbc(self, ciphertext: bytes, iv: bytes) -> bytes:
        """CBC模式解密"""
        cipher = Cipher(
            algorithms.AES(self.key), modes.CBC(iv), backend=default_backend()
        )
        decryptor = cipher.decryptor()

        padded_plaintext = decryptor.update(ciphertext) + decryptor.finalize()

        # 去除填充
        unpadder = aes_padding.PKCS7(128).unpadder()
        return unpadder.update(padded_plaintext) + unpadder.finalize()

    def _aes_encrypt_ecb(self, plaintext: bytes) -> bytes:
        """ECB模式加密"""
        # 使用 PKCS7 填充
        padder = aes_padding.PKCS7(128).padder()
        padded_data = padder.update(plaintext) + padder.finalize()

        cipher = Cipher(
            algorithms.AES(self.key), modes.ECB(), backend=default_backend()
        )
        encryptor = cipher.encryptor()

        return encryptor.update(padded_data) + encryptor.finalize()

    def _aes_decrypt_ecb(self, ciphertext: bytes) -> bytes:
        """ECB模式解密"""
        cipher = Cipher(
            algorithms.AES(self.key), modes.ECB(), backend=default_backend()
        )
        decryptor = cipher.decryptor()

        padded_plaintext = decryptor.update(ciphertext) + decryptor.finalize()

        # 去除填充
        unpadder = aes_padding.PKCS7(128).unpadder()
        return unpadder.update(padded_plaintext) + unpadder.finalize()


class RSAEncryptionUtils:

    SUPPORTED_ALGORITHMS = [
        "RSA512",
        "RSA1024",
        "RSA2048",
        "RSA4096",
    ]

    SUPPORTED_PADDING_SCHEMES = [
        "pkcs1",
        "oaep",  # 更安全
    ]

    def __init__(
        self,
        private_key: rsa.RSAPrivateKey,
        public_key: rsa.RSAPublicKey,
        algorithm: str = "RSA2048",
        padding_scheme: str = "pkcs1",
    ):
        """
        初始化RSA加密工具类实例

        Args:
            private_key (RSAPrivateKey): 私钥
            public_key (RSAPublicKey): 公钥
            algorithm (str, optional): 加密算法 (RSA1024, RSA2048, RSA4096)
            padding_scheme (str, optional): 填充方案 ('pkcs1' 或 'oaep')

        Raises:
            ValueError: 当算法不可用或密钥长度不正确时抛出错误

        Returns:
            RSAEncryptionUtils: 加密工具类实例
        """
        if algorithm not in self.SUPPORTED_ALGORITHMS:
            raise ValueError(_("算法必须为 'RSA1024', 'RSA2048' 或 'RSA4096'。"))

        if padding_scheme not in self.SUPPORTED_PADDING_SCHEMES:
            raise ValueError(_("填充方案必须为 'pkcs1' 或 'oaep'。"))

        # 设置私钥和公钥
        self.private_key = private_key
        self.public_key = public_key
        self.padding_scheme = padding_scheme

        # 检查密钥长度是否正确
        expected_key_length = int(algorithm[3:])
        if private_key.key_size != expected_key_length:
            raise ValueError(
                _("{0} 算法私钥长度不正确：{1} 位，期望长度为 {2} 位。").format(
                    algorithm, private_key.key_size, expected_key_length
                )
            )

    def rsa_encrypt(self, plaintext: bytes) -> bytes:
        """
        RSA 加密（使用公钥加密）

        Args:
            plaintext (bytes): 明文数据

        Returns:
            bytes: 密文数据
        """
        if self.padding_scheme == "pkcs1":
            padding_scheme = rsa_padding.PKCS1v15()
        elif self.padding_scheme == "oaep":
            padding_scheme = rsa_padding.OAEP(
                mgf=rsa_padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            )

        ciphertext = self.public_key.encrypt(plaintext, padding_scheme)
        return ciphertext

    def rsa_decrypt(self, ciphertext: bytes) -> bytes:
        """
        RSA 解密（使用私钥解密）

        Args:
            ciphertext (bytes): 密文数据

        Returns:
            bytes: 明文数据
        """

        if self.padding_scheme == "pkcs1":
            padding_scheme = rsa_padding.PKCS1v15()
        elif self.padding_scheme == "oaep":
            padding_scheme = rsa_padding.OAEP(
                mgf=rsa_padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            )

        plaintext = self.private_key.decrypt(ciphertext, padding_scheme)
        return plaintext
