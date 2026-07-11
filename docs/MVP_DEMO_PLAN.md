# Clario — MVP Investor-Ready Battle Plan (tối nay → demo ngày mai)

*Product-lead, 2026-07-12. Nguồn sự thật DUY NHẤT cho đêm nay. Thay cho mọi prompt lẻ trước đó.*
*Bổ trợ: bối cảnh audit + research đầy đủ ở `AGENT_CONSOLIDATION_v1.md`.*

---

## 0. Nguyên tắc chỉ đạo (đọc trước khi mở Cursor)
1. **De-risk đường demo, không thêm tích hợp mong manh.** Deadline ngày mai + tôi không chạy verify hộ được → mọi thay đổi phải tự chứa, có fallback, không đụng data path đang chạy ngon.
2. **Scope freeze.** Chỉ làm mục "MUST". "STRETCH" chỉ đụng nếu MUST đã xong và đã rehearse. "DEFER" tuyệt đối không đụng trước demo.
3. **Rehearse là bắt buộc.** Sau mỗi prompt, chạy checklist ở §4. Không có "chắc là chạy".
4. **"Agent thật" theo cách an toàn:** cái gì thật hoá được mà không rủi ro (on-chain exposure trên graph có sẵn) thì làm; cái gì cần tích hợp ngoài (OFAC feed, vendor) thì **gắn nhãn "simulated" trung thực** thay vì giả vờ — investor tinh sẽ hỏi, trung thực an toàn hơn.

---

## 1. Đường demo vàng (investor thấy gì — định nghĩa cái gì PHẢI chạy)
Kịch bản 5 nhịp, ~6 phút:
1. **Alert Queue → Demo Mode:** reset, tự triage ALT-3003, mở case ALT-3002 (Brooke). Investor thấy hàng đợi + số liệu.
2. **Case ALT-3002:** bấm Run Agent Workflow → xem **4 agent chạy live** (timeline streaming) → ESCALATE, kèm rationale + confidence. Mở tab **Connections Graph** thấy mixer/Tornado sáng lên. Thấy **SAR draft**.
3. **Submit transaction:** chọn scenario "Dính mixer" → Validate with agents → ESCALATE, mở case timeline mới.
4. **AML Copilot:** bind ALT-3002, hỏi "screening status / summarize risk" → trả lời có nội dung.
5. **Risk Insights + Analyst:** xem portfolio VASP (câu chuyện quy mô) + hỏi Analyst "high-KYT transactions by partner" → bảng + chart.

→ Mọi thứ trong 5 nhịp này là **MUST chạy**. Ngoài ra là phụ.

---

## 2. Quyết định scope

### MUST — làm tối nay (ưu tiên giá trị × an toàn)
| # | Việc | Vì sao | Rủi ro |
|---|---|---|---|
| M1 | **Rebrand LowTrans → Clario** (chỉ chuỗi hiển thị: header, logo "LT"→"CL"/logo, `<title>`, copy) | Thương hiệu chắp vá = mất điểm tín nhiệm ngay | Rất thấp (giữ nguyên key/event nội bộ) |
| M2 | **Fix Copilot chat** (off-by-one) | Nhịp 4 đang **hỏng**; investor sẽ thử chat | Thấp (frontend, cô lập) |
| M3 | **Verify SQLite ON + Analyst chạy** (không docker) | Nhịp 5 phụ thuộc DB; hiện có thể đã on, cần chắc | Thấp–trung (đổi nguồn dữ liệu nếu đang JSON) |
| M4 | **Financial Crime: bỏ "skip" + on-chain exposure thật** | Nhịp 2 là cao trào; agent phải nhìn "thật & đều" | Trung (tự chứa, trên graph có sẵn) |
| M5 | **Demo reliability + nhãn trung thực** (offline/error states; "Powered by Bedrock Nova"; "simulated connector") | Chống vỡ trên sân khấu + trung thực | Thấp |
| M6 | **Agents page trung thực** (fix routing click → đúng nơi; đồng bộ skill hiển thị = skill chạy thật) | Investor bấm quanh; hiện Financial Crime/Arbiter nhảy sang /cases + card liệt kê skill không thật sự chạy | Thấp–trung |
| **UX** | **Enterprise UI pass** (design tokens + kỷ luật màu, bảng queue dày dữ liệu, states, chrome) | UI hiện "startup"; investor enterprise cần nhìn "compliance-grade" | Trung — **frontend-only, chạy phiên Cursor SONG SONG, độc lập backend M3/M4** |

### STRETCH — chỉ nếu MUST xong & đã rehearse
- S1: **SAR narrative bằng LLM** (gated Bedrock, fallback template) — tăng độ "thật" nhịp 2.
- S2: **OFAC SDN subset đóng gói sẵn** (bundle ~50 tên nổi tiếng vào repo, fuzzy match, không gọi mạng) — "sanctions thật" an toàn qua đêm.

### DEFER — sau raise, KHÔNG đụng trước demo
Orchestrator routing có điều kiện · KYT score độc lập nâng cao · audit hash-chain · HITL theo ngưỡng confidence · tích hợp vendor sanctions/OSINT/KYB thật · nguồn chain-analytics thật · **dẹp dual JSON/DB path** · Postgres/pgvector · model-risk logging (FP/FN) · conditional autonomy.

> Ghi chú: "Phase 2 đúng-hướng-thật" tôi đề xuất trước đây phần lớn nằm ở DEFER — hợp lý, vì mục tiêu bây giờ là **MVP demo được**, không phải production-hardening. Sau khi gọi được vốn, ta lấy nguyên mục DEFER làm roadmap kỹ thuật.

---

## 3. Trình tự thực thi (prompt Cursor, theo thứ tự phụ thuộc)

> Làm tuần tự M1→M5. Sau MỖI prompt, chạy checklist §4 tương ứng rồi mới sang bước sau. Commit từng bước để rollback được.

### M1 — Rebrand (an toàn nhất, làm trước)
```
Rebrand "LowTrans" → "Clario" trên frontend, CHỈ đổi chuỗi hiển thị cho người dùng.
Có 19 occurrences trong 8 file dưới apps/web/src (AppShell.tsx, layout.tsx, page.tsx, copilot/page.tsx,
policy/page.tsx, cases/[id]/page.tsx, lib/api.ts, context/AgentFleetContext.tsx).
- Đổi tên hiển thị "LowTrans" → "Clario", logo chữ "LT" → "CL", document <title>, mọi copy nhìn thấy được.
- GIỮ NGUYÊN: localStorage key `lowtrans_role`, custom event `lowtrans-role-change`, biến env LOWTRANS_*,
  bất kỳ API path/field nào (để không vỡ). Chỉ đụng text hiển thị.
Nghiệm thu: rà toàn app không còn chữ "LowTrans" nào người dùng thấy; app vẫn build (`npm run build`),
role switch + case page vẫn chạy (event nội bộ không đổi tên).
```

### M2 — Fix Copilot chat (off-by-one)
```
File: apps/web/src/app/copilot/page.tsx, hàm `send`.
Bug: reply không bao giờ hiện (bong bóng xám rỗng). `assistantIdx.idx = h.length + 1` trong khi
placeholder nằm ở index h.length → cập nhật stream ghi vào index không tồn tại; backend luôn phát
event `meta` nên fallback non-stream không chạy → luôn rỗng.
Fix: bỏ theo dõi index; với mỗi event stream, cập nhật PHẦN TỬ CUỐI của history (placeholder assistant).
Token cộng dồn vào content; meta (skill_name, cards, visualization, type) merge vào bong bóng đó;
nhánh catch cập nhật chính bong bóng đó thành lỗi (hiện ev.message nếu có); xoá biến assistantIdx.
Nghiệm thu: gõ/bấm starter → user bubble → loading → reply stream vào; bind ALT-3002 +
"Screening status for this alert" → hiện skill_name + cards; API sập → bong bóng báo lỗi, không rỗng.
Không đổi backend / api.ts.
```

### M3 — Verify SQLite ON + Analyst (không docker)
```
Mục tiêu: chắc chắn app chạy SQLite mặc định (db/models.py đã hỗ trợ), Data Analyst hoạt động,
queue KHÔNG đổi so với hiện tại.
- Xác nhận init_db() chạy trong lifespan và USE_DB không bị đặt false; DATABASE_URL để trống →
  dùng sqlite:///data/lowtrans.db (tự tạo). Ghi vào .env.example + README.
- Xác nhận lifespan seed khi transactions rỗng (scripts/seed_db.py). Chạy `python scripts/seed_db.py`
  một lần cho chắc; in ra số alerts/cases/transactions.
- FIX: ingest.submit_transaction khi is_db_ready() phải INSERT thêm một TransactionRow cho giao dịch
  mới (map các field như seed_db), để Analyst thấy giao dịch vừa submit. (Hiện chỉ ghi AlertRow.)
- Data Analyst robustness (analyst.py): (a) truyền dialect đúng vào prompt/generate theo is_sqlite()
  (SQLite date syntax vs Postgres); (b) ép LIMIT 100 nếu SELECT thiếu LIMIT; (c) handle_analyst_nl_sql
  chỉ đọc ["visualization"] khi tồn tại, tránh KeyError; (d) sql_tools.run_sql trả thẳng dict của
  run_analyst_query (bỏ unpack "columns, rows = ...").
Nghiệm thu: khởi động API sạch (không docker) → is_db_ready()==true, is_sqlite()==true; queue vẫn đủ
ALT-3002/3003/3005/3010...; Analyst hỏi "high-KYT transactions by partner" → bảng + chart, không lỗi
"Postgres not connected"; submit 1 scenario rồi hỏi Analyst thấy giao dịch mới.
```

### M4 — Financial Crime: bỏ skip + on-chain exposure thật
```
File: apps/api/agent/supervisor.py (node_investigator) + agent/tools/graph_tools.py.
1) KHÔNG dùng status "skipped" cho OnChain_Graph_Analyzer và Behavioral Pattern Engine nữa — luôn emit
   "completed" với kết luận rõ ("No on-chain exposure to flagged entities" / "No behavioral pattern matched").
2) graph_tools: thêm compute_exposure(alert_id) đọc data/graphs/{id}.json, BFS từ node ví chính, tính:
   direct_exposure (tổng amount_usd cạnh trực tiếp tới node flagged/mixer/SDN/risk=high),
   indirect_exposure (>=2 hop, kèm min hop), và list đường hop tới từng node flagged.
   node_investigator emit điểm + hop path này thay cho summary chung chung.
Nghiệm thu: mở ALT-3002 (mixer) và một case sạch — cả hai đều thấy Financial Crime chạy ĐỦ bước, không
"skipped"; ALT-3002 hiện direct+indirect exposure + đường hop tới Tornado/cluster; case sạch hiện "no exposure".
Không đổi frontend timeline; chỉ dựa vào status/output đã emit.
```

### M5 — Reliability + nhãn trung thực
```
1) apps/web/src/components/shell/AppShell.tsx: trạng thái API disconnected hiện tại là chữ đỏ trông như
   lỗi — đổi thành banner trung tính "Demo/offline mode" khi mất API, không hù người xem.
2) Thêm nhãn nhỏ "Powered by Amazon Bedrock (Nova)" ở footer/health badge (dùng /api/health đã có).
3) Các bước/skill dùng dữ liệu mô phỏng (OSINT, KYB, UBO, Fiat-Bridge) gắn tag "simulated" rõ ràng trong
   output hiển thị. Trung thực với investor.
Nghiệm thu: tắt API → UI hiện chế độ demo có chủ đích, không màn đỏ; các bước mock có nhãn "simulated";
badge Bedrock hiển thị model đang dùng.
```

### M6 — Agents page: trung thực hoá (routing + đồng bộ skill)

Hai vấn đề trên trang Agents: (1) bấm card **Financial Crime / Arbiter nhảy sang `/cases`** vì `registry.yaml` đặt `workspace: /cases` và frontend ưu tiên `agent.workspace` (map `AGENT_WORKSPACE` ở frontend là dead code); không có "workspace" riêng cho agent. (2) Card **liệt kê skill không thật sự chạy trong triage** (policy-qa, analyst-nl-sql, rule-fire-rates, rule-build chỉ gọi qua Copilot).

**Bảng sự thật — skill chạy trong triage vs chỉ qua Copilot:**

| Agent | Chạy trong triage | Chỉ qua Copilot |
|---|---|---|
| Orchestrator | intake-parse, context-retrieve, rag-lookup, sla-priority | policy-qa |
| Entity Identity | sanctions-check, osint-research, kyb-verify, ubo-unroll, device-ip-check | — |
| Financial Crime | ml-validate, kyt-score, travel-rule-check, graph-summary *(conditional)*, behavioral-patterns, fiat-crypto-bridge | analyst-nl-sql, rule-fire-rates |
| Arbiter | confidence-score, sar-draft, audit-compile | rule-build |

```
Phần A — Fix routing (apps/web/src/app/agents/page.tsx + registry.yaml):
- Bấm mỗi agent card → deep-link tới case ALT-3002 ở tab minh hoạ agent đó:
  orchestrator → /cases/ALT-3002?tab=Timeline
  entity-identity → /cases/ALT-3002?tab=Overview
  financial-crime-investigator → /cases/ALT-3002?tab=Connections+Graph
  arbiter → /cases/ALT-3002?tab=Overview (SAR)
- Chọn MỘT nguồn sự thật cho link (registry.workspace HOẶC map frontend), bỏ cái còn lại (đang mâu thuẫn).
- Chỉ để link "Open workspace" bấm được, KHÔNG để cả card là <Link>.

Phần B — Đồng bộ skill (backend là nguồn sự thật):
- supervisor.py: canonical map node → skill_id thực thi (theo bảng trên); graph-summary = conditional.
- Mỗi bước emit gắn skill_id (WorkflowStep.skill_id đã có ở frontend).
- /api/skills: mỗi skill trả `mode`: "triage" | "copilot"; graph-summary thêm `conditional: true`.
  Suy ra từ canonical map — skill không nằm trong map = "copilot".
- agents/page.tsx: badge chip theo mode (triage = nhấn; copilot = mờ + "via Copilot");
  graph-summary nhãn "conditional"; dùng runningSkillId/completedSkillIds để chip SÁNG khi chạy.
  Chú thích: "triage = chạy mỗi điều tra · copilot = gọi theo yêu cầu". Không hardcode danh sách thứ 3.

Nghiệm thu:
- Bấm mỗi agent → đúng tab ALT-3002 minh hoạ agent đó; không nhảy /cases chung; bấm vùng trống không điều hướng.
- policy-qa / analyst-nl-sql / rule-fire-rates / rule-build hiện rõ "via Copilot".
- Chạy triage ALT-3002: chip skill "triage" sáng theo bước; graph-summary "conditional" sáng khi có mixer.
- /api/skills trả `mode` cho mọi skill; frontend chỉ đọc từ đó.
```

### UX — Enterprise UI pass (phiên Cursor SONG SONG, frontend-only)

**Chuẩn tham chiếu:** IBM Carbon (data-heavy + WCAG AA + bảng/chart), Salesforce Lightning (record page/form/table quy mô lớn), Ant Design (admin dày dữ liệu). Thứ khiến một UI "trông enterprise compliance" không phải màu mè — mà là **kỷ luật màu, mật độ dữ liệu, phân cấp thông tin, trạng thái đầy đủ, và khả năng truy cập**.

**Clario design tokens (mục tiêu):**
- **Kỷ luật màu:** bỏ indigo "startup" làm màu chủ đạo tràn lan. Chrome dùng **neutral (slate/zinc)**; MỘT accent tương tác kiềm chế (vd blue-700) dùng tiết chế. **Xanh/vàng/đỏ CHỈ dành cho ngữ nghĩa rủi ro** (clear/review/escalate) — không dùng cho nút/trang trí. Đây là tín hiệu "enterprise" lớn nhất.
- **Typography:** type scale rõ; **tabular-nums cho MỌI số** (KYT, amount, %); **monospace cho ID/wallet/tx hash** (đã có GeistMono).
- **Hình khối:** giảm bo góc `rounded-xl`→`rounded-md/lg`; ưu tiên **viền 1px + shadow-sm** thay vì đổ bóng nặng. Lưới 4/8pt.
- **Bảng dữ liệu (chuẩn):** sticky header, hàng gọn (~40px), **số căn phải**, ID monospace, cột **sortable** có chỉ báo, hover + selected row, empty state.
- **Trạng thái:** **skeleton** thay "Loading…"; empty state có icon + hướng dẫn + action; **toast** cho hành động (assign/note/override/triage); confirm dialog cho hành động phá huỷ.
- **Chrome:** left nav **có nhãn** (rail mở rộng được) nhóm theo chức năng; top bar có **breadcrumb + role switcher + badge môi trường "Demo" + global search (⌘K)**.
- **A11y (WCAG 2.1 AA):** tương phản ≥4.5:1, focus ring nhìn thấy, điều hướng bàn phím, `aria-label` cho nút chỉ-icon.

> **Thực tế deadline:** một design-system Carbon-grade là việc nhiều ngày. Qua đêm chỉ làm được **"visual polish đáng tin"**. Ưu tiên UX-1 → UX-2 → UX-3 (nhảy vọt "enterprise" lớn nhất); UX-4 nếu còn giờ. Chạy như **phiên Cursor riêng, chỉ đụng frontend**, song song backend. Nếu chỉ 1 người/1 Cursor: gộp **M1 (rebrand) + UX-1 (tokens)** làm chung (đều đụng shell), rồi M2→M3→M4, rồi UX-2/UX-3.

```
UX-1 — Design tokens + primitives (nền tảng, làm chung với M1 rebrand):
File: apps/web/tailwind.config.ts, src/app/globals.css, tạo src/components/ui/*.
- Định nghĩa token màu: chrome neutral (slate), 1 accent tương tác kiềm chế; giữ semantic
  risk (emerald/amber/red) CHỈ cho clear/review/escalate. Bỏ indigo tràn lan.
- Bật tabular-nums mặc định cho số; class .mono cho ID/wallet/hash.
- Chuẩn hoá radius (md/lg) + shadow-sm + viền 1px.
- Tạo primitive dùng chung: Badge (status/risk), Button (primary/secondary/tertiary/danger),
  Card, StatCard, SectionHeader. Refactor AppShell + trang chủ dùng primitive này.
Nghiệm thu: toàn app một ngôn ngữ hình ảnh nhất quán; màu semantic chỉ xuất hiện ở ngữ cảnh rủi ro;
build pass; không đổi logic.

UX-2 — Alert Queue thành enterprise data-table:
File: apps/web/src/app/page.tsx (+ component table dùng chung nếu tách được).
- Sticky header; hàng gọn; KYT/amount căn phải + tabular-nums; Alert ID/wallet monospace;
  cột sortable (KYT, amount, risk, created_at) có chỉ báo; hover + selected; risk badge dùng token;
  empty state khi lọc rỗng. Giữ nguyên filter hiện có.
Nghiệm thu: bảng scannable khi cuộn, header dính, số căn phải, sort chạy, không đổi API.

UX-3 — States (skeleton / empty / toast / error):
- Thay mọi "Loading..." (queue, case, insights, copilot) bằng skeleton.
- Empty state có hướng dẫn cho queue/insights/analyst.
- Toast cho assign/note/override/approve/triage (thành công + lỗi).
- Error boundary cho các trang chính.
Nghiệm thu: không còn text "Loading..."; hành động có phản hồi toast; trang lỗi không trắng.

UX-4 — Chrome (nếu còn giờ):
- Left nav có nhãn (rail mở rộng), nhóm chức năng; top bar: breadcrumb + role switcher +
  badge "Demo" + (tùy chọn) global search ⌘K. Focus ring + aria-label cho nút icon (WCAG AA).
Nghiệm thu: điều hướng rõ nhãn; role switcher + badge môi trường hiển thị; tab/keyboard đi hết được.
```

### STRETCH (chỉ khi dư giờ)
```
S1 (SAR LLM): supervisor.py node_arbiter/_draft_sar — khi ESCALATE và Bedrock is_configured(), sinh SAR
   bằng safe_invoke, prompt CHỈ dùng dữ liệu trong audit pack (cấm bịa), policy gate vẫn thắng (không đổi
   decision). Không Bedrock → giữ template. Nhãn "SAR_Generator (LLM)" vs "(template)".
S2 (OFAC subset): thêm data/ofac_sdn_sample.json (~50 tên SDN nổi tiếng, tĩnh, commit vào repo) +
   agent/domain/sanctions.py screen_ofac() fuzzy match; packs.screening_with_policy_overlay dùng nó làm
   nguồn "OFAC SDN (sample list)". KHÔNG gọi mạng. Nhãn rõ là sample.
```

---

## 4. Checklist rehearse (vì tôi không chạy verify được — bạn/Cursor phải chạy)
Sau khi xong M1–M5, chạy đúng đường demo vàng §1, kỳ vọng:
- [ ] Không còn chữ "LowTrans" nào; `npm run build` pass.
- [ ] Demo Mode: reset → triage ALT-3003 → mở ALT-3002 mượt, không lỗi console.
- [ ] ALT-3002: 4 agent chạy live → ESCALATE; Financial Crime chạy đủ bước (không "skipped"); exposure + hop hiện ra; tab Connections Graph sáng node mixer.
- [ ] Submit scenario "mixer" → ESCALATE; scenario "clean" → CLEAR.
- [ ] Copilot: hỏi có alert_id → có reply (stream), có skill_name; API sập → báo lỗi gọn.
- [ ] Analyst: "high-KYT transactions by partner" → bảng + chart; submit tx mới rồi hỏi lại thấy nó.
- [ ] Insights: portfolio VASP hiển thị.
- [ ] Agents (M6): bấm mỗi agent → đúng tab ALT-3002; skill "via Copilot" hiện rõ; không nhảy /cases chung.
- [ ] UX: màu semantic chỉ ở ngữ cảnh rủi ro; số căn phải + tabular-nums; không còn "Loading..."; bảng queue có sticky header + sort.
- [ ] Rollback: mỗi M/UX commit riêng; nếu gãy → revert đúng commit đó, demo vẫn chạy các phần còn lại.

**Nếu hết giờ:** bỏ dần từ dưới lên — S2, S1, UX-4, UX-3, M6, rồi M5 (chỉ giữ banner offline), rồi M4 (chấp nhận Financial Crime vẫn skip). **Không bao giờ bỏ M1–M3 và UX-1** (tokens/rebrand là bộ mặt enterprise cơ bản nhất).

---

## 5. Positioning một câu cho pitch
"Clario là **agent điều tra AML thật** cho crypto — 4 agent chạy end-to-end với tool thật (on-chain exposure, KYT, RAG precedent, ML scoring), **gate compliance deterministic không thể bị AI ghi đè**, audit trail đầy đủ, và người ra quyết định cuối. Cùng ngôn ngữ Unit21/Elliptic/Verafin đang dùng và đúng thứ regulator (SR 11-7, EU AI Act) đòi hỏi."

---

## 6. Cần bạn xác nhận (để tôi chốt/điều chỉnh)
1. **Đồng ý scope freeze M1–M5 + UX track, dời phần còn lại sau raise?**
2. Rebrand/logo: dùng logo chữ "CL" tạm, hay bạn có logo + màu thương hiệu Clario riêng để tôi đưa vào tokens (UX-1)?
3. **Hướng UI enterprise:** đi **neutral/Carbon-style** (xám chuyên nghiệp, 1 accent) — khuyến nghị; hay giữ tông xanh thương hiệu hiện tại nhưng siết kỷ luật?
4. Có **phiên Cursor thứ 2 chạy song song** cho UX không (khuyến nghị, vì UX-track độc lập backend)? Nếu chỉ 1, tôi sắp lại thứ tự xen kẽ như mục UX.
5. Mở STRETCH S1 (SAR LLM) không — cần Bedrock chạy lúc demo (Nova, hoặc đổi sang Claude).

---

## Sources (research UX + agentic AML)
- [Enterprise B2B dashboard UX (FlowmazeUX)](https://flowmazeux.com/saas-dashboard-design-best-practices/) · [Dashboard best practices (context.dev)](https://www.context.dev/blog/dashboard-design-best-practices) · [B2B SaaS UI/UX (Callin)](https://callin.io/best-ui-ux-practices-for-b2b-saas-platforms/)
- [IBM Carbon Design System](https://www.brilworks.com/blog/ibm-carbon-design-system/) · [Design system examples 2026 (UXPin)](https://www.uxpin.com/studio/blog/best-design-system-examples/)
- [AML investigation software UX (Tookitaki)](https://www.tookitaki.com/compliance-hub/aml-investigation-software) · [AML solution features (Unit21)](https://www.unit21.ai/blog/aml-software-solutions) · [AML analysis workspace (DataWalk)](https://datawalk.com/solutions/aml-software/)
```
