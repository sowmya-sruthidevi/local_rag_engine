(function () {
    "use strict";

    const $ = (sel, el = document) => el.querySelector(sel);
    const $$ = (sel, el = document) => Array.from(el.querySelectorAll(sel));
    const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

    const els = {
        uploadArea: $("#uploadArea"),
        fileInput: $("#fileInput"),
        fileList: $("#fileList"),
        embedBtn: $("#embedBtn"),
        embedBtnText: $("#embedBtnText"),
        embedSpinner: $(".action-spinner", $("#embedBtn")),
        embedResult: $("#embedResult"),

        stream: $("#chatMessages"),
        emptyChat: $("#emptyChat"),
        chatInput: $("#chatInput"),
        sendBtn: $("#sendBtn"),
        clearBtn: $("#clearChatBtn"),

        toastStack: $("#notifications"),

        statDocs: $("#stat-documents"),
        statVectors: $("#stat-vectors"),
        statQueries: $("#stat-queries"),
    };

    const state = {
        files: [],
        thread: [],
        totals: {
            docs: 0,
            vectors: 233,
            queries: 0,
        },
    };

    /* -------------------- Helpers -------------------- */

    function fmtSize(bytes) {
        if (!bytes && bytes !== 0) return "";
        const units = ["B", "KB", "MB", "GB"];
        let i = 0;
        let n = bytes;
        while (n >= 1024 && i < units.length - 1) {
            n /= 1024;
            i++;
        }
        return (n >= 100 ? n.toFixed(0) : n.toFixed(1)) + " " + units[i];
    }

    function extOf(name) {
        const p = name.lastIndexOf(".");
        return p >= 0 ? name.slice(p + 1).toLowerCase() : "";
    }

    function updateStats() {
        els.statDocs.textContent = state.totals.docs;
        els.statVectors.textContent = state.totals.vectors;
        els.statQueries.textContent = state.totals.queries;
    }

    function toast(kind, title, desc) {
        const icons = { good: "✓", bad: "!", info: "i" };
        const t = document.createElement("div");
        t.className = "toast " + kind;
        t.innerHTML =
            `<div class="toast-icon">${icons[kind] || "i"}</div>` +
            `<div class="toast-text"><div class="toast-title">${esc(title)}</div>` +
            (desc ? `<div class="toast-desc">${esc(desc)}</div>` : "") +
            `</div>`;
        els.toastStack.appendChild(t);
        setTimeout(() => {
            t.style.opacity = "0";
            t.style.transform = "translateX(16px)";
            t.style.transition = "all .28s ease";
            setTimeout(() => t.remove(), 300);
        }, 4200);
    }

    function escapeFormat(text) {
        return esc(text)
            .replace(/\*\*([^*]+)\*\*/g, "<b>$1</b>")
            .replace(/(^|\W)\*([^*\n]+)\*(?=\W|$)/g, "$1<em>$2</em>")
            .replace(/`([^`]+)`/g, "<code>$1</code>")
            .replace(/\n/g, "<br>");
    }

    /* -------------------- Upload handling -------------------- */

    const VALID = ["pdf", "docx", "doc", "txt"];

    function addFiles(list) {
        let added = 0;
        let skipped = 0;
        for (const f of list) {
            if (!f || !f.name) continue;
            if (!VALID.includes(extOf(f.name))) {
                skipped++;
                continue;
            }
            state.files.push(f);
            added++;
        }
        renderFileList();
        updateEmbedButton();
        if (added) toast("info", "Files added", `${added} file${added > 1 ? "s" : ""} ready to index.`);
        if (skipped) toast("bad", "Unsupported files", `${skipped} file${skipped > 1 ? "s" : ""} skipped. Use PDF, DOCX, or TXT.`);
    }

    function renderFileList() {
        els.fileList.innerHTML = "";
        if (!state.files.length) return;

        state.files.forEach((f, idx) => {
            const ext = extOf(f.name) || "txt";
            const row = document.createElement("div");
            row.className = "file-card";
            row.innerHTML =
                `<div class="file-card-icon ${esc(ext)}" title="${esc(ext.toUpperCase())} file">${esc(ext.slice(0, 4))}</div>` +
                `<div class="file-card-body">
                    <div class="file-card-name" title="${esc(f.name)}">${esc(f.name)}</div>
                    <div class="file-card-meta">${fmtSize(f.size)}</div>
                </div>` +
                `<button class="file-card-remove" data-idx="${idx}" type="button" aria-label="Remove file" title="Remove">
                    <svg viewBox="0 0 14 14" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                        <path d="M3.5 3.5l7 7M10.5 3.5l-7 7"/>
                    </svg>
                </button>`;
            els.fileList.appendChild(row);
        });

        $$(".file-card-remove", els.fileList).forEach((btn) => {
            btn.addEventListener("click", (e) => {
                const i = parseInt(btn.getAttribute("data-idx"), 10);
                if (!Number.isNaN(i)) {
                    state.files.splice(i, 1);
                    renderFileList();
                    updateEmbedButton();
                }
            });
        });
    }

    function updateEmbedButton() {
        const n = state.files.length;
        els.embedBtn.disabled = n === 0;
        els.embedBtnText.textContent = n ? `Index ${n} file${n > 1 ? "s" : ""}` : "Index documents";
    }

    /* Dropzone events */

    els.uploadArea.addEventListener("click", (e) => {
        if (e.target.closest("input")) return;
        els.fileInput.click();
    });
    els.uploadArea.addEventListener("keydown", (e) => {
        if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            els.fileInput.click();
        }
    });
    els.uploadArea.addEventListener("dragover", (e) => {
        e.preventDefault();
        els.uploadArea.classList.add("dragover");
    });
    els.uploadArea.addEventListener("dragleave", () => els.uploadArea.classList.remove("dragover"));
    els.uploadArea.addEventListener("drop", (e) => {
        e.preventDefault();
        els.uploadArea.classList.remove("dragover");
        if (e.dataTransfer?.files?.length) addFiles(e.dataTransfer.files);
    });
    els.fileInput.addEventListener("change", (e) => {
        if (e.target.files?.length) addFiles(e.target.files);
        e.target.value = "";
    });

    /* -------------------- Embed / Index -------------------- */

    els.embedBtn.addEventListener("click", async () => {
        if (!state.files.length) return;

        els.embedBtn.disabled = true;
        els.embedSpinner.classList.add("is-spinning");
        els.embedBtnText.textContent = "Indexing…";

        const fd = new FormData();
        state.files.forEach((f) => fd.append("files", f));

        try {
            const r = await fetch("/embed", { method: "POST", body: fd });
            const data = await r.json().catch(() => ({}));
            renderSummary(data);

            if (data.status === "success" || data.status === "partial_success") {
                state.totals.docs += data.processed_files || 0;
                state.totals.vectors += data.total_chunks || 0;
                updateStats();
                toast(
                    "good",
                    data.status === "success" ? "Indexing complete" : "Partial success",
                    `${data.processed_files}/${data.total_files} files · ${data.total_chunks} chunks stored`
                );
            } else {
                toast("bad", "Indexing failed", "No documents were indexed.");
            }
        } catch (err) {
            console.error(err);
            renderSummary({ status: "failed", message: "Could not reach the server." });
            toast("bad", "Request failed", "Is the API server running?");
        } finally {
            state.files.length = 0;
            renderFileList();
            els.embedSpinner.classList.remove("is-spinning");
            updateEmbedButton();
        }
    });

    function renderSummary(data) {
        if (!data || !data.status) {
            els.embedResult.className = "summary";
            els.embedResult.innerHTML = "";
            return;
        }
        const kind = data.status === "success" ? "ok" : data.status === "partial_success" ? "warn" : "bad";
        const icon = kind === "ok" ? "✓" : kind === "warn" ? "!" : "✕";
        const filesHtml = (data.files || [])
            .map((f) => {
                const ok = f.status === "success";
                const statusText = ok ? `${f.chunks_created} chunks` : (f.error || "Failed");
                return (
                    `<div class="summary-file">
                        <span class="summary-file-name" title="${esc(f.filename)}">${esc(f.filename)}</span>
                        <span class="summary-file-status ${ok ? "ok" : "bad"}">
                            <span class="dot ${ok ? "ok" : "bad"}"></span> ${esc(statusText)}
                        </span>
                    </div>`
                );
            })
            .join("");

        els.embedResult.className = `summary summary-${kind} is-visible`;
        els.embedResult.innerHTML =
            `<div class="summary-head"><span style="font-size:15px">${icon}</span><span>${esc(data.message || "")}</span></div>` +
            `<div class="summary-stats">
                <div class="summary-stat"><b>${esc(String((data.processed_files || 0) + "/" + (data.total_files || 0)))}</b><span>Files</span></div>
                <div class="summary-stat"><b>${esc(String(data.total_chunks || 0))}</b><span>Chunks</span></div>
                <div class="summary-stat"><b>${esc(String(data.total_embeddings || 0))}</b><span>Vectors</span></div>
            </div>` +
            `<div class="summary-files">${filesHtml}</div>`;
    }

    /* -------------------- Chat -------------------- */

    function ensureThreadWrap() {
        if (!els.stream.querySelector(".thread")) {
            const w = document.createElement("div");
            w.className = "thread";
            els.stream.appendChild(w);
        }
        return $(".thread", els.stream);
    }

    function showWelcome(show) {
        if (show) {
            els.stream.innerHTML = "";
            els.stream.appendChild(els.emptyChat);
            els.emptyChat.style.display = "";
        } else {
            if (els.emptyChat.parentNode) els.emptyChat.remove();
            ensureThreadWrap();
        }
    }

    function appendMessage(role, text, extra = {}) {
        showWelcome(false);
        const wrap = ensureThreadWrap();
        const me = role === "user";

        const initials = me ? "You" : "AI";
        const now = new Date();
        const hh = String(now.getHours()).padStart(2, "0");
        const mm = String(now.getMinutes()).padStart(2, "0");

        const msg = document.createElement("div");
        msg.className = "msg " + (me ? "me" : "them");

        let bubbleInner = me ? escapeFormat(text) : escapeFormat(text);

        let metaExtras = "";
        if (!me && extra.usedLlm) {
            metaExtras = `<span class="badge-llm"><svg viewBox="0 0 12 12" width="10" height="10" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" style="display:inline-block"><path d="M2 9.5L4.5 7M10 2.5L7.5 5M4.5 5.5a2 2 0 102.83-2.83A2 2 0 004.5 5.5zM5 9a2 2 0 102.83 2.83A2 2 0 005 9z"/></svg> LLM</span>`;
        }

        let sources = "";
        if (!me && extra.sources && extra.sources.length) {
            const chips = extra.sources
                .map((src, i) => {
                    const s = extra.scores && extra.scores[i] != null ? Number(extra.scores[i]).toFixed(3) : "";
                    const short = src.length > 40 ? src.slice(0, 40) + "…" : src;
                    return (
                        `<span class="source-chip" title="${esc(src)}">
                            <svg viewBox="0 0 12 12" width="11" height="11" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M2.5 2.5h5.25L10 4.75V9.5a1 1 0 01-1 1h-5.5a1 1 0 01-1-1v-7a0 0 0 010 0z"/><path d="M7.75 2.5V4.5h2"/></svg>
                            <span style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:180px">${esc(short)}</span>
                            ${s ? `<b>${esc(s)}</b>` : ""}
                        </span>`
                    );
                })
                .join("");

            sources = `<div class="sources">
                <span class="sources-label">Referenced sources · ${extra.sources.length}</span>
                <div class="sources-list">${chips}</div>
            </div>`;
        }

        let chunks = "";
        if (!me && extra.chunks && extra.chunks.length) {
            const unique = Array.from(new Set(extra.chunks));
            const items = unique
                .map((c) => {
                    const snippet = c.length > 420 ? c.slice(0, 420) + "…" : c;
                    return `<div class="chunk-item">${esc(snippet)}</div>`;
                })
                .join("");
            chunks = `<div class="chunks-block">
                <button type="button" class="chunks-toggle" data-collapse>
                    <span>Retrieved passages · ${unique.length}</span>
                    <span class="chev">▾</span>
                </button>
                <div class="chunks-list">${items}</div>
            </div>`;
        }

        msg.innerHTML =
            `<div class="msg-avatar" title="${me ? "You" : "Assistant"}">${esc(initials)}</div>` +
            `<div class="msg-main">
                <div class="msg-meta"><span>${me ? "You" : "Assistant"}</span><span>·</span><span>${hh}:${mm}</span>${metaExtras ? `<span>·</span>` : ""}${metaExtras}</div>
                <div class="bubble">${bubbleInner}${sources}${chunks}</div>
            </div>`;

        wrap.appendChild(msg);
        els.stream.scrollTop = els.stream.scrollHeight;

        const toggle = msg.querySelector("[data-collapse]");
        if (toggle) {
            const list = toggle.nextElementSibling;
            toggle.addEventListener("click", () => {
                toggle.classList.toggle("is-open");
                if (list) list.classList.toggle("is-open");
            });
        }

        return msg;
    }

    function showTyping() {
        showWelcome(false);
        const wrap = ensureThreadWrap();
        const row = document.createElement("div");
        row.className = "msg them";
        row.id = "typing-" + Date.now();
        row.innerHTML =
            `<div class="msg-avatar" title="Assistant">AI</div>
            <div class="msg-main">
                <div class="msg-meta"><span>Assistant</span><span>·</span><span>Thinking…</span></div>
                <div class="typing">
                    <span class="typing-dots" aria-hidden="true"><i></i><i></i><i></i></span>
                    <span>Searching + drafting answer</span>
                </div>
            </div>`;
        wrap.appendChild(row);
        els.stream.scrollTop = els.stream.scrollHeight;
        return row.id;
    }

    function removeRow(id) {
        const r = document.getElementById(id);
        if (r) r.remove();
    }

    async function sendQuestion(q) {
        const question = (q || "").trim();
        if (!question) return;

        appendMessage("user", question);
        state.thread.push({ role: "user", content: question });
        els.chatInput.value = "";
        autoResize();

        const id = showTyping();
        try {
            const r = await fetch("/ask", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ question }),
            });
            removeRow(id);
            if (!r.ok) {
                const body = await r.json().catch(() => ({}));
                const err = body.detail || `HTTP ${r.status}`;
                appendMessage("assistant", "❌ " + err, { usedLlm: false });
                toast("bad", "Query failed", err);
                return;
            }
            const data = await r.json();
            appendMessage("assistant", data.answer || "", {
                sources: data.sources || [],
                scores: data.similarity_scores || [],
                chunks: data.retrieved_chunks || [],
                usedLlm: !!data.used_llm,
            });
            state.totals.queries++;
            updateStats();
        } catch (err) {
            console.error(err);
            removeRow(id);
            appendMessage("assistant", "❌ Network error. Could not reach the server.", { usedLlm: false });
            toast("bad", "Network error", "Check that the API server is running.");
        }
    }

    /* Textarea auto-resize + enter to send */

    function autoResize() {
        els.chatInput.style.height = "auto";
        els.chatInput.style.height = Math.min(els.chatInput.scrollHeight, 150) + "px";
    }

    els.chatInput.addEventListener("input", autoResize);
    els.chatInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            sendQuestion(els.chatInput.value);
        }
    });
    els.sendBtn.addEventListener("click", () => sendQuestion(els.chatInput.value));

    /* Prompt chips */

    $$(".prompt", els.emptyChat).forEach((chip) => {
        chip.addEventListener("click", () => {
            const q = chip.getAttribute("data-question");
            if (q) sendQuestion(q);
        });
    });

    /* Clear chat */

    els.clearBtn.addEventListener("click", () => {
        if (!state.thread.length && !els.stream.querySelector(".msg")) return;
        state.thread.length = 0;
        showWelcome(true);
        toast("info", "Conversation cleared", "Chat history has been removed.");
    });

    /* -------------------- Init -------------------- */

    updateStats();
    updateEmbedButton();
    autoResize();
})();
