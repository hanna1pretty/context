"""Screen texts (Indonesian primary, English variants).

Every text is already HTML-escaped where it embeds user/API data: the
helpers here escape first and wrap second (see telegram_html.py). Empty
API fields render as "Tidak tersedia" / "Not available", never as a
broken layout or an error. Raw long JSON is never rendered: result
screens offer Lihat JSON / Download / Salin buttons instead.
"""
from __future__ import annotations

from .telegram_html import bold, code, escape_html, italic, link, quote, redact_secrets

EMPTY_ID = "Tidak tersedia"
EMPTY_EN = "Not available"


def _empty(language: str = "id") -> str:
    return EMPTY_ID if language == "id" else EMPTY_EN


def _or_empty(value, language: str = "id") -> str:
    """Escaped value (for insertion into raw HTML) or the empty marker."""
    if value is None or (isinstance(value, str) and not value.strip()):
        return _empty(language)
    return escape_html(value)


def _raw_or_empty(value, language: str = "id") -> str:
    """Raw value (for insertion into an escaping wrapper such as code()
    or quote(), which escapes exactly once) or the empty marker."""
    if value is None or (isinstance(value, str) and not value.strip()):
        return _empty(language)
    return str(value)


def main_menu_text(language: str = "id") -> str:
    if language == "en":
        return (
            "<b>Context Intelligence Bot</b>\n\n"
            "<blockquote>Fast web intelligence to read, search, extract, "
            "and monitor information from the internet.</blockquote>\n\n"
            "<b>Choose a feature:</b>\n"
            "Pick one of the menus below, or send a URL or question directly."
        )
    return (
        "<b>Context Intelligence Bot</b>\n\n"
        "<blockquote>Web intelligence cepat untuk membaca, mencari, "
        "mengekstrak, dan memantau informasi dari internet.</blockquote>\n\n"
        "<b>Pilih fitur:</b>\n"
        "Pilih salah satu menu di bawah atau kirim URL dan pertanyaan langsung."
    )


def scrape_menu_text(language: str = "id") -> str:
    if language == "en":
        return ("<b>Scrape URL — apa ini?</b>\n\nFetch the content of ONE "
                "web page: title, text, and links, via Context.dev.\n\n"
                "<b>How to use:</b>\n1. Pick a mode below (Markdown/HTML/"
                "Screenshot/JSON)\n2. Send the URL, or use "
                "<code>/scrape https://example.com</code>\n\n"
                "<i>Result comes as a new message with title, excerpt, "
                "sources, and credits — no endless queue.</i>")
    return ("<b>Scrape URL — ini apa?</b>\n\nMengambil isi SATU halaman "
            "web: judul, teks, dan link-nya, lewat Context.dev.\n\n"
            "<b>Cara pakai:</b>\n1. Pilih mode di bawah (Markdown/HTML/"
            "Screenshot/JSON)\n2. Kirim URL-nya, atau pakai "
            "<code>/scrape https://example.com</code>\n\n"
            "<i>Hasilnya dikirim sebagai pesan baru: judul, cuplikan, "
            "sumber, dan kredit — bukan antrean tanpa ujung.</i>")


def scrape_confirm_text(url: str, mode: str, cache: str = "Default",
                        language: str = "id") -> str:
    shown = redact_secrets(url)
    if language == "en":
        return (f"<b>Scrape Confirmation</b>\n\n<b>URL:</b> {code(shown)}\n"
                f"<b>Mode:</b> {code(mode)}\n<b>Cache:</b> {code(cache)}\n\n"
                "Is this request correct?")
    return (f"<b>Konfirmasi Scrape</b>\n\n<b>URL:</b> {code(shown)}\n"
            f"<b>Mode:</b> {code(mode)}\n<b>Cache:</b> {code(cache)}\n\n"
            "Apakah permintaan ini sudah benar?")


def scrape_fresh_warning_text(language: str = "id") -> str:
    if language == "en":
        return ("<b>Fresh Fetch</b>\n\n<i>Fresh Fetch bypasses the cache, "
                "so it may cost more and take longer than a cached fetch. "
                "Continue only if you need the latest content.</i>")
    return ("<b>Fresh Fetch</b>\n\n<i>Fresh Fetch melewati cache, sehingga "
            "dapat memakan biaya lebih besar dan waktu lebih lama daripada "
            "pengambilan dari cache. Lanjutkan hanya jika kamu butuh "
            "konten terbaru.</i>")


def search_menu_text(language: str = "id") -> str:
    if language == "en":
        return ("<b>Search Web</b>\n\nSearch web pages with a natural "
                "language query.\n\n<b>Example:</b>\n"
                "<code>/search latest AI developments in Indonesia</code>")
    return ("<b>Search Web — ini apa?</b>\n\nMencari halaman web dari "
            "pertanyaan bahasa sehari-hari, bukan kata kunci kaku.\n\n"
            "<b>Cara pakai:</b> kirim pertanyaanmu, atau pakai\n"
            "<code>/search perkembangan AI di Indonesia</code>\n\n"
            "<b>Hasilnya:</b> daftar halaman + cuplikan + sumber, "
            "bisa dibuka satu per satu dari tombolnya.")


def search_results_text(query: str, page: int, total_pages: int,
                        results: list[dict], language: str = "id") -> str:
    head = (f"<b>{'Search results' if language == 'en' else 'Hasil pencarian'}</b>\n"
            f"<b>{'Query' if language == 'en' else 'Query'}:</b> {code(query)}\n"
            f"<b>{'Page' if language == 'en' else 'Halaman'}:</b> "
            f"{code(f'{page}/{total_pages}')}")
    if not results:
        return head + "\n\n" + (_empty(language) if language == "en"
                                else "Tidak ada hasil.")
    lines = [head]
    for i, item in enumerate(results, 1):
        # Escape exactly once: title/domain go into raw HTML (escaped
        # here), snippet goes through quote() (which escapes itself).
        title = _or_empty(item.get("title"), language)
        snippet = quote(item.get("snippet")) if item.get("snippet") else _empty(language)
        domain = _or_empty(item.get("domain"), language)
        date = escape_html(item.get("date")) if item.get("date") else ""
        meta = domain + (f" · {date}" if date else "")
        lines.append(f"\n<b>{i}. {title}</b>\n{snippet}\n<i>{meta}</i>")
    return "\n".join(lines)


def crawl_menu_text(language: str = "id") -> str:
    if language == "en":
        return ("<b>Crawl Website</b>\n\nFollow links from a start URL and "
                "fetch several pages asynchronously.\n\n"
                "<i>Page count, depth, and cost follow your plan and API limits.</i>")
    return ("<b>Crawl Website — ini apa?</b>\n\nMerayapi sebuah website: "
            "mulai dari satu URL, lalu mengikuti link-nya dan mengambil "
            "konten banyak halaman sekaligus.\n\n"
            "<b>Cara pakai:</b> <code>/crawl https://example.com</code>\n"
            "Jumlah halaman dan depth mengikuti paket dan limit API.\n\n"
            "<b>Hasilnya:</b> kumpulan halaman yang berhasil dirayapi, "
            "bukan satu halaman saja.")


def crawl_confirm_text(url: str, max_pages: int, depth: int,
                       output: str = "Markdown", language: str = "id") -> str:
    if language == "en":
        return (f"<b>Crawl Confirmation</b>\n\n<b>Start URL:</b> {code(redact_secrets(url))}\n"
                f"<b>Max pages:</b> {code(str(max_pages))}\n"
                f"<b>Depth:</b> {code(str(depth))}\n"
                f"<b>Output:</b> {code(output)}\n\n"
                "This job will be processed in the background.")
    return (f"<b>Konfirmasi Crawl</b>\n\n<b>URL awal:</b> {code(redact_secrets(url))}\n"
            f"<b>Maks. halaman:</b> {code(str(max_pages))}\n"
            f"<b>Depth:</b> {code(str(depth))}\n"
            f"<b>Output:</b> {code(output)}\n\n"
            "Pekerjaan ini akan diproses di background.")


def map_menu_text(language: str = "id") -> str:
    if language == "en":
        return ("<b>Map URLs</b>\n\nList the URLs on a domain, with filters "
                "and export. Export requires a plan that allows it.")
    return ("<b>Map URLs — ini apa?</b>\n\nMemetakan sebuah domain: "
            "menampilkan daftar semua URL yang ada di website itu.\n\n"
            "<b>Cara pakai:</b> <code>/map https://example.com</code>\n\n"
            "<b>Hasilnya:</b> daftar URL yang bisa dijelajahi. Export "
            "memerlukan paket yang mengizinkannya.")


def map_results_text(domain: str, page: int, total_pages: int,
                     urls: list[str], language: str = "id") -> str:
    title = "Map results" if language == "en" else "Hasil Map"
    body = "\n".join(code(redact_secrets(u)) for u in urls) if urls else _empty(language)
    return (f"<b>{title}</b>\n<b>Domain:</b> {code(domain)}\n"
            f"<b>{'Page' if language == 'en' else 'Halaman'}:</b> {code(f'{page}/{total_pages}')}\n\n{body}")


def answers_menu_text(language: str = "id") -> str:
    if language == "en":
        return ("<b>Ask / Answers</b>\n\nAsk a research question. The bot "
                "returns an answer and source URLs when available.\n\n"
                "<i>For important decisions, verify the answer against the "
                "original sources.</i>")
    return ("<b>Ask / Answers — ini apa?</b>\n\nBertanya seperti ke "
            "asisten riset: bot menjawab dari isi web, lengkap dengan "
            "URL sumbernya bila tersedia.\n\n"
            "<b>Cara pakai:</b> <code>/ask apa itu Context.dev?</code>\n\n"
            "<i>Untuk keputusan penting, verifikasi jawaban pada sumber asli.</i>")


def answers_result_text(answer: str, sources: list[str], language: str = "id") -> str:
    title = "Answer" if language == "en" else "Jawaban"
    body = quote(answer) if answer else _empty(language)
    src_lines = []
    for src in sources or []:
        src_lines.append(link(src, src))
    src_block = "\n".join(src_lines) if src_lines else _empty(language)
    label = "Sources" if language == "en" else "Sumber"
    note = ("<i>Please verify important information against the sources above.</i>"
            if language == "en" else
            "<i>Verifikasi info penting ke sumber aslinya.</i>")
    return f"<b>{title}</b>\n\n{body}\n\n<b>{label}:</b>\n{src_block}\n\n{note}"


def parse_menu_text(language: str = "id") -> str:
    if language == "en":
        return ("<b>Parse File</b>\n\nSend a PDF, document, spreadsheet, "
                "presentation, image, or file URL in a supported format.\n\n"
                "<i>Files are processed securely and kept for a limited time.</i>")
    return ("<b>Parse File — ini apa?</b>\n\nMengubah file menjadi teks "
            "yang bisa dibaca dan dicari: PDF, dokumen, spreadsheet, "
            "presentasi, gambar, atau URL file.\n\n"
            "<b>Cara pakai:</b> kirim file-nya langsung ke chat ini, atau "
            "<code>/parse https://example.com/file.pdf</code>\n\n"
            "<i>File diproses secara aman dan hanya disimpan sementara.</i>")


def parse_file_text(filename: str, size_bytes: int | None, mime: str | None,
                    output: str = "Markdown", language: str = "id") -> str:
    """File info only: name (escaped), size, MIME, output. NEVER a local
    server path."""
    size = _empty(language) if size_bytes is None else f"{size_bytes} bytes"
    title = "File received" if language == "en" else "File diterima"
    return (f"<b>{title}</b>\n\n<b>{'File' if language == 'en' else 'Nama'}:</b> "
            f"{code(filename)}\n<b>{'Size' if language == 'en' else 'Ukuran'}:</b> {code(size)}\n"
            f"<b>MIME:</b> {code(mime or _empty(language))}\n"
            f"<b>Output:</b> {code(output)}")


def intelligence_menu_text(language: str = "id") -> str:
    if language == "en":
        return ("<b>Intelligence</b>\n\nBrand, styleguide, people, and "
                "company lookups. People search/enrichment is only for "
                "legitimate use cases.")
    return ("<b>Brand Intel — ini apa?</b>\n\nMencari informasi tentang "
            "sebuah brand atau perusahaan: profil, website, dan gaya "
            "visualnya (styleguide).\n\n"
            "<b>Cara pakai:</b> <code>/brand nama-brand</code> atau "
            "<code>/company nama-perusahaan</code>, lalu pilih Brand "
            "Lookup / Brand Search / Styleguide di bawah.\n\n"
            "People search/enrichment hanya untuk keperluan yang sah.")


def people_warning_text(language: str = "id") -> str:
    if language == "en":
        return ("<i>Privacy notice: people data is only shown for "
                "legitimate purposes. Do not use it to harass, stalk, or "
                "contact people without consent.</i>")
    return ("<i>Peringatan privasi: data orang hanya ditampilkan untuk "
            "keperluan yang sah. Jangan digunakan untuk mengganggu, "
            "menguntit, atau menghubungi orang tanpa persetujuan.</i>")


def _field_lines(fields: dict, language: str = "id") -> str:
    if not fields:
        return _empty(language)
    return "\n".join(
        f"<b>{escape_html(key)}:</b> {_or_empty(value, language)}"
        for key, value in fields.items())


def brand_menu_text(language: str = "id") -> str:
    if language == "en":
        return ("<b>Brand — what is it?</b>\n\nLook up a brand: profile, "
                "website, and styleguide.\n\n<b>How to use:</b> "
                "<code>/brand brand-name</code>, then pick Brand Lookup, "
                "Brand Search, or Styleguide below.")
    return ("<b>Brand — ini apa?</b>\n\nMencari profil sebuah brand: "
            "website, deskripsi, dan styleguide-nya.\n\n"
            "<b>Cara pakai:</b> <code>/brand nama-brand</code>, lalu "
            "pilih Brand Lookup, Brand Search, atau Styleguide di bawah.")


def people_menu_text(language: str = "id") -> str:
    if language == "en":
        return ("<b>People — what is it?</b>\n\nSearch or enrich a "
                "person's public professional profile.\n\n"
                "<b>How to use:</b> <code>/people full-name</code>, then "
                "pick People Search or People Enrich below.\n\n"
                "<i>Only for legitimate purposes.</i>")
    return ("<b>People — ini apa?</b>\n\nMencari atau melengkapi profil "
            "profesional publik seseorang.\n\n"
            "<b>Cara pakai:</b> <code>/people nama-lengkap</code>, lalu "
            "pilih People Search atau People Enrich di bawah.\n\n"
            "<i>Hanya untuk keperluan yang sah.</i>")


def company_menu_text(language: str = "id") -> str:
    if language == "en":
        return ("<b>Company — what is it?</b>\n\nLook up a company: "
                "profile, website, and related info.\n\n"
                "<b>How to use:</b> <code>/company company-name</code>, "
                "then pick Company Search below.")
    return ("<b>Perusahaan — ini apa?</b>\n\nMencari profil sebuah "
            "perusahaan: website dan info terkaitnya.\n\n"
            "<b>Cara pakai:</b> <code>/company nama-perusahaan</code>, "
            "lalu pilih Company Search di bawah.")


def batches_menu_text(language: str = "id") -> str:
    if language == "en":
        return ("<b>Batches — what is it?</b>\n\nRun many URLs at once "
                "as one batch instead of one by one.\n\n"
                "<b>How to use:</b> "
                "<code>/batch https://a.com,https://b.com</code>\n\n"
                "Job Center below shows every batch and job status.")
    return ("<b>Batches — ini apa?</b>\n\nMenjalankan banyak URL "
            "sekaligus dalam satu batch, bukan satu per satu.\n\n"
            "<b>Cara pakai:</b> "
            "<code>/batch https://a.com,https://b.com</code>\n\n"
            "Job Center di bawah menampilkan status semua batch dan job.")


def monitors_menu_text(language: str = "id") -> str:
    if language == "en":
        return ("<b>Monitors — what is it?</b>\n\nWatch a URL and get "
                "notified when its content changes.\n\n"
                "<b>How to use:</b> <code>/monitor https://example.com</code> "
                "to create one, or <code>/monitor list</code> to see yours.")
    return ("<b>Monitors — ini apa?</b>\n\nMemantau sebuah URL dan "
            "memberi kabar saat isinya berubah.\n\n"
            "<b>Cara pakai:</b> <code>/monitor https://example.com</code> "
            "untuk membuat monitor, atau <code>/monitor list</code> "
            "untuk melihat monitor kamu.")


def brand_text(fields: dict, language: str = "id") -> str:
    title = "Brand" if language == "en" else "Brand"
    return f"<b>{title}</b>\n\n{_field_lines(fields, language)}"


def people_text(fields: dict, language: str = "id") -> str:
    title = "People" if language == "en" else "People"
    return (f"<b>{title}</b>\n\n{people_warning_text(language)}\n\n"
            f"{_field_lines(fields, language)}")


def company_text(fields: dict, language: str = "id") -> str:
    title = "Company" if language == "en" else "Perusahaan"
    return f"<b>{title}</b>\n\n{_field_lines(fields, language)}"


def news_menu_text(language: str = "id") -> str:
    if language == "en":
        return "<b>News</b>\n\nSearch news, follow company news, and save queries."
    return ("<b>News — ini apa?</b>\n\nMencari berita terbaru tentang "
            "topik atau perusahaan, dan menyimpan query-nya.\n\n"
            "<b>Cara pakai:</b> <code>/news nama-perusahaan</code> atau "
            "kirim topik beritanya.")


def job_center_text(language: str = "id") -> str:
    if language == "en":
        return ("<b>Job Center</b>\n\nHere you can see active, finished, "
                "failed, or expired jobs.")
    return ("<b>Job Center</b>\n\nDi sini kamu dapat melihat pekerjaan "
            "aktif, selesai, gagal, atau kadaluarsa.")


def job_text(job: dict, language: str = "id") -> str:
    """Real stored status only — never a fabricated progress value."""
    job_id = _raw_or_empty(job.get("job_id") or job.get("id"), language)
    kind = _raw_or_empty(job.get("kind") or job.get("type"), language)
    status = _raw_or_empty(job.get("status"), language)
    created = _raw_or_empty(job.get("created_at") or job.get("created"), language)
    label = "Job" if language == "en" else "Job"
    return (f"<b>{label}:</b> {code(job_id)}\n<b>{'Type' if language == 'en' else 'Tipe'}:</b> {code(kind)}\n"
            f"<b>Status:</b> {code(status)}\n<b>{'Created' if language == 'en' else 'Dibuat'}:</b> {code(created)}")


def monitor_delete_text(language: str = "id") -> str:
    if language == "en":
        return ("<b>Delete monitor?</b>\n\nThe monitor will stop sending "
                "notifications after it is deleted.")
    return ("<b>Hapus monitor?</b>\n\nMonitor tidak akan mengirimkan "
            "notifikasi lagi setelah dihapus.")


def usage_text(plan: str, used_today: int, daily_limit: int,
               active_jobs: int, reset_text: str = "besok 00:00",
               language: str = "id") -> str:
    if language == "en":
        return (f"<b>Usage &amp; Plan</b>\n\n<b>Plan:</b> {code(plan.upper())}\n"
                f"<b>Usage today:</b> {code(f'{used_today} / {daily_limit}')}\n"
                f"<b>Active jobs:</b> {code(str(active_jobs))}\n"
                f"<b>Limit reset:</b> {code(reset_text)}")
    return (f"<b>Usage &amp; Paket</b>\n\n<b>Paket:</b> {code(plan.upper())}\n"
            f"<b>Penggunaan hari ini:</b> {code(f'{used_today} / {daily_limit}')}\n"
            f"<b>Job aktif:</b> {code(str(active_jobs))}\n"
            f"<b>Reset limit:</b> {code(reset_text)}")


def plan_text(language: str = "id") -> str:
    if language == "en":
        return ("<b>Plans</b>\n\nFree, Pro, and Business plans. Choosing a "
                "plan here only opens the checkout confirmation — nothing "
                "is charged automatically.")
    return ("<b>Paket</b>\n\nPaket Free, Pro, dan Business. Memilih paket "
            "di sini hanya membuka konfirmasi checkout — tidak ada "
            "pembayaran otomatis.")


def locked_feature_text(feature: str, required_plan: str, language: str = "id") -> str:
    if language == "en":
        return (f"<b>Feature locked</b>\n\n{escape_html(feature)} requires "
                f"the {code(required_plan)} plan. See the plan options to upgrade.")
    return (f"<b>Fitur terkunci</b>\n\n{escape_html(feature)} memerlukan "
            f"paket {code(required_plan)}. Lihat pilihan paket untuk upgrade.")


def settings_menu_text(language: str = "id") -> str:
    if language == "en":
        return "<b>Settings</b>\n\nLanguage, timezone, notifications, default output, and data controls."
    return ("<b>Pengaturan — ini apa?</b>\n\nMengatur bot untuk kamu: "
            "bahasa, timezone, notifikasi, output default, dan kontrol "
            "data (hapus history / hapus data saya).\n\n"
            "<b>Cara pakai:</b> pilih salah satu tombol di bawah.")


def settings_delete_text(language: str = "id") -> str:
    if language == "en":
        return ("<b>Delete my data?</b>\n\nThis removes your stored history "
                "and settings. This action cannot be undone.")
    return ("<b>Hapus data saya?</b>\n\nIni menghapus history dan pengaturan "
            "tersimpan kamu. Tindakan ini tidak dapat dibatalkan.")


def settings_clear_text(language: str = "id") -> str:
    if language == "en":
        return "<b>Clear history?</b>\n\nYour chat history in this bot will be cleared."
    return "<b>Hapus history?</b>\n\nHistory chat kamu di bot ini akan dihapus."


def help_text(language: str = "id") -> str:
    """Premium help screen (inline-first). This is what /help now sends:
    a short guide + inline topics, NOT a raw command dump. The full
    command list lives behind the 'Semua Command' button only."""
    if language == "en":
        return (
            "<b>Help — OktaScrape</b>\n\n"
            "<blockquote>Read, search, crawl, extract, and monitor the "
            "web with Context.dev — from the buttons below.</blockquote>\n\n"
            "<b>How to use:</b>\n"
            "1. Pick a menu below\n"
            "2. Send a URL to scrape or crawl\n"
            "3. Or send a question directly\n\n"
            "Commands like /scrape are shortcuts; the buttons are the "
            "primary way to use the bot. Pick a topic below."
        )
    return (
        "<b>Bantuan — OktaScrape</b>\n\n"
        "<blockquote>Baca, cari, rayapi, ekstrak, dan pantau informasi "
        "dari web lewat Context.dev — lewat tombol di bawah.</blockquote>\n\n"
        "<b>Cara pakai:</b>\n"
        "1. Pilih menu di bawah\n"
        "2. Kirim URL untuk di-scrape / di-crawl\n"
        "3. Atau kirim pertanyaan langsung\n\n"
        "Command seperti /scrape hanya jalan pintas; tombol inline "
        "adalah cara utama memakai bot. Pilih topik di bawah."
    )


def help_commands_text(language: str = "id") -> str:
    cmds = ("/start /help /scrape /search /crawl /map /ask /parse /brand "
            "/styleguide /people /company /news /batch /monitor /usage "
            "/plan /language /cancel /admin /delete_my_data")
    if language == "en":
        return f"<b>All commands</b>\n\n{code(cmds)}"
    return f"<b>Semua Command</b>\n\n{code(cmds)}"


def help_examples_text(language: str = "id") -> str:
    if language == "en":
        return ("<b>Usage examples</b>\n\n"
                "<code>/scrape https://example.com</code>\n"
                "<code>/search latest technology news</code>\n"
                "<code>/crawl https://docs.example.com</code>\n"
                "<code>/ask what is this company's main product?</code>")
    return ("<b>Contoh penggunaan</b>\n\n"
            "<code>/scrape https://example.com</code>\n"
            "<code>/search berita teknologi terbaru</code>\n"
            "<code>/crawl https://docs.example.com</code>\n"
            "<code>/ask apa produk utama perusahaan ini?</code>")


def help_status_text(status: str = "OK", language: str = "id") -> str:
    if language == "en":
        return f"<b>System status</b>\n\n<b>Status:</b> {code(status)}"
    return f"<b>Status Sistem</b>\n\n<b>Status:</b> {code(status)}"


def help_privacy_text(language: str = "id") -> str:
    if language == "en":
        return ("<b>Privacy &amp; Data</b>\n\nYour data is used only to run "
                "your requests. Use Settings to clear history or delete "
                "your data. Secrets are never shown in chat.")
    return ("<b>Privacy &amp; Data</b>\n\nData kamu hanya digunakan untuk "
            "menjalankan permintaanmu. Gunakan Pengaturan untuk menghapus "
            "history atau data kamu. Secret tidak pernah ditampilkan di chat.")


def error_validation_text(language: str = "id") -> str:
    if language == "en":
        return ("<b>Input not valid yet</b>\n\nThe URL sent is not valid. "
                "Use a URL in the format <code>https://...</code>.")
    return ("<b>Input belum valid</b>\n\nURL yang dikirim tidak valid. "
            "Gunakan URL dengan format <code>https://...</code>.")


def error_rate_limit_text(language: str = "id") -> str:
    if language == "en":
        return ("<b>Requests are busy right now</b>\n\nPlease wait a "
                "moment. The bot will retry within the service limits.")
    return ("<b>Permintaan sedang padat</b>\n\nSilakan tunggu beberapa "
            "saat. Bot akan mencoba kembali sesuai batas layanan.")


def error_quota_text(language: str = "id") -> str:
    if language == "en":
        return ("<b>Plan limit reached</b>\n\nYou can try again after the "
                "reset, or look at other plan options.")
    return ("<b>Limit paket tercapai</b>\n\nKamu dapat mencoba lagi "
            "setelah reset atau melihat pilihan paket lain.")


def error_context_text(internal_code: str, retryable: bool = True,
                       language: str = "id") -> str:
    """Context.dev error: a SAFE internal code only (alphanumeric,
    dash/underscore, max 32 chars) — never a stack trace or raw payload."""
    import re as _re
    code_value = internal_code if _re.fullmatch(r"[A-Za-z0-9_-]{1,32}", internal_code or "") else "UNKNOWN"
    if language == "en":
        text = ("<b>Service error</b>\n\nThe service could not complete "
                f"this request. <b>Code:</b> {code(code_value)}")
        if retryable:
            text += "\n\n<i>You can try again.</i>"
        return text
    text = ("<b>Terjadi kesalahan layanan</b>\n\nLayanan tidak dapat "
            f"menyelesaikan permintaan ini. <b>Kode:</b> {code(code_value)}")
    if retryable:
        text += "\n\n<i>Kamu dapat mencoba lagi.</i>"
    return text
