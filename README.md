# IUH LMS Blog Bot

Bot theo dõi Blog cá nhân trên LMS IUH, tìm bài có mẫu kích hoạt, gửi câu hỏi và nội dung file đính kèm sang AI Groq, sau đó đăng câu trả lời dưới dạng comment ngay trên LMS.

## Tính năng hiện tại

- Tự đăng nhập LMS bằng tài khoản trong `config.json`.
- Giữ session bằng profile riêng `.browser_profile`; trước khi dùng lại bot xác minh `userid` và tên hiển thị đúng với tài khoản `username` trong `config.json`.
- Tự đăng nhập lại khi session hết hạn hoặc bị văng khỏi LMS.
- Tự reconnect và tạo lại browser khi mất mạng/browser lỗi; host không tự dừng vì một lỗi tạm thời.
- Tự restart browser định kỳ để giải phóng cache/tài nguyên Playwright.
- Theo dõi RAM Python + toàn bộ process con Playwright/Chrome; nếu vượt ngưỡng thì yêu cầu supervisor restart toàn bộ bot.
- Ghi heartbeat vào `bot_health.json`; `RUN_BOT_JOB.ps1` giám sát heartbeat từ bên ngoài và trả exit code `75` khi bot treo/stale để `START_BOT.bat` tự khởi động lại.
- Tự xác định `userid` của tài khoản trong `config.json`; nếu persistent session đang là tài khoản cũ/khác, bot tự xóa cookie và đăng nhập lại đúng tài khoản.
- Quét nhanh trang đầu theo chu kỳ và chạy deep scan định kỳ qua pagination để không bỏ sót backlog khi có nhiều hơn `max_posts_per_scan` bài mới.
- Chỉ đánh dấu bài đã xử lý sau khi comment được xác minh trên LMS; câu trả lời đang chờ gửi được lưu vào `pending_comments.json` để tránh comment trùng sau crash/restart.
- Hỗ trợ tìm mẫu kích hoạt trong tiêu đề, nội dung hoặc cả hai.
- Hỗ trợ lệnh phụ cấu hình được như `#short`, `#code`, `#nocmt`.
- Đọc file đính kèm: PDF, DOCX, XLSX, CSV và nhiều định dạng text/code.
- Giới hạn số file, dung lượng và lượng text trích xuất để tránh prompt quá lớn.
- Lưu `processed.json` tách theo khóa `username:userid` để tránh comment lặp và không lẫn trạng thái giữa nhiều tài khoản.
- Ghi `processed.json` và `bot_health.json` theo kiểu atomic (`.tmp` → replace) để giảm nguy cơ hỏng JSON khi crash/mất điện lúc đang ghi.
- Log ra console đồng thời ghi `logs/bot.log`; tự rotate khi log vượt 10 MB.
- Tự dọn file đính kèm tạm cũ còn sót trong `.attachments`.
- Chống chạy hai bot đồng thời trong cùng project/browser profile trên Windows bằng single-instance mutex.
- Chạy trong Windows Job Object: đóng cửa sổ launcher thì Python và browser của bot cũng dừng theo.
- Tự tạo `.venv` và tự cài dependency cần thiết khi chạy `START_BOT.bat`.

## Thay đổi gần đây

- Sửa logic nhận diện trạng thái đăng nhập: không còn nhầm trang `/login/index.php` là đã logout khi session thực tế vẫn còn.
- Thêm xác minh danh tính tài khoản: lưu `username -> userid + display_name`; nếu tên/ID session không khớp config, bot chủ động đăng xuất session cũ và đăng nhập lại.
- Thêm tự đăng nhập lại khi session hết và tự reconnect khi browser/mạng lỗi.
- Thêm đọc nội dung file đính kèm trực tiếp từ bài Blog.
- Thêm `in_progress` + single-instance mutex để giảm nguy cơ comment trùng.
- Thêm Windows Job Object để đóng launcher là dừng luôn Python và browser của bot.
- Thêm supervisor/watchdog ngoài process Python: phát hiện heartbeat stale, dừng cả Job Object và cho launcher tự restart bot.
- Thêm memory watchdog và chu kỳ restart browser phục vụ chạy 24/7 lâu dài.
- Thêm atomic write cho state/health và log rotation.
- Sửa `only_new_posts` để baseline chỉ được tạo khi tài khoản chưa có state; restart/reconnect không đánh dấu lại các bài mới thành bài cũ.

---

## 1. Cài đặt từ GitHub

```bash
git clone https://github.com/unkluco/chatlms.git
cd chatlms
```

Yêu cầu khuyến nghị:

- Windows 10/11.
- Python 3 đã cài trên máy.
- Google Chrome hoặc Microsoft Edge.
- Tài khoản LMS IUH hợp lệ.
- Groq API key.

Sau khi clone:

1. Copy `config.example.json` thành `config.json`.
2. Điền tài khoản LMS, mật khẩu và Groq API key; hoặc dùng biến môi trường `LMS_USERNAME`, `LMS_PASSWORD`, `GROQ_API_KEY`.
3. Chạy `START_BOT.bat`.
4. Lần đầu bot sẽ tự tạo `.venv` và đồng bộ đúng dependency trong `requirements.txt`.

`config.json`, `.browser_profile`, `.attachments`, `processed.json`, `pending_comments.json`, `bot_health.json`, `account_identities.json`, `session_username.txt`, `.bot_runtime`, `logs` và `.venv` đều là dữ liệu local và đã được bỏ qua trong Git.

---

## 2. Chạy bot

Chạy:

```text
START_BOT.bat
```

Launcher hiện thực hiện các bước:

1. Kiểm tra `.venv`; nếu lỗi hoặc chưa có thì tự tạo lại.
2. Kiểm tra `pip`.
3. Nếu có `requirements.txt`, đồng bộ đúng các phiên bản dependency đã pin.
4. Nếu không có file pin, fallback sang kiểm tra/cài riêng Playwright, Groq, thư viện đọc file và `psutil`.
5. Gọi `RUN_BOT_JOB.ps1` để chạy bot trong Windows Job Object và giám sát heartbeat.
6. Nếu bot dừng bất thường hoặc yêu cầu restart, launcher tự chạy lại với backoff 5 → 10 → 30 → 60 → tối đa 300 giây; nếu phiên trước đã chạy ổn định ít nhất 10 phút thì bộ đếm backoff được reset về đầu.
7. Exit code `2` (đã có instance khác) và `3` (config/state/AI permanent error) sẽ dừng thay vì restart vô hạn.

Khi đóng cửa sổ `START_BOT.bat`, Job Object sẽ dừng cả Python và browser con của bot, tránh tình trạng bot vẫn chạy ngầm.

---

## 3. Cấu hình đầy đủ

Ví dụ cấu hình đang phù hợp với phiên bản hiện tại:

```json
{
  "lms_base_url": "https://lms.iuh.edu.vn",
  "username": "YOUR_LMS_USERNAME",
  "password": "YOUR_LMS_PASSWORD",
  "provider": "groq",
  "groq_api_key": "gsk_...",
  "ai_model": "",
  "detect_pattern": "@bot",
  "trigger_position": "title",
  "default_system_prompt": "Trả lời đúng trọng tâm câu hỏi, rõ ràng, tự nhiên và hữu ích.",
  "poll_interval_seconds": 6,
  "max_posts_per_scan": 10,
  "fast_scan_pages": 1,
  "deep_scan_interval_seconds": 300,
  "deep_scan_max_posts": 500,
  "deep_scan_max_pages": 100,
  "max_answer_length": 6000,
  "retry_count": 2,
  "retry_delay_seconds": 2,
  "retry_max_delay_seconds": 30,
  "cooldown_seconds": 0,
  "ignored_recheck_seconds": 300,
  "only_new_posts": true,
  "debug": true,
  "headless": true,
  "ignore_https_errors": false,
  "reconnect_delay_seconds": 5,
  "login_retry_seconds": 5,
  "health_interval_seconds": 60,
  "maintenance_interval_seconds": 3600,
  "browser_restart_hours": 6,
  "max_python_memory_mb": 800,
  "max_browser_children_memory_mb": 1500,
  "watchdog_stale_seconds": 600,
  "watchdog_check_seconds": 15,
  "commands": {
    "#short": {
      "system_prompt": "Trả lời thật ngắn gọn, chỉ nêu ý chính cần thiết."
    },
    "#code": {
      "system_prompt": "Ưu tiên giải thích theo hướng lập trình và đưa code khi phù hợp."
    },
    "#nocmt": {
      "system_prompt": "Nếu trả lời code thì chỉ đưa câu trả lời trực tiếp, không thêm phần giải thích kiểu comment."
    }
  },
  "attachments": {
    "enabled": true,
    "max_file_size_mb": 15,
    "max_files_per_post": 3,
    "max_extracted_chars_per_file": 20000,
    "max_total_attachment_chars": 40000,
    "delete_after_processing": true
  }
}
```

### Các option chính

`lms_base_url`: URL gốc của LMS. Với IUH hiện dùng `https://lms.iuh.edu.vn`.

`username`, `password`: thông tin đăng nhập LMS. Bot dùng để tự đăng nhập và tự đăng nhập lại khi session hết.

`provider`: hiện code hỗ trợ `groq`.

`groq_api_key`: API key Groq. Không commit key lên GitHub.

`ai_model`: model Groq. Nếu để rỗng, bot mặc định dùng `openai/gpt-oss-120b`.

`detect_pattern`: chuỗi kích hoạt chính, ví dụ `@bot`.

`trigger_position` có 3 giá trị:

- `title`: tìm mẫu kích hoạt trong tiêu đề.
- `content`: tìm trong nội dung bài.
- `both`: tìm cả hai.

Nếu dùng `title`, phần nội dung sau mẫu kích hoạt trong tiêu đề sẽ được ghép với toàn bộ nội dung bài để làm prompt.

`poll_interval_seconds`: số giây giữa hai lần quét Blog. Code ép tối thiểu 2 giây.

`max_posts_per_scan`: số bài chưa xử lý tối đa ở vòng quét nhanh. Các bài đã có trong `processed.json` không chiếm quota này.

`fast_scan_pages`: số trang pagination được quét ở vòng nhanh. Mặc định 1 để giảm tải LMS.

`deep_scan_interval_seconds`: chu kỳ chạy deep scan để tìm backlog nằm ở trang cũ hơn. Mặc định 300 giây.

`deep_scan_max_posts`: số bài chưa xử lý tối đa mỗi deep scan. Mặc định 500.

`deep_scan_max_pages`: số trang tối đa một deep scan có thể đi qua. Mặc định 100.

`max_answer_length`: giới hạn số ký tự của câu trả lời trước khi comment.

`retry_count`: số lần retry thêm khi gọi AI lỗi tạm thời.

`retry_delay_seconds`, `retry_max_delay_seconds`: AI retry dùng exponential backoff + jitter, bắt đầu từ delay cơ sở và không vượt quá max delay. Lỗi xác thực/quyền/model không tồn tại được coi là permanent error và bot dừng để tránh spam API.

`cooldown_seconds`: thời gian nghỉ thêm sau khi comment thành công.

`ignored_recheck_seconds`: bài mới chưa có marker không bị đánh dấu processed vĩnh viễn; bot tạm bỏ qua rồi kiểm tra lại sau khoảng thời gian này để vẫn bắt được trường hợp người dùng sửa bài và thêm `@bot` sau đó.

`debug`: bật log chi tiết như URL profile được phát hiện và lỗi retry AI.

`headless`:

- `true`: browser chạy ẩn.
- `false`: hiện cửa sổ browser, phù hợp khi debug.

`ignore_https_errors`: mặc định `false`. Chỉ bật khi môi trường test dùng certificate tự ký; với LMS thật nên giữ `false` để browser xác minh TLS bình thường.

`reconnect_delay_seconds`: thời gian chờ trước khi bot tạo lại phiên browser sau lỗi kết nối/browser.

`login_retry_seconds`: thời gian chờ giữa các lần thử đăng nhập LMS.

`health_interval_seconds`: chu kỳ heartbeat/health và kiểm tra RAM. Code ép tối thiểu 30 giây.

`maintenance_interval_seconds`: chu kỳ dọn file đính kèm tạm và log archive cũ. Mặc định 3600 giây, ép tối thiểu 300 giây để tránh quét ổ đĩa quá thường xuyên.

`browser_restart_hours`: số giờ một browser session được giữ trước khi chủ động tạo lại. Mặc định 6 giờ.

`max_python_memory_mb`: ngưỡng RAM của process Python. Khi vượt ngưỡng, bot yêu cầu supervisor restart toàn bộ process để giải phóng RAM thực sự. Mặc định 800 MB.

`max_browser_children_memory_mb`: ngưỡng tổng RAM process con của bot (Playwright driver + Chrome của bot). Mặc định 1500 MB; không cộng Chrome cá nhân không thuộc process tree của bot.

`watchdog_stale_seconds`: heartbeat quá cũ bao lâu thì `RUN_BOT_JOB.ps1` coi bot bị treo. Mặc định 600 giây, supervisor ép tối thiểu 120 giây.

`watchdog_check_seconds`: chu kỳ supervisor kiểm tra heartbeat. Mặc định 15 giây, ép tối thiểu 5 giây.

---

## 4. Cơ chế đăng nhập và tự phục hồi

Bot dùng `.browser_profile` làm persistent browser profile.

Luồng hoạt động:

```text
Khởi động
  ↓
Mở Chrome → nếu lỗi thử Edge → nếu lỗi thử Chromium của Playwright
  ↓
Mở trang login LMS
  ↓
Đọc session hiện tại: userid + tên hiển thị
  ↓
So với danh tính đã xác minh của username trong config.json
  ├─ Khớp → dùng tiếp session
  └─ Không khớp/chưa có mốc → xóa cookie session cũ → đăng nhập lại bằng config.json
  ↓
Lưu username -> userid + display_name vào account_identities.json
  ↓
Mở đúng Blog của userid đã xác minh và bắt đầu quét
```

Điểm quan trọng: bot **không còn kết luận logout chỉ vì URL chứa `/login/`**. Moodle có thể mở `/login/index.php` ngay cả khi người dùng đã đăng nhập. Bot chỉ xem là logout khi form `username` và `password` thực sự xuất hiện.

Nếu trong lúc chạy:

- Session LMS hết → bot tự đăng nhập lại và tiếp tục quét.
- Browser bị đóng/kết nối Playwright chết → bot tạo lại browser.
- Mạng/LMS lỗi tạm thời → bot giữ host sống, chờ `reconnect_delay_seconds` rồi thử lại.
- RAM Python hoặc process tree Playwright/Chrome vượt ngưỡng → Python thoát với code `75`; launcher tự chạy lại toàn bộ process sau 5 giây.
- Heartbeat `bot_health.json` mất/quá cũ → `RUN_BOT_JOB.ps1` terminate cả Job Object và trả code `75` để launcher tự phục hồi.
- CAPTCHA/MFA xuất hiện hoặc giao diện LMS thay đổi lớn → có thể cần cập nhật code.

Supervisor chạy ở PowerShell bên ngoài process Python. Vì vậy trường hợp Python bị deadlock/treo cứng và không còn tự xử lý được vẫn có một lớp khác theo dõi heartbeat. Trong giai đoạn khởi động supervisor cho phép grace period 120 giây để tránh kill nhầm lúc login/browser đang mở.

---

## 5. Mẫu kích hoạt và lệnh phụ

Ví dụ cấu hình:

```json
"detect_pattern": "@bot",
"trigger_position": "title"
```

Bạn có thể tạo tiêu đề:

```text
@bot #code
```

và nội dung bài:

```text
Viết Dijkstra bằng C++ và phân tích độ phức tạp.
```

Bot sẽ:

1. Phát hiện `@bot`.
2. Tìm lệnh phụ trong prompt.
3. Xóa tag lệnh phụ khỏi prompt.
4. Dùng `system_prompt` tương ứng.
5. Gọi Groq.
6. Comment câu trả lời lên bài.

Các lệnh phụ **không hard-code**; bạn có thể thêm/sửa/xóa trong object `commands` của `config.json`.

Nếu nhiều tag cùng xuất hiện, code hiện chọn một tag đầu tiên theo thứ tự ưu tiên nội bộ (tag dài hơn được xét trước). Nên dùng một lệnh phụ cho mỗi bài để hành vi rõ ràng.

---

## 6. Đọc file đính kèm

Bật bằng:

```json
"attachments": {
  "enabled": true,
  "max_file_size_mb": 15,
  "max_files_per_post": 3,
  "max_extracted_chars_per_file": 20000,
  "max_total_attachment_chars": 40000,
  "delete_after_processing": true
}
```

Bot chỉ lấy link file thuộc chính host LMS và nằm trong đường dẫn Moodle `pluginfile.php` hoặc `draftfile.php`.

Định dạng hỗ trợ:

- Tài liệu: `.pdf`, `.docx`.
- Bảng dữ liệu: `.xlsx`, `.csv`.
- Text/code: `.txt`, `.md`, `.py`, `.java`, `.c`, `.cpp`, `.h`, `.cs`, `.js`, `.ts`, `.tsx`, `.jsx`, `.html`, `.css`, `.json`, `.xml`, `.yaml`, `.yml`, `.sql`, `.sh`, `.bat`, `.ps1`, `.go`, `.rs`, `.php`, `.rb`, `.kt`, `.swift` và một số extension text tương tự.

Cách đọc:

- PDF: trích text theo từng trang.
- DOCX: đọc paragraph và bảng.
- XLSX: đọc giá trị của từng sheet.
- CSV: đọc theo hàng.
- Text/code: đọc trực tiếp với fallback encoding.

File được tải tạm vào:

```text
.attachments/<entry_id>/
```

Sau khi xử lý, nếu `delete_after_processing=true`, thư mục tạm của entry sẽ được xóa.

Giới hạn:

- Không OCR PDF scan/ảnh.
- Không phân tích ảnh đính kèm.
- Chưa hỗ trợ PPT/PPTX.
- File vượt `max_file_size_mb` sẽ bị bỏ qua.
- Tổng text file đưa vào AI bị giới hạn bởi `max_total_attachment_chars`.

Nếu tải file trả về HTML thay vì file thật, bot xem đó là dấu hiệu session có thể đã hết và kích hoạt quy trình đăng nhập lại.

---

## 7. Chống xử lý trùng

Bot có nhiều lớp bảo vệ:

### `processed.json`

Lưu `entryid` theo từng khóa `username:userid`. Vì vậy hai tài khoản khác nhau có thể có cùng `entryid` mà không bị coi nhầm là đã xử lý. State được giới hạn tối đa 50.000 ID cho mỗi tài khoản để file không tăng vô hạn; bot ưu tiên giữ các ID entry mới hơn.

File state có version + `account_meta`, được ghi atomic và có `processed.json.bak` làm last-known-good. Nếu file chính hỏng, bot thử phục hồi từ backup; nếu cả hai đều không hợp lệ thì bot dừng với exit code `3` thay vì coi state rỗng và có nguy cơ comment trùng.

### `pending_comments.json`

Trước khi bấm gửi comment, bot lưu câu trả lời AI vào pending state. Khi restart/crash, bot dùng lại đúng câu trả lời đó và kiểm tra xem comment đã tồn tại trên LMS hay chưa trước khi gửi lại.

Thứ tự ghi được cố ý thiết kế là: **lưu pending → gửi + xác minh comment → lưu processed → xóa pending**. Nhờ vậy crash ở giữa quy trình không tạo cửa sổ mà cả pending lẫn processed đều biến mất. Pending đã thuộc entry processed sẽ được tự dọn ở lần khởi động/reconnect sau.

Muốn reset state, hãy **dừng bot trước** rồi chạy:

```text
RESET_PROCESSED.bat
```

File này xóa cả `processed.json`/backup và `pending_comments.json`/backup. Nếu `only_new_posts=true`, lần chạy sau sẽ tạo baseline mới và vẫn bỏ qua các bài đang tồn tại. Muốn test lại bài cũ, hãy đặt `only_new_posts=false` trước khi chạy bot sau khi reset.

### `in_progress`

Trong một phiên chạy, entry đang xử lý được giữ trong bộ nhớ để không bị chạy đồng thời/lặp do vòng quét.

### Single instance trên Windows

Bot tạo mutex theo thư mục project + `lms_base_url`. Một project chỉ dùng một `.browser_profile`, nên instance thứ hai sẽ tự dừng kể cả khi `config.json` đã đổi sang tài khoản khác.

---

## 8. `only_new_posts`

Nếu:

```json
"only_new_posts": true
```

khi tài khoản `username:userid` chưa từng có state, bot tạo một mốc `ignore_through_entry_id` dựa trên entry hiện có. Những entry cũ hơn hoặc bằng mốc được coi là lịch sử; entry có ID mới hơn mới được xét xử lý.

Vòng quét nhanh ưu tiên bài mới ở trang đầu. Deep scan định kỳ đi qua pagination và chỉ tính các bài chưa xử lý vào quota, nên trường hợp trang đầu toàn bài đã processed vẫn có thể đi tiếp xuống backlog phía sau.

Restart hoặc reconnect không tạo lại baseline nếu account đã có metadata trong `processed.json`; đổi sang tài khoản khác sẽ dùng state/mốc riêng.

Nếu muốn bot có thể xử lý bài cũ chưa có trong `processed.json`:

```json
"only_new_posts": false
```

---

## 9. AI / Groq

Hiện provider được hỗ trợ trong code là:

```json
"provider": "groq"
```

Nếu `ai_model` để trống, model mặc định là:

```text
openai/gpt-oss-120b
```

Bot gọi Groq với:

- `temperature=0.3`.
- `reasoning_effort="low"`.
- `include_reasoning=false`.
- Timeout SDK khoảng 90 giây.
- Số completion token được suy ra từ `max_answer_length` và giới hạn tối đa 4096.
- Câu trả lời cuối cùng bị cắt theo `max_answer_length`.

Groq:

- Console: https://console.groq.com/
- API Keys: https://console.groq.com/keys
- Docs: https://console.groq.com/docs/

---

## 10. Bot xác định Blog của ai?

Sau khi mở session, bot đọc danh tính người đang đăng nhập và tìm link profile dạng:

```text
/user/profile.php?id=XXXX
```

rồi lấy `XXXX` để tạo:

```text
https://lms.iuh.edu.vn/blog/index.php?userid=XXXX
```

Do đó không cần cấu hình `userid`. Lần đầu gặp một `username`, bot chủ động đăng nhập bằng credential trong `config.json` để xác minh `userid` và tên hiển thị rồi lưu vào `account_identities.json`. Các lần sau nếu session đang là tài khoản khác, bot phát hiện lệch tên/ID và tự đăng nhập lại đúng tài khoản.

---

## 11. Log khi chạy

Log bình thường có dạng:

```text
=== IUH LMS BLOG BOT ===
Mau kich hoat: '@bot'; scan moi 6s
Lenh phu: #short, #code, #nocmt
AI provider: groq; model: openai/gpt-oss-120b
Tu dong reconnect sau 5s neu mat ket noi.
File dinh kem: ON | toi da 3 file/bai | 15 MB/file
Mo trinh duyet chrome...
Session dung tai khoan config: <ten hien thi> | userid=<id>
Tai khoan da xac minh: username=<username>, ten=<ten hien thi>, userid=<id>
Da xac dinh blog cua dung tai khoan config.
```

Khi phát hiện bài:

```text
Phat hien '@bot' o entry ...; mode=#code. Dang goi AI...
Entry ...: AI tra loi ... ky tu. Dang gui binh luan...
Entry ...: Da gui binh luan.
```

Khi session hết:

```text
Phien LMS da het/bi vang. Dang xac minh va dang nhap lai theo config...
Dang nhap lai dung tai khoan: <ten hien thi> | userid=<id>
```

Khi browser/mạng lỗi:

```text
Can khoi tao lai phien browser.
Host van dang chay. Cho 5s roi ket noi lai...
```

Khi memory watchdog yêu cầu restart toàn bộ process:

```text
Phat hien bo nho bot vuot nguong (...)
Supervisor se khoi dong lai toan bo bot de giai phong tai nguyen.
[WATCHDOG] Bot bi treo/stale. Tu khoi dong lai sau 5s...
```

Log đồng thời được ghi vào `logs/bot.log`. Khi file vượt 10 MB, bot đổi tên file cũ theo timestamp rồi tạo `bot.log` mới. Archive log cũ hơn 30 ngày hoặc vượt 30 file archive sẽ được dọn để thư mục log không tăng vô hạn. `bot_health.json` chứa heartbeat hiện tại, PID, tài khoản đang chạy và số liệu RAM gần nhất.

---

## 12. Cấu trúc project

```text
lms_bot/
├─ lms_blog_bot.py       # Logic chính
├─ health_monitor.py     # Heartbeat, RAM monitor, cleanup runtime
├─ START_BOT.bat         # Launcher, dependency pinned + restart backoff
├─ RUN_BOT_JOB.ps1       # Job Object + external heartbeat watchdog
├─ RESET_PROCESSED.bat   # Reset processed + pending state
├─ requirements.txt      # Dependency versions đã pin
├─ config.example.json   # Mẫu config an toàn để copy
├─ config.json           # Secret/local config, không commit
├─ processed.json        # Runtime state + account metadata, không commit
├─ pending_comments.json # Pending answer chống comment trùng, không commit
├─ bot_health.json       # Heartbeat/health runtime, không commit
├─ account_identities.json # Cache username -> userid + display_name, không commit
├─ session_username.txt  # Username session gần nhất, không commit
├─ .github/
│  ├─ workflows/tests.yml # CI compile + unit test + dependency audit
│  └─ dependabot.yml      # Theo dõi dependency update
├─ .bot_runtime/         # PID/runtime state, không commit
├─ logs/                 # Log runtime/rotated logs, không commit
├─ .browser_profile/     # Cookie/session browser, không commit
├─ .attachments/         # File LMS tải tạm, không commit
├─ .venv/                # Python virtual environment
├─ tests/
│  ├─ test_runtime_safety.py
│  └─ test_core_behavior.py
└─ README.md
```

---

## 13. Lưu ý bảo mật

`config.json` chứa:

- tài khoản LMS;
- mật khẩu LMS;
- Groq API key.

Không commit, upload hoặc gửi công khai file này. Bot cũng hỗ trợ override secret bằng biến môi trường `LMS_USERNAME`, `LMS_PASSWORD`, `GROQ_API_KEY`; cách này phù hợp hơn khi chạy bằng Task Scheduler/CI hoặc khi không muốn lưu credential trực tiếp trong JSON.

Kết nối LMS mặc định **không** bỏ qua lỗi chứng chỉ TLS (`ignore_https_errors=false`). Chỉ nên bật tùy chọn này trong môi trường test có certificate tự ký.

Repository hiện đã ignore:

```text
config.json
auth.json
.env
.env.*
processed.json
pending_comments.json
bot_health.json
account_identities.json
session_username.txt
.bot_runtime/
logs/
.browser_profile/
.attachments/
.venv/
```

Nếu API key từng bị lộ ở nơi công khai, hãy revoke key cũ và tạo key mới.

---

## 14. Giới hạn hiện tại

- Chỉ có provider Groq.
- Selector phụ thuộc giao diện Moodle/LMS IUH hiện tại; LMS đổi UI có thể cần cập nhật.
- CAPTCHA/MFA không được tự vượt qua.
- Chưa xử lý ảnh và OCR.
- Chưa đọc PPT/PPTX.
- Bot comment qua UI của LMS; nếu chức năng comment bị tắt hoặc selector đổi, bot sẽ báo không tìm thấy ô/nút comment.
- Entry chỉ vào `processed.json` sau khi comment đã được xác minh trên LMS. Nếu AI/comment lỗi tạm thời, bài được thử lại; nếu đã có pending answer thì bot tái sử dụng answer đó thay vì gọi AI lần nữa.

---

## 15. Quy trình sử dụng gợi ý

1. Chạy `START_BOT.bat`.
2. Chờ log báo đã xác định Blog.
3. Tạo bài Blog theo `trigger_position`.
4. Thêm `@bot` và lệnh phụ nếu cần.
5. Đính kèm file nếu muốn AI đọc file.
6. Lưu bài.
7. Bot phát hiện → gọi AI → đăng comment.
8. Đóng cửa sổ launcher khi muốn dừng toàn bộ bot.
---

## 16. Kiểm thử và CI

Chạy bộ test không cần truy cập LMS:

```text
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Bộ test hiện bao phủ các nhóm quan trọng: atomic state/health, state cap + backup recovery/fail-closed, pending comment lifecycle, không gọi AI lần hai khi đã có pending answer, pagination/deep-scan backlog, scan floor của `only_new_posts`, config validation, retry permanent AI error, log retention và attachment cleanup.

`.github/workflows/tests.yml` tự chạy compile + unit test trên Python 3.13 và `pip-audit` cho mỗi push/pull request. `dependabot.yml` theo dõi cả Python dependency lẫn GitHub Actions theo tuần.

Ngoài unit test, khi phát triển đã thực hiện các test vận hành thật: mở nhiều instance cùng lúc, kill browser Playwright để kiểm tra tự phục hồi, ép ngưỡng RAM thấp để kiểm tra exit code `75` + auto restart, giả lập heartbeat stale, đăng nhập thật với TLS validation bật, quét Blog thật và xác minh cơ chế nhận diện comment đã tồn tại mà không gửi comment mới.

Đã test cài `requirements.txt` trong một virtualenv sạch rồi chạy toàn bộ test; dependency audit hiện không phát hiện lỗ hổng đã biết.
