import asyncio

from f2.apps.douyin.handler import DouyinHandler

kwargs = {
    "headers": {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36 Edg/130.0.0.0",
        "Referer": "https://www.douyin.com/",
    },
    "proxies": {"http://": None, "https://": None},
    "cookie": "YOUR_COOKIE_HERE",
}


async def main():
    # 批量获取用户活跃状态，支持传入多个 sec_user_id
    sec_user_ids = [
        "MS4wLjABAAAAuWp7Fd0dRPjT2x6trbjVPv6imZCs_-Yhilt1xZwGH0Uj5ayjnHV4VML6XripmKnX",
        "MS4wLjABAAAAX_MPa-DBztrdwM1MB__Hv7lQYzuGKChhDwgMD8M7xad0DIwrpTpDZH_yGEcHWAjo",
        "MS4wLjABAAAAaTRBEyA6V3zubKzmX6C3svJmVzkYNfQkrvC8Pmw-57U",
        "MS4wLjABAAAAEfbNxdoojQY--uD1sRXxZApWa99hGe7fJUziOmnNvoA",
        "MS4wLjABAAAAVsoxT8Mb0c3xL48tHKoSU8vDjvsjFF5rPAHL2DV2BfG7-BbOe5UVDOOLcVWfXE1C",
        "MS4wLjABAAAA0YfFmWNJahTpHx-bQMz-ZLcqWllatMPv8bb2t0SGfBsE37YxtA6WAGiKZwiig-5F",
        "MS4wLjABAAAAwr3PiIrRdKh5vHpOGmRhb-8woqas1LTfJUZ_XB0Mhhg",
        "MS4wLjABAAAANuskCnX5E3LznF4jeUfS1G8IC_F0-zozAjgR_2PuStgfALc30Mt3TgVDPIRGl8xu",
        # ... more sec_user_ids
    ]
    user_status = await DouyinHandler(kwargs).fetch_user_active_status(
        sec_user_ids=sec_user_ids
    )
    print("=================_to_raw================")
    print(user_status._to_raw())
    # print("=================_to_dict===============")
    # print(user_status._to_dict())
    # print("=================属性================")
    # print(f"用户sec_uid: {user_status.sec_uid}")
    # print(f"活跃状态(1-在线, 0-离线): {user_status.active_status}")
    # print(f"最后活跃时间戳: {user_status.last_active_time}")
    # print(f"最后活跃时间: {user_status.last_active_time_str}")


if __name__ == "__main__":
    asyncio.run(main())
