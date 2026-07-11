# Clario — Consolidate 4-Agent: Market Research, Code Audit & Upgrade Plan

*Product-lead advisory · 2026-07-12 · mục tiêu: demo vững + kiến trúc agent thật, mở rộng được.*

---

## 0. TL;DR (đọc cái này trước)

**Sự thật về code hiện tại:** luồng triage 4-agent **không có LLM trong vòng lặp**. Chỉ **2 thứ là "thật"**: RAG similarity (TF-IDF/Cohere) và ML score (sklearn GradientBoosting). Toàn bộ Sanctions / OSINT / KYB / UBO / Fiat-Bridge là **mock**; KYT / Travel-Rule / Device chỉ **echo lại field** chứ không tính toán. Quyết định 100% deterministic (ML + heuristic + policy gate).

**Vì sao Financial Crime "chạy khác":** không phải vì tool của nó bị stub còn Identity thì thật (cả hai phần lớn đều mock). Mà vì **Investigator có nhánh skip có điều kiện** (bước on-chain graph bị *gate*, behavioral báo *skipped* khi không match mẫu), còn Identity **không có gate nên luôn chạy đủ 5 bước**. Nhìn ra là "làm ít việc hơn".

**Thị trường đang đặt chuẩn ở đâu:** Unit21, Sardine, Elliptic (AI Copilot), Nasdaq Verafin, Lucinity, Napier đều đã chuyển sang **agentic AI + human-in-the-loop + audit-trail bắt buộc**. Chuẩn "agent thật" = LLM tool-calling điều tra end-to-end, **guardrail deterministic không cho LLM ghi đè**, escalation theo ngưỡng confidence, và **maker-checker** (người xác nhận SAR/EDD).

**3 nước đi ROI cao nhất để "thật hoá" (Phase 1):**
1. **Sanctions thật bằng danh sách OFAC SDN công khai (miễn phí)** — cú nâng độ tín nhiệm lớn nhất, chi phí gần bằng 0.
2. **On-chain exposure thật**: duyệt đồ thị tính phơi nhiễm trực tiếp + gián tiếp theo hop (đúng cách KYT thật hoạt động) — thay cho bước graph "skip".
3. **SAR narrative bằng LLM thật**, có grounding trên evidence + policy gate làm guardrail (đúng mô hình Co-Investigator AI / maker-checker).

Chi tiết + prompt Cursor ở phần 6–7.

---

## 1. Market landscape (có dẫn nguồn)

### 1.1 Crypto-native (KYT / blockchain analytics)
Chainalysis, Elliptic, TRM Labs là 3 dẫn đầu, định vị khác nhau: **Chainalysis** tối ưu chất lượng bằng chứng & khả năng ra toà; **Elliptic** mạnh cross-chain; **TRM** thiên tốc độ + tự động hoá cho khối lượng lớn. Thị trường blockchain analytics ~**$2.5B (2025) → ~$9.9B (2032)**. Cả ba đều đã gọi vốn lớn gần đây (Elliptic Series D $120M, TRM unicorn $1B).

**Cách KYT "thật" hoạt động** (điểm cực quan trọng cho Clario): ingest dữ liệu on-chain → **quy ví về thực thể (attribution)** → chấm điểm rủi ro theo **phơi nhiễm đối tác trực tiếp VÀ gián tiếp nhiều hop** (ví nhận tiền từ địa chỉ rủi ro cách 2 hop vẫn bị tính) → **rescoring liên tục** khi có dữ liệu attribution mới. Đây chính là thứ bước "OnChain_Graph_Analyzer" của Clario nên làm thật.

### 1.2 Agentic-AI compliance (case management)
- **Unit21** đã *xây lại toàn bộ nền tảng quanh AI agent* (5/2025), agent chạy **toàn vòng đời**: phát hiện → điều tra → soạn kết luận regulator-ready + audit trail đầy đủ; >100k review/tháng. Khách giảm 57–72% false positive.
- **Sardine**: agentic AML tự động hoá triage, tăng tốc điều tra, mọi bước audit-ready.
- **Nasdaq Verafin**: "agentic workforce" (7/2025) giảm >80% alert sàng lọc sanction.
- **Lucinity / Napier**: autonomous case resolution + agentic workflow.

Mẫu hình chung: **graduated autonomy** — triage thường lệ / làm giàu dữ liệu / clear false-positive hiển nhiên → **agent tự làm end-to-end**; **SAR & EDD → agent soạn, người xác nhận**; đóng tài khoản / báo cơ quan chức năng → **bắt buộc người quyết**. Kèm **maker-checker**.

### 1.3 Kỹ thuật multi-agent (LangGraph)
Mẫu **hierarchical supervisor**: một supervisor điều phối, **quyết định gọi agent nào theo ngữ cảnh** (không phải chạy tuyến tính cứng). Điểm kiểm soát tập trung giúp chặn "khuếch đại lỗi" (vd agent này approve trong khi agent kia block). Bắt buộc: **permission boundary, audit log, phòng prompt-injection**. → Clario đang dùng LangGraph nhưng **chạy tuyến tính hardcode**, chưa có routing/branching thật.

### 1.4 Kỳ vọng regulator (để agent "thật" và defensible)
- **SR 11-7 (Fed) đã mở rộng sang AI/agentic** (làm rõ 1/2026): yêu cầu **explainability, validation, giám sát FP/FN liên tục, validation độc lập**.
- **EU AI Act**: hệ thống compliance là **"high-risk"** → cần risk management, data governance, technical documentation, **human oversight**, conformity assessment.
- **FATF 2025**: siết Travel Rule (mở sang DeFi), beneficial ownership, real-time sanctions screening, giám sát AI-driven.
- Mô hình được khuyến nghị: **human-in-the-loop + audit trail bắt buộc + guardrail chống "bằng chứng ảo" + escalation khi confidence < ngưỡng**.

> Hệ quả cho Clario: "agent thật" không chỉ là "gọi LLM". Nó là **LLM điều tra + tool thật + gate deterministic không thể ghi đè + audit bất biến + người xác nhận**. Đây vừa là chuẩn thị trường vừa là chuẩn pháp lý — và là câu chuyện bán hàng mạnh nhất cho investor/khách VASP.

---

## 2. Code audit — hiện trạng thật (đã đọc code)

### 2.1 Hai "cỗ máy" tách rời, gần như không dùng chung gì
| | Case triage | AML Copilot |
|---|---|---|
| Entry | `run_workflow` → 4-node supervisor | `run_agent_loop` |
| Bản chất | 4 node **tuyến tính hardcode** (LangGraph chỉ bọc lại đúng 4 hàm đó) | **LLM Converse tool-calling** thật *khi* Bedrock cấu hình, không thì keyword fallback |
| Tool | gọi thẳng hàm domain, **không qua skill registry** | gọi **skills** qua `dispatch_skill` |
| "4 agent" | chỉ tồn tại ở đây | không có — chỉ 1 persona "Orchestrator Loop" |

→ Hai đường phân kỳ hoàn toàn ở tầng điều phối. Đây là **nợ kiến trúc gốc** cần hợp nhất.

### 2.2 Real vs Mock theo từng agent (luồng triage thực thi)
| Agent | Bước | Loại | Ghi chú |
|---|---|---|---|
| **Orchestrator** | Intake Parser | MOCK | chỉ format chuỗi |
| | Context Retriever + RAG | **REAL** | `rag_engine.find_similar` |
| | SLA & Priority | HEURISTIC | ngưỡng + ML |
| **Entity Identity** | Sanctions_API (OFAC/PEP) | **MOCK** | echo `alert.sanctions_screening`, connector mock |
| | OSINT_Search | MOCK | dữ liệu "(mock)" hardcode |
| | VASP_Registry_Lookup | MOCK | "registered (mock)" |
| | UBO Unroller | MOCK | cây giả (đã cho biến thiên) |
| | Device & IP | passthrough | đọc field, không tính |
| **Financial Crime** | ML Transaction Validator | **REAL** | sklearn GB (+ heuristic fallback) |
| | KYT + Travel Rule | MOCK | **echo field, không chấm điểm** |
| | OnChain_Graph_Analyzer | REAL-ish nhưng **GATED** | đọc `data/graphs/{id}.json`; **skip** nếu không mixer/‑connections>8/‑structuring |
| | Behavioral Pattern Engine | HEURISTIC | báo **skipped** khi không match |
| | Fiat-Crypto Bridge | MOCK | template |
| **Arbiter** | Confidence Scorer | HEURISTIC | ML + gate + RAG-precedent |
| | SAR_Generator | **MOCK** | f-string template, **không LLM** (dù label ngụ ý LLM) |
| | Audit Trail Compiler | HEURISTIC | dict, **chưa bất biến** |

### 2.3 LLM có thật trong vòng lặp?
- **Triage: KHÔNG.** Không chỗ nào gọi `invoke_claude/converse` trên đường triage. `bedrock_health(live=False)` chỉ để đóng dấu `model_id` vào audit — **không phải gọi model**.
- **Copilot: có điều kiện.** Chỉ khi Bedrock cấu hình; và trong skill, LLM chỉ **đánh bóng chữ**, luôn bọc `safe_invoke` + fallback tĩnh.
- Không có Bedrock → copilot chạy keyword fallback; analyst dùng SQL mock; RAG tụt về TF-IDF.

### 2.4 Registry (trang Agents) ≠ thực thi
Supervisor không đọc registry, nên skill "quảng cáo" lệch với bước chạy thật: Orchestrator không chạy `policy-qa`; Financial Crime **không chạy** `analyst-nl-sql`/`rule-fire-rates` trong triage; Arbiter không chạy `rule-build`; nhãn bước ≠ id skill (không join được UI với workflow).

### 2.5 Danh sách bug (gộp để fix một thể)
1. **Route trùng** `GET /api/cases/{case_id}` (main.py:506 và :870) → `get_resolved_case` là **dead code**; `/api/cases/{id}` luôn trúng handler rollup, resolved-case id bị 404.
2. `safe_invoke` **không bắt `Exception`** (bedrock.py:155) → lỗi lạ (timeout) sẽ làm vỡ skill thay vì rơi về fallback.
3. `route_intent` **thứ tự sai**: keyword như "mixer/exposure" route sang `analyst-nl-sql` **trước** khi kịp tới `graph-summary`/`sanctions-check` (cần alert_id, kiểm tra muộn).
4. `fiat-crypto-bridge` **không có trong `LOOP_SKILLS`** → LLM copilot không bao giờ gọi được (dù registry quảng cáo).
5. Nhãn "SAR_Generator" **nói dối là LLM** nhưng là template tĩnh.
6. Bước "KYT + Travel Rule" **tự nhận chấm điểm** nhưng chỉ echo; `kyt` mặc định = ML score → số KYT hiển thị có thể chính là output ML.
7. `handle_analyst_nl_sql` có nhánh có thể `KeyError("visualization")` (edge case).
8. `WORKSPACE_LINKS` trùng lặp ở supervisor.py và orchestrator.py (bản orchestrator dead).
9. 3 connector **luôn là Mock** (`@lru_cache`) dù nhãn ngụ ý lookup thật + nhúng URL OFAC giả.

---

## 3. Target workflow cho 4 agent (thiết kế "thật")

Nguyên tắc: **1 engine điều tra duy nhất** (4-node supervisor) làm nguồn sự thật; copilot chỉ là lớp chat gọi lại chính engine/skill đó. Mỗi node = tổ hợp **tool thật + (tuỳ chọn) LLM suy luận** + **gate deterministic** + ghi **audit bất biến**.

### 1) Orchestrator — *State Manager / Router*
- **Thật hoá:** biến thành **router có điều kiện** (LangGraph conditional edges): case rủi ro thấp + không hit → fast-track auto-clear (bỏ qua điều tra sâu); case nghi ngờ → full path. Không chạy tuyến tính cứng nữa.
- Giữ: RAG context (đã thật), SLA/priority.
- Guardrail: nếu confidence tổng < ngưỡng → ép sang human review.

### 2) Entity Identity — *KYC/KYB*
- **Thật hoá (ROI cao):** **sàng OFAC SDN bằng danh sách công khai** (tải file SDN, fuzzy match tên/đối tác) → "sanctions thật" miễn phí.
- OSINT: giữ LLM-assisted nhưng **grounded** (chỉ tóm tắt nguồn, không bịa).
- UBO / Device: giữ **mô phỏng nhưng gắn nhãn rõ "simulated connector"** (trung thực với investor).

### 3) Financial Crime Investigator — *KYT* (sửa đúng chỗ "chạy khác")
- **Bỏ cảm giác "skip":** graph và behavioral **luôn emit một bước completed** ("no on-chain exposure detected" / "no behavioral pattern") thay vì biến mất.
- **On-chain exposure thật:** duyệt đồ thị scenario tính **phơi nhiễm trực tiếp + gián tiếp theo hop** tới node flagged (mixer/SDN) → ra điểm + đường dẫn hop. Đây là KYT thật, không mock.
- **KYT score độc lập:** tính riêng từ (exposure on-chain + travel-rule gap + behavioral), **tách khỏi ML score**, không echo.
- Fiat-bridge: giữ mô phỏng, gắn nhãn.

### 4) Arbiter — *Compliance Officer*
- **SAR narrative bằng LLM thật**, grounding trên audit pack (evidence + tool outputs), **policy gate vẫn thắng** (LLM không được lật OFAC/mixer hit) → đúng Co-Investigator AI + maker-checker.
- **Explainability block:** liệt kê feature/gate nào lái quyết định (bắt buộc cho SR 11-7 / EU AI Act).
- **Audit bất biến:** append-only + **hash-chain** mỗi entry.
- **Graduated autonomy:** auto-clear low-risk end-to-end; REVIEW/ESCALATE → chờ người xác nhận.

### Lớp governance xuyên suốt (từ regulator)
Gate deterministic > LLM · escalation theo ngưỡng confidence · mỗi hành động agent → 1 audit entry bất biến · LLM chỉ tóm tắt tool output (chống bằng chứng ảo) · log model_id/version + input/output để quản trị model-risk.

---

## 4. Lộ trình upgrade (demo vững + đúng hướng thật)

**Phase 1 — "thật hoá" nhìn thấy được trên demo (ưu tiên, ~1 tuần Cursor):**
`OFAC SDN thật` · `on-chain exposure thật` · `SAR LLM có guardrail` · `sửa skip của Financial Crime` · `hợp nhất copilot về cùng engine` · `gắn nhãn "Bedrock Nova" / "simulated connector"`.

**Phase 2 — đúng hướng kiến trúc:**
Orchestrator routing có điều kiện · KYT score độc lập · audit hash-chain · HITL theo ngưỡng confidence · logging model-risk (FP/FN).

**Phase 3 — production:**
Tích hợp vendor sanctions/OSINT/KYB thật · nguồn dữ liệu chain-analytics thật · validation & monitoring độc lập (SR 11-7).

---

## 5. Cách demo cho investor (positioning)
"**Agent thật, không phải chatbot**": 4 agent điều tra end-to-end với **tool thật (OFAC + on-chain exposure) + AI viết SAR + gate compliance không thể ghi đè + audit bất biến + người xác nhận**. Đây là ngôn ngữ Unit21/Elliptic/Verafin đang dùng và là thứ regulator đòi hỏi — kể đúng câu chuyện này là bạn đứng cùng hạng với các tay chơi đã gọi vốn lớn.

---

## 6. Bộ prompt Cursor (gộp fix một thể)

> Dán từng prompt vào Cursor. Đã sắp theo thứ tự ưu tiên. Mỗi prompt có tiêu chí nghiệm thu.

### Prompt 1 — Sửa "Financial Crime chạy khác" + on-chain exposure thật + KYT score độc lập
```
Trong apps/api/agent/supervisor.py (node_investigator) và agent/tools/graph_tools.py:

1) Bỏ cảm giác "skip": bước OnChain_Graph_Analyzer và Behavioral Pattern Engine phải
   LUÔN emit status "completed" với một câu kết luận rõ ràng, kể cả khi không có tín hiệu
   ("No on-chain exposure to flagged entities detected" / "No behavioral pattern matched").
   KHÔNG dùng status "skipped" cho hai bước này nữa.

2) On-chain exposure THẬT: trong graph_tools.py thêm hàm compute_exposure(alert_id) đọc
   data/graphs/{alert_id}.json và duyệt đồ thị (BFS từ node ví chính) để tính:
   - direct_exposure: tổng amount_usd các cạnh nối trực tiếp tới node flagged (mixer/SDN/counterparty risk=high)
   - indirect_exposure: phơi nhiễm gián tiếp theo hop (>=2 hop) tới node flagged, kèm số hop nhỏ nhất
   - danh sách đường dẫn hop tới từng node flagged
   node_investigator gọi hàm này và emit kết quả (điểm + hop path) thay cho summary chung chung.

3) KYT score ĐỘC LẬP: thêm hàm compute_kyt_score(alert, exposure) trong một module mới
   agent/kyt.py, tính điểm 0-100 từ: on-chain exposure (direct+indirect), travel_rule gap,
   behavioral hit. KHÔNG tái dùng ML score. Gán vào alert["kyt_score"] và emit ở bước KYT.

Tiêu chí nghiệm thu:
- Mở case ALT-3002 (mixer) và một case sạch: cả hai đều thấy Financial Crime chạy ĐỦ các bước,
  không bước nào "skipped".
- Case mixer hiện direct+indirect exposure và đường hop tới Tornado/cluster; case sạch hiện "no exposure".
- KYT score khác giá trị ML score (không còn echo).
Không đổi frontend timeline component; chỉ dựa vào status/output đã emit.
```

### Prompt 2 — Sanctions THẬT bằng OFAC SDN công khai
```
Mục tiêu: thay sàng lọc sanctions mock bằng match THẬT trên danh sách OFAC SDN công khai (miễn phí).

- Thêm script apps/api/scripts/fetch_ofac_sdn.py tải file SDN (CSV/XML công khai của US Treasury OFAC)
  về data/ofac_sdn.json (danh sách tên + alias + program). Cho phép chạy offline: nếu tải fail,
  dùng file đã cache.
- Thêm agent/domain/sanctions.py: hàm screen_ofac(name, counterparty) fuzzy-match (rapidfuzz hoặc
  difflib) tên khách + counterparty với danh sách SDN, trả {hit, score, matched_name, program}.
- Trong agent/domain/packs.py (screening_with_policy_overlay): nếu OFAC list có sẵn, dùng screen_ofac
  làm nguồn THẬT; giữ overlay policy/LLM để diễn giải. Đánh dấu nguồn "OFAC SDN (public list)".
- Các connector còn lại (OSINT, KYB) đổi nhãn output rõ ràng thành "simulated" để trung thực.

Tiêu chí nghiệm thu:
- Submit/triage một giao dịch với counterparty trùng tên trên SDN → hit thật, kèm matched_name + program.
- Tên không nằm trong list → no hit, có score.
- Không có mạng → dùng cache, không crash.
```

### Prompt 3 — SAR narrative bằng LLM thật (có guardrail) + explainability
```
Trong apps/api/agent/supervisor.py (node_arbiter, _draft_sar):

- Khi decision == ESCALATE và Bedrock is_configured(): sinh SAR narrative bằng bedrock.safe_invoke,
  prompt CHỈ được dùng dữ liệu trong audit pack (evidence, tool outputs, policy hits, ML attribution,
  exposure) — cấm bịa dữ kiện. Nếu Bedrock không có: giữ template hiện tại làm fallback.
- Policy gate vẫn THẮNG: LLM không được đổi decision; nó chỉ viết narrative cho quyết định đã chốt.
- Thêm "explainability" vào kết quả triage: danh sách yếu tố lái quyết định (feature ML + gate + exposure),
  để phục vụ SR 11-7 / EU AI Act. Đổi nhãn bước cho trung thực: "SAR_Generator (LLM)" khi dùng LLM,
  "SAR_Generator (template)" khi fallback.

Tiêu chí nghiệm thu:
- Case ESCALATE có Bedrock: narrative viết bằng LLM, bám evidence, không có dữ kiện lạ.
- Không Bedrock: vẫn ra SAR template, không lỗi.
- Kết quả có mảng explainability; nhãn bước phản ánh đúng LLM/template.
```

### Prompt 4 — Gộp bug fix + hợp nhất copilot về cùng engine
```
Fix loạt bug sau (một PR):
1) main.py: xoá route trùng GET /api/cases/{case_id}; gộp thành 1 handler xử lý cả case-rollup và
   resolved-case (thử rollup trước, không có thì tra resolved_cases).
2) agent/bedrock.py safe_invoke: bắt thêm Exception chung để luôn rơi về fallback text.
3) agent/skills/registry.py route_intent: ưu tiên các skill cần alert_id (graph-summary, sanctions-check)
   TRƯỚC khi rơi vào analyst-nl-sql cho keyword chung ("mixer", "exposure").
4) agent/loop.py: thêm fiat-crypto-bridge vào LOOP_SKILLS để LLM copilot gọi được.
5) Đồng bộ nhãn: bước workflow của supervisor phải map được về skill id trong registry (thêm field
   skill_id vào mỗi step emit), để trang Agents join được với timeline.
6) Copilot: cho handle_copilot khi có alert_id ưu tiên gọi lại chính engine điều tra (skills dùng chung
   hàm domain như supervisor) — không để copilot và triage phân kỳ logic.

Tiêu chí nghiệm thu:
- /api/cases/{resolved_id} trả đúng resolved case; /api/cases/{customer_id} vẫn trả rollup.
- Copilot hỏi "check mixer exposure on this alert" (có alert_id) → chạy graph/sanctions, không phải NL-SQL.
- Mỗi workflow step có skill_id; trang Agents highlight đúng skill đang chạy.
```

---

## 7. Việc tôi cần bạn quyết
1. **Bắt đầu Phase 1 theo thứ tự Prompt 1 → 4?** (tôi khuyến nghị vậy).
2. Sanctions thật: OK tải danh sách **OFAC SDN công khai** chứ? (miễn phí, không cần API key).
3. Có muốn tôi tách riêng một prompt cho **audit hash-chain** (Phase 2) ngay bây giờ không, hay để sau demo.

---

## Sources
- [Chainalysis vs Elliptic vs TRM (Spark)](https://www.spark.money/tools/crypto-aml-tool-comparison) · [TRM: best crypto AML 2026](https://www.trmlabs.com/resources/blog/what-is-the-best-crypto-aml-and-compliance-solution-in-2026) · [finconduit compare](https://finconduit.com/resources/blockchain-analytics-providers-compared)
- [Unit21 AI Agent](https://www.unit21.ai/products/ai-agent) · [Unit21: rebuilt around AI agents](https://www.unit21.ai/blog/the-new-unit21-why-we-rebuilt-everything-around-ai-agents) · [Unit21 relaunch (Yahoo)](https://finance.yahoo.com/news/unit21-relaunches-leader-ai-risk-120000868.html) · [Sardine agentic AML](https://www.sardine.ai/agentic-ai-for-aml)
- [LangGraph multi-agent enterprise guide](https://devops.gheware.com/blog/posts/langgraph-multi-agent-orchestration-enterprise-2026.html) · [Databricks financial crime multi-agent](https://medium.com/databricks-financial-services/transforming-financial-crime-detection-918eeb281bca) · [LangGraph Supervisor ref](https://reference.langchain.com/python/langgraph-supervisor)
- [Co-Investigator AI (arXiv 2509.08380)](https://arxiv.org/abs/2509.08380) · [Lucinity autonomous case resolution](https://lucinity.com/blog/advancing-aml-investigations-autonomous-case-resolution-with-agentic-ai-workflows-2) · [Napier: agentic AI in AML](https://www.napier.ai/knowledgehub/agentic-ai-aml-compliance) · [AI agents in the loop](https://towardsagenticai.com/ai-agents-in-the-loop-new-aml-compliance-model/)
- [SR 11-7 AI model risk 2026](https://www.bespokementis.com/blog/sr-11-7-guidance-revisited-ai-model-risk-in-2026-1780326072237) · [Moody's AML in 2025](https://www.moodys.com/web/en/us/kyc/resources/insights/aml-in-2025.html) · [Flagright 2025 regulatory changes](https://www.flagright.com/post/regulatory-changes-in-aml-compliance)
- [Chainalysis: transaction monitoring/KYT](https://www.chainalysis.com/glossary/transaction-monitoring/) · [Scorechain: what is KYT](https://www.scorechain.com/resources/crypto-compliance/what-is-kyt-know-your-transaction) · [TRM: KYT glossary](https://www.trmlabs.com/glossary/know-your-transaction-kyt)
