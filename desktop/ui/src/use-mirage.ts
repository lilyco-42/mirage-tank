import { useEffect, useRef, useState } from "react";

type Workspace = { id: string; hidden: string; surface: string };
type Job = { id: string; state: "queued" | "running" | "done" | "failed" | "cancelled"; error?: string; result?: { width: number; height: number; hidden_max: number; surface_min: number }; files: { name: string; size: number }[] };

export async function api<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(path, options);
  const data = await response.json();
  if (!response.ok) throw new Error(typeof data.detail === "string" ? data.detail : "请求无效，请重新选择图片后重试");
  return data;
}

export function useObjectUrl(file?: File) {
  const [url, setUrl] = useState<string>();
  useEffect(() => {
    if (!file) { setUrl(undefined); return; }
    const object = URL.createObjectURL(file); setUrl(object);
    return () => URL.revokeObjectURL(object);
  }, [file]);
  return url;
}

export function useMirage() {
  const [hidden, setHidden] = useState<File>();
  const [surface, setSurface] = useState<File>();
  const [hiddenMax, setHiddenMax] = useState(100);
  const [surfaceMin, setSurfaceMin] = useState(128);
  const [available, setAvailable] = useState(false);
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState("选择两张图片，开始你的第一次创作");
  const [error, setError] = useState(false);
  const [result, setResult] = useState<Job>();
  const [activeJob, setActiveJob] = useState<string>();
  const workspace = useRef<Workspace | undefined>(undefined);
  const cancelled = useRef(false);
  useEffect(() => {
    let alive = true;
    void api<{ available: boolean }>("/api/capabilities").then(data => {
      if (alive) { setAvailable(data.available); if (!data.available) { setStatus("合成引擎缺失，请下载完整桌面包"); setError(true); } }
    }).catch(e => { if (alive) { setStatus(e.message); setError(true); } });
    return () => { alive = false; };
  }, []);

  function choose(role: "hidden" | "surface", file?: File) {
    if (busy) return;
    if (file && (!/\.(png|jpe?g)$/i.test(file.name) || file.size > 16 * 1024 * 1024 || file.size === 0)) {
      setStatus("请选择不超过 16 MB 的 PNG / JPEG 图片"); setError(true); return;
    }
    if (role === "hidden") setHidden(file); else setSurface(file);
    setResult(undefined); setError(false); setStatus("图片已选择，合成后即可对比黑白背景");
  }

  async function run() {
    if (!hidden || !surface || busy || !available) return;
    setBusy(true); setError(false); setResult(undefined); cancelled.current = false;
    try {
      if (workspace.current) { await api(`/api/workspaces/${workspace.current.id}`, { method: "DELETE" }); workspace.current = undefined; }
      setStatus("正在读取两张图片…");
      const form = new FormData(); form.append("hidden", hidden); form.append("surface", surface);
      workspace.current = await api<Workspace>("/api/workspaces", { method: "POST", body: form });
      const current = workspace.current;
      const job = await api<Job>("/api/jobs", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ session: current.id, hidden: current.hidden, surface: current.surface, hidden_max: hiddenMax, surface_min: surfaceMin }) });
      setActiveJob(job.id); setStatus("正在合成透明图片…");
      const deadline = Date.now() + 140_000;
      while (Date.now() < deadline) {
        const updated = await api<Job>(`/api/jobs/${job.id}`);
        if (updated.state === "done") { setResult(updated); setStatus("处理完成 · 试试黑底和白底的不同效果"); return; }
        if (updated.state === "failed") throw new Error(updated.error || "合成失败，请核对图片格式");
        if (updated.state === "cancelled" || cancelled.current) { setStatus("任务已取消，可以重新选择图片"); return; }
        await new Promise(resolve => setTimeout(resolve, 250));
      }
      await api(`/api/jobs/${job.id}/cancel`, { method: "POST" });
      throw new Error("处理超时，请缩小图片后重试");
    } catch (e) { setError(true); setStatus(e instanceof Error ? e.message : "合成失败，请重试"); }
    finally { setBusy(false); setActiveJob(undefined); }
  }

  async function cancel() {
    if (!activeJob) return;
    try { await api(`/api/jobs/${activeJob}/cancel`, { method: "POST" }); cancelled.current = true; }
    catch (e) { setError(true); setStatus(e instanceof Error ? e.message : "取消失败，请重试"); }
  }

  async function clear() {
    if (busy) return;
    try {
      if (workspace.current) await api(`/api/workspaces/${workspace.current.id}`, { method: "DELETE" });
      workspace.current = undefined; setHidden(undefined); setSurface(undefined); setResult(undefined); setError(false);
      setStatus("工作区已删除，开始下一次创作吧");
    } catch (e) { setError(true); setStatus(e instanceof Error ? e.message : "删除失败，请重试"); }
  }

  function adjust(role: "hidden" | "surface", value: number) {
    if (busy) return;
    if (role === "hidden") setHiddenMax(value); else setSurfaceMin(value);
    setResult(undefined); setStatus("参数已调整，点击合成查看新效果"); setError(false);
  }
  return { hidden, surface, hiddenMax, surfaceMin, available, busy, status, error, result, activeJob, choose, adjust, run, cancel, clear };
}
