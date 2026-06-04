"""
性能测试 — 110 并发线程压测邮件服务器
统计：成功率、TPS、平均延迟、P50/P90/P95/P99 分位延迟
无需浏览器，直接发起 HTTP 请求
"""

import time
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    requests.packages.urllib3.disable_warnings()
except Exception:
    pass

BASE_URL = "https://stu.mail.ecust.edu.cn"
PERF_THREADS = 110


def _short_err(e):
    return str(e).split("\n")[0][:80]


def _log(msg, lv="INFO"):
    icons = {"PASS": "[+]", "FAIL": "[-]", "WARN": "[?]",
             "STEP": "  →", "INFO": "[*]"}
    print(f"{time.strftime('%H:%M:%S')} {icons.get(lv, '[*]')} {msg}")


def run_performance(threads: int = PERF_THREADS) -> dict:
    """发起 `threads` 个并发 HTTP 请求并返回性能指标字典"""

    print("\n" + "=" * 50)
    print(f"  性能测试（{threads} 并发线程）")
    print("=" * 50)
    _log(f"目标: {BASE_URL}", "STEP")
    _log("正在发起并发请求...", "STEP")

    records = []
    start = time.perf_counter()

    def req(tid):
        t0 = time.perf_counter()
        rec = {"ok": False, "ms": 0, "tid": tid}
        try:
            resp = requests.get(
                BASE_URL, timeout=10, verify=False,
                headers={"User-Agent": "ECUST-PerfTest"})
            rec["ms"] = round((time.perf_counter() - t0) * 1000, 1)
            rec["ok"] = resp.status_code < 500
        except Exception:
            rec["ms"] = round((time.perf_counter() - t0) * 1000, 1)
        return rec

    with ThreadPoolExecutor(max_workers=threads) as pool:
        futs = {pool.submit(req, i): i for i in range(1, threads + 1)}
        done = 0
        for fut in as_completed(futs):
            records.append(fut.result())
            done += 1
            if done % 30 == 0 or done == threads:
                _log(f"进度: {done}/{threads} 完成", "STEP")

    wall = time.perf_counter() - start
    lats = [r["ms"] for r in records]
    sl = sorted(lats)
    succ = [r for r in records if r["ok"]]

    def pct(p):
        return sl[max(0, int(len(sl) * p / 100) - 1)] if sl else 0

    m = {
        "threads": threads,
        "success": len(succ),
        "failed":  len(records) - len(succ),
        "rate":    f"{len(succ) / len(records) * 100:.1f}%" if records else "0%",
        "tps":     round(len(succ) / wall, 1) if wall > 0 else 0,
        "wall_s":  round(wall, 2),
        "avg":     round(sum(lats) / len(lats), 1) if lats else 0,
        "min":     round(min(lats), 1) if lats else 0,
        "max":     round(max(lats), 1) if lats else 0,
        "p50":     pct(50),
        "p90":     pct(90),
        "p95":     pct(95),
        "p99":     pct(99),
    }

    # 打印报告
    print("\n" + "=" * 50)
    print("  性能测试结果")
    print("=" * 50)
    print(f"  线程数:    {m['threads']}")
    print(f"  总耗时:    {m['wall_s']} 秒")
    print(f"  成功/失败: {m['success']} / {m['failed']}")
    print(f"  成功率:    {m['rate']}")
    print(f"  TPS:       {m['tps']}")
    print(f"  平均延迟:  {m['avg']} ms")
    print(f"  最小延迟:  {m['min']} ms")
    print(f"  最大延迟:  {m['max']} ms")
    print(f"  P50 延迟:  {m['p50']} ms")
    print(f"  P90 延迟:  {m['p90']} ms")
    print(f"  P95 延迟:  {m['p95']} ms")
    print(f"  P99 延迟:  {m['p99']} ms")
    print("=" * 50)

    _log(
        f"成功率={m['rate']}  TPS={m['tps']}  avg={m['avg']}ms  "
        f"P90={m['p90']}ms  P95={m['p95']}ms  P99={m['p99']}ms",
        "PASS" if m["success"] > 0 else "FAIL"
    )

    return m


def main():
    print("=" * 60)
    print("  ECUST 邮箱性能测试 — performance.py")
    print(f"  并发线程数: {PERF_THREADS}")
    print(f"  测试目标:   {BASE_URL}")
    print("=" * 60)

    try:
        run_performance(PERF_THREADS)
    except KeyboardInterrupt:
        _log("用户中断", "WARN")
    except Exception as e:
        _log(f"异常: {_short_err(e)}", "FAIL")
        import traceback
        traceback.print_exc()
    finally:
        input("\n按回车键退出...")


if __name__ == "__main__":
    main()
