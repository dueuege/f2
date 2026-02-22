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
    # 批量获取用户短信息，支持传入多个 sec_user_id
    sec_user_ids = [
        "MS4wLjABAAAAx4YsdS72GjvN-94-_O40KufZOkgVwaJ6YIp3MlrhHoKmEDk5xZa40fQJKcKR6_Yo",
        "MS4wLjABAAAAT3_ReMP9rvIfYrVW0vlRfcouCjaLqhsWqK2RITHI9NyMCt0mr225s913GCZ9Lefc",
        "MS4wLjABAAAA06feKvUxebSd0s9h3PGXlqt1MiphONtUcHYhhGHQ-tf-vngsnk3RRuycJQwUsHth",
        "MS4wLjABAAAA5QZ_7n-CxZRfUaE4LYlUn--laPZKkLJ2g3tmIkknuEY",
        "MS4wLjABAAAA4XXsSy4Jj5bRD1QGnOi8AfJQlljjNLft_7K8uYA1alU",
        "MS4wLjABAAAAjhim-biEjzknAEEe6m4Yc736Wmrijo4hvtbmccH9_vc",
        "MS4wLjABAAAAjTm64ye8WK64Su3P8XO-gImkLqC8622zFEnxLdgFPVdjnleDurVyLu3VU1O7JvRX",
        "MS4wLjABAAAAW4Ssl2BQWIm4U77TbCIrnH6hhkgc1LdWtypUCqlqMg6BIKshYKq-rBTJKrGaikRr",
        # ... more sec_user_ids
    ]
    user_info = await DouyinHandler(kwargs).fetch_user_short_info(
        sec_user_ids=sec_user_ids
    )
    print("=================_to_raw================")
    print(user_info._to_raw())
    # print("=================_to_dict===============")
    # print(user_info._to_dict())
    # print("=================属性================")
    # print(f"用户昵称: {user_info.nickname}")
    # print(f"用户UID: {user_info.uid}")
    # print(f"用户sec_uid: {user_info.sec_uid}")
    # print(f"用户头像: {user_info.avatar_larger}")
    # print(f"用户签名: {user_info.signature}")
    # print(f"关注状态: {user_info.follow_status}")


if __name__ == "__main__":
    asyncio.run(main())
