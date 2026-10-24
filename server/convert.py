#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""文件转换后端：处理 inbox/ 里的转换请求，结果写回 outbox/。
请求约定：inbox/<jobid>/input.<ext> + inbox/<jobid>/request.json
request.json: {"src":"<ext>","dst":"<ext>","params":{...}}
"""
import os, json, shutil, subprocess, sys, base64, zipfile

INBOX = "inbox"
OUTBOX = "outbox"

def log(m):
    print("[convert] " + m, flush=True)

def fail(job, msg):
    try:
        with open(os.path.join(OUTBOX, job, "error.txt"), "w", encoding="utf-8") as f:
            f.write(msg)
    except Exception:
        pass
    log("FAIL " + job + ": " + msg)

def norm_audio(args):
    # 统一转 WAV 用于参数调整（时长/音量/采样率）
    pass

def run_ffmpeg(args, job, src, dst, params):
    out_dir = os.path.join(OUTBOX, job)
    os.makedirs(out_dir, exist_ok=True)
    input_path = os.path.join(INBOX, job, "input" + src)
    out_path = os.path.join(out_dir, "output" + dst)
    cmd = ["ffmpeg", "-y", "-i", input_path]
    # 视频参数
    if "w" in params and "h" in params:
        cmd += ["-vf", "scale={}:{}".format(int(params["w"]), int(params["h"]))]
    if "fps" in params:
        cmd += ["-r", str(int(params["fps"]))]
    if "t" in params:
        cmd += ["-t", str(float(params["t"]))]
    if "vol" in params:
        cmd += ["-filter:a", "volume={}".format(float(params["vol"]))]
    cmd.append(out_path)
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        fail(job, "ffmpeg 失败: " + (r.stderr[-500:] if r.stderr else "无输出"))
        return False
    if os.path.exists(out_path):
        log("OK " + job + " -> " + out_path)
        return True
    fail(job, "未生成输出文件")
    return False

def run_text(job, src, dst, params):
    # 文本/代码/数据：改名或简单处理
    input_path = os.path.join(INBOX, job, "input" + src)
    out_dir = os.path.join(OUTBOX, job)
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "output" + dst)
    try:
        data = open(input_path, "rb").read()
    except Exception as e:
        fail(job, "读取失败: " + str(e)); return False
    open(out_path, "wb").write(data)
    log("OK " + job + " -> " + out_path)
    return True

def run_zip(job, src, dst):
    input_path = os.path.join(INBOX, job, "input" + src)
    out_dir = os.path.join(OUTBOX, job)
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "output" + dst)
    try:
        if dst in (".zip",):
            with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as z:
                z.write(input_path, os.path.basename(input_path))
        else:
            fail(job, "暂不支持目标压缩格式 " + dst); return False
        log("OK " + job + " -> " + out_path)
        return True
    except Exception as e:
        fail(job, "压缩失败: " + str(e)); return False

def main():
    os.makedirs(OUTBOX, exist_ok=True)
    if not os.path.isdir(INBOX):
        log("无 inbox"); return
    jobs = [d for d in os.listdir(INBOX) if os.path.isdir(os.path.join(INBOX, d))]
    log("发现任务: " + str(jobs))
    for job in jobs:
        job_dir = os.path.join(INBOX, job)
        req_path = os.path.join(job_dir, "request.json")
        if not os.path.exists(req_path):
            log("任务无 request.json，跳过 " + job); continue
        with open(req_path, encoding="utf-8") as f:
            req = json.load(f)
        src, dst, params = req.get("src"), req.get("dst"), req.get("params") or {}
        log("转换 " + job + ": " + src + " -> " + dst)
        if src.startswith(".") and dst.startswith("."):
            if src in (".mp4",".avi",".mov",".mkv",".webm",".mp3",".wav",".ogg",".aac",".flac") or dst in (".mp4",".avi",".mov",".mkv",".webm"):
                run_ffmpeg([], job, src, dst, params)
            elif dst == ".zip":
                run_zip(job, src, dst)
            else:
                run_text(job, src, dst, params)
        else:
            fail(job, "非法格式")
        # 转换后清掉 inbox 任务
        try:
            shutil.rmtree(job_dir)
        except Exception:
            pass

if __name__ == "__main__":
    main()
