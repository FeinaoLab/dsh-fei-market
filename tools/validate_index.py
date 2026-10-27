# -*- coding: utf-8 -*-
"""DSH 插件索引校验器（按官方 plugin-market 文档「索引格式参考」实现）。

规则来源：docs/user/guide/plugin-market.zh.md（deepseek-ai/deepseek-harness @ master）
违反任一条官方即拒绝整个索引——发布前必须全绿。
"""
import io
import json
import re
import sys

NPM_NAME = re.compile(r"^(@[a-z0-9-~][a-z0-9-._~]*/)?[a-z0-9-~][a-z0-9-._~]*$")
SEMVER = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)"
    r"(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$")
SHA40 = re.compile(r"^[0-9a-f]{40}$")

errors = []
warns = []


def err(path, msg):
    errors.append("%s: %s" % (path, msg))


def check_localized(obj, path, required_en=True):
    if isinstance(obj, str):
        return
    if isinstance(obj, dict):
        if required_en and "en" not in obj:
            err(path, "LocalizedText 对象必须包含 en")
        for k in obj:
            if not re.match(r"^[a-z]+(-[a-z]+)*$", k):
                err(path, "非法语言 id：%r" % k)
        return
    err(path, "应为字符串或 LocalizedText 对象")


def main(path):
    idx = json.load(io.open(path, encoding="utf-8"))

    # ---- 顶层 ----
    if idx.get("format") != 1:
        err("format", "必须为 1，实际 %r" % idx.get("format"))
    check_localized(idx.get("title"), "title")
    if "description" in idx:
        check_localized(idx["description"], "description")

    meta = idx.get("metadata") or {}
    cats = meta.get("categories") or {}
    labels = meta.get("labels") or {}
    for cid, c in cats.items():
        if "title" not in c:
            err("metadata.categories.%s" % cid, "缺 title")
        else:
            check_localized(c["title"], "metadata.categories.%s.title" % cid)

    plugins = idx.get("plugins")
    if not isinstance(plugins, list) or not plugins:
        err("plugins", "必须是非空数组")
        plugins = []

    names = set()
    for i, p in enumerate(plugins):
        pp = "plugins[%d]" % i
        name = p.get("name")
        if not name or not NPM_NAME.match(name or ""):
            err(pp + ".name", "不是合法 npm 包名：%r" % name)
            continue
        if name in names:
            err(pp + ".name", "包名在索引内重复：%s" % name)
        names.add(name)

        for f in ("title", "description"):
            if f in p:
                check_localized(p[f], pp + "." + f)
        if "icon" in p:
            icon = p["icon"]
            if icon.startswith("data:"):
                if len(icon) > 32 * 1024:
                    err(pp + ".icon", "内联图标超过 32 KiB")
            elif not (icon.startswith("https://") or icon.startswith("http://") or not re.match(r"^[a-z]+:", icon)):
                err(pp + ".icon", "必须是 data:/https:/http: 或相对路径")
        if "homepage" in p and not re.match(r"^https?://", p["homepage"]):
            err(pp + ".homepage", "必须是绝对 http(s) URL")
        if "repository" in p and not isinstance(p["repository"].get("url"), str):
            err(pp + ".repository.url", "缺 url")

        pm = p.get("metadata") or {}
        if "category" in pm and pm["category"] not in cats:
            err(pp + ".metadata.category", "未声明的分类 id：%r" % pm["category"])
        for lid in pm.get("labels", []):
            if lid not in labels:
                err(pp + ".metadata.labels", "未声明的标签 id：%r" % lid)

        versions = p.get("versions")
        if not isinstance(versions, list) or not versions:
            err(pp + ".versions", "至少一个版本")
            continue
        seen = set()
        for j, v in enumerate(versions):
            vp = "%s.versions[%d]" % (pp, j)
            ver = v.get("version")
            if not ver or not SEMVER.match(ver or ""):
                err(vp + ".version", "不是精确 SemVer：%r" % ver)
            elif ver in seen:
                err(vp + ".version", "版本在插件内重复：%s" % ver)
            seen.add(ver)
            ts = v.get("publishTimestamp")
            if not isinstance(ts, int) or ts < 0:
                err(vp + ".publishTimestamp", "必须是 Unix 秒整数：%r" % ts)
            src = v.get("source") or {}
            st = src.get("type")
            if st == "npm":
                if "registry" in src and not re.match(r"^https?://", src["registry"]):
                    err(vp + ".source.registry", "必须是 http(s) URL")
            elif st == "git":
                if not re.match(r"^https://", src.get("url", "")):
                    err(vp + ".source.url", "git 源必须是 https URL：%r" % src.get("url"))
                if not SHA40.match(src.get("commit", "")):
                    err(vp + ".source.commit", "必须是 40 位十六进制 SHA：%r" % src.get("commit"))
                if "path" in src and not isinstance(src["path"], str):
                    err(vp + ".source.path", "必须是字符串")
            else:
                err(vp + ".source.type", "必须是 npm 或 git，实际 %r" % st)
            if "engines" in v and "dsh" not in (v.get("engines") or {}):
                err(vp + ".engines", "有 engines 时必须含 dsh 范围")

    # ---- 汇总 ----
    print("插件数：%d ｜ 版本总数：%d" % (len(plugins), sum(len(p.get("versions", [])) for p in plugins)))
    for w in warns:
        print("WARN", w)
    if errors:
        print("\n校验失败 %d 条：" % len(errors))
        for e in errors:
            print("  ✗", e)
        return 1
    print("校验通过 ✅（%s 符合官方索引格式）" % path)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "site/index.json"))
