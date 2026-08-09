# path: tests/test_author_sidecar.py

import pytest

from f2.utils.utils import (
    check_invalid_sidecar_naming,
    format_sidecar_content,
    format_sidecar_name,
    inline_text,
    resolve_sidecar_fields,
    SIDECAR_CANONICAL_FIELDS,
    SIDECAR_DEFAULT_FIELDS,
    SIDECAR_DEFAULT_NAMING,
)

# 抖音映射，其余应用在 test_app_field_maps 中单独校验
DOUYIN_MAP = {
    "nickname": "nickname",
    "nickname_raw": "nickname_raw",
    "author_id": "uid",
    "author_handle": "sec_user_id",
    "work_id": "aweme_id",
    "work_type": "aweme_type",
    "create_time": "create_time",
    "desc": "desc",
}
DOUYIN_URLS = {
    "author_url": "https://www.douyin.com/user/{author_handle}",
    "work_url": "https://www.douyin.com/video/{work_id}",
}


def _content_to_dict(content: str) -> dict:
    return dict(
        line.split(": ", 1) if ": " in line else (line.rstrip(":"), "")
        for line in content.splitlines()
    )


# ===== inline_text =====


@pytest.mark.parametrize(
    "value, expected",
    [
        (None, ""),
        ("", ""),
        ("  spaced  ", "spaced"),
        ("line1\nline2", "line1 line2"),
        ("tab\tsep", "tab sep"),
        ("multi   space", "multi space"),
        (0, "0"),
        (68, "68"),
    ],
)
def test_inline_text(value, expected):
    """任意值都要压成安全的单行文本"""
    assert inline_text(value) == expected


# ===== check_invalid_sidecar_naming =====


@pytest.mark.parametrize(
    "naming",
    [
        SIDECAR_DEFAULT_NAMING,
        "Authors-{nickname}",
        "Authors-{nickname}_{author_id}",
        "作者-{nickname}",
        "Author",  # 无占位符，所有目录使用同一文件名
        "{nickname}",
    ],
)
def test_valid_sidecar_naming(naming):
    """合法模板必须通过，字面量文本是允许的"""
    assert check_invalid_sidecar_naming(naming, SIDECAR_CANONICAL_FIELDS) == []


@pytest.mark.parametrize(
    "naming",
    [
        "{bogus}",  # 不在通用词表中
        "{desc}{nope}",
        "a/b",  # 路径分隔符
        "a\\b",
        "../x",  # 目录穿越
        ".hidden",  # 隐藏文件
        "A:B",  # SMB 保留字符
    ],
)
def test_invalid_sidecar_naming(naming):
    """非法模板必须被拒绝"""
    assert check_invalid_sidecar_naming(naming, SIDECAR_CANONICAL_FIELDS) != []


def test_sidecar_naming_rejects_what_check_invalid_naming_cannot_accept():
    """
    回归测试：`check_invalid_naming` 会把 `Authors-` 逐字符判为非法，
    所以侧车文件名不能复用那个校验函数。
    """
    from f2.utils.utils import check_invalid_naming

    assert check_invalid_naming("Authors-{nickname}", ["{nickname}"], ["-", "_"]) != []
    assert check_invalid_sidecar_naming("Authors-{nickname}", ["nickname"]) == []


# ===== format_sidecar_name =====


def test_name_normal():
    data = {"nickname": "震动哥", "uid": "603", "aweme_id": "712"}
    assert format_sidecar_name(SIDECAR_DEFAULT_NAMING, data, DOUYIN_MAP) == (
        "Authors-震动哥"
    )


@pytest.mark.parametrize(
    "nickname",
    [None, "", "___"],  # 空、None、以及 replaceT 后只剩下划线的纯 emoji 昵称
)
def test_name_falls_back_to_author_id(nickname):
    """昵称不可用时回退到 author_id，而不是产出 `Authors-.txt`"""
    data = {"nickname": nickname, "uid": "603", "aweme_id": "712"}
    assert format_sidecar_name(SIDECAR_DEFAULT_NAMING, data, DOUYIN_MAP) == "Authors-603"


def test_name_falls_back_to_work_id():
    """昵称和 author_id 都不可用时回退到 work_id"""
    data = {"nickname": "", "uid": "", "aweme_id": "712"}
    assert format_sidecar_name(SIDECAR_DEFAULT_NAMING, data, DOUYIN_MAP) == "Authors-712"


def test_name_falls_back_to_unknown():
    """所有回退字段都不可用时使用 unknown"""
    assert (
        format_sidecar_name(SIDECAR_DEFAULT_NAMING, {}, DOUYIN_MAP) == "Authors-unknown"
    )


def test_name_is_byte_capped():
    """超长昵称必须截断，避免超过单个路径组件 255 字节的上限"""
    data = {"nickname": "很长的昵称" * 40, "uid": "603"}
    name = format_sidecar_name(SIDECAR_DEFAULT_NAMING, data, DOUYIN_MAP)
    assert len(name.encode("utf-8")) <= 100
    assert "......" in name


def test_name_flattens_newlines():
    data = {"nickname": "line1\nline2", "uid": "603"}
    assert "\n" not in format_sidecar_name(SIDECAR_DEFAULT_NAMING, data, DOUYIN_MAP)


def test_name_unknown_placeholder_raises():
    with pytest.raises(KeyError):
        format_sidecar_name("Authors-{nope}", {"nickname": "a"}, DOUYIN_MAP)


# ===== resolve_sidecar_fields / format_sidecar_content =====


def test_content_full():
    data = {
        "nickname": "震动哥",
        "nickname_raw": "震动哥🌟",
        "uid": "60312345678",
        "sec_user_id": "MS4wLjAB",
        "aweme_id": "7123456789",
        "create_time": "2024-04-02 06-23-54",
    }
    parsed = _content_to_dict(
        format_sidecar_content(
            resolve_sidecar_fields(
                data, DOUYIN_MAP, DOUYIN_URLS, SIDECAR_DEFAULT_FIELDS
            )
        )
    )
    assert parsed["nickname"] == "震动哥"
    assert parsed["nickname_raw"] == "震动哥🌟"
    assert parsed["author_id"] == "60312345678"
    assert parsed["work_id"] == "7123456789"
    assert parsed["author_url"] == "https://www.douyin.com/user/MS4wLjAB"
    assert parsed["work_url"] == "https://www.douyin.com/video/7123456789"
    assert parsed["seen_at"]  # 由运行时生成


def test_content_omits_unavailable_fields():
    """应用没有的字段整行省略，而不是写成空值"""
    data = {"nickname": "a", "uid": "603"}
    content = format_sidecar_content(
        resolve_sidecar_fields(data, DOUYIN_MAP, DOUYIN_URLS, SIDECAR_DEFAULT_FIELDS)
    )
    assert "author_handle" not in content  # sec_user_id 缺失
    assert "work_id" not in content  # aweme_id 缺失
    assert "author_url" not in content  # 依赖 author_handle
    assert "nickname: a" in content


def test_content_preserves_field_order():
    data = {"nickname": "a", "uid": "603", "aweme_id": "712"}
    fields = ["work_id", "nickname", "author_id"]
    content = format_sidecar_content(
        resolve_sidecar_fields(data, DOUYIN_MAP, DOUYIN_URLS, fields)
    )
    assert [line.split(":")[0] for line in content.splitlines()] == fields


def test_content_every_line_is_key_value():
    """昵称里的换行不能破坏 key: value 结构"""
    data = {"nickname": "a", "nickname_raw": "line1\nline2", "uid": "603"}
    content = format_sidecar_content(
        resolve_sidecar_fields(data, DOUYIN_MAP, DOUYIN_URLS, SIDECAR_DEFAULT_FIELDS)
    )
    assert all(": " in line for line in content.splitlines())
    assert "nickname_raw: line1 line2" in content


def test_content_keeps_zero_work_type():
    """aweme_type 为 0 是合法值，不能被当作空值丢弃"""
    data = {"aweme_type": 0}
    content = format_sidecar_content(
        resolve_sidecar_fields(data, DOUYIN_MAP, DOUYIN_URLS, ["work_type"])
    )
    assert content == "work_type: 0\n"


# ===== 各应用字段映射 =====


def test_app_field_maps():
    """
    四个应用的映射与 URL 模板都必须只使用通用词表里的名字。

    tiktok 的 utils 在导入时会发起网络请求（`DeviceIdManager` 类体内调用
    `gen_real_msToken`），与本功能无关，因此无法在离线环境导入。
    """
    checked = []
    for app in ("douyin", "twitter", "weibo", "tiktok"):
        try:
            module = __import__(f"f2.apps.{app}.utils", fromlist=["x"])
        except Exception:  # pragma: no cover - 仅 tiktok 在离线环境触发
            continue

        for canonical in module.AUTHOR_FIELD_MAP:
            assert canonical in SIDECAR_CANONICAL_FIELDS, (app, canonical)

        for canonical, template in module.AUTHOR_URL_TEMPLATES.items():
            assert canonical in SIDECAR_CANONICAL_FIELDS, (app, canonical)
            # URL 模板只能引用该应用真实拥有的字段
            for name in ("author_handle", "author_id", "work_id"):
                if "{" + name + "}" in template:
                    assert name in module.AUTHOR_FIELD_MAP, (app, canonical, name)

        checked.append(app)

    assert {"douyin", "twitter", "weibo"} <= set(checked)


def test_weibo_has_no_author_handle():
    """微博没有 author_handle 概念，其 URL 模板不能依赖该字段"""
    from f2.apps.weibo.utils import AUTHOR_FIELD_MAP, AUTHOR_URL_TEMPLATES

    assert "author_handle" not in AUTHOR_FIELD_MAP
    assert all("{author_handle}" not in t for t in AUTHOR_URL_TEMPLATES.values())


def test_douyin_wrappers():
    from f2.apps.douyin.utils import (
        format_author_file_content,
        format_author_file_name,
    )

    data = {"nickname": "震动哥", "uid": "603", "aweme_id": "712"}
    assert format_author_file_name(SIDECAR_DEFAULT_NAMING, data) == "Authors-震动哥"
    # fields 为 None 时使用默认字段表
    assert "work_id: 712" in format_author_file_content(None, data)
