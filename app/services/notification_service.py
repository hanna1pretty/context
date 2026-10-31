"""Notification message builders (transport injected by bot/workers). Pure stdlib.

All builders return Telegram HTML (parse_mode="HTML" at the send site).
Every user/API value is escaped, truncated, and never contains a secret
or a raw data URL. Job ids are short server-side ids only.
"""
from __future__ import annotations

from ..security.validators import escape_html


def _subject(payload: dict | None) -> str:
    if not isinstance(payload, dict):
        return ""
    for key in ("url", "query", "question"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return escape_html(value.strip()[:120])
    callback = payload.get("callback")
    if isinstance(callback, str) and callback.strip():
        return escape_html(callback.strip()[:80])
    urls = payload.get("urls")
    if isinstance(urls, list) and urls:
        return escape_html(str(urls[0])[:120])
    return ""


def accepted_message(job_id: str, kind: str, subject: str | None = None,
                     payload: dict | None = None) -> str:
    """Queued acknowledgement. Explicitly says a result message follows.

    ``subject`` overrides the payload-derived subject; ``payload`` is
    accepted for callers that already have it (see handlers/_common).
    """
    subj = escape_html(subject[:120]) if isinstance(subject, str) and subject else _subject(payload)
    lines = [
        "✅ <b>Antrian diterima</b>",
        f"Job: <code>{escape_html(job_id)}</code>",
        f"Jenis: {escape_html(kind)}",
    ]
    if subj:
        lines.append(f"Yang diproses: {subj}")
    lines.append(
        "Status: <b>mengantre</b> — bot akan mengirim pesan progres, "
        "lalu pesan hasil ke chat ini. Job ini tidak berhenti di sini."
    )
    return "\n".join(lines)


def progress_message(job_id: str, kind: str, subject: str | None = None,
                     payload: dict | None = None) -> str:
    """In-flight progress: what is running, not just 'memproses'."""
    subj = escape_html(subject[:120]) if isinstance(subject, str) and subject else _subject(payload)
    lines = [
        f"⏳ <b>Mengerjakan {escape_html(kind)}</b>",
        f"Job: <code>{escape_html(job_id)}</code>",
    ]
    if subj:
        lines.append(f"Target: {subj}")
    lines.append("Status: <b>sedang diproses di Context.dev…</b>")
    lines.append("Tunggu sebentar, hasil akan dikirim sebagai pesan baru.")
    return "\n".join(lines)


def result_message(job_id: str, kind: str, result: dict) -> str:
    """Clear success message: title, excerpt, sources, credits, partial note."""
    title = result.get("title") if isinstance(result, dict) else None
    text = result.get("text") if isinstance(result, dict) else None
    items = result.get("items") if isinstance(result, dict) else None
    sources = result.get("sources") if isinstance(result, dict) else None
    lines = [
        f"✅ <b>Hasil {escape_html(kind)}</b>",
        f"Job: <code>{escape_html(job_id)}</code>",
    ]
    if isinstance(title, str) and title.strip():
        lines.append(f"<b>{escape_html(title.strip()[:200])}</b>")
    if result.get("is_partial"):
        lines.append("⚠️ <i>Hasil sebagian — data mungkin belum lengkap.</i>")
    if isinstance(text, str) and text.strip():
        lines.append("")
        lines.append(escape_html(text.strip()[:1500]))
    if isinstance(items, list) and items:
        lines.append("")
        lines.append("<b>Hasil:</b>")
        for i, item in enumerate(items[:5], 1):
            if not isinstance(item, dict):
                continue
            label = item.get("title") or item.get("url") or ""
            lines.append(f"{i}. {escape_html(str(label)[:200])}")
            if item.get("url"):
                lines.append(f"   {escape_html(str(item['url'])[:200])}")
    if isinstance(sources, list) and sources:
        lines.append("")
        lines.append("<b>Sumber:</b>")
        for i, source in enumerate(sources[:5], 1):
            lines.append(f"{i}. {escape_html(str(source)[:200])}")
    credits = result.get("credits_consumed") if isinstance(result, dict) else None
    if credits is not None:
        lines.append(f"\nKredit terpakai: {escape_html(str(credits))}")
    request_id = result.get("request_id") if isinstance(result, dict) else None
    if isinstance(request_id, str) and request_id.strip():
        lines.append(f"Request ID: <code>{escape_html(request_id.strip())}</code>")
    return "\n".join(lines)


def done_message(job_id: str) -> str:
    return f"Job <code>{escape_html(job_id)}</code> selesai ✅"


def failed_message(job_id: str, safe_error: str) -> str:
    return (f"Job <code>{escape_html(job_id)}</code> gagal ❌\n"
            f"{escape_html(safe_error)}\nSilakan coba lagi atau buka Bantuan.")


def failure_message(job_id: str, kind: str, safe_error: str, *,
                    payload: dict | None = None) -> str:
    """Failure with a next step, never a bare 'gagal' and never a stack trace."""
    reason = (safe_error or "Terjadi kesalahan.").strip()
    # Next-step hint based on the reason text (all reasons are already
    # user-facing, never raw exceptions with secrets).
    if "belum di-set" in reason or "API key" in reason:
        hint = "Langkah berikutnya: admin, set kunci di /admin &gt; Set Context API Key, lalu ulangi."
    elif "kuota" in reason.lower() or "limit" in reason.lower():
        hint = "Langkah berikutnya: cek Usage &amp; Paket, tunggu reset harian, atau kurangi jumlah halaman."
    elif "waktu" in reason.lower() or "timeout" in reason.lower():
        hint = "Langkah berikutnya: coba lagi sebentar lagi dengan URL yang sama."
    else:
        hint = "Langkah berikutnya: coba lagi, atau buka Bantuan untuk contoh perintah."
    subj = _subject(payload)
    lines = [
        f"❌ <b>Gagal: {escape_html(kind)}</b>",
        f"Job: <code>{escape_html(job_id)}</code>",
    ]
    if subj:
        lines.append(f"Target: {subj}")
    lines.append(f"Alasan: {escape_html(reason[:500])}")
    lines.append(hint)
    return "\n".join(lines)
