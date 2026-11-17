"""web_human_review.py
Giao diện Web trực quan (chạy trên trình duyệt, không cần cài đặt thêm thư viện ngoài)
giúp người đánh giá thực hiện Bước 5: Human Quality Control dễ dàng và nhanh chóng nhất.

Cách chạy:
    python data_preparation/scripts/web_human_review.py
Sau đó mở trình duyệt tại:
    http://localhost:8080
"""

import http.server
import socketserver
import json
import urllib.parse
from pathlib import Path
import sys

PORT = 8080
PROJECT_ROOT = Path(__file__).resolve().parents[2]
HUMAN_DIR = PROJECT_ROOT / "data_preparation" / "human_review"
QUEUE_PATH = HUMAN_DIR / "review_queue.jsonl"
CORR_PATH = HUMAN_DIR / "human_corrections.jsonl"

def load_data():
    queue = [json.loads(line) for line in open(QUEUE_PATH, encoding="utf-8")]
    corrections = {}
    if CORR_PATH.exists():
        for line in open(CORR_PATH, encoding="utf-8"):
            try:
                r = json.loads(line)
                corrections[(r["paper_id"], r["facet"])] = r
            except Exception:
                pass
    return queue, corrections

def save_single_correction(record):
    queue, corrections = load_data()
    key = (record["paper_id"], record["facet"])
    corrections[key] = record

    # Ghi lại file
    with open(CORR_PATH, "w", encoding="utf-8") as f:
        for r in corrections.values():
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DS300 - Human Quality Control Review</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        .highlight-evidence { background-color: #fef08a; font-weight: 600; padding: 2px 4px; border-radius: 4px; border-left: 3px solid #eab308; }
        ::-webkit-scrollbar { width: 6px; }
        ::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 4px; }
    </style>
</head>
<body class="bg-slate-50 text-slate-800 h-screen flex flex-col font-sans">
    <!-- Navbar Header -->
    <header class="bg-slate-900 text-white px-6 py-3 flex items-center justify-between shadow-md flex-shrink-0">
        <div class="flex items-center space-x-3">
            <span class="bg-indigo-600 text-xs uppercase px-2 py-1 rounded font-bold tracking-wider">Step 5</span>
            <h1 class="text-lg font-bold">DS300 Human Quality Control Portal</h1>
            <span class="text-xs text-slate-400">Section 2.4 & 2.5 Specification</span>
        </div>
        <div class="flex items-center space-x-6 text-sm">
            <div id="statsBox" class="bg-slate-800 px-3 py-1.5 rounded-lg border border-slate-700">
                <span class="text-slate-400">Tiến độ:</span>
                <span id="reviewedCount" class="font-bold text-green-400">0</span> / <span id="totalCount">0</span>
                (<span id="percentCount" class="text-indigo-300 font-semibold">0%</span>)
            </div>
            <button onclick="triggerMerge()" class="bg-emerald-600 hover:bg-emerald-700 px-3 py-1.5 rounded text-xs font-semibold transition">
                ⚡ Cập nhật Validated Silver (Bước 6)
            </button>
        </div>
    </header>

    <!-- Main Layout -->
    <div class="flex-1 flex overflow-hidden">
        <!-- Sidebar Navigation -->
        <aside class="w-80 bg-white border-r border-slate-200 flex flex-col flex-shrink-0">
            <!-- Filter Toolbar -->
            <div class="p-3 border-b border-slate-200 space-y-2 bg-slate-50">
                <input id="searchInput" type="text" placeholder="Tìm Paper ID hoặc từ khóa..." 
                       class="w-full text-xs px-2.5 py-1.5 border border-slate-300 rounded focus:outline-none focus:border-indigo-500">
                
                <div class="flex space-x-1 text-xs">
                    <select id="filterType" class="flex-1 border border-slate-300 rounded px-2 py-1 bg-white focus:outline-none">
                        <option value="ALL">Tất cả trạng thái</option>
                        <option value="REJECTED">Chỉ REJECTED (2)</option>
                        <option value="NEEDS_REVIEW">Chỉ NEEDS_REVIEW</option>
                        <option value="AUTO_ACCEPT_QC_SAMPLE">Chỉ Mẫu QC Sample</option>
                        <option value="PENDING">Chỉ bản ghi chưa duyệt</option>
                        <option value="DONE">Chỉ bản ghi đã duyệt</option>
                    </select>
                    <select id="filterFacet" class="w-28 border border-slate-300 rounded px-2 py-1 bg-white focus:outline-none">
                        <option value="ALL">Mọi Facet</option>
                        <option value="problem">problem</option>
                        <option value="task">task</option>
                        <option value="method">method</option>
                        <option value="dataset">dataset</option>
                        <option value="contribution">contribution</option>
                    </select>
                </div>
            </div>

            <!-- Item List -->
            <div id="itemList" class="flex-1 overflow-y-auto divide-y divide-slate-100">
                <!-- Javascript will render items here -->
            </div>
        </aside>

        <!-- Right Content Details -->
        <main class="flex-1 overflow-y-auto p-6 flex flex-col space-y-5 bg-slate-100" id="mainContainer">
            <div id="loadingPlaceholder" class="text-center py-20 text-slate-400">Đang tải dữ liệu...</div>

            <!-- Detail Box (Hidden initially) -->
            <div id="detailView" class="hidden flex flex-col space-y-4 max-w-5xl mx-auto w-full">
                <!-- Header Card -->
                <div class="bg-white p-5 rounded-xl shadow-sm border border-slate-200">
                    <div class="flex items-center justify-between">
                        <div class="flex items-center space-x-3">
                            <span id="badgePaperId" class="text-sm font-mono font-bold bg-slate-900 text-white px-2.5 py-1 rounded"></span>
                            <span id="badgeFacet" class="text-xs uppercase font-extrabold bg-indigo-100 text-indigo-700 px-2.5 py-1 rounded"></span>
                            <span id="badgeAuditDec" class="text-xs font-semibold px-2 py-0.5 rounded"></span>
                        </div>
                        <div class="flex space-x-2">
                            <button onclick="navigate(-1)" class="px-3 py-1 bg-slate-100 hover:bg-slate-200 rounded text-xs font-medium">← Trước</button>
                            <button onclick="navigate(1)" class="px-3 py-1 bg-slate-100 hover:bg-slate-200 rounded text-xs font-medium">Tiếp →</button>
                        </div>
                    </div>
                    <h2 id="paperTitle" class="text-lg font-bold mt-3 text-slate-900 leading-snug"></h2>
                </div>

                <!-- Abstract & Evidence Card -->
                <div class="bg-white p-5 rounded-xl shadow-sm border border-slate-200">
                    <h3 class="text-xs uppercase font-bold tracking-wider text-slate-500 mb-2">Abstract & Bằng chứng nguồn (Source Evidence)</h3>
                    <div id="paperAbstract" class="text-sm text-slate-700 leading-relaxed font-serif bg-slate-50 p-4 rounded-lg border border-slate-200"></div>
                </div>

                <!-- Comparison & Audit Analysis Grid -->
                <div class="grid grid-cols-2 gap-4">
                    <!-- Current Silver Concepts -->
                    <div class="bg-white p-4 rounded-xl shadow-sm border border-slate-200 flex flex-col justify-between">
                        <div>
                            <span class="text-xs uppercase font-bold text-slate-500">Silver Facet hiện tại (Extractor)</span>
                            <div id="currentConcepts" class="mt-2 text-base font-semibold text-slate-800"></div>
                        </div>
                        <div class="mt-4 pt-3 border-t border-slate-100 text-xs text-slate-500" id="evidenceInfo"></div>
                    </div>

                    <!-- Qwen Semantic Audit Analysis -->
                    <div class="bg-white p-4 rounded-xl shadow-sm border border-slate-200 flex flex-col justify-between">
                        <div>
                            <div class="flex items-center justify-between">
                                <span class="text-xs uppercase font-bold text-slate-500">Đánh giá từ Qwen3-4B Semantic Audit</span>
                                <span id="qwenStatusBadge" class="text-xs font-bold px-2 py-0.5 rounded"></span>
                            </div>
                            <div class="mt-2 text-xs text-slate-600 space-y-1">
                                <div><strong class="text-slate-700">Cảnh báo lỗi:</strong> <span id="qwenIssues" class="text-amber-600 font-medium"></span></div>
                                <div><strong class="text-slate-700">Giải thích:</strong> <span id="qwenExplanation"></span></div>
                            </div>
                            <div class="mt-3 p-2 bg-indigo-50 border border-indigo-100 rounded text-xs" id="qwenRevisionBox">
                                <span class="font-bold text-indigo-700">Đề xuất sửa của Qwen:</span>
                                <span id="qwenProposedText" class="font-semibold text-indigo-900 ml-1"></span>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Decision Action Panel -->
                <div class="bg-white p-5 rounded-xl shadow-md border-2 border-indigo-200">
                    <div class="flex items-center justify-between mb-3">
                        <h4 class="text-sm font-bold text-slate-800">Quyết định của Người duyệt (Human Quality Control)</h4>
                        <span id="currentDecisionStatus" class="text-xs font-semibold px-2 py-0.5 rounded bg-slate-100"></span>
                    </div>

                    <div class="grid grid-cols-4 gap-3 mb-4">
                        <!-- Option 1: Accept -->
                        <button onclick="submitDecision('ACCEPT')" class="flex flex-col items-center justify-center p-3 rounded-lg border-2 border-emerald-500 bg-emerald-50 hover:bg-emerald-100 transition group text-left">
                            <span class="text-sm font-bold text-emerald-800 flex items-center space-x-1">
                                <span>✔ ACCEPT</span> <span class="text-xs opacity-60 font-mono">[1/A]</span>
                            </span>
                            <span class="text-xs text-emerald-600 mt-1 text-center">Chấp nhận Silver Facet hiện tại</span>
                        </button>

                        <!-- Option 2: Reject -->
                        <button onclick="submitDecision('REJECT')" class="flex flex-col items-center justify-center p-3 rounded-lg border-2 border-rose-500 bg-rose-50 hover:bg-rose-100 transition group text-left">
                            <span class="text-sm font-bold text-rose-800 flex items-center space-x-1">
                                <span>✖ REJECT</span> <span class="text-xs opacity-60 font-mono">[2/R]</span>
                            </span>
                            <span class="text-xs text-rose-600 mt-1 text-center">Bác bỏ (Hallucination / Sai lệch)</span>
                        </button>

                        <!-- Option 3: Accept Qwen Revision -->
                        <button id="btnQwenRevision" onclick="submitDecision('USE_QWEN')" class="flex flex-col items-center justify-center p-3 rounded-lg border-2 border-indigo-500 bg-indigo-50 hover:bg-indigo-100 transition group text-left">
                            <span class="text-sm font-bold text-indigo-800 flex items-center space-x-1">
                                <span>✨ Lấy đề xuất Qwen</span> <span class="text-xs opacity-60 font-mono">[3/Q]</span>
                            </span>
                            <span class="text-xs text-indigo-600 mt-1 text-center truncate w-full px-1" id="btnQwenSubtext">Áp dụng nội dung Qwen gợi ý</span>
                        </button>

                        <!-- Option 4: Custom Edit -->
                        <button onclick="focusCustomEdit()" class="flex flex-col items-center justify-center p-3 rounded-lg border-2 border-amber-500 bg-amber-50 hover:bg-amber-100 transition group text-left">
                            <span class="text-sm font-bold text-amber-800 flex items-center space-x-1">
                                <span>✏ Tự sửa nội dung</span> <span class="text-xs opacity-60 font-mono">[4/E]</span>
                            </span>
                            <span class="text-xs text-amber-600 mt-1 text-center">Nhập thủ công cụm từ chính xác</span>
                        </button>
                    </div>

                    <!-- Custom Edit Input -->
                    <div id="customEditBox" class="p-3 bg-amber-50 border border-amber-200 rounded-lg space-y-2 mb-3">
                        <label class="text-xs font-bold text-amber-900">Nội dung Facet sửa lại (phân cách nhiều concept bằng dấu phẩy):</label>
                        <div class="flex space-x-2">
                            <input id="customFacetInput" type="text" class="flex-1 text-sm px-3 py-1.5 border border-amber-300 rounded focus:outline-none focus:ring-1 focus:ring-amber-500" placeholder="VD: Text classification, Named entity recognition">
                            <button onclick="submitDecision('REVISE')" class="bg-amber-600 hover:bg-amber-700 text-white text-xs font-bold px-4 py-1.5 rounded">Lưu bản sửa</button>
                        </div>
                    </div>

                    <!-- Reviewer Notes -->
                    <div class="flex items-center space-x-2 text-xs">
                        <label class="font-medium text-slate-500">Ghi chú (tùy chọn):</label>
                        <input id="noteInput" type="text" placeholder="Lý do điều chỉnh hoặc phát hiện đặc biệt..." class="flex-1 px-2.5 py-1 border border-slate-300 rounded text-xs focus:outline-none focus:border-indigo-400">
                    </div>
                </div>
            </div>
        </main>
    </div>

    <!-- Script Application Logic -->
    <script>
        let allItems = [];
        let corrections = {};
        let filteredIndices = [];
        let currentIndex = 0;

        async function init() {
            try {
                const res = await fetch('/api/data');
                const data = await res.json();
                allItems = data.queue;
                corrections = data.corrections;
                applyFilters();
                updateStats();
                if (filteredIndices.length > 0) {
                    selectIndex(filteredIndices[0]);
                }
            } catch (err) {
                alert("Lỗi tải dữ liệu: " + err);
            }
        }

        function updateStats() {
            const total = allItems.length;
            let reviewed = 0;
            for (let item of allItems) {
                const key = item.paper_id + "_" + item.facet;
                if (corrections[key] && corrections[key].human_decision !== "PENDING") {
                    reviewed++;
                }
            }
            document.getElementById('reviewedCount').innerText = reviewed;
            document.getElementById('totalCount').innerText = total;
            document.getElementById('percentCount').innerText = total > 0 ? (reviewed / total * 100).toFixed(1) + '%' : '0%';
        }

        function applyFilters() {
            const search = document.getElementById('searchInput').value.trim().toLowerCase();
            const filterType = document.getElementById('filterType').value;
            const filterFacet = document.getElementById('filterFacet').value;

            filteredIndices = [];
            for (let i = 0; i < allItems.length; i++) {
                const item = allItems[i];
                const key = item.paper_id + "_" + item.facet;
                const corr = corrections[key] || { human_decision: "PENDING" };

                if (filterFacet !== "ALL" && item.facet !== filterFacet) continue;

                if (filterType === "REJECTED" && item.audit_decision !== "REJECTED") continue;
                if (filterType === "NEEDS_REVIEW" && item.audit_decision !== "NEEDS_REVIEW") continue;
                if (filterType === "AUTO_ACCEPT_QC_SAMPLE" && item.audit_decision !== "AUTO_ACCEPT_QC_SAMPLE") continue;
                if (filterType === "PENDING" && corr.human_decision !== "PENDING") continue;
                if (filterType === "DONE" && corr.human_decision === "PENDING") continue;

                if (search) {
                    const matchPid = item.paper_id.toLowerCase().includes(search);
                    const matchTitle = (item.title || "").toLowerCase().includes(search);
                    const matchConcepts = (item.current_concepts || []).join(" ").toLowerCase().includes(search);
                    if (!matchPid && !matchTitle && !matchConcepts) continue;
                }

                filteredIndices.push(i);
            }

            renderItemList();
            if (filteredIndices.length > 0) {
                if (!filteredIndices.includes(currentIndex)) {
                    selectIndex(filteredIndices[0]);
                }
            } else {
                document.getElementById('detailView').classList.add('hidden');
                document.getElementById('loadingPlaceholder').innerText = 'Không có mục nào khớp với bộ lọc.';
                document.getElementById('loadingPlaceholder').classList.remove('hidden');
            }
        }

        function renderItemList() {
            const listContainer = document.getElementById('itemList');
            listContainer.innerHTML = '';

            filteredIndices.forEach(idx => {
                const item = allItems[idx];
                const key = item.paper_id + "_" + item.facet;
                const corr = corrections[key] || { human_decision: "PENDING" };
                const isSelected = idx === currentIndex;

                const row = document.createElement('div');
                row.className = `p-3 cursor-pointer text-xs transition border-l-4 ${isSelected ? 'bg-indigo-50 border-indigo-600' : 'hover:bg-slate-50 border-transparent'}`;
                row.onclick = () => selectIndex(idx);

                let badgeColor = "bg-slate-200 text-slate-700";
                if (item.audit_decision === "REJECTED") badgeColor = "bg-red-100 text-red-700 font-bold";
                else if (item.audit_decision === "NEEDS_REVIEW") badgeColor = "bg-amber-100 text-amber-700 font-bold";
                else if (item.audit_decision === "AUTO_ACCEPT_QC_SAMPLE") badgeColor = "bg-blue-100 text-blue-700";

                let statusIcon = corr.human_decision === "PENDING" ? '<span class="text-slate-400">⏳</span>' : '<span class="text-emerald-600 font-bold">✔ ' + corr.human_decision + '</span>';

                row.innerHTML = `
                    <div class="flex items-center justify-between mb-1">
                        <span class="font-mono font-bold text-slate-800">${item.paper_id}</span>
                        <span class="text-[10px] uppercase px-1.5 py-0.5 rounded ${badgeColor}">${item.audit_decision}</span>
                    </div>
                    <div class="font-semibold text-slate-700 truncate">${item.facet.toUpperCase()}: ${(item.current_concepts || []).join(', ')}</div>
                    <div class="flex items-center justify-between mt-1 text-[11px] text-slate-500">
                        <span class="truncate max-w-[140px]">${item.title}</span>
                        ${statusIcon}
                    </div>
                `;
                listContainer.appendChild(row);
            });
        }

        function selectIndex(idx) {
            currentIndex = idx;
            renderItemList();
            displayDetail(allItems[idx]);
        }

        function displayDetail(item) {
            document.getElementById('loadingPlaceholder').classList.add('hidden');
            const view = document.getElementById('detailView');
            view.classList.remove('hidden');

            const key = item.paper_id + "_" + item.facet;
            const corr = corrections[key] || { human_decision: "PENDING", human_revised_facet: item.current_concepts, human_notes: "" };

            document.getElementById('badgePaperId').innerText = item.paper_id;
            document.getElementById('badgeFacet').innerText = item.facet;
            
            const badgeAudit = document.getElementById('badgeAuditDec');
            badgeAudit.innerText = item.audit_decision;
            if (item.audit_decision === "REJECTED") {
                badgeAudit.className = "text-xs font-semibold px-2 py-0.5 rounded bg-rose-100 text-rose-700";
            } else if (item.audit_decision === "NEEDS_REVIEW") {
                badgeAudit.className = "text-xs font-semibold px-2 py-0.5 rounded bg-amber-100 text-amber-700";
            } else {
                badgeAudit.className = "text-xs font-semibold px-2 py-0.5 rounded bg-blue-100 text-blue-700";
            }

            document.getElementById('paperTitle').innerText = item.title;

            // Highlight evidence sentence in abstract
            let absHtml = item.abstract || item.abstract_snippet || "";
            const evTexts = item.evidence_texts || [];
            if (evTexts.length > 0) {
                evTexts.forEach(ev => {
                    if (ev && absHtml.includes(ev)) {
                        absHtml = absHtml.replace(ev, `<span class="highlight-evidence">${ev}</span>`);
                    }
                });
            }
            document.getElementById('paperAbstract').innerHTML = absHtml;

            // Concepts
            const concepts = item.current_concepts || [];
            document.getElementById('currentConcepts').innerHTML = concepts.length > 0 
                ? concepts.map(c => `<span class="inline-block bg-slate-100 border border-slate-300 px-2 py-1 rounded mr-1 text-sm font-medium">${c}</span>`).join(' ')
                : '<span class="italic text-slate-400">Không có concept (rỗng)</span>';

            document.getElementById('evidenceInfo').innerHTML = evTexts.length > 0 
                ? `<strong>Bằng chứng MiniLM:</strong> Tìm thấy ${evTexts.length} câu hỗ trợ.`
                : `<strong class="text-rose-600">MiniLM Warning:</strong> Độ tương đồng thấp (&lt; 0.35), không có câu bằng chứng rõ ràng.`;

            // Qwen
            const qStatus = document.getElementById('qwenStatusBadge');
            qStatus.innerText = item.qwen_support_status || "N/A";
            if (item.qwen_support_status === "SUPPORTED") qStatus.className = "text-xs font-bold px-2 py-0.5 rounded bg-emerald-100 text-emerald-700";
            else if (item.qwen_support_status === "PARTIALLY_SUPPORTED") qStatus.className = "text-xs font-bold px-2 py-0.5 rounded bg-amber-100 text-amber-700";
            else qStatus.className = "text-xs font-bold px-2 py-0.5 rounded bg-rose-100 text-rose-700";

            document.getElementById('qwenIssues').innerText = item.qwen_detected_issues || "Không";
            document.getElementById('qwenExplanation').innerText = item.qwen_explanation || "Không có giải thích chi tiết.";

            const qRevBox = document.getElementById('qwenRevisionBox');
            const btnQwen = document.getElementById('btnQwenRevision');
            if (item.qwen_proposed_revision) {
                qRevBox.classList.remove('hidden');
                document.getElementById('qwenProposedText').innerText = item.qwen_proposed_revision;
                btnQwen.classList.remove('opacity-50', 'pointer-events-none');
                document.getElementById('btnQwenSubtext').innerText = item.qwen_proposed_revision;
            } else {
                qRevBox.classList.add('hidden');
                btnQwen.classList.add('opacity-50', 'pointer-events-none');
                document.getElementById('btnQwenSubtext').innerText = 'Không có đề xuất';
            }

            // Current Decision
            const decStatus = document.getElementById('currentDecisionStatus');
            decStatus.innerText = "Trạng thái: " + corr.human_decision;
            if (corr.human_decision === "ACCEPT") decStatus.className = "text-xs font-bold px-2.5 py-0.5 rounded bg-emerald-100 text-emerald-700";
            else if (corr.human_decision === "REJECT") decStatus.className = "text-xs font-bold px-2.5 py-0.5 rounded bg-rose-100 text-rose-700";
            else if (corr.human_decision === "REVISE") decStatus.className = "text-xs font-bold px-2.5 py-0.5 rounded bg-indigo-100 text-indigo-700";
            else decStatus.className = "text-xs font-semibold px-2.5 py-0.5 rounded bg-slate-100 text-slate-500";

            document.getElementById('noteInput').value = corr.human_notes || "";
            const revFacets = Array.isArray(corr.human_revised_facet) ? corr.human_revised_facet.join(", ") : (corr.human_revised_facet || "");
            document.getElementById('customFacetInput').value = revFacets || (item.qwen_proposed_revision || (item.current_concepts || []).join(", "));
        }

        async function submitDecision(action) {
            const item = allItems[currentIndex];
            const key = item.paper_id + "_" + item.facet;
            const note = document.getElementById('noteInput').value.trim();

            let decision = action;
            let revised = item.current_concepts;

            if (action === 'ACCEPT') {
                decision = 'ACCEPT';
                revised = item.current_concepts;
            } else if (action === 'REJECT') {
                decision = 'REJECT';
                revised = [];
            } else if (action === 'USE_QWEN') {
                decision = 'REVISE';
                revised = [item.qwen_proposed_revision];
            } else if (action === 'REVISE') {
                decision = 'REVISE';
                const text = document.getElementById('customFacetInput').value.trim();
                revised = text.split(',').map(s => s.trim()).filter(s => s.length > 0);
            }

            const payload = {
                paper_id: item.paper_id,
                facet: item.facet,
                human_decision: decision,
                human_revised_facet: revised,
                human_notes: note
            };

            corrections[key] = payload;
            updateStats();
            renderItemList();
            displayDetail(item);

            // Send to backend
            try {
                await fetch('/api/save', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
            } catch (err) {
                console.error("Save error:", err);
            }

            // Tự động nhảy sang mục tiếp theo
            navigate(1);
        }

        function focusCustomEdit() {
            document.getElementById('customFacetInput').focus();
        }

        function navigate(dir) {
            const curPos = filteredIndices.indexOf(currentIndex);
            if (curPos !== -1) {
                const nextPos = curPos + dir;
                if (nextPos >= 0 && nextPos < filteredIndices.length) {
                    selectIndex(filteredIndices[nextPos]);
                }
            }
        }

        // Bắt phím tắt
        window.addEventListener('keydown', (e) => {
            if (['input', 'textarea', 'select'].includes(document.activeElement.tagName.toLowerCase())) {
                if (e.key === 'Enter' && document.activeElement.id === 'customFacetInput') {
                    submitDecision('REVISE');
                }
                return;
            }

            if (e.key === '1' || e.key.toLowerCase() === 'a') submitDecision('ACCEPT');
            else if (e.key === '2' || e.key.toLowerCase() === 'r') submitDecision('REJECT');
            else if (e.key === '3' || e.key.toLowerCase() === 'q') submitDecision('USE_QWEN');
            else if (e.key === '4' || e.key.toLowerCase() === 'e') focusCustomEdit();
            else if (e.key === 'ArrowRight' || e.key.toLowerCase() === 's') navigate(1);
            else if (e.key === 'ArrowLeft' || e.key.toLowerCase() === 'p') navigate(-1);
        });

        document.getElementById('searchInput').addEventListener('input', applyFilters);
        document.getElementById('filterType').addEventListener('change', applyFilters);
        document.getElementById('filterFacet').addEventListener('change', applyFilters);

        async function triggerMerge() {
            if (!confirm("Bạn có muốn chạy ngay script Merge Bước 6 (08_merge_validated_silver.py) để áp dụng các quyết định con người vào Validated Silver không?")) return;
            const res = await fetch('/api/merge', { method: 'POST' });
            const data = await res.json();
            alert(data.message || "Đã gửi yêu cầu chạy Merge!");
        }

        init();
    </script>
</body>
</html>
"""

class ReviewRequestHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/" or parsed.path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_TEMPLATE.encode("utf-8"))
        elif parsed.path == "/api/data":
            queue, corrections = load_data()
            corr_map = {f"{r['paper_id']}_{r['facet']}": r for r in corrections.values()}
            response_data = {
                "queue": queue,
                "corrections": corr_map
            }
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps(response_data, ensure_ascii=False).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/save":
            content_length = int(self.headers.get("Content-Length", 0))
            post_body = self.rfile.read(content_length)
            record = json.loads(post_body.decode("utf-8"))
            save_single_correction(record)

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "success"}).encode("utf-8"))

        elif parsed.path == "/api/merge":
            # Chạy merge script
            import subprocess
            cmd = [sys.executable, str(PROJECT_ROOT / "data_preparation" / "scripts" / "08_merge_validated_silver.py")]
            res = subprocess.run(cmd, capture_output=True, text=True)
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps({
                "status": "success" if res.returncode == 0 else "error",
                "message": "Hợp nhất hoàn tất! Validated Silver đã được cập nhật." if res.returncode == 0 else res.stderr
            }, ensure_ascii=False).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        # Tắt bớt log rác
        pass

def main():
    with socketserver.TCPServer(("", PORT), ReviewRequestHandler) as httpd:
        print("="*75)
        print("🚀 CỔNG DUYỆT HUMAN QUALITY CONTROL (WEB GUI) ĐÃ SẴN SÀNG!")
        print("="*75)
        print(f"👉 Mở trình duyệt web của bạn và truy cập: http://localhost:{PORT}")
        print("   - Đầy đủ thông tin: Title, Abstract highlight bằng chứng, Qwen analysis")
        print("   - Thao tác 1-click hoặc bấm phím tắt: [1]/[A] Accept, [2]/[R] Reject, [3]/[Q] Qwen, [4]/[E] Edit")
        print("   - Tiến độ tự động lưu ngay lập tức vào human_corrections.jsonl")
        print("   - Nhấn Ctrl + C tại đây để dừng server khi hoàn thành.")
        print("="*75 + "\n")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nĐã dừng Web Server. Chúc bạn một ngày làm việc hiệu quả!")

if __name__ == "__main__":
    main()
