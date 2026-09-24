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
- Quét Blog theo chu kỳ và chỉ xử lý bài có mẫu kích hoạt.
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

1. Tạo `config.json` trong thư mục project.
2. Điền tài khoản LMS, mật khẩu và Groq API key.
3. Chạy `START_BOT.bat`.
4. Lần đầu bot sẽ tự tạo `.venv` và cài thư viện cần thiết.

`config.json`, `.browser_profile`, `.attachments`, `processed.json`, `account_identities.json`, `session_username.txt` và `.venv` đều là dữ liệu local và đã được bỏ qua trong Git.

---

## 2. Chạy bot

Chạy:

```text
START_BOT.bat
```

Launcher hiện thực hiện các bước:

1. Kiểm tra `.venv`; nếu lỗi hoặc chưa có thì tự tạo lại.
2. Kiểm tra `pip`.
3. Cài/kiểm tra `playwright`.
4. Cài/kiểm tra `groq`.
5. Cài/kiểm tra `pypdf`, `python-docx`, `openpyxl`.
6. Cài/kiểm tra `psutil` cho health/memory watchdog.
7. Gọi `RUN_BOT_JOB.ps1` để chạy bot trong Windows Job Object và giám sát heartbeat.
8. Nếu supervisor trả exit code `75`, launcher chờ 5 giây rồi tự khởi động lại bot.

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
  "max_answer_length": 6000,
  "retry_count": 2,
  "retry_delay_seconds": 2,
  "cooldown_seconds": 0,
  "only_new_posts": true,
  "debug": true,
  "headless": true,
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

`max_posts_per_scan`: số entry tối đa lấy trong mỗi vòng quét.

`max_answer_length`: giới hạn số ký tự của câu trả lời trước khi comment.

`retry_count`: số lần retry thêm khi gọi AI lỗi.

`retry_delay_seconds`: thời gian chờ giữa các lần retry AI.

`cooldown_seconds`: thời gian nghỉ thêm sau khi comment thành công.

`debug`: bật log chi tiết như URL profile được phát hiện và lỗi retry AI.

`headless`:

- `true`: browser chạy ẩn.
- `false`: hiện cửa sổ browser, phù hợp khi debug.

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

Muốn test lại bài cũ:

```text
RESET_PROCESSED.bat
```

File này sẽ xóa `processed.json`.

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

khi tài khoản `username:userid` chưa từng có state, bot lấy các bài đang thấy và tạo baseline một lần cho chính tài khoản đó. Sau đó chỉ bài mới xuất hiện mới được xử lý.

Restart hoặc reconnect không tạo lại baseline nếu tài khoản đã có state trong `processed.json`; đổi sang tài khoản khác sẽ dùng state riêng.

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
├─ START_BOT.bat         # Launcher, tạo venv + dependency + auto restart code 75
├─ RUN_BOT_JOB.ps1       # Job Object + external heartbeat watchdog
├─ RESET_PROCESSED.bat   # Xóa trạng thái bài đã xử lý
├─ config.json           # Secret/local config, không commit
├─ processed.json        # Runtime state theo username:userid, không commit
├─ bot_health.json       # Heartbeat/health runtime, không commit
├─ account_identities.json # Cache username -> userid + display_name, không commit
├─ session_username.txt  # Username session gần nhất, không commit
├─ .bot_runtime/         # PID/runtime state, không commit
├─ logs/                 # Log runtime/rotated logs, không commit
├─ .browser_profile/     # Cookie/session browser, không commit
├─ .attachments/         # File LMS tải tạm, không commit
├─ .venv/                # Python virtual environment
├─ tests/
│  └─ test_runtime_safety.py # Test atomic state/health, state cap, log retention
└─ README.md
```

---

## 13. Lưu ý bảo mật

`config.json` chứa:

- tài khoản LMS;
- mật khẩu LMS;
- Groq API key.

Không commit, upload hoặc gửi công khai file này.

Repository hiện đã ignore:

```text
config.json
auth.json
.env
.env.*
processed.json
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
- `processed.json` chỉ ghi bài sau khi comment thành công; nếu AI hoặc comment lỗi, bài có thể được thử lại ở vòng quét sau.

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

## 16. Kiểm thử runtime safety

Chạy bộ test không cần truy cập LMS:

```text
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Bộ test hiện kiểm tra:

- `processed.json` ghi atomic và bị giới hạn kích thước theo số ID.
- `bot_health.json` ghi atomic, không để lại file `.tmp`.
- Log archive được giới hạn số lượng/thời gian lưu.
- File đính kèm tạm quá hạn được xóa và thư mục rỗng được dọn.
- Logic giữ các `entryid` mới hơn khi state vượt giới hạn.

Các test vận hành thực tế đã dùng khi phát triển gồm: mở nhiều instance cùng lúc, kill browser Playwright để kiểm tra tự phục hồi, ép ngưỡng RAM thấp để kiểm tra exit code `75` + auto restart, và giả lập heartbeat stale để kiểm tra supervisor terminate Job Object.
