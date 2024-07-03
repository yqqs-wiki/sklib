import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import TypeGuard
from zipfile import is_zipfile

import httpx
from tqdm import tqdm


def extract_apk_vers(apk_name: str):
    return tuple(apk_name.removesuffix(".apk").split("-")[-1].split("."))


@dataclass
class Apk:
    url: str
    name: str = field(init=False)
    vers: tuple[str, str, str] = field(init=False)

    @staticmethod
    def _check_vers(vers: tuple[str, ...]) -> TypeGuard[tuple[str, str, str]]:
        if len(vers) != 3:
            raise RuntimeError("无法从官网获取下载链接")
        return True

    def __post_init__(self):
        self.name = self.url.split("/")[-1]

        if self._check_vers(vers := extract_apk_vers(self.name)):
            self.vers = vers


class Cache:
    def __init__(self, cache_dir=".cache"):
        cache_path = Path(cache_dir)
        cache_path.mkdir(exist_ok=True)

        paths = list(cache_path.glob("SoulKnight-*.apk"))
        self.apk = self.get_new_apk()
        self.apk_path = cache_path / self.apk.url.split("/")[-1]

        apk_new_vers = self.apk.vers

        if not paths:
            self._download_apk()
        elif not is_zipfile(self.apk_path):
            print("安装包出现问题，正在重新下载")
            self.apk_path.unlink()
            self._download_apk()
        else:
            apk_old_vers = extract_apk_vers(max(path.name for path in paths))
            if tuple(map(int, apk_new_vers)) > tuple(map(int, apk_old_vers)):
                self._download_apk()

        print(f"已下载{'.'.join(apk_new_vers)}版本的元气骑士")

    def _download_apk(self):
        with (
            httpx.stream("get", self.apk.url) as r,
            open(self.apk_path, mode="wb") as f,
        ):
            total = float(r.headers["Content-Length"]) / 1024 / 1024
            with tqdm(
                desc="安装包下载进度",
                unit="MB",
                total=total,
                bar_format="{l_bar}{bar}| {n:.2f}/{total:.2f} [{elapsed}<{remaining},{rate_fmt}{postfix}]",
            ) as progress:
                for chunk in r.iter_raw():
                    f.write(chunk)
                    progress.update(len(chunk) / 1024 / 1024)

    @staticmethod
    def get_new_apk() -> Apk:
        r = httpx.get("https://www.chillyroom.com/zh")
        m = re.search(r"https://apk.chillyroom.com/apks/.*?.apk", r.text)
        if m is None:
            raise RuntimeError("官网找不到新版本")

        return Apk(m.group())
