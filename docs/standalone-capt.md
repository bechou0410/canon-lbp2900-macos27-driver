# Canon LBP2900 v27.3.2 — technical guide

**Bản hiện tại: Canon LBP2900 v27.3.2**, dành cho mục tiêu LBP2900/2900B. Tên bộ cài và máy in bỏ “CAPT” và “Standalone”; tên công cụ, receipt và runtime nội bộ giữ nguyên để tương thích. v27.3.2 là phiên bản project; máy thử chạy macOS 27.2.

Xem [README tiếng Anh](../README.md), [README tiếng Việt](../README.vi.md) và [phạm vi nghiệm thu](verification.md). Bộ cài có tài nguyên Anh/Việt, bản tự chọn theo ngôn ngữ macOS với dự phòng tiếng Anh, chỉ phát hành một PKG chung. Nội dung Canon gốc vẫn là tiếng Anh.

## Phạm vi

Một PKG tích hợp thành phần cần thiết từ Canon CAPT V10.0.10 English và patch LBP2900. Máy mới không cần cài toàn bộ driver Canon trước. Gói chỉ đăng ký một model LBP2900, dùng chung cho mục tiêu LBP2900/2900B; không mang PPD, monitor, recipe, ảnh trạng thái hoặc dữ liệu in hiệu chuẩn của các model khác. Bộ profile tương thích nội bộ vẫn mang tên LBP3000 vì đó là profile đã được kiểm chứng với bản 0.1.0.

Giữ Canon StatusMonitor, BackGrounder, CCPD, CAPTUIKit dùng chung và các PDE Finishing/Paper Source/Quality/About, tài liệu trợ giúp và thư viện dựng trang dùng chung. Các thư viện và giao diện Canon có thể chứa mã/tên của nhiều model; điều đó không cài thêm driver hoặc đăng ký các thiết bị đó. Không loại bỏ mã dùng chung bên trong binary vì có thể làm mất chức năng. LBP2900 không có in màu hoặc duplex tự động.

## Cài chung với driver Canon chính thức

| Thành phần | Gói độc lập 2900 | Driver Canon V10.0.10 gốc |
|---|---|---|
| Runtime | `/Library/Printers/Canon/LBP2900RT` | `/Library/Printers/Canon/CUPSCAPT2` |
| Backend/scheme | `lb29u2` | `cnbma2` |
| Cổng dữ liệu / điều khiển | `59290` / `59390` | `59687` / `59787` |
| LaunchAgent | `jp.co.canon.LBP2900RT.BackGrounder` | `jp.co.canon.CUPSCAPT2.BackGrounder` |
| Tiến trình nền | `Canon 2900 BackGrounder.app` | `Canon CAPT BackGrounder.app` |
| Kênh thông báo tự mở Utility | `lb29` | `capt` |
| Monitor USB | `lb29monitor` | Các monitor `captmon…` |
| PPD được thêm | `LocalLBP2900CAPT.ppd.gz` | Các PPD model chính thức |
| Receipt | `local.canon-lbp2900.capt10.standalone` | Receipt của Canon |

Build đổi đồng bộ đường dẫn, namespace IPC/cache/bundle và 26 hằng số cổng đã xác định trong hai kiến trúc arm64/x86_64. Cả 36 binary đều khóa checksum, tập kiến trúc và số lần thay chuỗi; thay đổi cổng kiểm thêm mã lệnh gốc. Thay chuỗi giữ nguyên chiều dài và từ chối nếu chạm vào machine code. Sau đó ký ad-hoc lại các binary/bundle. Đây không phải chữ ký/chứng nhận Canon hoặc notarization của Apple.

Đã chạy lại installer Canon V10.0.10 chính thức sau driver này trên hệ thống thật: cài thành công, toàn bộ hash riêng, receipt, URI/PPD các queue và máy in mặc định giữ nguyên. BackGrounder/CCPD/monitor/Utility riêng tiếp tục chạy với cùng PID. Trang in sau đó từ Preview ra đúng theo xác nhận người dùng. Payload/tiện ích Canon gốc vẫn qua kiểm tra integrity; chưa có máy Canon model khác để kiểm in vật lý. Driver/installer Canon phiên bản khác cần kiểm tra riêng.

## Build và kiểm thử

```sh
python3 tools/capt-standalone.py
python3 tests/standalone-test.py
```

Đầu ra: `artifacts/Canon-LBP2900-v27.3.2.pkg` và file `.sha256` cùng tên. Build xác minh lại DMG gốc, chữ ký installer Canon và notarization; giải nén mới, chọn payload, patch/ký, đóng gói rồi giải nén PKG để kiểm checksum. Gói cục bộ chứa thành phần bản quyền Canon và kèm license gốc trong màn hình Installer. Payload Canon không đưa vào Git; archive bộ cài phát hành giữ license và thông báo bản quyền gốc.

`config/standalone-binary-patches.json` là nguồn của các vị trí/hằng số được sửa. `tools/capt-standalone.py:selected()` sở hữu danh sách thành phần giữ lại. `relocation.json`, `installed.sha256`, `installed-paths.txt` được sinh trong payload để truy vết và kiểm tra file; không chỉnh thủ công.

Kiểm thử dựng trang chạy filter thật, so sánh từng byte với nguồn Canon cho A4, Letter, ba trang, toner/media/halftone và hai bản sao. `DYLD_PRINT_LIBRARIES` xác nhận filter của driver nạp thư viện từ cây private, không nhờ runtime Canon đã cài trên máy. Kiểm thêm dependencies tuyệt đối và `@rpath` qua `@loader_path`, chữ ký cả hai kiến trúc, tài nguyên PPD, nội dung gói, cài chồng payload và gỡ trong root thử có dấu cách. Không gửi job, mở kết nối USB hoặc cài lên hệ thống trong bộ test.

## Cài và kết nối máy in

Hoàn tất/hủy mọi job trước khi đổi driver. Có thể cài đè bản driver dự án còn nguyên vẹn, không cần gỡ trước. Bật đúng một LBP2900, cắm USB rồi cài PKG. Ở máy chưa cài, postinstall kiểm integrity và chạy `configure-connected`; khi tên queue chưa bị sử dụng, nó tạo `Canon_LBP2900` với kết nối `lb29u2://` và khởi động LaunchAgent cho desktop đang đăng nhập.

Nếu máy chưa cắm, không có đúng một thiết bị hoặc queue cũ cần xem xét, bộ cài không ghi đè queue. Sau khi chuẩn bị thiết bị và hoàn tất/xóa queue cũ của riêng 2900, chạy:

```sh
sudo '/Library/Application Support/CanonLBP2900Standalone/lbp2900-standalone' configure-connected
```

Tên hiển thị là **Canon LBP2900**. Không đổi máy in mặc định. Trong Printers & Scanners, mở Options & Supplies → Utility → Open Printer Utility. Không thêm queue USB trực tiếp bằng Add Printer để thay cho bước thiết lập native; thiếu kết nối/dịch vụ này từng làm Utility thoát rồi crash trên 0.2.4.

Với nhiều thiết bị, lấy URI cụ thể từ `lpinfo -v` rồi dùng lệnh `configure USB_URI`. Helper từ chối queue cùng tên không thuộc nó, job chưa xong hoặc monitor gốc còn giữ đúng USB. Hoàn tất mọi job và đăng xuất/đăng nhập lại nếu monitor cũ chưa dừng.

Installer không tự in. Nó từ chối runtime riêng đã có; muốn cài lại phải gỡ trước bằng helper. Chưa có Developer ID Installer/notarization; không cần thay đổi SIP/Gatekeeper trong quy trình đã kiểm.

## Kiểm tra và gỡ

```sh
'/Library/Application Support/CanonLBP2900Standalone/lbp2900-standalone' check
```

Khi gỡ, hoàn tất/hủy job trong Utility, xóa các queue dùng `lb29u2` rồi chạy:

```sh
sudo '/Library/Application Support/CanonLBP2900Standalone/lbp2900-standalone' remove
```

Helper từ chối file đã sửa, file lạ, queue còn dùng runtime hoặc tiến trình riêng không dừng. Nhận diện monitor bằng file thực thi đang nạp vì Canon khởi chạy nó bằng tên ngắn; gửi TERM và chờ tối đa 15 giây; monitor treo chỉ được KILL sau khi xác minh lại file thực thi thuộc runtime riêng. Nó chỉ gỡ runtime/PPD/backend/LaunchAgent/support và receipt riêng; không gỡ driver Canon gốc. Preference/cache theo người dùng được giữ lại để tránh xóa dữ liệu phiên chưa xác minh. Nếu cài lỗi giữa chừng hoặc integrity check không qua, giữ log và kiểm tra các file cụ thể; không dùng lệnh xóa chung thư mục Canon.

## Kết quả nghiệm thu ngày 2026-10-08

| Hạng mục | Bằng chứng |
|---|---|
| Bộ cài nền đã kiểm | 0.2.4: 12.210.325 byte; một profile 2900, runtime riêng; 9 kiểm thử tự động đạt; binary giống từng byte với 0.2.3 |
| In thực | Một A4 BEFORE OEM với toner save trên 0.2.1; một A4 AFTER OEM từ Preview trên 0.2.2. Người dùng xác nhận đúng cả hai. 0.2.2 giữ nguyên từng byte 727 file payload đã có; chỉ bổ sung CAPTUIKit cho PDE |
| Utility | Ready, hết giấy, mở nắp, mất USB/tự kết nối lại, Pause/Resume/Cancel đạt; các job kiểm tra đã hủy khi khay trống |
| Cài thủ công 0.2.4 | Đã phát hiện queue USB trực tiếp làm Utility crash; chuyển sang kết nối CAPT và khởi động dịch vụ bằng helper thì nút Open Printer Utility mở đúng ứng dụng, Ready to Print; không in thêm |
| Tự mở Utility | 0.2.3: kênh riêng mở đúng một Utility, hai lần thông báo khi OEM cùng chạy; không mở thêm Utility gốc, không crash mới; không dùng giấy |
| Print Center | Pause/resume queue, Remove Job trước bàn giao và mở đúng Utility riêng đạt |
| Tùy chọn Canon | Finishing/Details/Advanced, Paper Source, Quality/Toner, Color brightness/contrast, About 10.0.10 mở được. Tiến trình macOS nạp bốn PDE và CAPTUIKit từ cây riêng |
| Cài chung | Cài lại Canon V10.0.10 gốc thành công; runtime riêng và các queue được giữ, in tiếp được |
| Vòng đời | Helper gỡ runtime/receipt/listener riêng trên hệ thống thật rồi cài lại thành công, giữ file Canon gốc và các queue khác/default. 0.2.2 bổ sung framework được kiểm gỡ trong root thử |

LBP2900B, Intel, máy sạch chưa từng cài Canon, logout/reboot toàn máy, Cleaning, kẹt giấy, mọi tùy chọn trên giấy và chạy dài còn cần nghiệm thu riêng. Không cố tạo kẹt giấy. Lượt hiện tại đã dùng đúng 2/2 tờ được phép; lượt patch-only trước đó dùng 4 tờ riêng. Chưa có Developer ID/notarization, nhưng gói đã cài và chạy cục bộ mà không thay đổi SIP/Gatekeeper.

Chi tiết phiên thử và lỗi đã sửa: [phạm vi kiểm tra công khai](verification.md). Các log máy và serial chỉ nằm trong `artifacts/` bị Git bỏ qua.

## Cài đè từ v27.3.1

Preinstall dùng manifest/checksum và danh sách file để nhận diện bản dự án nguyên vẹn. Từ chối file lạ, file đã sửa và job CUPS chưa hoàn tất. Lưu danh sách file cũ, queue/trạng thái IPP và các phiên chạy LaunchAgent trong thư mục root-only `/Library/Application Support/CanonLBP2900InstallState`; tạm dừng queue và tiến trình riêng trước khi PackageKit thay file. Không thay PPD đang dùng, URI, máy in mặc định hoặc tùy chọn queue.

Postinstall kiểm payload mới, dọn các file của bản cũ không còn trong payload, khởi động lại các phiên dịch vụ còn đăng nhập và phục hồi queue vốn đang chạy; queue vốn tạm dừng vẫn tạm dừng. Nếu không còn queue riêng thì chạy nhận diện USB như cài mới. File Canon gốc và Epson nằm ngoài đường dẫn sở hữu.

Nếu cài bị gián đoạn, chạy lại PKG. Gói chỉ phục hồi trạng thái đã lưu khi integrity của bản đang có đạt; payload không nguyên vẹn cần kiểm tra log trước, không tự xóa thư mục Canon. Cần hoàn tất/hủy job trong Canon Utility kể cả job đã bàn giao khỏi CUPS.
