"""netmask: 子网计算器。

用法：
    python -m netmask 192.168.1.10/24
    python -m netmask 192.168.1.10/24 --contains 192.168.1.200
    python -m netmask 192.168.1.0/24 --split 26
    python -m netmask 2001:db8::/32
"""
import argparse
import ipaddress
import json
import sys


def ip_class_v4(addr):
    first = int(str(addr).split(".")[0])
    if first < 128:
        return "A"
    if first < 192:
        return "B"
    if first < 224:
        return "C"
    if first < 240:
        return "D（组播）"
    return "E（保留）"


def describe(net):
    d = {
        "input": str(net),
        "version": net.version,
        "network": str(net.network_address),
        "prefixlen": net.prefixlen,
        "netmask": str(net.netmask),
        "num_addresses": net.num_addresses,
        "is_private": net.is_private,
        "is_global": net.is_global,
    }
    if net.version == 4:
        d["broadcast"] = str(net.broadcast_address)
        d["wildcard"] = str(net.hostmask)
        d["class"] = ip_class_v4(net.network_address)
        if net.num_addresses > 2:
            hosts = list(net.hosts())
            d["first_host"] = str(hosts[0])
            d["last_host"] = str(hosts[-1])
            d["usable_hosts"] = net.num_addresses - 2
        elif net.num_addresses == 2:
            d["first_host"] = str(net.network_address)
            d["last_host"] = str(net.broadcast_address)
            d["usable_hosts"] = 2
        else:
            d["first_host"] = str(net.network_address)
            d["last_host"] = str(net.network_address)
            d["usable_hosts"] = 1
    return d


def fmt_card(d):
    lines = []
    lines.append("===== 子网信息：%s =====" % d["input"])
    lines.append("网络地址：%s" % d["network"])
    lines.append("前缀长度：/%d" % d["prefixlen"])
    lines.append("子网掩码：%s" % d["netmask"])
    if d["version"] == 4:
        lines.append("广播地址：%s" % d["broadcast"])
        lines.append("反掩码：%s" % d["wildcard"])
        lines.append("IP 类别：%s" % d["class"])
        lines.append("首个可用主机：%s" % d["first_host"])
        lines.append("末个可用主机：%s" % d["last_host"])
        lines.append("可用主机数：%d" % d["usable_hosts"])
    lines.append("地址总数：%d" % d["num_addresses"])
    lines.append("私有地址：%s" % ("是" if d["is_private"] else "否"))
    lines.append("公网地址：%s" % ("是" if d["is_global"] else "否"))
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="netmask",
        description="子网计算器：输入 CIDR，输出网络地址、广播、可用的主机范围等。",
    )
    ap.add_argument("network", help="CIDR，如 192.168.1.10/24 或 2001:db8::/32")
    ap.add_argument("--contains", metavar="IP", help="判断该 IP 是否属于此子网")
    ap.add_argument("--split", metavar="NEWPREFIX", type=int,
                    help="按新的前缀长度划分子网（如 --split 26）")
    ap.add_argument("--json", action="store_true", help="输出 JSON")
    args = ap.parse_args(argv)

    try:
        net = ipaddress.ip_network(args.network, strict=False)
    except ValueError as e:
        print("error: 无效的网络地址：%s" % e, file=sys.stderr)
        return 1

    out = describe(net)

    if args.contains:
        try:
            ip = ipaddress.ip_address(args.contains)
        except ValueError as e:
            print("error: 无效的 IP 地址：%s" % e, file=sys.stderr)
            return 1
        out["contains"] = {args.contains: ip in net}

    if args.split is not None:
        if args.split <= net.prefixlen:
            print("error: --split 的前缀长度必须大于当前 /%d" % net.prefixlen,
                  file=sys.stderr)
            return 1
        try:
            subs = [str(s) for s in net.subnets(new_prefix=args.split)]
        except ValueError as e:
            print("error: 无法划分：%s" % e, file=sys.stderr)
            return 1
        out["subnets"] = subs

    if args.json:
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        print(fmt_card(out))
        if args.contains:
            ip, inside = next(iter(out["contains"].items()))
            print("%s %s %s" % (ip, "属于" if inside else "不属于", out["input"]))
        if args.split is not None:
            subs = out["subnets"]
            print("共划分为 %d 个 /%d 子网：" % (len(subs), args.split))
            for s in subs[:16]:
                print("  " + s)
            if len(subs) > 16:
                print("  ……（仅显示前 16 个）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
