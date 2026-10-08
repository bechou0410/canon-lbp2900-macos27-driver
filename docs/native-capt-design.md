# Thiết kế native CAPT

Tài liệu này mô tả **patch-only 0.1.0**. Với bộ cài tích hợp runtime riêng, xem [driver LBP2900/2900B CAPT](standalone-capt.md).

## Phạm vi

Dùng driver và tiện ích Canon V10.0.10 English, mục tiêu LBP2900/2900B qua USB trên Apple Silicon/macOS 27.2. Không dùng lại `rastertocapt`. Chưa tuyên bố đủ chức năng khi chưa qua [kiểm thử thiết bị](native-capt-acceptance.md).

Luồng dự kiến: ứng dụng → PDF → Canon `capdftopdl`/`libcaptfilter2` → backend `cnbma2` → CCPD → monitor `captmonlbp2900` → USB. Canon StatusMonitor đọc dịch vụ trạng thái của cùng runtime; BackGrounder tiếp tục chạy.

## Thay đổi có giới hạn

`package/capt-patch` tạo bản sao riêng của `Bidi/captmoncnab3`. Trong mỗi slice arm64/x86_64, thay duy nhất chuỗi độc lập `MDL:LBP3000;` thành `MDL:LBP2900;`. Không thay chuỗi tên một cách hàng loạt và không sửa mã lệnh. Bản sao được ký ad-hoc để chạy trên Apple Silicon; chữ ký này không phải chứng nhận của Canon/Apple.

Nguồn V10.0.10 đã kiểm chứng có chuỗi này trong bảng `_ModelInfo`; `_CheckDeviceId` so chuỗi với device ID đọc từ máy in và từ chối khi không khớp. Trên arm64, bảng ở `0x100048b00` trỏ tới `0x100041cb9`; chuỗi bắt đầu tại file offset `0xa9cb9` (x86_64: `0x45d3e`). Đây là bằng chứng cho sửa nhận diện, **không chứng minh toàn bộ giao thức LBP3000 tương thích LBP2900**.

PPD mới giữ nguyên `cupsModelNumber`, `CNTblModel`, `CNPrinterName`, `CNOEFLibName`, recipe, mọi tùy chọn in, PDE và `APPrinterUtilityPath`. Chỉ đổi tên hiển thị/nhận diện PPD, tốc độ khai báo và tên monitor. Giữ `CNPrinterName=Canon LBP3000` có chủ đích để utility dùng đúng profile và tài nguyên Canon. Giao diện có thể vẫn hiện LBP3000 ở một số nơi.

Các file Canon gốc không bị ghi đè. Build PKG chỉ đóng gói script/checksum, không đóng gói file Canon. Manifest được sinh từ payload chính thức đã xác minh, kiểm tra đủ runtime trước khi áp dụng. Reapply hoặc remove từ chối file patch không rõ nguồn hoặc đã bị chỉnh sửa. Lỗi trong bước xuất cặp file khôi phục cặp đã có trước đó.

## Nguồn và kiểm chứng

Nguồn công khai: [Canon Việt Nam V10.0.10](https://vn.canon/en/support/0101321320). URL/checksum/signer và các hash mốc thuộc `config/canon-capt-10.0.10.json`; không sao chép chúng sang tài liệu.

`tools/capt-project.py` kiểm tra SHA-256 DMG, signer Canon, kết quả notarization, rồi giải nén lại từ package. Driver gốc được giữ trong `artifacts/canon-source/MacOSX/` để cài bằng Installer riêng và xem license thật. Không có nested installer trong script PKG.

Kiểm thử thực với payload gốc nằm ở `tests/native-patch-test.py`. Kiểm tra mã lệnh hai kiến trúc không đổi, mọi file gốc giữ nguyên byte, hợp đồng PPD còn đủ, checksum/version guard, reapply/remove và render PDF bằng filter Canon. Không kết nối máy in trong bộ kiểm thử này.

## Chẩn đoán cần phân biệt

- `STATE: -com.canon.unsupportedsize-error` xóa cờ lỗi; dấu `+` mới đặt cờ lỗi. Không dùng dòng dấu `-` để kết luận driver không hoạt động.
- PPD gốc có `Resolution=600`, bị `cupstestppd` báo không đúng tên lựa chọn Adobe; patch giữ hợp đồng tùy chọn này. Chấp nhận đúng một lỗi baseline đó, từ chối lỗi khác. Các cảnh báo tên khổ giấy của PPD gốc vẫn được ghi nhận.
- Chạy `cupstestppd` trên hệ thống thật không truyền `-R /` vì nó tạo đường dẫn `//Library` và báo sai capitalization. Giữ `-R` cho root giải nén. Apple CUPS dùng `LANG` khi có biến `SOFTWARE`; script đặt định danh caller và locale chỉ trong tiến trình của mình để phân tích diagnostic ổn định. Căn cứ: [mã nguồn Apple CUPS](https://github.com/apple/cups/blob/master/cups/language.c).
- Trên root thử nghiệm thuộc người dùng, bỏ phép kiểm quyền root của các filter. Khi cài vào `/`, vẫn kiểm quyền tài nguyên CUPS đầy đủ. Hash/presence và chữ ký vẫn kiểm trong cả hai trường hợp.
- Launcher Canon không xử lý `CNDriverRootPath` có dấu cách trong phép thử relocation. Render dùng extraction không có dấu cách; cài thật giữ đúng đường dẫn Canon chuẩn.
- Native filter có thể trả exit 0 khi launcher lỗi. Kiểm thử còn yêu cầu dữ liệu đầu ra thực và không có `execv() error`.

## Giới hạn

CCPD đã nạp monitor mới trên arm64; một trang A4 đã ra giấy đúng theo xác nhận người dùng. Utility đã phản ánh Ready, Printing, Out of Paper và Top Cover Open; nút Cancel Job đã hủy job hết giấy. Xem [ma trận nghiệm thu](native-capt-acceptance.md) cho các phần còn lại.

Backend Canon chuyển job sang CCPD rồi kết thúc job CUPS trước khi giấy ra hết. Canon Utility quản lý trạng thái và điều khiển job sau bước bàn giao; Print Center vẫn dùng được để tạm dừng hoặc hủy job còn trong CUPS. Không thay cơ chế này bằng backend khác.

Chưa thử Intel hoặc biến thể LBP2900B riêng biệt. Không gắn nhãn stable/full-feature trước khi có bằng chứng đủ cho từng chức năng.
